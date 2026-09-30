# V56 预注册：step 712 fertilizer carrier 返仓

V54 后审计显示，step 712 仍有距仓库 4 格、携带可售商品的 actor 执行 `COLLECT_FERTILIZER`。与 V55 的 WATER 不同，该机会成本严格为当前动作可新增的 1 个 fertilizer，不会改变作物供其他 actor 收获的产量；V52/V53 已在 714/716 验证同类交换。

V56 只对 step 712、clone distance 不超过 6、距入口恰为 4、携货且动作恰为 `COLLECT_FERTILIZER` 的 actor 改为最短返仓，到达即 DROP+SELL。其余行为保持 V54。

- 父代：`v54_terminal_water_bypass`。
- 活动金牌门：V19、V20、V21/V29、V32、V33、V34、V37、V46、V51、V52、V53、V54。
- 烟测：内部 seeds `56001-56008`，双座位，候选/父代合计 384 场。
- 烟测门槛：event/units 非零、PGU 不低于父代、负向配对为 0、零运行错误。
- 通过后 Development 3,072 场、Confirmation 12,288 场；正式 Replay 使用 08-20/08-27。

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
