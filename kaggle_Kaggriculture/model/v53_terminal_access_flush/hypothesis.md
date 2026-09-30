# V53 预注册：终局入口立即清货

V52 终局审计显示，step 716 仍有携带可售商品且已经位于仓库入口的 actor 执行 `COLLECT_FERTILIZER`，整批货物要到 717 才 DROP+SELL。此时只剩 3 个动作，新增 fertilizer 已无生产用途；提前一回合卖出整批携货可在同质对手之前获取价格。

V53 只对 step 716、clone distance 不超过 6、位于仓库入口、携带可售商品且动作恰为 `COLLECT_FERTILIZER` 的 actor 改为 DROP，并复用 V51 的同回合 projected-shed SELL。其余行为保持 V52。

- 父代：`v52_terminal_route_acceleration`。
- 活动金牌门：V19、V20、V21/V29、V32、V33、V34、V37、V46、V51、V52。
- 烟测：内部 seeds `53001-53008`，双座位，候选/父代合计 320 场。
- 烟测门槛：access event/units 非零、PGU 不低于父代、负向配对为 0、零运行错误。
- 通过后 Development 2,560 场，Confirmation 10,240 场。

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
