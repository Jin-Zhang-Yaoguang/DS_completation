# V56 Terminal Fertilizer Route

V56 尝试把 step 712、距仓库 4 格且携货的 `COLLECT_FERTILIZER` actor 提前送回仓库。

- 父代：`v54_terminal_water_bypass`。
- 烟测：384 场，PGU `+2.08pp`，`4/188/0`。
- Development：3,072 场，PGU `+0.13pp`，95% CI `[-0.13,+0.39]pp`。
- Confirmation：12,288/12,288 零错误，PGU `0.00pp`，95% CI `[-0.15,+0.15]pp`，`18/6108/18`。
- 直接父代得分率：50.39%，95% CI `[48.83%,51.95%]`。

决策：`REJECT_CONFIRMATION`。不执行 package/官方引擎 QA，也不注册为金牌。
