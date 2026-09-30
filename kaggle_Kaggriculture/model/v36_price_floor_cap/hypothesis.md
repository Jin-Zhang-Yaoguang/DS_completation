# V36 预注册：前置出售的价格地板上限

## 冻结假设

官方引擎在 SELL 价格高于 1 时才增加市场库存；价格等于 1 的后续单位不会继续压低市场，也就没有抢在同质对手之前卖出的外部性收益。[VERIFY: community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim/sim/sim.hpp:592]

V36 保留 V34 的商品、需求边界、窗口、生产和安全逻辑，只把每次前置数量限制为“从当前公开库存开始，报价仍高于 1 的单位数”。上限由官方定价函数精确计算，不搜索价格阈值。

## 冻结门控

- 父代：`v34_demand_boundary_preempt`。
- 活动金牌门：V19、V20、V21/V29、V32、V33、V34，共 6 个。
- 机制烟测：内部 seeds `36001-36008`，192 场；必须实际触发价格地板上限、总体不低于父代且无负翻转。
- 通过后 Development 64 source、1,536 场；Confirmation 256 source、6,144 场。

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
