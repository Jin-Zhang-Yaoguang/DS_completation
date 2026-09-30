# V49 预注册：713/714/715 三阶段终局抢跑

最后一次进入终局窗口前的 shop demand 在 step 712 市场之后执行；step 713、714、715 之间没有需求恢复。V49 以 V46 为父代，完整保留 715，新增 713 与 714 两次基于当步实际可执行余量的清扫；后续阶段只处理新到或未售库存。

- 父代：`v46_full_terminal_front_run`。
- 活动金牌门：V19、V20、V21/V29、V32、V33、V34、V37、V46。
- 烟测：内部 seeds `49001-49008`，256 场；总体不低于父代且无负翻转。
- 通过后 Development 2,048 场、Confirmation 8,192 场。

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
