# V35 预注册：全商品需求边界前置

## 冻结假设

官方市场对每一种商品都按共享库存逐单位报价，SELL 会增加该商品库存并压低后续报价；该外部性并不只存在于 V34 的四种 premium 商品。[VERIFY: community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim/sim/sim.hpp:554] [VERIFY: community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim/sim/sim.hpp:592]

V35 完整保留 V34 的 premium 商品优先级与动作，只在仍有 market 槽时，把 WHEAT、CARROT、TOMATO、EGG、FERTILIZER 的未来计划 SELL 按相同需求边界前置；不修改生产、购买、需求延迟或安全执行器。商品范围由官方可售集合直接决定，不在 Replay 上筛选商品。

## 冻结门控

- 父代：`v34_demand_boundary_preempt`。
- 活动金牌行为门：V19、V20、V21/V29、V32、V33、V34，共 6 个。
- 机制烟测：内部 seeds `35001-35008`，候选/父代、全部 6 门、双座位，共 192 场；必须有非 premium 前置动作，总体配对得分不低于父代且无负翻转。
- Development：64 个未暴露官方 Replay source，共 1,536 场。
- Confirmation：另 256 个未暴露 source，共 6,144 场。

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
