# V50 预注册：终局 carried goods 同回合变现

V46 的 step 715 前置只计算 shed；位于仓库入口且当前动作 PASS 的 farmer/hand 所携带商品仍会等到后续。V50 保留 V46，step 715 对这类零机会成本 actor 选择当前价值最高的携带商品执行 `PLACE`，并把同量 SELL 合并进当回合市场；不覆盖非 PASS 动作，不处理非仓库入口 actor，不超过 100 shed 容量。

- 父代：`v46_full_terminal_front_run`。
- 活动金牌门：V19、V20、V21/V29、V32、V33、V34、V37、V46。
- 烟测：内部 seeds `50001-50008`，256 场；必须实际 flush carried units、总体不低于父代且无负翻转。
- 通过后 Development 2,048 场、Confirmation 8,192 场。

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
