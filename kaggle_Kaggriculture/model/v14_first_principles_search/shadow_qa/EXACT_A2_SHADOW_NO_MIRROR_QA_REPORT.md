# Q2 no-mirror：exact-A2 shadow 真值 QA

## 结论

**GO（严格限定真实对手为所绑定的 exact A2）。** Q2 移除 public-production/clone heuristic 后，在原 3 个 package-QA seed、双席位的 6 场完整闭环中没有出现任何 shadow 真值偏差：

- 完整 private state：`4314 / 4314` calls exact；
- 预测 A2 action：`4314 / 4314` calls exact；
- day-boundary：`174 / 174` private exact，`174 / 174` action exact；
- 首次 mismatch：`null`；
- SELL queue reorder：`76` 次，验证覆盖了实际干预路径；
- `shadow_faults = 0`，`shadow_update_errors = 0`；
- 每场末尾 `shadow_trusted = true`、`conformance_steps = 718`，双方均为 `DONE`。

因此，在 exact-A2 身份成立时，删除冗余 mirror heuristic 没有破坏 private forward model 或 opponent-action prediction。

## 被测代码绑定

- Q2 wrapper SHA-256：`c57213ed8831b96ff990c236fc5d5f2e64e216c72da6a1c9febba4cf4006f604`；
- stateful core SHA-256：`439f5ceaacae2b19edd34b4590947bb1b7302e9583fceec55c037d76dbaac3a0`；
- QA driver SHA-256：`af1c0841ed24f2601613f9b23209dd82f59840519c6ebb7a89dab7d9a7f24b77`；
- 通用 truth harness SHA-256：`fd2d039ff58abf0545bf4b259d8e4131ce0758d7c08bb03871c3d1a206cfd50c`。

## 隔离与方法

- 只使用 `93451031`、`93451032`、`93451033` 三个既有 package-QA seeds；
- 候选 seat 0/1 均覆盖；
- 不修改 Q2 wrapper 或 stateful core，只通过透明 callable wrapper 记录内部 shadow 的输入和输出；
- V14 fresh screen、confirmatory、test 均未消费。

## 边界

本结果证明 Q2 对 exact A2 的 shadow 递推正确，不证明它能从有限公共轨迹唯一识别任意未知对手。陌生或伪装对手的安全性仍取决于 72-step public conformance、V8/V8 gate 和 mismatch 后 fail-closed。
