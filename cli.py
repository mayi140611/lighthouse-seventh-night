#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

from engine.game import GameSession, load_previous_run
from engine.providers import ScriptedProvider
from engine.script import DEMO_ROUTES, NPC_PROFILES

ROUTE_EXPECT = {"boat": "同舟", "lamp": "守灯", "key": "钥匙", "night": "第七夜"}


def render_panel(session, title=""):
    panel = session.panel()
    print(f"\n--- {title or '状态面板'} | 第 {panel['turn']} 轮 ---")
    for npc in ("sailor", "girl", "oldman"):
        stats = panel["states"][npc]
        print(
            f"  {NPC_PROFILES[npc]['name']:<2} trust={stats['trust']:>3} "
            f"fear={stats['fear']:>3} debt={stats['debt']:>3}"
        )
    print(f"  旗帜={panel['flags'] or '无'} 给出物资={panel['given_count']} 结局={panel['ending'] or '进行中'}")


def play_route(route, save_path=None, previous=None, verbose=True):
    provider = ScriptedProvider(route=route)
    session = GameSession(provider, save_path=save_path, previous_run=previous)
    if verbose:
        print(f"\n================ 路线：{route} → 预期 {ROUTE_EXPECT[route]} ================")
    for idx, item in enumerate(DEMO_ROUTES[route], start=1):
        npc, text = item[0], item[1]
        result = session.turn(text, npc=npc)
        if verbose:
            print(f"\n[{idx}] 你对{NPC_PROFILES[npc]['name']}说：{text}")
            print(f"    {NPC_PROFILES[result.npc]['name']}：{result.reply}")
            print(f"    提案={result.proposed_deltas} 采纳={result.applied_deltas} 意图={result.intent}")
            if result.gate_reason:
                print(f"    闸门：{result.gate_reason}")
            if result.rejected_intent:
                print("    ⚠ 意图被规则层拒绝，本轮不加状态")
            if result.memory_refs:
                print(f"    记忆引用：{result.memory_refs}")
        if session.finished:
            break
    session.finish()
    if verbose:
        render_panel(session, f"{route} 终局")
    return session


def run_demo(save_dir=None):
    failures = []
    for route, expect in ROUTE_EXPECT.items():
        save_path = str(Path(save_dir) / f"ending_{route}.json") if save_dir else None
        session = play_route(route, save_path=save_path)
        if session.ending != expect:
            failures.append((route, expect, session.ending))
    if failures:
        for route, expect, actual in failures:
            print(f"✗ {route}: 预期 {expect}，实际 {actual}")
        return 1
    if save_dir:
        previous = load_previous_run(Path(save_dir) / "ending_boat.json")
        session = play_route("key", previous=previous, verbose=False)
        seed = session.memory.entries[0] if session.memory.entries else None
        print(f"\n二周目彩蛋：载入上一局 → {seed.text if seed else '无记忆'}")
    print("\n✓ 四条路线全部到达预期结局")
    return 0


def interactive(save_path=None, previous=None):
    session = GameSession(ScriptedProvider(), save_path=save_path, previous_run=previous)
    print("《灯塔第七夜》CLI（W1 规则层）｜1=船员 2=少女 3=老人｜quit 退出")
    mapping = {"1": "sailor", "2": "girl", "3": "oldman"}
    npc = "sailor"
    while not session.finished:
        render_panel(session)
        print(f"当前对话对象：{NPC_PROFILES[npc]['name']}（b 换人）")
        raw = input("> ").strip()
        if raw.lower() in ("quit", "exit", "q"):
            break
        if raw == "b":
            choice = input("换成 1/2/3：").strip()
            npc = mapping.get(choice, npc)
            continue
        result = session.turn(raw, npc=npc)
        print(f"{NPC_PROFILES[result.npc]['name']}：{result.reply}")
        print(f"状态变化：{result.applied_deltas}｜意图：{result.intent}")
    session.finish()
    if session.ending:
        render_panel(session, "终局")
        print(f"结局：{session.ending}")


def main(argv=None):
    parser = argparse.ArgumentParser(description="灯塔第七夜 W1 规则层 CLI")
    parser.add_argument("--demo", action="store_true", help="跑 4 条路线验证 4 个结局")
    parser.add_argument("--route", choices=list(DEMO_ROUTES), help="单跑一条路线")
    parser.add_argument("--save-dir", help="结局存档目录")
    parser.add_argument("--previous", help="载入上一局存档")
    args = parser.parse_args(argv)

    previous = load_previous_run(args.previous) if args.previous else None
    if args.demo:
        return run_demo(args.save_dir)
    if args.route:
        session = play_route(args.route, save_path=None, previous=previous)
        return 0 if session.ending == ROUTE_EXPECT[args.route] else 1
    save_path = str(Path(args.save_dir) / "ending.json") if args.save_dir else None
    interactive(save_path=save_path, previous=previous)
    return 0


if __name__ == "__main__":
    sys.exit(main())
