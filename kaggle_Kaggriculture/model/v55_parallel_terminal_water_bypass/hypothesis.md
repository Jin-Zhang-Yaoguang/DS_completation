# V55 预注册：并行终局浇水旁路

V54 每局只接管第一个符合条件的 WATER actor。V54 后审计仍显示 step 712 有 672 单位携货 actor 在距仓库 3 格时执行 WATER；这类 actor 同样已经进入不可返回收获的终局返仓窗口。

V55 保留 V54 对第一个 actor 的处理，只对 V54 动作之后仍为 WATER、距入口 3–4 格且携货的其余 actor 并行建立最短返仓状态，到达即 DROP+SELL。不会扩大到 HARVEST、COLLECT_FERTILIZER 或非 clone-like 对局。

- 父代：`v54_terminal_water_bypass`。
- 活动金牌门：V19、V20、V21/V29、V32、V33、V34、V37、V46、V51、V52、V53、V54。
- 烟测：内部 seeds `55001-55008`，双座位，候选/父代合计 384 场。
- 烟测门槛：parallel water event/units 非零、PGU 不低于父代、负向配对为 0、零运行错误。
- 通过后 Development 3,072 场；Confirmation 12,288 场。
- 正式 Replay 日期：完全未使用的 2026-08-20 与新增 2026-08-27，Development 各 32，Confirmation 各 128。

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
