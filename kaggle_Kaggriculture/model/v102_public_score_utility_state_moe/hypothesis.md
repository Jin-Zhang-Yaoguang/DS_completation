# V102：公开比分—效用状态 Hierarchical MoE

- `strategy_parent=null`；公开高分路线仅作为完整增长专家的数据，不调用历史 agent；V76 只作强度比较器。
- Router 使用公开双方现金差、我方当前及同回合可入 shed 的库存市值、step：默认 `growth_compound`；现金落后超过 5,000 且库存可覆盖时进入 `deficit_recovery`；step≥600 且领先超过 5,000 进入 `lead_lock`；step≥700 强制 `terminal_utility`。
- 三个效用专家都自行生成商品级 SELL 控制；单位生产动作保持同一完整增长专家，避免跨域切换。
- 主消融始终使用增长专家市场动作。预构造要求三类效用专家中至少两类覆盖 8 局、MCU>0、PanelScore≥60%、直接 V76≥50%、灾难率恶化≤1pp。

