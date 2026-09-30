# V38 预注册：Router 后立即启用需求边界前置

V37 的需求边界机制固定从 step 120 才启用，但首商店与公开农场在 step 72 已可见，父代 Router 也在该步完成路线选择。V38 完整保留 V37，只将起点从 120 移到 72；不读取 seed、对手私有库存或未公开商店。[VERIFY: v38_postrouter_boundary_preempt/main.py:48] [VERIFY: v38_postrouter_boundary_preempt/main.py:1637]

- 父代：`v37_preterminal_boundary_preempt`。
- 活动金牌门：V19、V20、V21/V29、V32、V33、V34、V37，共 7 个。
- 烟测：内部 seeds `38001-38008`，224 场；必须触发 step<120 动作、总体不低于父代且无负翻转。
- 通过后 Development 64 source、1,792 场；Confirmation 256 source、7,168 场。

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
