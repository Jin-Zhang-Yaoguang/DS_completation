# V51 Post-Action Terminal Sell

V51 在 step 716–718 的最终动作返回前，用 projected shed 补齐当回合 `DROP`/`PLACE` 新增库存的 SELL；生产路线、单位动作和既有市场计划保持 V46。

- 父代：`v46_full_terminal_front_run`。
- 机制烟测：256 场，补卖 3,744 单位，PGU `+6.25pp`，`15/113/0`。
- Development：64 source、8 个金牌门、2,048 场；PoolScore 94.63%，PGU `+5.81pp`，95% CI `[+5.57,+6.10]pp`，`111/913/0`。
- Confirmation：另 256 source、8,192 场；PoolScore 93.09%，PGU `+6.14pp`，95% CI `[+5.59,+6.71]pp`，`426/3670/0`。
- 直接 V46 得分率 85.74%，95% CI `[83.20%,88.28%]`；灾难率不变，CVaR10 改善。
- package parity 16/16；官方 Python 1.32.7 parity 512/512，零错误。

决策：`PROMOTE_LOCAL_GOLD`，当前 Goal 第 6/15 个新本地金牌，未提交 Kaggle。
