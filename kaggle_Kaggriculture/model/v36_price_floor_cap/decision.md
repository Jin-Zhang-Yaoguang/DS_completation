# V36 决策

- 决策：`REJECT_MECHANISM_SMOKE`
- 父代：`v34_demand_boundary_preempt`
- archive SHA256：`9631b5fef986dff641991a7be71f8217a8956be46d057520f7c2a332fa4bc9ad`
- 烟测：192 场，地板上限触发 911 次，PGU `0pp`，`4/90/2`，平均 margin `-2.29`。
- 证伪：价格为 1 的提前出售虽然不增加供给，但仍可能有清库存和时点价值；简单截断会删除有效动作。
- 数据：未消费新的官方 Replay source。
