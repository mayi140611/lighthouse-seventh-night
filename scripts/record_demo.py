#!/usr/bin/env python3
import json
import shutil
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "demo"
RAW = Path("/tmp/lh_video")
URL = "http://127.0.0.1:8097/"

CURSOR_JS = """
(() => {
  const make = () => {
    if (document.getElementById('__cursor')) return;
    const d = document.createElement('div');
    d.id = '__cursor';
    d.style.cssText = 'position:fixed;width:18px;height:18px;border:2px solid #f0b429;border-radius:50%;' +
      'box-shadow:0 0 12px rgba(240,180,41,.8);pointer-events:none;z-index:999999;' +
      'transform:translate(-50%,-50%);transition:left .08s linear,top .08s linear;left:-50px;top:-50px';
    document.body.appendChild(d);
    window.addEventListener('mousemove', (e) => {
      d.style.left = e.clientX + 'px';
      d.style.top = e.clientY + 'px';
    }, true);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', make);
  else make();
})();
"""


def main():
    if RAW.exists():
        shutil.rmtree(RAW)
    RAW.mkdir(parents=True)
    OUT.mkdir(parents=True, exist_ok=True)
    ts = {"intro": 0.0}
    t0 = time.monotonic()

    def mark(name):
        ts[name] = round(time.monotonic() - t0, 3)
        print(name, ts[name], flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--hide-scrollbars"])
        ctx = browser.new_context(
            viewport={"width": 1600, "height": 1000},
            record_video_dir=str(RAW),
            record_video_size={"width": 1600, "height": 1000},
        )
        ctx.add_init_script(CURSOR_JS)
        page = ctx.new_page()
        page.goto(URL, wait_until="load", timeout=60000)
        page.wait_for_timeout(2500)
        mark("intro")

        textarea = page.locator("textarea").first
        page.mouse.move(900, 500, steps=20)
        page.wait_for_timeout(9000)

        mark("design")
        page.mouse.move(1250, 300, steps=25)
        page.wait_for_timeout(1600)
        page.mouse.move(1280, 700, steps=15)
        page.wait_for_timeout(1600)
        page.mouse.move(1330, 640, steps=10)
        page.wait_for_timeout(8500)

        def send_preset(label, wait_ms=4600):
            page.get_by_role("button", name=label, exact=True).click()
            page.wait_for_timeout(400)
            textarea.press("Enter")
            page.wait_for_timeout(wait_ms)

        mark("give")
        send_preset("给面包")
        mark("key")
        send_preset("提钥匙")
        mark("oldman")
        page.locator("input[type=radio]").nth(2).check(force=True)
        page.wait_for_timeout(800)
        send_preset("问真相", 5200)
        ending_found = "结局：" in page.inner_text("body")
        extra = 0
        while not ending_found and extra < 4:
            send_preset("问真相", 5200)
            ending_found = "结局：" in page.inner_text("body")
            extra += 1
        mark("ending")
        page.wait_for_timeout(6500)
        page.get_by_role("button", name="再来一局（保留记忆）", exact=True).click()
        page.wait_for_timeout(6000)
        mark("outro")
        page.mouse.move(800, 500, steps=20)
        page.wait_for_timeout(4500)
        mark("end")
        video = page.video.path()
        ctx.close()
        browser.close()

    shutil.copy(video, OUT / "raw_demo.webm")
    (OUT / "timeline.json").write_text(json.dumps(ts, ensure_ascii=False, indent=2), encoding="utf-8")
    print("VIDEO", OUT / "raw_demo.webm", flush=True)
    print("TIMELINE", json.dumps(ts, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    sys.exit(main())
