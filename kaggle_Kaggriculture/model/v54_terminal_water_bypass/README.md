# V54 Terminal Water Bypass

V54 在 clone-like 对局中，把 step 712 已携货、距仓库 3–4 格且原计划 `WATER` 的 actor 改为立即最短返仓，到达后 DROP+SELL；其余行为保持 V53。

- 父代：`v53_terminal_access_flush`。
- 机制烟测：352 场，触发 176 次、2,288 单位，PGU `+3.98pp`，`14/162/0`。
- Development：64 source、11 个金牌门、2,816 场；PoolScore 90.63%，PGU `+3.91pp`，95% CI `[+3.41,+4.40]pp`，`100/1308/0`。
- Confirmation：另 256 source、11,264 场；PoolScore 91.29%，PGU `+4.61pp`，95% CI `[+4.23,+4.99]pp`，`455/5177/0`。
- 直接 V53 得分率 83.59%，95% CI `[80.86%,86.13%]`；灾难率不变，CVaR10 改善。
- package parity 16/16；官方 Python 1.32.7 parity 704/704，零错误。

决策：`PROMOTE_LOCAL_GOLD`，当前 Goal 第 9/15 个新本地金牌，未提交 Kaggle。
