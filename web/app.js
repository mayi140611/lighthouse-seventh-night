const NPC_ORDER = ["sailor", "girl", "oldman"];
const NPC_NAMES = { sailor: "船员", girl: "少女", oldman: "老人" };
const PORTRAITS = {
  sailor: "雨衣 · 手电 · 腰间钥匙",
  girl: "湿发 · 泡皱的航海日志",
  oldman: "驼背 · 提灯 · 袖口盐渍",
};
const AVATARS = {
  sailor: "/art/portrait_sailor.jpg",
  girl: "/art/portrait_girl.jpg",
  oldman: "/art/portrait_oldman.jpg",
};
const SCENES = {
  sailor: "/art/bg_lighthouse.jpg",
  girl: "/art/bg_shore.jpg",
  oldman: "/art/bg_lamp.jpg",
};

const ENDING_TEXT = {
  同舟: "救生艇挤下了所有人。天亮时，灯塔还亮着，你们谁也没回头。",
  守灯: "你留下了。灯芯剪短，光稳住了，海面下的东西安静了一整夜。",
  钥匙: "钥匙在你手里。门开了，但只够一个人走——你选了谁，海记得。",
  第七夜: "灯灭了。岛上再没有第七夜，因为已经没有第八天。",
};

const state = {
  sessionId: null,
  npc: "sailor",
  busy: false,
  logs: [],
};

const el = {
  dialogue: document.getElementById("dialogue"),
  message: document.getElementById("message"),
  send: document.getElementById("send"),
  speaking: document.getElementById("speaking"),
  npcs: document.getElementById("npcs"),
  given: document.getElementById("given"),
  provider: document.getElementById("provider"),
  log: document.getElementById("log"),
  logBody: document.getElementById("log-body"),
  ending: document.getElementById("ending"),
  endingTitle: document.getElementById("ending-title"),
  endingText: document.getElementById("ending-text"),
};

async function api(path, body) {
  const res = await fetch(path, {
    method: body ? "POST" : "GET",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

function addLine(who, text, player = false, meta = "") {
  const wrap = document.createElement("div");
  wrap.className = "line" + (player ? " player" : "");
  wrap.innerHTML = `
    <div class="who">${player ? "你" : who}</div>
    <div class="bubble"></div>
    ${meta ? `<div class="meta">${meta}</div>` : ""}
  `;
  const bubble = wrap.querySelector(".bubble");
  el.dialogue.appendChild(wrap);
  typewrite(bubble, text);
  el.dialogue.scrollTop = el.dialogue.scrollHeight;
}

function typewrite(node, text) {
  let i = 0;
  node.textContent = "";
  const timer = setInterval(() => {
    node.textContent += text.slice(i, i + 2);
    i += 2;
    el.dialogue.scrollTop = el.dialogue.scrollHeight;
    if (i >= text.length) clearInterval(timer);
  }, 18);
}

function renderPanel(panel) {
  if (!panel) return;
  el.given.textContent = panel.given_count ?? 0;
  if (panel.provider) {
    el.provider.textContent = panel.provider === "modelscope" ? "线上模型" : "脚本 NPC";
  }
  el.npcs.innerHTML = "";
  for (const key of NPC_ORDER) {
    const st = panel.states[key];
    const card = document.createElement("div");
    card.className = "npc" + (state.npc === key ? " active" : "");
    card.dataset.npc = key;
    card.innerHTML = `
      <div class="row">
        <img class="avatar" src="${AVATARS[key]}" alt="${NPC_NAMES[key]}">
        <span class="name">${NPC_NAMES[key]}</span>
        <span class="portrait">${PORTRAITS[key]}</span>
      </div>
      ${statBar("信任", st.trust, "trust")}
      ${statBar("恐惧", st.fear, "fear")}
      ${statBar("亏欠", st.debt, "debt")}
    `;
    card.addEventListener("click", () => {
      setScene(key);
      renderPanel(panel);
    });
    el.npcs.appendChild(card);
  }
}

function setScene(key) {
  state.npc = key;
  el.speaking.textContent = `你在对 ${NPC_NAMES[key]} 说话`;
  document.body.style.setProperty("--scene", `url("${SCENES[key]}")`);
}

function statBar(label, value, kind) {
  return `
    <div class="stat">
      <span>${label}</span>
      <div class="bar"><i class="${kind}" style="width:${Math.max(0, Math.min(100, value))}%"></i></div>
      <b>${value}</b>
    </div>`;
}

function deltaMeta(applied, proposed, gate, rejected, fallback) {
  const parts = [];
  for (const [k, v] of Object.entries(applied || {})) {
    if (!v) continue;
    const name = { trust: "信任", fear: "恐惧", debt: "亏欠" }[k];
    parts.push(`<span class="${v > 0 && k === "trust" ? "up" : v < 0 && k === "trust" ? "down" : ""}">${name}${v > 0 ? "+" : ""}${v}</span>`);
  }
  if (gate) parts.push(gate);
  if (rejected) parts.push("意图被规则层拒绝");
  if (fallback) parts.push("模型输出非法 → 兜底台词");
  return parts.join(" · ");
}

function pushLog(result) {
  state.logs.unshift(result);
  el.logBody.innerHTML = state.logs
    .slice(0, 12)
    .map((r) => {
      const proposed = JSON.stringify(r.proposed_deltas || {});
      const applied = JSON.stringify(r.applied_deltas || {});
      const refs = (r.memory_refs || []).length ? `<br>记忆引用：${r.memory_refs.join(" / ")}` : "";
      return `<div class="entry"><b>第 ${r.turn} 轮 · ${r.npc_name}</b> · 意图 ${r.intent}<br>
        提案 ${proposed} → 采纳 ${applied}${r.gate_reason ? "<br>" + r.gate_reason : ""}${refs}</div>`;
    })
    .join("");
}

async function send() {
  const text = el.message.value.trim();
  if (!text || state.busy) return;
  state.busy = true;
  el.send.disabled = true;
  el.message.value = "";
  addLine("你", text, true);
  try {
    const result = await api("/api/turn", {
      session_id: state.sessionId,
      npc: state.npc,
      message: text,
    });
    state.sessionId = result.session_id;
    if (result.applied_deltas && Object.keys(result.applied_deltas).length === 0 && result.fallback) {
      addLine(result.npc_name, result.reply, false, "模型暂不可用，已用角色兜底台词");
    } else {
      addLine(result.npc_name, result.reply, false, deltaMeta(result.applied_deltas, result.proposed_deltas, result.gate_reason, result.rejected_intent, result.fallback));
    }
    renderPanel(result.panel);
    pushLog(result);
    if (result.ending) showEnding(result.ending);
  } catch (err) {
    addLine("系统", `请求失败：${err.message}`, false);
  } finally {
    state.busy = false;
    el.send.disabled = false;
    el.message.focus();
  }
}

function showEnding(ending) {
  el.endingTitle.textContent = ending;
  el.endingText.textContent = ENDING_TEXT[ending] || "";
  el.ending.classList.remove("hidden");
}

async function newGame(secondRun) {
  const data = await api("/api/new", { session_id: state.sessionId, second_run: secondRun });
  state.sessionId = data.session_id;
  state.logs = [];
  el.dialogue.innerHTML = "";
  el.logBody.innerHTML = "";
  el.ending.classList.add("hidden");
  renderPanel(data.panel);
  setScene("sailor");
  addLine(
    "旁白",
    secondRun ? "又一班船靠岸。他们看你的眼神，像记得上一局。" : "风暴把最后一班船按在了雾里。灯塔下，三个人在等你开口。",
    false
  );
  el.message.focus();
}

el.send.addEventListener("click", send);
el.message.addEventListener("keydown", (e) => {
  if (e.key === "Enter") send();
});
document.getElementById("restart").addEventListener("click", () => newGame(false));
document.getElementById("again").addEventListener("click", () => newGame(true));
document.getElementById("fresh").addEventListener("click", () => newGame(false));
document.getElementById("toggle-log").addEventListener("click", () => el.log.classList.toggle("hidden"));
document.querySelectorAll(".hint").forEach((btn) => {
  btn.addEventListener("click", () => {
    el.message.value = btn.dataset.text;
    el.message.focus();
  });
});

(async function boot() {
  const data = await api("/api/session", {});
  state.sessionId = data.session_id;
  renderPanel(data.panel);
  addLine("旁白", "风暴把最后一班船按在了雾里。灯塔下，三个人在等你开口。", false);
  el.message.focus();
})();
