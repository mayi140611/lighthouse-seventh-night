import json
import tempfile
import sys
import unittest
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))

from pathlib import Path

from engine.game import GameSession, load_previous_run
from engine.providers import InvalidProvider, ScriptedProvider
from engine.script import DEMO_ROUTES

ROUTE_EXPECT = {"boat": "同舟", "lamp": "守灯", "key": "钥匙", "night": "第七夜"}


class TestRoutes(unittest.TestCase):
    def test_each_route_reaches_expected_ending(self):
        for route, expect in ROUTE_EXPECT.items():
            with self.subTest(route=route):
                session = GameSession(ScriptedProvider(route=route))
                for npc, text, *_rest in DEMO_ROUTES[route]:
                    session.turn(text, npc=npc)
                    if session.finished:
                        break
                session.finish()
                self.assertEqual(session.ending, expect)

    def test_key_route_sets_key_flag(self):
        session = GameSession(ScriptedProvider(route="key"))
        for npc, text, *_rest in DEMO_ROUTES["key"]:
            session.turn(text, npc=npc)
        session.finish()
        self.assertIn("key", session.flags)

    def test_key_action_rejected_below_trust(self):
        class TakeKeyProvider:
            def propose(self, npc, player_input, state, memories, strict=False):
                return {
                    "reply": "钥匙在这儿。",
                    "deltas": {"trust": 0, "fear": 0, "debt": 0},
                    "memory_writes": [],
                    "intent": "reveal",
                    "action": "take_key",
                }

        session = GameSession(TakeKeyProvider())
        result = session.turn("钥匙给我", npc="sailor")
        self.assertNotIn("key", session.flags)
        self.assertIn("信任不足", result.gate_reason)

    def test_boat_route_requires_two_gifts(self):
        session = GameSession(ScriptedProvider(route="boat"))
        for npc, text, *_rest in DEMO_ROUTES["boat"]:
            session.turn(text, npc=npc)
        session.finish()
        self.assertGreaterEqual(session.given_count, 2)

    def test_night_route_hits_catastrophe(self):
        session = GameSession(ScriptedProvider(route="night"))
        for npc, text, *_rest in DEMO_ROUTES["night"]:
            session.turn(text, npc=npc)
        session.finish()
        self.assertEqual(session.ending, "第七夜")

    def test_no_turn_after_finish(self):
        session = GameSession(ScriptedProvider(route="night"))
        for npc, text, *_rest in DEMO_ROUTES["night"]:
            session.turn(text, npc=npc)
        session.finish()
        result = session.turn("还要说", npc="sailor")
        self.assertFalse(result.ok)
        self.assertEqual(result.ending, "第七夜")


class TestFallback(unittest.TestCase):
    def test_invalid_provider_falls_back(self):
        provider = InvalidProvider("always")
        session = GameSession(provider)
        result = session.turn("你好", npc="sailor")
        self.assertTrue(result.fallback)
        self.assertTrue(result.validation_errors)
        self.assertTrue(all(v == 0 for v in result.applied_deltas.values()))
        self.assertEqual(provider.calls, 2)

    def test_invalid_once_recovers(self):
        provider = InvalidProvider("once")
        session = GameSession(provider)
        result = session.turn("你好", npc="sailor")
        self.assertFalse(result.fallback)
        self.assertEqual(result.applied_deltas.get("trust"), 1)

    def test_gate_rejects_intent_and_keeps_state(self):
        session = GameSession(ScriptedProvider())
        session.states["sailor"].fear = 80
        result = session.turn("我给你面包", npc="sailor")
        self.assertTrue(result.rejected_intent)
        self.assertIn("恐惧", result.gate_reason)
        self.assertTrue(all(v == 0 for v in result.applied_deltas.values()))


class TestSaveAndPreviousRun(unittest.TestCase):
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ending.json"
            session = GameSession(ScriptedProvider(route="key"), save_path=str(path))
            for npc, text, *_rest in DEMO_ROUTES["key"]:
                session.turn(text, npc=npc)
            session.finish()
            self.assertTrue(path.exists())
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(data["ending"], "钥匙")
            self.assertIn("key", data["flags"])

    def test_previous_run_seeds_memory_and_trust(self):
        previous = {
            "ending": "钥匙",
            "key_npc": "sailor",
            "key_action": "给过面包",
            "memories": [{"who": "sailor", "type": "gift", "text": "给过面包"}],
        }
        session = GameSession(ScriptedProvider(route="lamp"), previous_run=previous)
        self.assertEqual(session.states["sailor"].trust, 40)
        self.assertTrue(any(e.type == "previous_run" for e in session.memory.entries))

    def test_load_previous_run_missing_file(self):
        self.assertIsNone(load_previous_run("/tmp/definitely-not-exists-xyz.json"))

    def test_load_previous_run_bad_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{not json", encoding="utf-8")
            self.assertIsNone(load_previous_run(str(path)))


class TestPanel(unittest.TestCase):
    def test_panel_shape(self):
        session = GameSession(ScriptedProvider())
        panel = session.panel()
        self.assertEqual(set(panel["states"]), {"sailor", "girl", "oldman"})
        self.assertEqual(panel["turn"], 0)
        self.assertIsNone(panel["ending"])


if __name__ == "__main__":
    unittest.main()
