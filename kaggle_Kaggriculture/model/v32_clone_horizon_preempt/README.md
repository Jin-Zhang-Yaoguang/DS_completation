# V32 Clone-Horizon Premium Preempt

V32 是 V21 的单机制升级：当双方公开农场的 clone distance 不超过 6 时，把 premium 商品的计划出售从固定前看 1 步扩展到 3 步；每笔前移量按原未来回合和商品分别记账并扣回，不改变生产 Router、V20 需求延迟和安全执行器。[VERIFY: v32_clone_horizon_preempt/main.py:188] [VERIFY: v32_clone_horizon_preempt/main.py:237] [VERIFY: v32_clone_horizon_preempt/main.py:1594]

## 冻结确认结果

- 256 个未暴露官方 Replay source，覆盖 2026-08-21 至 08-26、八种首商店；候选和父代对 V19/V20/V21、双座位共 3,072 场，全部完成且零安全错误。[VERIFY: v32_clone_horizon_preempt/confirmation_summary.json:9] [VERIFY: v32_clone_horizon_preempt/confirmation_summary.json:15]
- PoolScore 96.35%，父代 78.32%；PGU `+18.03pp`，source/date/shop 分层 bootstrap 95% CI `[+17.06,+19.01]pp`，翻转 `456/1080/0`。[VERIFY: v32_clone_horizon_preempt/confirmation_summary.json:20] [VERIFY: v32_clone_horizon_preempt/confirmation_summary.json:22] [VERIFY: v32_clone_horizon_preempt/confirmation_summary.json:42]
- 对 V19/V20/V21 的候选得分率分别为 96.68%/96.48%/95.90%；直接父代 95% CI 为 `[94.34%,97.46%]`。[VERIFY: v32_clone_horizon_preempt/confirmation_summary.json:60] [VERIFY: v32_clone_horizon_preempt/confirmation_summary.json:65]
- 灾难失败率相对父代下降 0.46pp，CVaR10 margin 从 `-2514.44` 改善到 `-1660.09`；256 个 source、八种首商店全部发生有效动作变化。[VERIFY: v32_clone_horizon_preempt/confirmation_summary.json:33] [VERIFY: v32_clone_horizon_preempt/confirmation_summary.json:70] [VERIFY: v32_clone_horizon_preempt/confirmation_summary.json:73]

## 工程确认

- 研究源码与解包提交版 16/16 场逐动作、逐奖励一致，最后 callable 为 `agent`，每场 719 calls。[VERIFY: v32_clone_horizon_preempt/package_qa_results.json:2]
- 官方 `kaggle_environments 1.32.7` 从 Confirmation 固定 16 个 source，对候选/父代、三条金牌谱系、双座位复算 192 场；192/192 奖励精确一致、胜负方向一致、`DONE/DONE`、719 calls，零错误。[VERIFY: v32_clone_horizon_preempt/official_parity_results.json:2]
- 自包含归档 SHA256：`a84feb80cbb52fe96d938ffefaf3ae0e9cd9a069287ec8ec0578a3a464af3dbc`。[VERIFY: v32_clone_horizon_preempt/submission_manifest.json:1]

最终状态：`PROMOTE_LOCAL_GOLD`。它是本轮 8 个新金牌目标中的第 1 个；未自动提交 Kaggle。
