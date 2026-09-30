# V51 预注册：终局同回合入仓补卖

V46 在 step 716–718 的 `_terminal_liquidation` 只读取回合开始时的 shed；但随后 unit action 可能在同回合执行 `DROP` 或 `PLACE`。V46 的 `_projected_shed` 能看见这些入仓量，却没有在最终动作返回前为其补充 SELL，因此最后三小时可能残留可变现金币。

V51 保留 V46 的单位动作和既有市场动作，只在 step 716–718、所有安全执行器完成后，按 projected shed 减去已计划 SELL，补齐正的可执行余量。优先扩展同商品 SELL；仅在市场少于 10 条时新增订单，再按既有规则重排。

- 父代：`v46_full_terminal_front_run`。
- 活动金牌门：V19、V20、V21/V29、V32、V33、V34、V37、V46。
- 机制烟测：内部 seeds `51001-51008`，双座位，候选/父代合计 256 场。
- 烟测门槛：`post_units > 0`、PGU 不低于父代、负向配对为 0、零运行错误。
- 通过后 Development：64 个冻结 Replay source，2,048 场。
- 通过后 Confirmation：另 256 个未暴露 Replay source，8,192 场。

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
