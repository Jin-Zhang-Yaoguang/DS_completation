# V13C：A2 + V8-only no-WOOL

预注册差异只有一项：仅当 learned Router 已选择 `baseline_v8` 时，WOOL
恢复父策略出售量；`baseline_v5` 继续执行 A2 的 EGG/MILK/WOOL 节流。

动机是 V5 分支在既有 formal 证据中对 learned Router 较强，不应把 V8 路线
发现的 WOOL 风险外推到 V5。候选不改变 worker、路线、订单顺序或安全守卫；
V13 专属逻辑异常时保留 A2 决策。

工程实现阶段只使用既有 QA seeds；候选冻结后才运行 V13 独立 screen 与
confirmatory。最终对 r002/A2 的 Kaggle 得分率为 77.50%/61.25%，两者
source-cluster bootstrap 95% CI 下界均高于 50%。

2026-08-24（Asia/Taipei）经用户授权提交为 Kaggle Submission `55719781`，
描述 `v13C: A2 + V8-only no-WOOL throttle; dual-anchor confirmed`。状态
`COMPLETE`，初始 Rating 600.0；Validation Episode `97749443` 为 720 states、
双席位 `DONE/DONE`、719 条动作与日志、零 stdout/stderr，奖励
27922/28061。线上归档 SHA256 仍为
`ef279bbc937c73027ce17293aba19eeaa419563d2093880487ec9849400af0c1`。
