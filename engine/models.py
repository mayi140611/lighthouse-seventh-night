from dataclasses import dataclass, field, asdict
from typing import Any

NPC_KEYS = ("sailor", "girl", "oldman")
STAT_KEYS = ("trust", "fear", "debt")


@dataclass
class NPCState:
    trust: int = 30
    fear: int = 30
    debt: int = 0

    def values(self) -> dict[str, int]:
        return {k: getattr(self, k) for k in STAT_KEYS}

    def as_dict(self) -> dict[str, int]:
        return self.values()


@dataclass
class MemoryEntry:
    who: str
    type: str
    text: str
    turn: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TurnResult:
    ok: bool
    npc: str
    reply: str
    intent: str
    proposed_deltas: dict[str, int] = field(default_factory=dict)
    applied_deltas: dict[str, int] = field(default_factory=dict)
    gate_reason: str = ""
    rejected_intent: bool = False
    memory_refs: list[str] = field(default_factory=list)
    fallback: bool = False
    validation_errors: list[str] = field(default_factory=list)
    ending: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
