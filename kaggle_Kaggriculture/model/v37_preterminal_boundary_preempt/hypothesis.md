# V37 预注册：终局清仓前的需求边界前置

V34 在 step 680 固定停止前置，但终局清仓从 step 716 才开始。V37 保留 V34 全部行为，只开放 step 680-715，并要求原计划出售与偿还都发生在 step 716 之前；因此不会跨入终局清仓，也不搜索停止时点。[VERIFY: v37_preterminal_boundary_preempt/main.py:49] [VERIFY: v37_preterminal_boundary_preempt/main.py:278]

- 父代：`v34_demand_boundary_preempt`。
- 金牌门：V19、V20、V21/V29、V32、V33、V34。
- 烟测：内部 seeds `37001-37008`，192 场；必须触发 late event、总体不低于父代且无负翻转。
- 通过后 Development 64 source、1,536 场；Confirmation 256 source、6,144 场。

状态：`FROZEN_BEFORE_MECHANISM_SMOKE`。
