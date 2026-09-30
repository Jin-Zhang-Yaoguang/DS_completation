# V33 Demand-Gap Horizon-4 Preempt

V33 继承 V32 的 1–3 步 premium 前移，只新增第 4 步机会：当前至原出售前没有该商品的已知 town/shop 需求，且不跨未知商店解锁时才提前出售；所有前移量仍按原 future step/item 偿还。[VERIFY: v33_demand_gap_horizon4/main.py:237] [VERIFY: v33_demand_gap_horizon4/main.py:272]

一次性 Confirmation 使用 256 个未暴露官方 Replay source，对 V19/V20/V21/V32、双座位，候选/父代共 4,096 场：PoolScore 90.53%，PGU `+5.62pp`，95% CI `[+4.93,+6.25]pp`，翻转 `223/1825/0`；对前三条旧金牌胜负不变，对直接父代 V32 提升 `+22.46pp`。[VERIFY: v33_demand_gap_horizon4/confirmation_summary.json:15] [VERIFY: v33_demand_gap_horizon4/confirmation_summary.json:28] [VERIFY: v33_demand_gap_horizon4/confirmation_summary.json:42]

直接父代得分率 72.46%，95% CI `[69.73%,75.20%]`；灾难失败率不变，CVaR10 margin 略有改善，256 source 和八种首商店均有动作支持。[VERIFY: v33_demand_gap_horizon4/confirmation_summary.json:60] [VERIFY: v33_demand_gap_horizon4/confirmation_summary.json:70] [VERIFY: v33_demand_gap_horizon4/confirmation_summary.json:73]

包内外 16/16 场逐动作、逐奖励一致；官方 Python 1.32.7 对 16 source 复算 256 场，全部奖励精确一致、`DONE/DONE`、719 calls、零错误。[VERIFY: v33_demand_gap_horizon4/package_qa_results.json:2] [VERIFY: v33_demand_gap_horizon4/official_parity_results.json:2]

状态：`PROMOTE_LOCAL_GOLD`，本轮第 2 个新金牌；归档 SHA256 `54b01befda00aacd101a82c605eb331bc78243fb1a744f3c62e3c84775c44397`，未自动提交 Kaggle。[VERIFY: v33_demand_gap_horizon4/submission_manifest.json:1]
