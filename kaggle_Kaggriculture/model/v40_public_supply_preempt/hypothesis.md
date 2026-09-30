# V40 预注册：逐商品公开供给信号

V37 仅在两座公开农场的整体 clone distance 不超过 6 时启用前置，这会漏掉整体路线不同但双方都生产同一种 premium 商品的市场竞争。V40 保留 clone 路径；对非 clone 局面，只在对手公开地块显示对应作物/动物时开放该商品：STRAWBERRY、MELON、COW->MILK、SHEEP->WOOL。

信号只来自公开 `farms[opponent].tiles`，不读取私有 shed、当前动作或 seed。机制仍受 V37 的需求边界、订单槽、库存、价格与偿还约束。

- 父代：`v37_preterminal_boundary_preempt`。
- 活动金牌门：V19、V20、V21/V29、V32、V33、V34、V37。
- 烟测：内部 seeds `40001-40008`，224 场；必须出现非 clone supply event、总体不低于父代且无负翻转。
- 通过后 Development 1,792 场、Confirmation 7,168 场。

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
