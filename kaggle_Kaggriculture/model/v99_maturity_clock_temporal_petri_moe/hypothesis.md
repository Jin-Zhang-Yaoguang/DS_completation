# V99：成熟时钟—Temporal Petri Hierarchical MoE

- `strategy_parent=null`；无 Replay 动作流、无历史 agent。V76 只作冻结强度比较器。
- 每个地块维护由公开状态直接恢复的时间 token：作物类别、`planted_day`、首次成熟日、持续产出间隔、最大产出次数和寿命。阶段 Router 只允许 `establish → maintain → mature_harvest → replant` 的合法转移。
- 商店需求层在粮食、速生根茎、高价多年生和终局短周期专家间选作物；全局匹配器把当前合法任务分配给 farmer/hands；现金预算器先变现、再雇工、再扩地和买种。
- 主消融移除成熟时钟，退化为 `yield_units>0` 即收获的即时反应图；其他 Router、任务分配、市场和执行器相同。
- 预构造 576 局；要求 full 相对消融 MCU>0、正翻转多于负翻转、至少三类生产专家覆盖、PanelScore≥60%、直接 V76≥50%、灾难率恶化≤1pp、零错误。

