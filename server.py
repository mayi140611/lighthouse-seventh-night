#!/usr/bin/env python3
import argparse
import json
import mimetypes
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from engine.webapp import SessionRegistry, load_env  # noqa: E402

WEB_DIR = ROOT / "web"
STATIC = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js", "/style.css": "style.css"}


def make_handler(registry: SessionRegistry):
    class Handler(SimpleHTTPRequestHandler):
        server_version = "Lighthouse/0.2"

        def log_message(self, fmt, *args):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

        def _json(self, code, payload):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            length = int(self.headers.get("Content-Length") or 0)
            if not length:
                return {}
            raw = self.rfile.read(length)
            try:
                return json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return {}

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path
            if not path.startswith("/api"):
                rel = path.lstrip("/") or "index.html"
                file_path = (WEB_DIR / rel).resolve()
                if WEB_DIR.resolve() in file_path.parents and file_path.is_file():
                    data = file_path.read_bytes()
                    ctype = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
                    if ctype.startswith("text/") or ctype in ("application/javascript",):
                        ctype += "; charset=utf-8"
                    self.send_response(200)
                    self.send_header("Content-Type", ctype)
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "public, max-age=86400")
                    self.end_headers()
                    self.wfile.write(data)
                    return
                return self._json(404, {"error": "missing web asset"})
            if path == "/api/state":
                sid = (parse_qs(parsed.query).get("session_id") or [""])[0]
                state = registry.state(sid)
                if not state:
                    return self._json(404, {"error": "session not found"})
                return self._json(200, state)
            return self._json(404, {"error": "not found"})

        def do_POST(self):
            path = urlparse(self.path).path
            body = self._body()
            try:
                if path == "/api/session":
                    sid = registry.create(body.get("session_id"), second_run=bool(body.get("second_run")))
                    return self._json(200, {"session_id": sid, "panel": registry.state(sid)})
                if path == "/api/turn":
                    sid = body.get("session_id")
                    if not sid or sid not in registry.sessions:
                        sid = registry.create(sid)
                    result = registry.turn(sid, body.get("npc") or "sailor", body.get("message") or "")
                    if result is None:
                        return self._json(404, {"error": "session not found"})
                    return self._json(200, result)
                if path == "/api/new":
                    sid = registry.reset(body.get("session_id") or "", second_run=bool(body.get("second_run")))
                    return self._json(200, {"session_id": sid, "panel": registry.state(sid)})
            except Exception as exc:
                return self._json(500, {"error": f"{type(exc).__name__}: {exc}"})
            return self._json(404, {"error": "not found"})

    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(description="灯塔第七夜 本地服务")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--provider", choices=["scripted", "modelscope"], default=None)
    args = parser.parse_args(argv)
    load_env()
    registry = SessionRegistry(provider_kind=args.provider)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(registry))
    print(f"http://{args.host}:{args.port}  provider={registry.provider_name()}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
