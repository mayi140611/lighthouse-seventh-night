#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time

WS = "/home/emp001/Documents/agent_workspace/p2p/ou_cae300ff8d233e62ec5c3532f13d0333"
REPO = os.path.join(WS, "projects/20261106083000_IndexTTS_A_B/repo")
MODEL_DIR = "/home/emp001/models/IndexTTS-2"
REF = os.path.join(WS, "projects/20261027124100_Ian声音克隆配音/assets/ian_ref_43s.wav")
sys.path.insert(0, REPO)
os.environ.setdefault("USE_MODELSCOPE", "true")
os.environ.setdefault("MODELSCOPE_CACHE", "/home/emp001/.cache/modelscope")

import indextts.utils.front as _front  # noqa: E402


def _load_wetext(self):
    if self.zh_normalizer is not None and self.en_normalizer is not None:
        return
    from wetext import Normalizer

    self.zh_normalizer = Normalizer(remove_erhua=False, lang="zh", operator="tn")
    self.en_normalizer = Normalizer(lang="en", operator="tn")


_front.TextNormalizer.load = _load_wetext

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
import indextts.utils.common as _common  # noqa: E402


def _save_pcm_wav_sf(path, wav, sampling_rate, **kw):
    import torch

    w = (wav.detach().to(device="cpu", dtype=torch.float32) / 32767.0).clamp_(-1.0, 1.0).numpy()
    if w.ndim > 1:
        w = w.squeeze(0) if w.shape[0] == 1 else w.T
    sf.write(path, w, int(sampling_rate), subtype="PCM_16")


_common.save_pcm_wav = _save_pcm_wav_sf
import indextts.infer_v2 as _iv2  # noqa: E402

_iv2.save_pcm_wav = _save_pcm_wav_sf
from indextts.infer_v2 import IndexTTS2  # noqa: E402

LINES = [
    ("intro", "这是灯塔第七夜，一个十五分钟的 AI NPC 互动叙事。风暴夜，最后一班船还有三小时，救生艇只有一个位置。",
     "像纪录片旁白，平静、克制，带一点悬念。"),
    ("design", "关键设计是，大模型只负责提案，规则层负责裁判。台词它演，数值和结局，由一段可以单测的 Python 决定。",
     "自信、清晰，像在讲一个自己很满意的设计。"),
    ("give", "先给船员面包。信任上升，物资计一。", "轻快、鼓励，节奏稍快。"),
    ("key", "提钥匙。信任不够，规则层直接拒绝。", "略带紧张，语气压低。"),
    ("oldman", "换老人，逼问灯塔的真相。注意他的恐惧和信任此消彼长。第四次追问，信任跌破十五。",
     "压低声音，悬疑，像在讲一件不该说的事。"),
    ("ending", "恐惧压过了信任，规则层自动判定第七夜。结局不是模型选的，是状态组合算出来的，可以复现。",
     "低沉、收束，带一点无奈。"),
    ("outro", "再来一局，他记得上一局帮过谁。", "温和、放松，带一点笑意。"),
    ("closing", "代码开源，九十四个单测，四个结局可复现。链接在简介里。", "明亮、干脆，收尾。"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--emo-alpha", type=float, default=0.4)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    t0 = time.time()
    tts = IndexTTS2(
        cfg_path=os.path.join(MODEL_DIR, "config.yaml"), model_dir=MODEL_DIR,
        use_fp16=True, device="cuda:0", use_cuda_kernel=False,
        use_deepspeed=False, use_torch_compile=False, use_qwen_emo=True,
    )
    load_s = time.time() - t0
    print(f"LOADED {load_s:.1f}s", flush=True)

    rows = []
    for i, (key, text, emo) in enumerate(LINES):
        path = os.path.join(a.out_dir, f"vo_{i}_{key}.wav")
        ts = time.time()
        tts.infer(spk_audio_prompt=REF, text=text, output_path=path, verbose=False,
                  use_emo_text=True, emo_text=emo, emo_alpha=a.emo_alpha)
        gen = time.time() - ts
        data, sr = sf.read(path)
        if data.ndim > 1:
            data = data.mean(1)
        dur = len(data) / sr
        rows.append({"key": key, "file": os.path.basename(path), "audio_s": round(dur, 2),
                     "gen_s": round(gen, 1), "sr": sr, "chars": len(text),
                     "chars_per_s": round(len(text) / dur, 2), "emo": emo})
        print(f"{key} audio={dur:.2f}s gen={gen:.1f}s 语速={len(text)/dur:.2f}字/秒", flush=True)

    meta = {"model": "IndexTTS-2", "ref": os.path.basename(REF), "emo_alpha": a.emo_alpha,
            "load_s": round(load_s, 1), "rows": rows,
            "total_audio_s": round(sum(r["audio_s"] for r in rows), 2)}
    with open(os.path.join(a.out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    print("META", json.dumps(meta, ensure_ascii=False)[:400], flush=True)


if __name__ == "__main__":
    main()
