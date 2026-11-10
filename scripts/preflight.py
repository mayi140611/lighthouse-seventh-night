#!/usr/bin/env python3
import argparse
import json
import re
import time
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "preflight_report.json"
STUDIO = "https://modelscope.cn/studios/mayi140611/lighthouse-seventh-night"
LOCAL = "http://127.0.0.1:8097/"

TURNS = [
    ("sailor", "面包给你，上船时带上我。"),
    ("sailor", "我不会抢你的位置，我只要钥匙开门。"),
    ("girl", "我知道你藏了半本日志，我替你保密。"),
    ("oldman", "灯下面到底有什么？第七夜为什么不能灭灯？"),
    ("sailor", "干柴也给你，别冻着。"),
    ("girl", "面包分你一半，别哭。"),
    ("oldman", "我不跑，我留下守灯。"),
    ("sailor", "船靠岸时，你先上，我断后。"),
    ("girl", "船靠岸我喊你，一起走。"),
    ("oldman", "真相我记住了，灯也交给你。"),
]
NPC_INDEX = {"sailor": 0, "girl": 1, "oldman": 2}


def get_frame(page, timeout=90000):
    page.goto(STUDIO if not args.local else LOCAL, wait_until="load", timeout=timeout)
    for _ in range(30):
        page.wait_for_timeout(1000)
        frames = [f for f in page.frames if "ms.show" in f.url] if not args.local else [page.main_frame]
        if frames:
            try:
                if "灯塔第七夜" in frames[0].inner_text("body"):
                    return frames[0]
            except Exception:
                pass
    raise RuntimeError("没有找到应用 iframe / 页面没加载出来")


def parse_turn(text):
    m = re.search(r"回合\s*(\d+)", text.replace("\n", " "))
    return int(m.group(1)) if m else -1


def main():
    global args
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", action="store_true")
    ap.add_argument("--turns", type=int, default=10)
    args = ap.parse_args()

    report = {"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "target": "local" if args.local else STUDIO,
              "turns": [], "console_errors": [], "mobile": {}}
    t0 = time.monotonic()
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--hide-scrollbars"])
        page = browser.new_page(viewport={"width": 1360, "height": 950})
        page.on("console", lambda m: report["console_errors"].append(m.text[:200]) if m.type == "error" else None)
        frame = get_frame(page)
        report["load_s"] = round(time.monotonic() - t0, 2)
        textarea = frame.locator("textarea").first

        for i, (npc, msg) in enumerate(TURNS[: args.turns], start=1):
            body = frame.inner_text("body")
            if "结局：" in body:
                frame.get_by_role("button", name="再来一局（保留记忆）", exact=True).click()
                frame.page.wait_for_timeout(2500)
            frame.locator("input[type=radio]").nth(NPC_INDEX[npc]).check(force=True)
            frame.page.wait_for_timeout(300)
            before = parse_turn(frame.inner_text("body"))
            started = time.monotonic()
            textarea.fill(msg)
            textarea.press("Enter")
            after = before
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                frame.page.wait_for_timeout(300)
                after = parse_turn(frame.inner_text("body"))
                if after > before:
                    break
            elapsed = round(time.monotonic() - started, 2)
            body = frame.inner_text("body")
            report["turns"].append({
                "n": i, "npc": npc, "latency_s": elapsed, "turn_advanced": after > before,
                "fallback": "兜底台词" in body, "ending": "结局：" in body,
            })
            print(f"turn {i}: {elapsed:.2f}s advanced={after > before}", flush=True)
            if after <= before:
                break

        ctx2 = browser.new_context(**p.devices["iPhone 13"])
        page2 = ctx2.new_page()
        page2.goto(STUDIO if not args.local else LOCAL, wait_until="load", timeout=90000)
        page2.wait_for_timeout(18000)
        frames = [f for f in page2.frames if "ms.show" in f.url] if not args.local else [page2.main_frame]
        mobile_ok = False
        overflow = None
        if frames:
            f = frames[0]
            try:
                txt = f.inner_text("body")
                mobile_ok = "对话对象" in txt and "灯塔第七夜" in txt
                overflow = f.evaluate("() => document.documentElement.scrollWidth - window.innerWidth")
                page2.screenshot(path=str(ROOT / "docs" / "preflight_mobile.png"), full_page=False)
            except Exception as exc:
                report["mobile"]["error"] = str(exc)
        report["mobile"].update({"ok": mobile_ok, "horizontal_overflow_px": overflow})
        browser.close()

    lat = [t["latency_s"] for t in report["turns"] if t["turn_advanced"]]
    report["summary"] = {
        "turns_ok": sum(1 for t in report["turns"] if t["turn_advanced"]),
        "turns_total": len(report["turns"]),
        "latency_avg_s": round(sum(lat) / len(lat), 2) if lat else None,
        "latency_max_s": max(lat) if lat else None,
        "under_6s": all(x < 6 for x in lat) if lat else False,
        "console_error_count": len(report["console_errors"]),
        "mobile_ok": report["mobile"].get("ok", False),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
