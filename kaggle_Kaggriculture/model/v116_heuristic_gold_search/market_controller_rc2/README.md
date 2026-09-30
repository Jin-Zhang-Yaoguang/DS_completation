# V116 商品级市场控制器 RC2

这是一个无状态、无父模型、无 Replay 动作流的市场子系统。它只读取：

1. 当前 `observation`；
2. 单位动作执行后的 `projected_shed`；
3. 当日聚合目标 `daily_target`；
4. 不可出售的商品储备 `reserves`。

稳定接口：

```python
orders = market_orders(observation, projected_shed, daily_target, reserves)
```

`orders` 可直接放入 Kaggriculture action 的 `market` 字段，且不超过 10 单。
`daily_target` 支持 `max_hands`、`quadrants`、`seeds`、`animals` 和
`products`（或 `inputs`）这些日级绝对目标。动物目标会扣除农场已安装数量和
`projected_shed` 中等待放置的数量。

默认普通出售按对手同商品先成交 12 单做估值折扣；只有当 SELL 收入要为后续
采购融资时，现金账本才按对手先成交 100 单的极端压力计价。两者都可通过
`ControllerPolicy` 显式调整。

该目录只验证机制正确性，未进行任何金牌模型对战，不构成金牌证明。
