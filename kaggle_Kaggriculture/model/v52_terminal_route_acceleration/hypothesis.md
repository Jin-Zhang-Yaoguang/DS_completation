# V52 预注册：终局携货路线加速

V51 终局审计显示，step 714 有携带可售商品、距仓库入口 1 格的 actor 仍执行 `COLLECT_FERTILIZER`，导致整批货物延后至 step 716 才出售。终局只剩 4 个动作，新增 1 个 fertilizer 的生产用途已经消失；在 clone-like 对局中，提前成交整批库存的价格优先权可能高于这 1 个 fertilizer。

V52 只对 step 714、clone distance 不超过 6、距离入口恰为 1、携带可售商品且动作恰为 `COLLECT_FERTILIZER` 的 actor 改为最短一步进仓；step 715 对同一 actor 执行 DROP，并复用 V51 projected-shed SELL。其他单位、路线和市场控制不变。

- 父代：`v51_post_action_terminal_sell`。
- 活动金牌门：V19、V20、V21/V29、V32、V33、V34、V37、V46、V51。
- 烟测：内部 seeds `52001-52008`，双座位，候选/父代合计 288 场。
- 烟测门槛：route event/units 均非零、PGU 不低于父代、负向配对为 0、零运行错误。
- 通过后 Development 2,304 场，Confirmation 9,216 场。

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
