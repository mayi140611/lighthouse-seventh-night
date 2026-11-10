import os
import uuid
from pathlib import Path

from .game import GameSession
from .providers import ModelScopeProvider, ProviderError, ScriptedProvider
from .script import NPC_PROFILES

ROOT = Path(__file__).resolve().parent.parent
SAVE_DIR = ROOT / "saves"
SECRETS_ENV = ROOT.parent.parent / "secrets" / "modelscope.env"


def load_env(path=None):
    path = Path(path) if path else SECRETS_ENV
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)


def build_provider(kind=None):
    kind = (kind or os.environ.get("LLM_PROVIDER") or "scripted").lower()
    if kind in ("modelscope", "ms", "api"):
        load_env()
        return ModelScopeProvider()
    if kind == "scripted":
        return ScriptedProvider()
    raise ProviderError(f"未知 LLM_PROVIDER: {kind}")


class SessionRegistry:
    def __init__(self, provider_kind=None, save_dir=None):
        self.provider_kind = provider_kind
        self.save_dir = Path(save_dir) if save_dir else SAVE_DIR
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.sessions: dict[str, GameSession] = {}
        self.last_run: dict[str, dict] = {}

    def provider_name(self) -> str:
        return (self.provider_kind or os.environ.get("LLM_PROVIDER") or "scripted").lower()

    def create(self, session_id=None, second_run=False):
        sid = session_id or uuid.uuid4().hex[:12]
        previous = self.last_run.get(sid) if second_run else None
        provider = build_provider(self.provider_kind)
        session = GameSession(
            provider,
            save_path=str(self.save_dir / f"{sid}.json"),
            previous_run=previous,
        )
        self.sessions[sid] = session
        return sid

    def get(self, sid):
        return self.sessions.get(sid)

    def state(self, sid):
        session = self.sessions.get(sid)
        if not session:
            return None
        panel = session.panel()
        panel["npc_names"] = {k: v["name"] for k, v in NPC_PROFILES.items()}
        panel["provider"] = self.provider_name()
        panel["last_latency"] = getattr(session.provider, "last_latency", None)
        return panel

    def turn(self, sid, npc, message):
        session = self.sessions.get(sid)
        if not session:
            return None
        if npc not in NPC_PROFILES:
            npc = "sailor"
        result = session.turn(message, npc=npc)
        payload = result.as_dict()
        payload.update(
            {
                "session_id": sid,
                "turn": session.turn_no,
                "npc_name": NPC_PROFILES[result.npc]["name"],
                "panel": self.state(sid),
                "last_latency": getattr(session.provider, "last_latency", None),
            }
        )
        if session.finished:
            self.last_run[sid] = {
                "ending": session.ending,
                "key_npc": max(session.npc_turns, key=session.npc_turns.get),
                "key_action": "陪我说了很久",
                "memories": [
                    {"who": e.who, "type": e.type, "text": e.text}
                    for e in session.memory.entries
                    if e.type in ("promise", "gift", "threat", "secret", "truth")
                ][:6],
            }
        return payload

    def reset(self, sid, second_run=False):
        if sid in self.sessions:
            self.last_run.setdefault(sid, self.last_run.get(sid, {}))
        return self.create(sid, second_run=second_run)


def anger_check(message: str) -> str:
    text = message or ""
    if any(word in text for word in ("傻", "滚", "闭嘴")):
        return "注意：这局是叙事对局，辱骂不会让 NPC 更快交底。"
    return ""


__all__ = [
    "SessionRegistry",
    "build_provider",
    "load_env",
    "anger_check",
    "NPC_PROFILES",
]
