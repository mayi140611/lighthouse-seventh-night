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
python3 server.py --port 8080              # 网页版：状态面板 / 规则层日志 / 结局
python3 server.py --provider modelscope    # 网页版接线上模型（标准库，零依赖）
```

线上创空间（Gradio 入口）：https://modelscope.cn/studios/mayi140611/lighthouse-seventh-night

本地两种入口：

```bash
pip install -r requirements.txt
python3 app.py                                  # Gradio（与线上一致，7860）
uvicorn app_fastapi:app --port 7860             # 标准库版网页（FastAPI）
```

部署步骤见 `docs/创空间部署.md`。

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

## 美术

3 张场景背景（灯塔外景 / 礁石岸边 / 灯室内部）+ 3 张剪影立绘，ComfyUI `qwen_image_2.1` 生成，统一「剪影 + 雾 + 冷蓝黑」风格；网页按当前对话对象自动切背景。原图在 `assets/art/`（不入库），网页用压缩版在 `web/art/`。

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
- [x] W2-2 网页 UI（状态面板 / 规则层日志 / 打字机 / 结局与二周目，stdlib 零依赖）
- [x] W3-1 美术：3 背景 + 3 剪影立绘，网页场景随对话对象切换（11-10）
- [ ] W3-2 音效 / 环境声
- [x] W4-1 创空间壳（FastAPI `app.py` + requirements + 部署文档，本地已验证）
- [x] W4-2 创空间上线：https://modelscope.cn/studios/mayi140611/lighthouse-seventh-night （11-10，运行中）
- [ ] W4-3 演示视频 + 参赛手记

## 交付文档

- `docs/演示脚本_3分钟.md`：分镜、旁白、备用方案
- `docs/参赛手记.md`：设计取舍、三个失败与修正、评审权重映射
- `docs/提交清单.md`：12-01 前必交项与自查

## 已知边界

- 网页服务用 Python 标准库 `http.server`，便于本地零依赖运行；创空间要求 FastAPI/Gradio 入口，W4 再包一层壳。
- 记忆引用（NPC 主动提起玩家旧事）目前由提示词与规则层共同保证，尚未做「引用命中率」度量，W3 补。

## License

MIT
