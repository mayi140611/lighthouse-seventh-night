#!/usr/bin/env python3
import base64
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import gradio as gr

from engine.script import NPC_PROFILES
from engine.webapp import SessionRegistry, load_env

WEB_DIR = ROOT / "web"
ART = WEB_DIR / "art"
NPC_ORDER = ["sailor", "girl", "oldman"]
NPC_NAMES = {k: NPC_PROFILES[k]["name"] for k in NPC_ORDER}
ENDING_TEXT = {
    "同舟": "救生艇挤下了所有人。天亮时，灯塔还亮着，你们谁也没回头。",
    "守灯": "你留下了。灯芯剪短，光稳住了，海面下的东西安静了一整夜。",
    "钥匙": "钥匙在你手里。门开了，但只够一个人走——你选了谁，海记得。",
    "第七夜": "灯灭了。岛上再没有第七夜，因为已经没有第八天。",
}

load_env()
registry = SessionRegistry(
    provider_kind=os.environ.get("LLM_PROVIDER"),
    save_dir=os.environ.get("SAVE_DIR") or str(ROOT / "saves"),
)


def _b64(path: Path) -> str:
    if not path.exists():
        return ""
    return base64.b64encode(path.read_bytes()).decode()


BG = _b64(ART / "bg_lighthouse.jpg")
AVATARS = {npc: _b64(ART / f"portrait_{npc}.jpg") for npc in NPC_ORDER}

CSS = f"""
body, .gradio-container {{
  background-image: linear-gradient(180deg, rgba(4,8,14,.78), rgba(4,8,14,.94) 60%, rgba(4,8,14,.98)),
    url("data:image/jpeg;base64,{BG}");
  background-size: cover; background-attachment: fixed; background-position: center;
}}
.gradio-container {{ max-width: 1180px !important; background: transparent !important; }}
.dark #title h1, .dark #title p {{ color: #dbe6f2 !important; }}
.dark .panel-card {{ color: #dbe6f2; }}
#title h1 {{ letter-spacing: .12em; margin-bottom: 0; }}
#title p {{ color: #8296ac; margin-top: 4px; }}
.panel-card {{ background: rgba(14,22,34,.72); border: 1px solid rgba(120,170,220,.18);
  border-radius: 14px; padding: 14px; }}
.npc-block {{ display:flex; gap:10px; align-items:center; margin: 10px 0 4px; }}
.npc-block img {{ width: 44px; height: 44px; border-radius: 50%; object-fit: cover;
  border: 1px solid rgba(160,190,220,.25); }}
.npc-name {{ font-weight: 600; color:#dbe6f2; }}
.stat-row {{ display:grid; grid-template-columns: 34px 1fr 30px; gap:6px; align-items:center;
  margin: 3px 0; font-size: 11px; color:#8296ac; }}
.stat-bar {{ height:5px; background: rgba(255,255,255,.08); border-radius:99px; overflow:hidden; }}
.stat-bar i {{ display:block; height:100%; border-radius:99px; }}
.trust {{ background:#6fbf8a; }} .fear {{ background:#c0574a; }} .debt {{ background:#b58bd9; }}
.log-entry {{ font-size: 11px; color:#8296ac; border-left:2px solid rgba(120,170,220,.25);
  padding-left:8px; margin-bottom:8px; line-height:1.6; }}
.log-entry b {{ color:#dbe6f2; }}
"""


def panel_html(panel) -> str:
    if not panel:
        return ""
    blocks = ['<div class="panel-card">']
    for npc in NPC_ORDER:
        st = panel["states"][npc]
        blocks.append(
            f'<div class="npc-block"><img src="data:image/jpeg;base64,{AVATARS[npc]}">'
            f'<span class="npc-name">{NPC_NAMES[npc]}</span></div>'
        )
        for key, label in (("trust", "信任"), ("fear", "恐惧"), ("debt", "亏欠")):
            value = st[key]
            blocks.append(
                f'<div class="stat-row"><span>{label}</span>'
                f'<div class="stat-bar"><i class="{key}" style="width:{value}%"></i></div>'
                f"<span>{value}</span></div>"
            )
    blocks.append(
        f'<div style="margin-top:12px;padding-top:10px;border-top:1px solid rgba(120,170,220,.18);'
        f'font-size:12px;color:#8296ac;display:flex;justify-content:space-between">'
        f"<span>已给出物资</span><b style='color:#dbe6f2;font-size:16px'>{panel['given_count']}</b></div>"
    )
    blocks.append(
        f'<div style="margin-top:6px;font-size:11px;color:#8296ac">回合 {panel["turn"]} · 模型 {panel.get("provider", "")}</div>'
    )
    blocks.append("</div>")
    return "".join(blocks)


def log_html(sid) -> str:
    session = registry.sessions.get(sid)
    if not session:
        return ""
    lines = ['<div style="max-height:300px;overflow:auto">']
    for item in reversed(session.history[-8:]):
        r = item["result"]
        proposed = {k: v for k, v in (r.get("proposed_deltas") or {}).items() if v}
        applied = {k: v for k, v in (r.get("applied_deltas") or {}).items() if v}
        gate = r.get("gate_reason") or ""
        refs = r.get("memory_refs") or []
        lines.append(
            f'<div class="log-entry"><b>第 {item["turn"]} 轮 · {NPC_NAMES.get(item["npc"], item["npc"])}</b>'
            f' · 意图 {r.get("intent")}<br>提案 {proposed} → 采纳 {applied}'
            + (f"<br>{gate}" if gate else "")
            + (f"<br>记忆引用：{' / '.join(refs)}" if refs else "")
            + "</div>"
        )
    lines.append("</div>")
    return "".join(lines)


def ending_md(ending) -> str:
    if not ending:
        return ""
    return f"## 结局：{ending}\n\n{ENDING_TEXT.get(ending, '')}"


def new_session(second_run: bool = False):
    sid = registry.create(second_run=second_run)
    session = registry.sessions[sid]
    intro = "又一班船靠岸。他们看你的眼神，像记得上一局。" if second_run else "风暴把最后一班船按在了雾里。灯塔下，三个人在等你开口。"
    history = [{"role": "assistant", "content": f"旁白：{intro}"}]
    return sid, history, panel_html(session.panel()), "", ""


def on_send(message, history, sid, npc):
    history = history or []
    if not message or not message.strip():
        session = registry.sessions.get(sid)
        return "", history, panel_html(session.panel() if session else None), log_html(sid), ""
    if sid not in registry.sessions:
        sid = registry.create(sid)
    result = registry.turn(sid, npc, message)
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": f"{result['npc_name']}：{result['reply']}"},
    ]
    return (
        "",
        history,
        panel_html(result["panel"]),
        log_html(sid),
        ending_md(result.get("ending")),
    )


def restart(second_run: bool):
    return new_session(second_run)


FORCE_DARK = """
() => {
  document.documentElement.classList.add('dark');
  if (document.body) document.body.classList.add('dark');
}
"""

with gr.Blocks(title="灯塔第七夜") as demo:
    session_state = gr.State("")
    gr.Markdown(
        "# 灯塔第七夜\n风暴夜 · 最后一班船还有三小时 · 救生艇只有一个位置",
        elem_id="title",
    )
    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(height=480, show_label=False, elem_id="chat")
            message = gr.Textbox(
                placeholder="说点什么……（回车发送）",
                show_label=False,
                container=False,
                lines=1,
            )
            with gr.Row():
                npc = gr.Radio(
                    choices=[(NPC_NAMES[k], k) for k in NPC_ORDER],
                    value="sailor",
                    label="对话对象",
                    scale=3,
                )
                send_btn = gr.Button("说", variant="primary", scale=1)
            with gr.Row():
                for label, text in (
                    ("给面包", "面包给你，上船时带上我。"),
                    ("提钥匙", "我只要钥匙开门，不会抢你的位置。"),
                    ("问真相", "灯下面到底有什么？第七夜为什么不能灭灯？"),
                    ("威胁", "把日志给我，不然我把你留在岛上。"),
                ):
                    btn = gr.Button(label, size="sm")
                    btn.click(lambda t=text: t, outputs=message)
            with gr.Row():
                restart_btn = gr.Button("重开")
                again_btn = gr.Button("再来一局（保留记忆）")
        with gr.Column(scale=2):
            panel = gr.HTML()
            ending = gr.Markdown()
            with gr.Accordion("规则层日志（LLM 只提案，规则层裁判）", open=False):
                log = gr.HTML()

    demo.load(new_session, inputs=None, outputs=[session_state, chatbot, panel, log, ending])
    send_btn.click(
        on_send,
        inputs=[message, chatbot, session_state, npc],
        outputs=[message, chatbot, panel, log, ending],
    )
    message.submit(
        on_send,
        inputs=[message, chatbot, session_state, npc],
        outputs=[message, chatbot, panel, log, ending],
    )
    restart_btn.click(lambda: restart(False), outputs=[session_state, chatbot, panel, log, ending])
    again_btn.click(lambda: restart(True), outputs=[session_state, chatbot, panel, log, ending])

if __name__ == "__main__":
    demo.queue().launch(
        css=CSS,
        js=FORCE_DARK,
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", "7860")),
        footer_links=[],
    )
