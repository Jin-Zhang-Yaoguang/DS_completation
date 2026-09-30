# V52 Terminal Route Acceleration

V52 在 clone-like 对局中，把 step 714 距仓库入口 1 格、携带可售商品且原计划 `COLLECT_FERTILIZER` 的 actor 提前送入仓库，step 715 DROP+SELL；其他路线和市场控制保持 V51。

- 父代：`v51_post_action_terminal_sell`。
- 机制烟测：288 场，触发 108 次、1,296 单位，PGU `+2.78pp`，`8/136/0`。
- Development：64 source、9 个金牌门、2,304 场；PoolScore 93.66%，PGU `+3.69pp`，95% CI `[+3.26,+4.12]pp`，`87/1063/2`。
- Confirmation：另 256 source、9,216 场；PoolScore 90.07%，PGU `+2.70pp`，95% CI `[+2.34,+3.06]pp`，`268/4320/20`。
- 直接 V51 得分率 74.12%，95% CI `[70.90%,77.34%]`；灾难率不变，CVaR10 改善。
- package parity 16/16；官方 Python 1.32.7 parity 576/576，零错误。

决策：`PROMOTE_LOCAL_GOLD`，当前 Goal 第 7/15 个新本地金牌，未提交 Kaggle。
