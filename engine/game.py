import json
import time
from pathlib import Path

from .memory import MemoryStore
from .models import NPC_KEYS, NPCState, TurnResult
from .rules import (
    CATASTROPHE_TRUST,
    INTENTS,
    apply_deltas,
    determine_ending,
    gate_action,
    gate_intent,
    validate_proposal,
)
from .script import NPC_PROFILES, START_STATE


def load_previous_run(path) -> dict | None:
    if not path:
        return None
    file_path = Path(path)
    if not file_path.exists():
        return None
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


class GameSession:
    def __init__(self, provider, save_path=None, previous_run=None) -> None:
        self.provider = provider
        self.save_path = save_path
        self.previous_run = previous_run
        self.states = {npc: NPCState(**START_STATE[npc]) for npc in NPC_KEYS}
        self.flags: set[str] = set()
        self.memory = MemoryStore()
        self.turn_no = 0
        self.npc_turns = {npc: 0 for npc in NPC_KEYS}
        self.given_count = 0
        self.given_resources: set[str] = set()
        self.ending: str | None = None
        self.max_turns = 24
        self.history: list[dict] = []
        self.memory_reference_count = 0
        if previous_run:
            self._seed_previous(previous_run)

    def _seed_previous(self, previous: dict) -> None:
        ending = previous.get("ending")
        key_npc = previous.get("key_npc")
        if key_npc in NPC_KEYS:
            self.memory.add(
                who=key_npc,
                type_="previous_run",
                text=f"上一局你{previous.get('key_action', '帮过我')}，结局是「{ending}」",
                turn=0,
            )
            self.states[key_npc].trust = min(100, self.states[key_npc].trust + 5)
        for item in previous.get("memories", [])[:6]:
            if item.get("who") in NPC_KEYS:
                self.memory.add(
                    who=item["who"],
                    type_=item.get("type", "previous"),
                    text=item.get("text", ""),
                    turn=0,
                )

    @property
    def finished(self) -> bool:
        return self.ending is not None

    def finish(self) -> str:
        if self.ending is None:
            self.ending = determine_ending(self.states, self.flags, self.given_count)
            self._save()
        return self.ending

    def _implicit_action(self, target: str, intent: str, player_input: str) -> str | None:
        text = player_input or ""
        if target == "sailor" and intent in ("reveal", "bargain", "threaten"):
            if any(word in text for word in ("钥匙", "开门", "救生艇")):
                return "take_key"
        if target == "oldman" and intent in ("reveal", "bargain"):
            if any(word in text for word in ("真相", "第七夜", "灯下", "灯芯")):
                return "learn_truth"
        return None

    def panel(self) -> dict:
        return {
            "turn": self.turn_no,
            "states": {npc: self.states[npc].values() for npc in NPC_KEYS},
            "flags": sorted(self.flags),
            "given_count": self.given_count,
            "ending": self.ending,
        }

    def _fallback(self, npc: str, reason: str, errors: list[str]) -> dict:
        fallbacks = NPC_PROFILES[npc]["fallbacks"]
        reply = fallbacks[self.turn_no % len(fallbacks)]
        return {
            "reply": reply,
            "deltas": {"trust": 0, "fear": 0, "debt": 0},
            "memory_writes": [],
            "intent": "silent",
            "fallback": True,
            "validation_errors": errors + ([reason] if reason else []),
        }

    def turn(self, player_input: str, npc: str = "sailor") -> TurnResult:
        if self.finished:
            return TurnResult(
                ok=False,
                npc=npc,
                reply="本局已结束。",
                intent="silent",
                ending=self.ending,
            )
        self.turn_no += 1
        memories = self.memory.retrieve(npc, player_input, self.turn_no)
        errors: list[str] = []
        try:
            proposal = self.provider.propose(npc, player_input, self.states[npc], memories, False)
            ok, errors = validate_proposal(proposal)
            if not ok:
                proposal = self.provider.propose(npc, player_input, self.states[npc], memories, True)
                ok, errors = validate_proposal(proposal)
        except Exception as exc:
            ok, errors = False, [f"provider 异常: {type(exc).__name__}: {exc}"]
            proposal = {}
        if not ok:
            proposal = self._fallback(npc, "结构校验两次失败" if not errors else "", errors)
        else:
            proposal.setdefault("fallback", False)
            proposal.setdefault("validation_errors", [])

        target = proposal.get("npc") if proposal.get("npc") in NPC_KEYS else npc
        if target not in NPC_KEYS:
            target = npc
        intent = proposal.get("intent", "silent")
        if intent not in INTENTS:
            intent = "silent"

        allowed, gate_reason = gate_intent(self.states[target], intent)
        applied: dict[str, int] = {}
        rejected_intent = False
        writes = proposal.get("memory_writes") or []
        if allowed:
            applied = apply_deltas(self.states[target], proposal.get("deltas") or {})
        else:
            rejected_intent = True
            writes = []

        action = proposal.get("action") or self._implicit_action(target, intent, player_input)
        action_note = ""
        if action:
            action_ok, action_reason = gate_action(self.states[target], action)
            if action_ok:
                if action in ("give_key", "take_key"):
                    self.flags.add("key")
                elif action == "learn_truth":
                    self.flags.add("truth")
                action_note = f"动作 {action} 生效"
            else:
                action_note = f"动作 {action} 被拒：{action_reason}"

        added = self.memory.add_many(writes, self.turn_no)
        for entry in added:
            if entry.type == "gift":
                resource = next((w for w in ("面包", "干柴", "绷带") if w in entry.text), entry.text[:8])
                self.given_resources.add(resource)
        if intent != "threaten":
            for resource in ("面包", "干柴", "绷带"):
                if resource in player_input and resource not in self.given_resources:
                    self.memory.add(target, "gift", f"给过{NPC_PROFILES[target]['name']}{resource}", self.turn_no)
                    self.given_resources.add(resource)
        self.given_count = len(self.given_resources)
        self.npc_turns[target] += 1

        refs = [e.text for e in memories if e.text and e.text[:8] in (proposal.get("reply") or "")]
        declared_refs = proposal.get("memory_refs") or []
        if declared_refs:
            refs = list(dict.fromkeys(declared_refs + refs))
        if refs:
            self.memory_reference_count += 1

        catastrophe = any(state.trust < CATASTROPHE_TRUST for state in self.states.values())
        computed = determine_ending(self.states, self.flags, self.given_count)
        if catastrophe:
            self.ending = "第七夜"
        elif computed != "第七夜":
            self.ending = computed
        elif self.turn_no >= self.max_turns:
            self.ending = "第七夜"
        result = TurnResult(
            ok=True,
            npc=target,
            reply=proposal.get("reply", ""),
            intent=intent,
            proposed_deltas=proposal.get("deltas") or {},
            applied_deltas=applied,
            gate_reason=" ; ".join(x for x in (gate_reason, action_note) if x),
            rejected_intent=rejected_intent,
            memory_refs=refs,
            fallback=bool(proposal.get("fallback")),
            validation_errors=list(proposal.get("validation_errors") or []),
            ending=self.ending,
        )
        self.history.append(
            {
                "turn": self.turn_no,
                "npc": target,
                "input": player_input,
                "result": result.as_dict(),
            }
        )
        if self.ending:
            self._save()
        return result

    def _save(self) -> None:
        if not self.save_path:
            return
        payload = {
            "ts": int(time.time()),
            "ending": self.ending,
            "flags": sorted(self.flags),
            "given_count": self.given_count,
            "states": {npc: self.states[npc].values() for npc in NPC_KEYS},
            "key_npc": max(self.npc_turns, key=self.npc_turns.get),
            "key_action": "陪我说了很久",
            "memories": [
                {"who": e.who, "type": e.type, "text": e.text}
                for e in self.memory.entries
                if e.type in ("promise", "gift", "threat", "secret", "truth")
            ][:6],
        }
        Path(self.save_path).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
