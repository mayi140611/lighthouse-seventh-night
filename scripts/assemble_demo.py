#!/usr/bin/env python3
import argparse
import asyncio
import json
import math
import subprocess
import sys
from pathlib import Path

import edge_tts

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "assets" / "demo"
RAW = DEMO / "raw_demo.webm"
TIMELINE = DEMO / "timeline.json"
OUT = DEMO / "lighthouse_demo.mp4"
IAN_DIR = DEMO / "vo_indextts"
FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
VOICE = "zh-CN-YunxiNeural"

SEGMENTS = [
    ("intro", "这是灯塔第七夜，一个十五分钟的 AI NPC 互动叙事。风暴夜，最后一班船还有三小时，救生艇只有一个位置。"),
    ("design", "关键设计是，大模型只负责提案，规则层负责裁判。台词它演，数值和结局，由一段可以单测的 Python 决定。"),
    ("give", "先给船员面包。信任上升，物资计一。"),
    ("key", "提钥匙。信任不够，规则层直接拒绝。"),
    ("oldman", "换老人，逼问灯塔的真相。注意他的恐惧和信任此消彼长。第四次追问，信任跌破十五。"),
    ("ending", "恐惧压过了信任，规则层自动判定第七夜。结局不是模型选的，是状态组合算出来的，可以复现。"),
    ("outro", "再来一局，他记得上一局帮过谁。"),
]


def dur(path):
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)
    ]).decode().strip()
    return float(out)


async def synth(text, rate, path):
    comm = edge_tts.Communicate(text, VOICE, rate=rate)
    await comm.save(str(path))


def gen_segment(text, target, path):
    asyncio.run(synth(text, "+0%", path))
    d = dur(path)
    if d > target - 0.2:
        factor = d / max(1.0, target - 0.2)
        rate_pct = min(45, max(0, int((factor - 1) * 100) + 2))
        asyncio.run(synth(text, f"+{rate_pct}%", path))
        d = dur(path)
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", choices=["edge", "indextts"], default="edge")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    out_path = Path(args.out) if args.out else OUT
    tl = json.loads(TIMELINE.read_text(encoding="utf-8"))
    keys = ["intro", "design", "give", "key", "oldman", "ending", "outro"]
    starts = {k: tl[k] for k in keys}
    total_video = dur(RAW)
    pad_tail = 4.0
    total = max(total_video, tl["end"] + pad_tail) + 0.8

    seg_files = []
    if args.voice == "indextts":
        meta = json.loads((IAN_DIR / "meta.json").read_text(encoding="utf-8"))
        for i, row in enumerate(meta["rows"]):
            key = row["key"]
            path = IAN_DIR / row["file"]
            d = dur(path)
            if key == "closing":
                continue
            start = 0.6 if key == "intro" else starts[key]
            print(f"{key}: start={start:.2f}s dur={d:.2f}s", flush=True)
            seg_files.append((start, path, d))
        closing_path = IAN_DIR / meta["rows"][-1]["file"]
        closing_start = max(total_video - 1.0, tl["end"] - 0.2)
    else:
        for i, (key, text) in enumerate(SEGMENTS):
            if key == "intro":
                start = 0.6
            else:
                start = starts[key]
            if key == "outro":
                target = max(6.0, total_video - start + pad_tail)
            else:
                nxt = keys[i + 1]
                target = max(4.0, starts[nxt] - start - 0.3)
            path = DEMO / f"vo_{i}_{key}.mp3"
            d = gen_segment(text, target, path)
            print(f"{key}: start={start:.2f}s target={target:.2f}s dur={d:.2f}s", flush=True)
            seg_files.append((start, path, d))

        closing_path = DEMO / "vo_closing.mp3"
        asyncio.run(synth("代码开源，九十四个单测，四个结局可复现。链接在简介里。", "+8%", closing_path))
        closing_start = total_video - 0.5
    seg_files.append((closing_start, closing_path, dur(closing_path)))
    total = max(total, closing_start + dur(closing_path) + 1.0)
    pad_tail = max(pad_tail, total - total_video)

    inputs = ["-i", str(RAW)]
    for _, path, _ in seg_files:
        inputs += ["-i", str(path)]
    noise_idx = len(seg_files) + 1
    inputs += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anoisesrc=color=pink:amplitude=0.03"]

    chains = []
    mix_labels = []
    for idx, (start, _, d) in enumerate(seg_files, start=1):
        ms = int(start * 1000)
        chains.append(f"[{idx}:a]aresample=44100,adelay={ms}|{ms}[v{idx}]")
        mix_labels.append(f"[v{idx}]")
    chains.append(f"[{noise_idx}:a]highpass=f=200,lowpass=f=1400,volume=0.10[amb]")
    mix_labels.append("[amb]")
    mix = "".join(mix_labels) + f"amix=inputs={len(mix_labels)}:normalize=0:dropout_transition=0,alimiter=limit=0.95,loudnorm=I=-16:TP=-1.5:LRA=11[aout]"

    title_file = Path("/tmp/demo_url.txt")
    title_file.write_text("https://modelscope.cn/studios/mayi140611/lighthouse-seventh-night", encoding="utf-8")
    vf = (
        f"tpad=stop_mode=clone:stop_duration={pad_tail:.1f},"
        "scale=1920:1200,scale=1728:1080,pad=1920:1080:96:0:black,"
        "fade=t=in:st=0:d=0.8,"
        f"fade=t=out:st={total-1.2:.2f}:d=1.2,"
        f"drawtext=fontfile={FONT}:textfile={title_file}:fontsize=30:fontcolor=white@0.85:"
        f"box=1:boxcolor=black@0.45:boxborderw=16:x=(w-text_w)/2:y=h-70:enable='gte(t,{closing_start:.2f})'"
    )

    cmd = ["ffmpeg", "-y", "-v", "error"] + inputs + [
        "-filter_complex", ";".join(chains) + ";" + mix,
        "-map", "0:v", "-map", "[aout]",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-ar", "44100",
        "-t", f"{total:.2f}", "-movflags", "+faststart", str(out_path),
    ]
    subprocess.run(cmd, check=True)
    print("OUT", out_path, "duration", round(dur(out_path), 2), "size_MB", round(out_path.stat().st_size / 1e6, 2))


if __name__ == "__main__":
    main()
