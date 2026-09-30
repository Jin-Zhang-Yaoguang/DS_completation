# V47 决策

- 决策：`REJECT_MECHANISM_SMOKE`
- 父代：`v46_full_terminal_front_run`
- archive SHA256：`8a9b17674c8ea34b690770fcb5ec90a0ba941ccf1ca49cbf98d2f8f6eb14dfa8`
- 烟测：256 场，PGU `-10.9375pp`，`0/102/26`，平均 margin `-17.38`。
- 根因：step 715 新增可售库存，单纯移动会丢失父代在 715 的补卖。
- 数据：未消费新的官方 Replay source。
