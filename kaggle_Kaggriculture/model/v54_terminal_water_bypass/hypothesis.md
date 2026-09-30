# V54 预注册：终局无回收浇水旁路

V53 审计显示，step 712 仍有携带 2,320 单位可售商品、距仓库 3–4 格的 actor 执行 `WATER`，之后连续返仓。距离与剩余时长决定这些 actor 已不可能返回田块收获本次浇水新增产量，因此该动作没有可回收终局价值，却延迟携货出售一回合。

V54 只对 step 712、clone distance 不超过 6、距入口 3–4 格、携带可售商品且动作恰为 `WATER` 的 actor 改为最短返仓；后续每步保持最短路线，到达入口即 DROP，并复用 V51 同回合 SELL。其余行为保持 V53。

- 父代：`v53_terminal_access_flush`。
- 活动金牌门：V19、V20、V21/V29、V32、V33、V34、V37、V46、V51、V52、V53。
- 烟测：内部 seeds `54001-54008`，双座位，候选/父代合计 352 场。
- 烟测门槛：water bypass event/units 非零、PGU 不低于父代、负向配对为 0、零运行错误。
- 通过后 Development 2,816 场，Confirmation 11,264 场；Confirmation 每日期哈希候选池冻结为 70（正式配额仍为 43/43/43/43/42/42）。

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
