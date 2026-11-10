# 灯塔第七夜 · Lighthouse: Seventh Night

AI NPC 互动叙事小品。风暴夜的孤岛灯塔，最后一班船还有三小时到，救生艇只有一个位置。三个 NPC、三组可量化状态、四个结局。

> 参赛作品：魔搭 AI+∞ 开发者创作大赛 第三期「AI 造游戏」· 故事与 AI NPC 赛道
> 当前阶段：**W1 完成**（规则层 + 单测 + CLI）。W2-W4 见 `docs/技术方案_v1.md`。

## 设计原则：LLM 只提案，规则层裁判

```
玩家输入
   │
   ▼
LLM 适配层 ──► 提案 {reply, deltas, memory_writes, intent}
   │                │
   │                ▼
   │         契约校验（字段/范围/intent 枚举）
   │                │ 非法 → 重试 1 次 → 兜底台词，deltas 归零
   ▼                ▼
规则层 StateMachine（纯 Python，零 LLM）
   · 状态钳制：trust / fear / debt ∈ 0..100，单轮 delta ∈ -10..+10
   · 阈值闸门：trust<40 拒交钥匙｜fear>70 只能沉默｜debt≥60 必须说真话
   · 结局判定：只由状态组合 + 旗帜 + 物资计数决定，不由 LLM 选
   │
   ▼
记忆层（只记玩家做过的事）+ 状态面板
```

## 快速开始

```bash
python3 -m unittest discover -s tests -v   # 84 个用例
python3 cli.py --demo --save-dir saves     # 四条路线复现四个结局
python3 cli.py                             # 交互模式（用脚本 NPC，不联网）
```

零第三方依赖（仅 Python 3.9+ 标准库）。

### 接入真实模型（可选）

```bash
export MODELSCOPE_API_KEY=ms-xxxxxxxx
export MODELSCOPE_API_BASE=https://api-inference.modelscope.cn/v1
export MODELSCOPE_MODEL=Qwen/Qwen3.8-Flash-Next
python3 scripts/smoke_llm.py               # 三轮真实对局
```

可用任意 OpenAI 兼容端点；Qwen 系列会自动关闭 thinking 以压低时延（实测单轮约 2.2s）。
模型输出非法时自动重试一次，仍失败则用角色预置兜底台词且状态不变。

## 四个结局

| 结局 | 触发条件（规则层） |
|---|---|
| 钥匙 | 船员 trust ≥ 60 且拿到钥匙 |
| 同舟 | 三个 NPC trust 都 ≥ 50 且给出 ≥ 2 件物资 |
| 守灯 | 老人 trust ≥ 55 且得知灯塔真相 |
| 第七夜 | 任一 NPC trust < 15，或以上都不满足 |

## 目录

```
engine/models.py     数据结构（NPCState / MemoryEntry / TurnResult）
engine/rules.py      钳制、闸门、结局判定、提案契约校验
engine/memory.py     记忆存取（同角色优先 + 关键词 + 新鲜度）
engine/providers.py  ScriptedProvider（确定性）/ InvalidProvider（降级测试）
engine/game.py       单局编排、闸门执行、存档与二周目
engine/script.py     NPC 设定、初始状态、剧本路线（改剧情只改这里）
cli.py               CLI 入口
tests/               规则层与编排层单测
docs/                概念设计与技术方案
```

## 路线图

- [x] W1 规则层 + 单测 + CLI（11-10）
- [x] W2-1 LLM 通道（ModelScope API-Inference / 任意 OpenAI 兼容端点，11-10 实测 2.2s/轮）
- [ ] W2-2 前端 UI + 记忆层打磨
- [ ] W3 ComfyUI 美术 / 音效 / 规则层日志面板 / 二周目
- [ ] W4 创空间部署 + 演示视频 + 手记

## License

MIT
