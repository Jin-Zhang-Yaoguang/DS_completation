# V38 决策

- 决策：`REJECT_MECHANISM_INERT`
- 父代：`v37_preterminal_boundary_preempt`
- archive SHA256：`66fccd75e6bef1866438506e9b066b2884f13f920e0723da0d4f66f4ea2e1632`
- 烟测：224 场，early events=0，PGU=0，`0/112/0`。
- 原因：step 72-119 没有同时满足可用库存、未来 premium SELL 和需求边界的动作机会。
- 数据：未消费新的官方 Replay source。
