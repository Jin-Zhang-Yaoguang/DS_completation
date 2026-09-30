# V45 预注册：动态终局库存抢跑

V37 只前置冻结路线中可见的未来 SELL；step 716 起的 `_terminal_liquidation` 会按真实剩余 shed 动态补卖，未包含在 `_future_sells` 中。V45 在 step 715、仅对 clone-like 对手，把当前动作后仍可执行的 premium shed 余量提前卖出。715 与 716 之间没有先于 716 市场结算的需求恢复；下一步终局清仓按实际剩余库存运行，因此不会重复出售。

- 父代：`v37_preterminal_boundary_preempt`。
- 活动金牌门：V19、V20、V21/V29、V32、V33、V34、V37。
- 烟测：内部 seeds `45001-45008`，224 场；必须实际前置终局库存、总体不低于父代且无负翻转。
- 通过后 Development 1,792 场、Confirmation 7,168 场。

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
