from .script import (
    DEMO_ROUTES,
    KEYWORD_INTENTS,
    KEYWORD_TARGETS,
    NPC_PROFILES,
    ROUTE_ACTIONS,
)

class ScriptedProvider:
    def __init__(self, route: str | None = None) -> None:
        self.route = route
        self.turn_no = 0

    def reset(self) -> None:
        self.turn_no = 0

    def propose(self, npc, player_input, state, memories, strict=False):
        if not strict:
            self.turn_no += 1
        if self.route:
            return self._route_proposal()
        return self._keyword_proposal(npc, player_input)

    def _route_proposal(self) -> dict:
        route = DEMO_ROUTES[self.route]
        if self.turn_no > len(route):
            return {
                "reply": "（远处传来汽笛声。）",
                "deltas": {"trust": 0, "fear": 0, "debt": 0},
                "memory_writes": [],
                "intent": "silent",
            }
        npc, _player_text, reply, deltas, intent, writes = route[self.turn_no - 1]
        return {
            "reply": reply,
            "npc": npc,
            "deltas": deltas,
            "memory_writes": writes,
            "intent": intent,
            "action": ROUTE_ACTIONS.get(self.route, {}).get(self.turn_no),
            "memory_refs": self._route_memory_refs(),
        }

    def _route_memory_refs(self) -> list[str]:
        if self.turn_no <= 3:
            return []
        refs = []
        for entry in DEMO_ROUTES[self.route][: self.turn_no - 1]:
            refs.extend(w["text"] for w in entry[5])
        return refs[:3]

    def _keyword_proposal(self, npc: str, player_input: str) -> dict:
        target = npc
        for word, key in KEYWORD_TARGETS.items():
            if word in player_input:
                target = key
                break
        intent = "bargain"
        if any(word in player_input for word in ("威胁", "抢", "滚", "留在这儿", "不给")):
            intent = "threaten"
        else:
            for word, value in KEYWORD_INTENTS.items():
                if word in player_input:
                    intent = value
                    break
        if intent in ("threaten",):
            deltas = {"trust": -8, "fear": 8, "debt": 0}
            writes = [{"who": target, "type": "threat", "text": player_input[:40]}]
        elif intent == "reveal":
            deltas = {"trust": 5, "fear": 2, "debt": 0}
            writes = [{"who": target, "type": "secret", "text": player_input[:40]}]
        elif intent == "deflect":
            deltas = {"trust": -2, "fear": 2, "debt": 0}
            writes = []
        elif intent == "silent":
            deltas = {"trust": 0, "fear": -2, "debt": 0}
            writes = []
        elif any(word in player_input for word in ("给", "面包", "干柴", "绷带", "答应")):
            deltas = {"trust": 8, "fear": -2, "debt": 2}
            writes = [{"who": target, "type": "gift", "text": player_input[:40]}]
        else:
            deltas = {"trust": 3, "fear": 0, "debt": 0}
            writes = []
        fallback = NPC_PROFILES[target]["fallbacks"][
            (self.turn_no - 1) % len(NPC_PROFILES[target]["fallbacks"])
        ]
        return {
            "reply": f"{fallback} {player_input[:24]}",
            "npc": target,
            "deltas": deltas,
            "memory_writes": writes,
            "intent": intent,
            "memory_refs": [],
        }


class InvalidProvider:
    def __init__(self, mode: str = "always") -> None:
        self.mode = mode
        self.calls = 0

    def propose(self, npc, player_input, state, memories, strict=False):
        self.calls += 1
        if self.mode == "always":
            return {"reply": "x", "deltas": {"trust": 99}, "intent": "fly"}
        if self.mode == "once" and self.calls == 1:
            return {"reply": "x", "deltas": {"trust": 99}, "intent": "fly"}
        return {
            "reply": "（恢复。）",
            "deltas": {"trust": 1, "fear": 0, "debt": 0},
            "memory_writes": [],
            "intent": "silent",
        }


class ProviderError(RuntimeError):
    pass


def _strip_code_fence(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def parse_json_content(content: str) -> dict:
    import json

    raw = _strip_code_fence(content)
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < start:
        raise ProviderError("模型输出里没有 JSON 对象")
    try:
        data = json.loads(raw[start : end + 1])
    except json.JSONDecodeError as exc:
        raise ProviderError(f"模型输出 JSON 解析失败: {exc}") from exc
    if not isinstance(data, dict):
        raise ProviderError("模型输出不是 JSON 对象")
    return data


class ModelScopeProvider:
    def __init__(
        self,
        api_key=None,
        base_url=None,
        model=None,
        timeout=30,
        temperature=0.7,
    ):
        import os

        self.api_key = api_key or os.environ.get("MODELSCOPE_API_KEY", "")
        self.base_url = (base_url or os.environ.get("MODELSCOPE_API_BASE", "")).rstrip("/")
        self.model = model or os.environ.get("MODELSCOPE_MODEL", "Qwen/Qwen3.8-Flash-Next")
        self.timeout = timeout
        self.temperature = temperature
        self.last_latency = None
        if not self.api_key or not self.base_url:
            raise ProviderError("缺少 MODELSCOPE_API_KEY / MODELSCOPE_API_BASE")

    def system_prompt(self, npc, state, memories) -> str:
        profile = NPC_PROFILES[npc]
        memory_lines = "\n".join(f"- {m}" for m in memories) or "（无）"
        return (
            f"你在演一个互动叙事游戏里的{NPC_PROFILES[npc]['name']}。\n"
            f"设定：{profile['secret']}\n"
            f"当前状态：信任 {state.trust}/100，恐惧 {state.fear}/100，亏欠 {state.debt}/100。\n"
            f"你记得玩家做过的事：\n{memory_lines}\n"
            "规则：台词不超过60字，符合角色口吻；不要替玩家做决定，不要说出这些数值。\n"
            "只输出一个 JSON 对象，不要额外文字，格式：\n"
            '{"reply":"台词","deltas":{"trust":整数-10..10,"fear":整数-10..10,"debt":整数-10..10},'
            '"memory_writes":[{"who":"sailor|girl|oldman","type":"promise|gift|threat|secret|truth","text":"玩家做过的事"}],'
            '"intent":"deflect|reveal|threaten|bargain|silent"}'
        )

    def propose(self, npc, player_input, state, memories, strict=False):
        import json
        import time
        import urllib.error
        import urllib.request

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.system_prompt(npc, state, memories)},
                {"role": "user", "content": player_input},
            ],
            "max_tokens": 200,
            "temperature": 0.3 if strict else self.temperature,
            "response_format": {"type": "json_object"},
        }
        if "Qwen" in self.model or "qwen" in self.model:
            payload["enable_thinking"] = False
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = time.time()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise ProviderError(f"请求 API-Inference 失败: {exc}") from exc
        self.last_latency = time.time() - started
        choices = body.get("choices") or []
        if not choices:
            raise ProviderError(f"响应缺少 choices: {str(body)[:200]}")
        message = choices[0].get("message") or {}
        data = parse_json_content(message.get("content") or "")
        data.setdefault("npc", npc)
        return data
