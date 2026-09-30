# V34 预注册：需求边界前的动态 premium 前移

## 冻结假设

官方引擎里市场库存不会随时间自行减少；除玩家交易外，只有商店或城镇消费会降低库存并恢复后续卖价。[VERIFY: official_kaggriculture.py:627] [VERIFY: official_kaggriculture.py:737]

因此，当 V33 未来计划出售 premium 商品，而当前到原出售时点之间既没有该商品的已知需求，也不跨未知商店解锁点时，等待没有价格恢复收益。V34 保留 V33 的 horizon 1-4 行为，只把同一安全条件推广到下一需求边界，最长 23 步；24 步城镇消费形成天然上界，不搜索窗口参数。[VERIFY: v34_demand_boundary_preempt/main.py:237] [VERIFY: v34_demand_boundary_preempt/main.py:274]

## 冻结门控

- 父代：`v33_demand_gap_horizon4`。
- 活动金牌行为门：V19、V20、V21/V29、V32、V33，共 5 个。
- 机制烟测：内部 seeds `34001-34008`，候选/父代对全部 5 个门、双座位，共 160 场；必须存在 horizon >= 5 的动作，总体配对得分不低于父代且无负翻转。
- Development：64 个未暴露官方 Replay source，共 1,280 场。
- Confirmation：另 256 个未暴露 source，共 5,120 场。
- 不在 Replay 上搜索最长窗口、价格阈值或前移比例。

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
