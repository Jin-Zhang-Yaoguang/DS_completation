# V50 Terminal Carrier Flush

V50 尝试在 step 715 对仓库入口且当前为 `PASS` 的 actor，把携带商品 `PLACE` 并同回合 `SELL`。

- 父代：`v46_full_terminal_front_run`。
- 机制烟测：8 个金牌门、8 个内部种子、双座位，候选/父代合计 256 场。
- 结果：`terminal_units=0`，候选相对父代 PGU `0.00pp`，`0/128/0`。
- 根因：实际处于仓库入口且携带商品的 actor 已执行 `DROP`；V46 的 `_projected_shed` 已计入这些入仓量。没有满足“仓库入口 + 携带商品 + PASS”的 actor。

决策：`REJECT_MECHANISM_INERT`。未消费官方 Replay，未进入 Development/Confirmation，未注册为金牌。
