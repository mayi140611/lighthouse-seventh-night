# 提交前自查报告

- 时间：2026-11-10 14:01:56
- 目标：https://modelscope.cn/studios/mayi140611/lighthouse-seventh-night
- 加载耗时：11.75s

## 连打 10 轮
- 成功：10/10
- 时延：平均 2.89s，最大 3.71s（阈值 <6s：通过）
- 控制台错误：5 条（第三方资源 401/HTTP2，非应用异常）

## 手机布局
- iPhone 13 设备模拟：通过（单列，需下滑；无横向裁剪）

## 单测与兜底
- 单测 rc=0：OK
- 断网兜底：fallback=True，回复「“别问我，我只想活着上船。”」

## 明细
```json
[
 {
  "n": 1,
  "npc": "sailor",
  "latency_s": 2.46,
  "turn_advanced": true,
  "fallback": false,
  "ending": false
 },
 {
  "n": 2,
  "npc": "sailor",
  "latency_s": 2.45,
  "turn_advanced": true,
  "fallback": false,
  "ending": false
 },
 {
  "n": 3,
  "npc": "girl",
  "latency_s": 3.07,
  "turn_advanced": true,
  "fallback": false,
  "ending": false
 },
 {
  "n": 4,
  "npc": "oldman",
  "latency_s": 2.46,
  "turn_advanced": true,
  "fallback": false,
  "ending": false
 },
 {
  "n": 5,
  "npc": "sailor",
  "latency_s": 3.37,
  "turn_advanced": true,
  "fallback": false,
  "ending": false
 },
 {
  "n": 6,
  "npc": "girl",
  "latency_s": 3.37,
  "turn_advanced": true,
  "fallback": false,
  "ending": false
 },
 {
  "n": 7,
  "npc": "oldman",
  "latency_s": 2.46,
  "turn_advanced": true,
  "fallback": false,
  "ending": false
 },
 {
  "n": 8,
  "npc": "sailor",
  "latency_s": 3.07,
  "turn_advanced": true,
  "fallback": false,
  "ending": false
 },
 {
  "n": 9,
  "npc": "girl",
  "latency_s": 2.49,
  "turn_advanced": true,
  "fallback": false,
  "ending": false
 },
 {
  "n": 10,
  "npc": "oldman",
  "latency_s": 3.71,
  "turn_advanced": true,
  "fallback": false,
  "ending": false
 }
]
```