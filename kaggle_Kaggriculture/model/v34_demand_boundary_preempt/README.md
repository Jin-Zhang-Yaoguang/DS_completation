# V34 Demand-Boundary Premium Preempt

V34 继承 V33，只把 premium 计划出售的安全前看窗口从固定第 4 步推广到下一个已知需求或未知商店解锁边界，最长 23 步。官方引擎中市场库存不会自行衰减，因此边界前等待没有价格恢复收益。[VERIFY: main.py:237] [VERIFY: main.py:274]

- Development：64 个未暴露官方 source、5 个活动金牌门、双座位，候选/父代共 1,280 场；PGU `+5.70pp`，95% CI `[+4.92,+6.48]pp`，`65/575/0`。[VERIFY: development_summary.json:15]
- Confirmation：另 256 个未暴露 source，共 5,120 场；PoolScore `87.30%`，PGU `+5.20pp`，95% CI `[+4.57,+5.82]pp`，`234/2326/0`。[VERIFY: confirmation_summary.json:15]
- 直接父代得分率 `73.83%`，95% CI `[71.29%,76.56%]`；灾难率不变，CVaR10 改善。[VERIFY: confirmation_summary.json:62]
- 包内外 16/16 场逐动作、逐奖励一致；官方 Python 1.32.7 复算 320/320 场奖励与胜负方向完全一致，零错误。[VERIFY: package_qa_results.json:2] [VERIFY: official_parity_results.json:2]

决策：`PROMOTE_LOCAL_GOLD`。这是当前 Goal 的第 3/8 个新本地金牌，未提交 Kaggle。
