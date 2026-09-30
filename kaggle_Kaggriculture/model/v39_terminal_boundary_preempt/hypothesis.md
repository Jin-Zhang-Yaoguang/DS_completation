# V39 预注册：覆盖最后三个可行动步

V37 为避免跨终局清仓而排除了 future step 716-718，但游戏仍会完整执行这些市场动作。V39 保留 V37，只允许前置原计划中位于 716-718 的 premium SELL，并在原步按商品偿还；任何 future step >=719 继续拒绝。实际库存已在提前出售时减少，终局动态清仓只处理剩余库存，不会重复卖出。

- 父代：`v37_preterminal_boundary_preempt`。
- 活动金牌门：V19、V20、V21/V29、V32、V33、V34、V37。
- 烟测：内部 seeds `39001-39008`，224 场；必须出现 terminal event、总体不低于父代且无负翻转。
- 通过后 Development 1,792 场、Confirmation 7,168 场。

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
