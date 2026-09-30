# R15 Settlement-safe Cap-10 HMoE

状态：`NOT_GOLD_KILLFAST_REJECT`。

R15 从冻结的 R13 自包含源码分叉，`strategy_parent=null`，保留五个完整生产专家、商店 Router、全局任务拍卖、动作类型 guard、收据安全、并行 plant-water admission、有限 replacement continuity、批量交付和终局资产保护。运行时不导入或包装 R13、RC8、R12 或历史金牌模型。

## 限定增量

- 日程和市场招聘双重强制 hands 上限 10，不采用 R14 未过门的复杂自适应公式。
- `step >= 696` 禁止 `BUY_PRODUCT/BUY_SEED/BUY_ANIMAL/BUY_LAND/HIRE`，仍允许出售和单位动作完成结算。
- WHEAT `BUY_PRODUCT` 按引擎语义逐单位使用 `inventory-1, inventory-2, ...` 报价，按累计成本决定数量并扣减内部预算。
- `act()` 将实际执行动作交给 `_true_eligible_harvests(grid, units, verbs)`，再把非空收获链传入市场种子缺口计算。
- 预算拒绝诊断改名为 `purchase_withheld_budget`。

## 门控证据

机制检查 24/24 通过。唯一一次 seed7100/router/seat0/idle killfast：

- bank：96,287，低于 100,000 门槛；
- step144 assets：22，通过 12 门槛；
- terminal assets：52，低于 58 门槛；
- calls：719；runtime/schema/invalid/missed-water 均为 0；
- 因 bank 和 terminal assets 两项失败，最终判定淘汰。

未运行 P2、P3 或 Replay。该版本不得注册 golden_model，不得提交 Kaggle。
