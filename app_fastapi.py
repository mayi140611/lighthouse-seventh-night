#!/usr/bin/env python3
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from engine.webapp import SessionRegistry, load_env

WEB_DIR = ROOT / "web"

load_env()
registry = SessionRegistry(
    provider_kind=os.environ.get("LLM_PROVIDER"),
    save_dir=os.environ.get("SAVE_DIR") or str(ROOT / "saves"),
)

app = FastAPI(title="灯塔第七夜", docs_url=None, redoc_url=None)

if (WEB_DIR / "art").exists():
    app.mount("/art", StaticFiles(directory=str(WEB_DIR / "art")), name="art")


class TurnRequest(BaseModel):
    session_id: str | None = None
    npc: str = "sailor"
    message: str = ""


class SessionRequest(BaseModel):
    session_id: str | None = None
    second_run: bool = False


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/app.js")
def app_js():
    return FileResponse(WEB_DIR / "app.js", media_type="application/javascript; charset=utf-8")


@app.get("/style.css")
def style_css():
    return FileResponse(WEB_DIR / "style.css", media_type="text/css; charset=utf-8")


@app.post("/api/session")
def create_session(body: SessionRequest | None = None):
    body = body or SessionRequest()
    sid = registry.create(body.session_id, second_run=body.second_run)
    return {"session_id": sid, "panel": registry.state(sid)}


@app.post("/api/turn")
def turn(body: TurnRequest):
    sid = body.session_id
    if not sid or sid not in registry.sessions:
        sid = registry.create(sid)
    result = registry.turn(sid, body.npc, body.message)
    if result is None:
        raise HTTPException(status_code=404, detail="session not found")
    return result


@app.post("/api/new")
def new_game(body: SessionRequest | None = None):
    body = body or SessionRequest()
    sid = registry.reset(body.session_id or "", second_run=body.second_run)
    return {"session_id": sid, "panel": registry.state(sid)}


@app.get("/api/state")
def state(session_id: str):
    panel = registry.state(session_id)
    if not panel:
        raise HTTPException(status_code=404, detail="session not found")
    return panel


@app.get("/healthz")
def healthz():
    return {"ok": True, "provider": registry.provider_name()}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "7860"))
    uvicorn.run(app, host="0.0.0.0", port=port)
