# Q2b conservative no-equality：exact-A2 shadow 最终 QA

## 结论

**GO（限定真实对手为 exact A2）。** Q2b 只删除 full public-production equality，同时保留 `clone_distance <= 4`。在原 3 个 package-QA seed、双席位的最终 4314-call 协议中：

- 完整 private state：`4314 / 4314` exact；
- predicted A2 action：`4314 / 4314` exact；
- day-boundary：`174 / 174` private exact，`174 / 174` action exact；
- SELL queue reorder：`76` 次；
- first mismatch：`null`；
- `shadow_faults = 0`，`shadow_update_errors = 0`；
- 6 场末尾均 `shadow_trusted = true`、双方 `DONE`。

## 最终源码绑定

- Q2b wrapper SHA-256：`698b913ea71f36373c48e06769fd47854b432ad1578dbe620d2ec9d96ef1c284`；
- stateful core SHA-256：`ec915bd66402ad6fd0e3da0bfebdb37fc35c6082046aaf5f47e9de0490f3c0ca`；
- QA driver SHA-256：见 `exact_a2_shadow_q2b_qa.json` 的 `artifacts.qa_driver_sha256`；
- 通用 truth harness SHA-256：`fd2d039ff58abf0545bf4b259d8e4131ce0758d7c08bb03871c3d1a206cfd50c`。

## 隔离

仅使用已暴露的 `93451031`、`93451032`、`93451033`，每个 seed 覆盖候选 seat 0/1。V14 fresh screen、confirmatory、test 均未消费；被测 Q2b 与 core 均未修改。

## 边界

该 GO 证明 Q2b 在 exact-A2 路径上的 private forward 与 action prediction 逐步精确，不构成对任意未知对手身份识别的证明。
