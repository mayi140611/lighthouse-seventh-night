import sys
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.webapp import SessionRegistry, build_provider  # noqa: E402
from server import make_handler  # noqa: E402


class TestRegistry(unittest.TestCase):
    def test_create_and_turn(self):
        registry = SessionRegistry(provider_kind="scripted", save_dir="/tmp/lighthouse_test_saves")
        sid = registry.create()
        result = registry.turn(sid, "sailor", "面包给你，上船带上我。")
        self.assertEqual(result["session_id"], sid)
        self.assertTrue(result["reply"])
        self.assertIn("states", result["panel"])
        self.assertEqual(result["turn"], 1)

    def test_turn_unknown_session(self):
        registry = SessionRegistry(provider_kind="scripted", save_dir="/tmp/lighthouse_test_saves")
        self.assertIsNone(registry.turn("nope", "sailor", "hi"))

    def test_ending_and_second_run(self):
        registry = SessionRegistry(provider_kind="scripted", save_dir="/tmp/lighthouse_test_saves")
        sid = registry.create()
        registry.sessions[sid].states["sailor"].trust = 90
        result = registry.turn(sid, "sailor", "钥匙给我，我只要开门。")
        self.assertEqual(result["ending"], "钥匙")
        self.assertIn(sid, registry.last_run)
        sid2 = registry.reset(sid, second_run=True)
        self.assertEqual(sid2, sid)
        seeded = [e for e in registry.sessions[sid2].memory.entries if e.type == "previous_run"]
        self.assertTrue(seeded)

    def test_provider_factory_default(self):
        import os

        os.environ.pop("LLM_PROVIDER", None)
        self.assertEqual(build_provider("scripted").__class__.__name__, "ScriptedProvider")


class TestHttpServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        registry = SessionRegistry(provider_kind="scripted", save_dir="/tmp/lighthouse_test_saves")
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(registry))
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def _post(self, path, payload):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}",
            data=__import__("json").dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return __import__("json").loads(resp.read().decode())

    def test_index_served(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/", timeout=10) as resp:
            body = resp.read().decode()
        self.assertIn("灯塔第七夜", body)

    def test_session_and_turn(self):
        session = self._post("/api/session", {})
        sid = session["session_id"]
        self.assertTrue(sid)
        result = self._post("/api/turn", {"session_id": sid, "npc": "oldman", "message": "灯下面有什么？"})
        self.assertEqual(result["session_id"], sid)
        self.assertIn("panel", result)
        self.assertIn("reply", result)

    def test_state_endpoint(self):
        session = self._post("/api/session", {})
        sid = session["session_id"]
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/api/state?session_id={sid}", timeout=10) as resp:
            state = __import__("json").loads(resp.read().decode())
        self.assertEqual(state["turn"], 0)


if __name__ == "__main__":
    unittest.main()
