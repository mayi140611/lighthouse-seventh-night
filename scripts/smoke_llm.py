#!/usr/bin/env python3
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from engine.game import GameSession
from engine.providers import ModelScopeProvider

SEED = Path(__file__).resolve().parent.parent.parent.parent / "secrets" / "modelscope.env"


def load_env(path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value)


def main():
    load_env(SEED)
    provider = ModelScopeProvider(model=os.environ.get("MODELSCOPE_MODEL"))
    session = GameSession(provider)
    turns = [
        ("sailor", "面包给你，上船时带上我。"),
        ("sailor", "我不会抢你的位置，我只要钥匙开门。"),
        ("oldman", "灯我来守，你先坐下歇会儿。"),
    ]
    latencies = []
    for npc, text in turns:
        result = session.turn(text, npc=npc)
        latencies.append(provider.last_latency or 0)
        print(f"[{result.npc}] {result.reply}")
        print(f"  deltas提案={result.proposed_deltas} 采纳={result.applied_deltas} intent={result.intent} fallback={result.fallback}")
    panel = session.panel()
    print("panel:", {k: v for k, v in panel.items() if k != "states"})
    print("states:", panel["states"])
    print(f"latency avg={sum(latencies)/len(latencies):.2f}s max={max(latencies):.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
