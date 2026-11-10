import sys
import unittest
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))


from engine.memory import MemoryStore
from engine.models import NPCState
from engine.rules import (
    apply_deltas,
    clamp_delta,
    clamp_stat,
    determine_ending,
    gate_action,
    gate_intent,
    validate_proposal,
)


def states(trust=50, fear=30, debt=0, overrides=None):
    data = {npc: {"trust": trust, "fear": fear, "debt": debt} for npc in ("sailor", "girl", "oldman")}
    for npc, values in (overrides or {}).items():
        data[npc].update(values)
    return {npc: NPCState(**values) for npc, values in data.items()}


class TestClampDelta(unittest.TestCase):
    def test_min_boundary(self):
        self.assertEqual(clamp_delta(-10), -10)

    def test_max_boundary(self):
        self.assertEqual(clamp_delta(10), 10)

    def test_below_min(self):
        self.assertEqual(clamp_delta(-11), -10)

    def test_above_max(self):
        self.assertEqual(clamp_delta(11), 10)

    def test_zero(self):
        self.assertEqual(clamp_delta(0), 0)

    def test_extreme_low(self):
        self.assertEqual(clamp_delta(-999), -10)

    def test_extreme_high(self):
        self.assertEqual(clamp_delta(999), 10)

    def test_negative_one(self):
        self.assertEqual(clamp_delta(-1), -1)

    def test_reject_float(self):
        with self.assertRaises(TypeError):
            clamp_delta(3.5)

    def test_reject_string(self):
        with self.assertRaises(TypeError):
            clamp_delta("3")

    def test_reject_bool(self):
        with self.assertRaises(TypeError):
            clamp_delta(True)

    def test_reject_none(self):
        with self.assertRaises(TypeError):
            clamp_delta(None)


class TestClampStat(unittest.TestCase):
    def test_zero(self):
        self.assertEqual(clamp_stat(0), 0)

    def test_hundred(self):
        self.assertEqual(clamp_stat(100), 100)

    def test_negative(self):
        self.assertEqual(clamp_stat(-5), 0)

    def test_over(self):
        self.assertEqual(clamp_stat(105), 100)

    def test_normal(self):
        self.assertEqual(clamp_stat(37), 37)


class TestApplyDeltas(unittest.TestCase):
    def test_basic(self):
        state = NPCState(trust=50, fear=30, debt=0)
        applied = apply_deltas(state, {"trust": 5, "fear": -10, "debt": 4})
        self.assertEqual((state.trust, state.fear, state.debt), (55, 20, 4))
        self.assertEqual(applied, {"trust": 5, "fear": -10, "debt": 4})

    def test_upper_clamp(self):
        state = NPCState(trust=98, fear=0, debt=0)
        applied = apply_deltas(state, {"trust": 10})
        self.assertEqual(applied["trust"], 2)
        self.assertEqual(state.trust, 100)

    def test_lower_clamp(self):
        state = NPCState(trust=50, fear=3, debt=0)
        applied = apply_deltas(state, {"fear": -10})
        self.assertEqual(applied["fear"], -3)
        self.assertEqual(state.fear, 0)

    def test_unknown_key_ignored(self):
        state = NPCState()
        applied = apply_deltas(state, {"luck": 5})
        self.assertEqual(applied, {})

    def test_empty(self):
        state = NPCState()
        self.assertEqual(apply_deltas(state, {}), {})

    def test_multi_large_delta_clamped(self):
        state = NPCState(trust=0, fear=100, debt=50)
        apply_deltas(state, {"trust": 10, "fear": -10})
        self.assertEqual((state.trust, state.fear), (10, 90))


class TestGateIntent(unittest.TestCase):
    def test_fear_exactly_70_allows(self):
        ok, _ = gate_intent(NPCState(fear=70), "reveal")
        self.assertTrue(ok)

    def test_fear_71_blocks_reveal(self):
        ok, reason = gate_intent(NPCState(fear=71), "reveal")
        self.assertFalse(ok)
        self.assertIn("恐惧", reason)

    def test_fear_71_blocks_bargain(self):
        ok, _ = gate_intent(NPCState(fear=71), "bargain")
        self.assertFalse(ok)

    def test_fear_71_allows_silent(self):
        ok, _ = gate_intent(NPCState(fear=71), "silent")
        self.assertTrue(ok)

    def test_debt_60_blocks_deflect(self):
        ok, reason = gate_intent(NPCState(debt=60), "deflect")
        self.assertFalse(ok)
        self.assertIn("真话", reason)

    def test_debt_59_allows_deflect(self):
        ok, _ = gate_intent(NPCState(debt=59), "deflect")
        self.assertTrue(ok)

    def test_debt_60_allows_reveal(self):
        ok, _ = gate_intent(NPCState(debt=60), "reveal")
        self.assertTrue(ok)

    def test_unknown_intent(self):
        ok, _ = gate_intent(NPCState(), "fly")
        self.assertFalse(ok)

    def test_normal(self):
        ok, reason = gate_intent(NPCState(), "reveal")
        self.assertTrue(ok)
        self.assertEqual(reason, "")


class TestGateAction(unittest.TestCase):
    def test_trust_39_refuses_key(self):
        ok, reason = gate_action(NPCState(trust=39), "take_key")
        self.assertFalse(ok)
        self.assertIn("钥匙", reason)

    def test_trust_40_allows_key(self):
        ok, _ = gate_action(NPCState(trust=40), "take_key")
        self.assertTrue(ok)

    def test_unrelated_action(self):
        ok, _ = gate_action(NPCState(trust=0), "give_bread")
        self.assertTrue(ok)


class TestDetermineEnding(unittest.TestCase):
    def test_catastrophe_boundary_14(self):
        s = states(overrides={"girl": {"trust": 14}})
        self.assertEqual(determine_ending(s, set(), 0), "第七夜")

    def test_catastrophe_boundary_15_not_catastrophe(self):
        s = states(overrides={"girl": {"trust": 15}, "oldman": {"trust": 60}})
        self.assertEqual(determine_ending(s, {"truth"}, 0), "守灯")

    def test_key_boundary_59_falls_through(self):
        s = states(overrides={"sailor": {"trust": 59}, "oldman": {"trust": 60}})
        self.assertEqual(determine_ending(s, {"key", "truth"}, 0), "守灯")

    def test_key_boundary_60(self):
        s = states(overrides={"sailor": {"trust": 60}, "oldman": {"trust": 20}})
        self.assertEqual(determine_ending(s, {"key"}, 0), "钥匙")

    def test_key_requires_flag(self):
        s = states(overrides={"sailor": {"trust": 90}, "oldman": {"trust": 20}})
        self.assertEqual(determine_ending(s, set(), 0), "第七夜")

    def test_boat_requires_given_two(self):
        s = states(trust=50)
        self.assertEqual(determine_ending(s, set(), 1), "第七夜")

    def test_boat_with_two_gifts(self):
        s = states(trust=50)
        self.assertEqual(determine_ending(s, set(), 2), "同舟")

    def test_boat_boundary_49(self):
        s = states(trust=50, overrides={"girl": {"trust": 49}})
        self.assertEqual(determine_ending(s, set(), 5), "第七夜")

    def test_lamp_boundary_54(self):
        s = states(trust=30, overrides={"oldman": {"trust": 54}})
        self.assertEqual(determine_ending(s, {"truth"}, 0), "第七夜")

    def test_lamp_boundary_55(self):
        s = states(trust=30, overrides={"oldman": {"trust": 55}})
        self.assertEqual(determine_ending(s, {"truth"}, 0), "守灯")

    def test_lamp_requires_flag(self):
        s = states(trust=30, overrides={"oldman": {"trust": 90}})
        self.assertEqual(determine_ending(s, set(), 0), "第七夜")

    def test_key_precedes_boat(self):
        s = states(trust=60, overrides={"sailor": {"trust": 80}})
        self.assertEqual(determine_ending(s, {"key"}, 3), "钥匙")

    def test_catastrophe_precedes_all(self):
        s = states(trust=80, overrides={"oldman": {"trust": 10}})
        self.assertEqual(determine_ending(s, {"key", "truth"}, 3), "第七夜")


class TestValidateProposal(unittest.TestCase):
    def valid(self):
        return {
            "reply": "好。",
            "deltas": {"trust": 5, "fear": -3, "debt": 0},
            "memory_writes": [{"who": "sailor", "type": "promise", "text": "答应带他上船"}],
            "intent": "bargain",
        }

    def test_valid(self):
        ok, errors = validate_proposal(self.valid())
        self.assertTrue(ok)
        self.assertEqual(errors, [])

    def test_not_dict(self):
        ok, _ = validate_proposal(["x"])
        self.assertFalse(ok)

    def test_missing_reply(self):
        data = self.valid()
        del data["reply"]
        ok, _ = validate_proposal(data)
        self.assertFalse(ok)

    def test_reply_too_long(self):
        data = self.valid()
        data["reply"] = "字" * 121
        ok, _ = validate_proposal(data)
        self.assertFalse(ok)

    def test_delta_out_of_range(self):
        data = self.valid()
        data["deltas"] = {"trust": 11}
        ok, errors = validate_proposal(data)
        self.assertFalse(ok)
        self.assertTrue(any("超出" in e for e in errors))

    def test_delta_not_int(self):
        data = self.valid()
        data["deltas"] = {"trust": 1.5}
        ok, _ = validate_proposal(data)
        self.assertFalse(ok)

    def test_unknown_delta_key(self):
        data = self.valid()
        data["deltas"] = {"luck": 1}
        ok, _ = validate_proposal(data)
        self.assertFalse(ok)

    def test_bad_intent(self):
        data = self.valid()
        data["intent"] = "fly"
        ok, _ = validate_proposal(data)
        self.assertFalse(ok)

    def test_memory_who_invalid(self):
        data = self.valid()
        data["memory_writes"] = [{"who": "ghost", "type": "promise", "text": "x"}]
        ok, _ = validate_proposal(data)
        self.assertFalse(ok)

    def test_memory_not_list(self):
        data = self.valid()
        data["memory_writes"] = {"who": "sailor"}
        ok, _ = validate_proposal(data)
        self.assertFalse(ok)

    def test_empty_memory_ok(self):
        data = self.valid()
        data["memory_writes"] = []
        ok, _ = validate_proposal(data)
        self.assertTrue(ok)


class TestMemoryStore(unittest.TestCase):
    def test_retrieve_prefers_same_npc(self):
        store = MemoryStore()
        store.add("sailor", "promise", "答应给面包", 1)
        store.add("girl", "secret", "答应了面包", 2)
        got = store.retrieve("sailor", "面包", 3)
        self.assertEqual(got[0].who, "sailor")

    def test_retrieve_limit(self):
        store = MemoryStore()
        for i in range(10):
            store.add("sailor", "gift", f"第{i}次给东西", i + 1)
        self.assertEqual(len(store.retrieve("sailor", "东西", 11, k=6)), 6)

    def test_retrieve_empty(self):
        store = MemoryStore()
        self.assertEqual(store.retrieve("sailor", "面包", 1), [])


if __name__ == "__main__":
    unittest.main()


class TestParseJsonContent(unittest.TestCase):
    def test_plain(self):
        from engine.providers import parse_json_content

        self.assertEqual(parse_json_content('{"a":1}'), {"a": 1})

    def test_code_fence(self):
        from engine.providers import parse_json_content

        self.assertEqual(parse_json_content('```json\n{"a":1}\n```'), {"a": 1})

    def test_surrounding_text(self):
        from engine.providers import parse_json_content

        self.assertEqual(parse_json_content('好的：{"a":1} 以上'), {"a": 1})

    def test_no_json(self):
        from engine.providers import ProviderError, parse_json_content

        with self.assertRaises(ProviderError):
            parse_json_content("没有对象")

    def test_non_dict(self):
        from engine.providers import ProviderError, parse_json_content

        with self.assertRaises(ProviderError):
            parse_json_content("[1,2]")

    def test_broken_json(self):
        from engine.providers import ProviderError, parse_json_content

        with self.assertRaises(ProviderError):
            parse_json_content('{"a":}')
