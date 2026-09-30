# V100：因子化可行域—专家仲裁 Hierarchical MoE

- `strategy_parent=null`；四个完整专家来自公开高分 Replay 数据，不调用任何历史 agent；V76 只作强度比较器。
- 日边界双 Router：`topology_router` 以商店、土地、作物/杂草/空地计数选择单位生产专家；`balance_sheet_router` 以商店、现金、仓库、种子和土地选择市场专家。两域选择整日冻结，禁止逐回合最近邻跳转。
- `cross_domain_barrier` 对齐实际 hand 数和市场槽位；专家组合只在日边界改变。
- 主消融固定使用同一条公开强专家的单位与市场动作。预构造要求至少两条单位专家和两条市场专家各覆盖 8 局、MCU>0、PanelScore≥60%、直接 V76≥50%、灾难率恶化≤1pp、零错误。

