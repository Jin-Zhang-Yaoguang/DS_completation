# V32 晋级决策

决策：`PROMOTE_LOCAL_GOLD`。

V32 的唯一策略变化是同质对手下把 premium 计划出售前看窗口从 1 步扩成 3 步，并逐未来回合偿还；生产路线和后续安全链保持 V21。[VERIFY: v32_clone_horizon_preempt/main.py:227] [VERIFY: v32_clone_horizon_preempt/main.py:237] [VERIFY: v32_clone_horizon_preempt/main.py:1594]

Development 为 `+18.49pp` 且零负翻转；一次性 Confirmation 为 `PGU +18.03pp`、95% CI `[+17.06,+19.01]pp`，PoolScore 96.35%，对每条金牌谱系均高于 95%，456 次正翻转、0 次负翻转，全部强度、尾部和真实性门通过。[VERIFY: v32_clone_horizon_preempt/development_summary.json:15] [VERIFY: v32_clone_horizon_preempt/confirmation_summary.json:15] [VERIFY: v32_clone_horizon_preempt/confirmation_summary.json:84]

提交包逐动作等价和官方 Python 1.32.7 的 192 场精确复算均通过。[VERIFY: v32_clone_horizon_preempt/package_qa_results.json:2] [VERIFY: v32_clone_horizon_preempt/official_parity_results.json:2]

因此 V32 加入 `golden_model.md`，成为后续版本的直接父代与活动金牌门控。线上 Kaggle 提交不属于本轮自动动作，仍需用户单独授权。
