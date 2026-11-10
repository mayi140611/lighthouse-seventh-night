from .script import (
    DEMO_ROUTES,
    KEYWORD_INTENTS,
    KEYWORD_TARGETS,
    NPC_PROFILES,
    ROUTE_ACTIONS,
)

class ScriptedProvider:
    def __init__(self, route: str | None = None) -> None:
        self.route = route
        self.turn_no = 0

    def reset(self) -> None:
        self.turn_no = 0

    def propose(self, npc, player_input, state, memories, strict=False):
        if not strict:
            self.turn_no += 1
        if self.route:
            return self._route_proposal()
        return self._keyword_proposal(npc, player_input)

    def _route_proposal(self) -> dict:
        route = DEMO_ROUTES[self.route]
        if self.turn_no > len(route):
            return {
                "reply": "（远处传来汽笛声。）",
                "deltas": {"trust": 0, "fear": 0, "debt": 0},
                "memory_writes": [],
                "intent": "silent",
            }
        npc, _player_text, reply, deltas, intent, writes = route[self.turn_no - 1]
        return {
            "reply": reply,
            "npc": npc,
            "deltas": deltas,
            "memory_writes": writes,
            "intent": intent,
            "action": ROUTE_ACTIONS.get(self.route, {}).get(self.turn_no),
            "memory_refs": self._route_memory_refs(),
        }

    def _route_memory_refs(self) -> list[str]:
        if self.turn_no <= 3:
            return []
        refs = []
        for entry in DEMO_ROUTES[self.route][: self.turn_no - 1]:
            refs.extend(w["text"] for w in entry[5])
        return refs[:3]

    def _keyword_proposal(self, npc: str, player_input: str) -> dict:
        target = npc
        for word, key in KEYWORD_TARGETS.items():
            if word in player_input:
                target = key
                break
        intent = "bargain"
        for word, value in KEYWORD_INTENTS.items():
            if word in player_input:
                intent = value
                break
        if intent in ("threaten",):
            deltas = {"trust": -8, "fear": 8, "debt": 0}
            writes = [{"who": target, "type": "threat", "text": player_input[:40]}]
        elif intent == "reveal":
            deltas = {"trust": 5, "fear": 2, "debt": 0}
            writes = [{"who": target, "type": "secret", "text": player_input[:40]}]
        elif intent == "deflect":
            deltas = {"trust": -2, "fear": 2, "debt": 0}
            writes = []
        elif intent == "silent":
            deltas = {"trust": 0, "fear": -2, "debt": 0}
            writes = []
        elif any(word in player_input for word in ("给", "面包", "干柴", "绷带", "答应")):
            deltas = {"trust": 8, "fear": -2, "debt": 2}
            writes = [{"who": target, "type": "gift", "text": player_input[:40]}]
        else:
            deltas = {"trust": 3, "fear": 0, "debt": 0}
            writes = []
        fallback = NPC_PROFILES[target]["fallbacks"][
            (self.turn_no - 1) % len(NPC_PROFILES[target]["fallbacks"])
        ]
        return {
            "reply": f"{fallback} {player_input[:24]}",
            "npc": target,
            "deltas": deltas,
            "memory_writes": writes,
            "intent": intent,
            "memory_refs": [],
        }


class InvalidProvider:
    def __init__(self, mode: str = "always") -> None:
        self.mode = mode
        self.calls = 0

    def propose(self, npc, player_input, state, memories, strict=False):
        self.calls += 1
        if self.mode == "always":
            return {"reply": "x", "deltas": {"trust": 99}, "intent": "fly"}
        if self.mode == "once" and self.calls == 1:
            return {"reply": "x", "deltas": {"trust": 99}, "intent": "fly"}
        return {
            "reply": "（恢复。）",
            "deltas": {"trust": 1, "fear": 0, "debt": 0},
            "memory_writes": [],
            "intent": "silent",
        }
