from .models import NPCState, NPC_KEYS, STAT_KEYS

DELTA_MIN = -10
DELTA_MAX = 10
STAT_MIN = 0
STAT_MAX = 100

INTENTS = ("deflect", "reveal", "threaten", "bargain", "silent")
ENDINGS = ("同舟", "守灯", "钥匙", "第七夜")

REPLY_MAX_LEN = 120

TRUST_REFUSE_KEY = 40
FEAR_SILENCE = 70
DEBT_TRUTH = 60

ALL_TRUST_FOR_BOAT = 50
SAILOR_TRUST_FOR_KEY = 60
OLDMAN_TRUST_FOR_LAMP = 55
CATASTROPHE_TRUST = 15
GIVEN_FOR_BOAT = 2


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def clamp_delta(value) -> int:
    if not _is_int(value):
        raise TypeError(f"delta must be int, got {type(value).__name__}")
    return max(DELTA_MIN, min(DELTA_MAX, value))


def clamp_stat(value) -> int:
    if not _is_int(value):
        raise TypeError(f"stat must be int, got {type(value).__name__}")
    return max(STAT_MIN, min(STAT_MAX, value))


def apply_deltas(state: NPCState, deltas: dict[str, int]) -> dict[str, int]:
    applied: dict[str, int] = {}
    for key, raw in deltas.items():
        if key not in STAT_KEYS:
            continue
        before = getattr(state, key)
        after = clamp_stat(before + clamp_delta(raw))
        setattr(state, key, after)
        applied[key] = after - before
    return applied


def gate_intent(state: NPCState, intent: str) -> tuple[bool, str]:
    if intent not in INTENTS:
        return False, "契约外 intent"
    if state.fear > FEAR_SILENCE and intent != "silent":
        return False, "恐惧封锁：只能沉默"
    if state.debt >= DEBT_TRUTH and intent == "deflect":
        return False, "负债阈值：必须说真话"
    return True, ""


def gate_action(state: NPCState, action: str) -> tuple[bool, str]:
    if action in ("give_key", "take_key") and state.trust < TRUST_REFUSE_KEY:
        return False, "信任不足：拒绝交出钥匙"
    return True, ""


def determine_ending(
    states: dict[str, NPCState],
    flags: set[str],
    given_count: int,
) -> str:
    if any(states[npc].trust < CATASTROPHE_TRUST for npc in NPC_KEYS):
        return "第七夜"
    if states["sailor"].trust >= SAILOR_TRUST_FOR_KEY and "key" in flags:
        return "钥匙"
    if (
        all(states[npc].trust >= ALL_TRUST_FOR_BOAT for npc in NPC_KEYS)
        and given_count >= GIVEN_FOR_BOAT
    ):
        return "同舟"
    if states["oldman"].trust >= OLDMAN_TRUST_FOR_LAMP and "truth" in flags:
        return "守灯"
    return "第七夜"


def validate_proposal(obj) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not isinstance(obj, dict):
        return False, ["proposal 必须是 dict"]

    reply = obj.get("reply")
    if not isinstance(reply, str) or not reply.strip():
        errors.append("reply 必须是非空字符串")
    elif len(reply) > REPLY_MAX_LEN:
        errors.append(f"reply 超过 {REPLY_MAX_LEN} 字")

    deltas = obj.get("deltas")
    if not isinstance(deltas, dict):
        errors.append("deltas 必须是 dict")
    else:
        for key, value in deltas.items():
            if key not in STAT_KEYS:
                errors.append(f"deltas 含未知字段 {key}")
            elif not _is_int(value):
                errors.append(f"deltas.{key} 必须是整数")
            elif not DELTA_MIN <= value <= DELTA_MAX:
                errors.append(f"deltas.{key} 超出 {DELTA_MIN}..{DELTA_MAX}")

    writes = obj.get("memory_writes", [])
    if not isinstance(writes, list):
        errors.append("memory_writes 必须是 list")
    else:
        for item in writes:
            if not isinstance(item, dict):
                errors.append("memory_writes 项必须是 dict")
                continue
            if item.get("who") not in NPC_KEYS:
                errors.append("memory_writes.who 非法")
            if not isinstance(item.get("type"), str) or not item.get("type"):
                errors.append("memory_writes.type 非法")
            if not isinstance(item.get("text"), str) or not item.get("text"):
                errors.append("memory_writes.text 非法")

    intent = obj.get("intent")
    if intent not in INTENTS:
        errors.append("intent 非法")

    return (not errors), errors
