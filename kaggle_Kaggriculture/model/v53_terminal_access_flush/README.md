# V53 Terminal Access Flush

V53 在 clone-like 对局中，把 step 716 已位于仓库入口、携带可售商品且原计划 `COLLECT_FERTILIZER` 的 actor 改为当回合 DROP+SELL；其余行为保持 V52。

- 父代：`v52_terminal_route_acceleration`。
- 机制烟测：320 场，触发 120 次、1,080 单位，PGU `+5.00pp`，`14/146/0`。
- Development：64 source、10 个金牌门、2,560 场；PoolScore 89.22%，PGU `+3.52pp`，95% CI `[+3.05,+3.98]pp`，`85/1195/0`。
- Confirmation：另 256 source、10,240 场；PoolScore 90.90%，PGU `+3.87pp`，95% CI `[+3.48,+4.27]pp`，`350/4770/0`。
- 直接 V52 得分率 79.10%，95% CI `[76.56%,81.64%]`；灾难率不变，CVaR10 改善。
- package parity 16/16；官方 Python 1.32.7 parity 640/640，零错误。

决策：`PROMOTE_LOCAL_GOLD`，当前 Goal 第 8/15 个新本地金牌，未提交 Kaggle。
