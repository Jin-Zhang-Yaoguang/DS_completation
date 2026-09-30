# V14 stateful queue：exact-A2 shadow 真值 QA

## 结论

**GO（仅对“真实对手就是 exact A2”这一身份假设）。** 候选内部 opposite-seat A2 shadow 在 3 个既有 QA seed、双席位的 6 场完整闭环中，与真实 opposite-seat A2 达到：

- 完整 private state：`4314 / 4314` calls exact，首次 mismatch 为 `null`；
- 预测 action：`4314 / 4314` calls exact，首次 mismatch 为 `null`；
- day-boundary 输入：`174 / 174` private exact，`174 / 174` action exact；
- 候选确实发生 `38` 次 SELL queue reorder，因而不是“零干预时自然相等”的空测试；
- `shadow_faults = 0`，`shadow_update_errors = 0`，6 场末尾均 `shadow_trusted = true`；
- 每场 `719` 次双方对齐调用、`720` 个环境 step、双方状态均为 `DONE`。

## 验证方法

没有修改或插桩 `prototype_queue_solver.py`。QA 脚本只给候选已有的 `opponent_shadow` 套透明 wrapper，并给同一场中的真实 opposite-seat A2 套独立 wrapper。每一步直接比较：

1. 候选注入内部 A2 shadow 的完整 private observation；
2. 真实 opposite-seat A2 收到的完整 private observation；
3. 内部 A2 shadow 预测 action；
4. 真实 opposite-seat A2 实际 action。

wrapper 透传 `_selected_branch` 等属性，所以不会关闭候选的 queue intervention。比较覆盖候选在 seat 0 和 seat 1 的两种执行顺序。

## 数据隔离

- seeds：`93451031`、`93451032`、`93451033`；
- 来源：`v12a2_no_shop_gate/package_qa.py` 已公开使用的 3 个 package-QA seeds；
- V14 fresh screen：未消费；
- V14 confirmatory：未消费；
- test：未消费。

## 证据绑定

- 被测 prototype SHA-256：`3ea07d561526e0375f68425f986973ee0ca9ce4b456808a5b4f574c29c7e2968`；
- QA 脚本 SHA-256：`fd2d039ff58abf0545bf4b259d8e4131ce0758d7c08bb03871c3d1a206cfd50c`；
- 机器可读结果：`exact_a2_shadow_qa.json`；
- 可复跑脚本：`verify_exact_a2_shadow.py`。

## GO 的边界

这项 QA 证明的是：在对手确为所绑定 A2 代码时，stateful private forward model 与 opponent action prediction 在已覆盖路径上逐步精确。它**不证明**任意未知 Kaggle 对手可由公共状态识别为 A2；未知对手仍只能依赖候选的公开状态 conformance 与 fail-closed 机制。
