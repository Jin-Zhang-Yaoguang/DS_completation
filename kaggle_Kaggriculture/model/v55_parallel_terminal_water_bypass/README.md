# V55 Parallel Terminal Water Bypass

V55 尝试在 V54 之后并行接管其余终局 WATER carriers。

- 父代：`v54_terminal_water_bypass`。
- 机制烟测：384 场；触发 168 次、1,008 单位。
- 配对结果：PGU `-17.71pp`，`0/155/37`，平均 margin 下降 59.83。
- 结论：剩余 actor 的 WATER 并非无回收价值，可能被其他 actor 的后续 HARVEST 利用；单 actor 的 V54 结论不能并行泛化。

决策：`REJECT_MECHANISM_SMOKE`。未消费官方 Replay，不进入 Development/Confirmation。
