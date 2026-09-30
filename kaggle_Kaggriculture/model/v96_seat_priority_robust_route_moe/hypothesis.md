# V96：座位优先权—稳健路线 Hierarchical MoE

- `strategy_parent=null`；两个完整路线专家均来自公开 top-5 Replay 数据，不调用历史 agent；V76 只作强度比较器。
- 引擎 `process_market` 在每个市场槽内按 player 0 → player 1 提交，造成可观测且不可消除的座位竞争非对称。source qualification 的 768 局显示：episode 100414724 在 seat1 得分率 100%、灾难率 0，但 seat0 灾难率 12.5%；episode 100458412 双座位灾难率均为 0。
- full 在 step0 一次性路由：seat0 → `robust_first_mover`，seat1 → `upside_second_mover`，整局不切换；`arity_safe_executor` 只对齐实际 hand 数，不提供策略动作。
- 主消融两席均使用稳健专家。正式预构造改用未参与 source qualification 的 16 个 seed；要求 MCU > 0、正翻转多于负翻转、两路线专家均覆盖、PanelScore ≥60%、直接 V76 ≥50%、灾难率相对 V76 恶化 ≤1pp。

