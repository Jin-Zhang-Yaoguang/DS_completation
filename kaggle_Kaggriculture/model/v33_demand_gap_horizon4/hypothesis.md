# V33 预注册：无需求间隙的第 4 步 premium 前移

## 冻结假设

V32 的 3 步窗口覆盖 4-turn 商店消费周期内的大多数抢跑机会，并在盲确认中显著战胜 V19/V20/V21。[VERIFY: v32_clone_horizon_preempt/main.py:255] [VERIFY: v32_clone_horizon_preempt/confirmation_summary.json:15]

仍有一类合法机会：某 premium 商品不属于当前已解锁商店，未来第 4 步存在计划 SELL，而当前至原出售前没有该商品的 town/shop 需求。此时等待不会获得需求恢复价格，先卖可在 V32 之前占据非线性市场库存。[VERIFY: v33_demand_gap_horizon4/main.py:237] [VERIFY: v33_demand_gap_horizon4/main.py:282]

V33 完整保留 V32 的 horizon 1–3 行为；只对 horizon 4 增加严格门：中间没有该商品的已知 shop/town-center demand，且不跨尚未公开身份的商店解锁点。前移量仍按未来 step/item 记账偿还。[VERIFY: v33_demand_gap_horizon4/main.py:237] [VERIFY: v33_demand_gap_horizon4/main.py:272]

## 冻结门控

- 父代：`v32_clone_horizon_preempt`。
- 活动金牌行为门：V19、V20、V21/V29、V32，共 4 个。
- 机制烟测：内部 seeds `33001–33008`，候选/父代对全部 4 个门、双座位，共 128 场；必须有 horizon-4 动作支持、总体配对得分不低于父代且无负翻转。
- Development：64 个未暴露官方 Replay source，盐 `kaggriculture-v33-dev-v1`，候选/父代对 4 个金牌门、双座位，共 1,024 场。
- Confirmation：Development 通过后固定另 256 个 source，盐 `kaggriculture-v33-confirm-v1`，共 4,096 场。
- 全部门槛采用更新后的 `loop_model.md`，不在 V33 内搜索第 4 步门或窗口参数。[VERIFY: loop_model.md:163] [VERIFY: loop_model.md:234]

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
