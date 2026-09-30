# V95：路径不变控制屏障 Hierarchical MoE

- `strategy_parent=null`；V76 只作强度比较器。
- 固定生产路径上的每个单位任务由动作前置条件 Router 分配给 `direct_task`、`same_tile_prerequisite`、`resource_cap` 或 `safe_idle`；屏障禁止移动替换、手位交换和延期任务。
- 市场层只做同序可行性封顶与终局仓库兑现，不重排原交易队列。
- 主消融直接执行相同固定任务流。预构造要求至少 8 局有屏障干预、MCU > 0、正翻转多于负翻转、PanelScore ≥60%、直接 V76 ≥50%、灾难率恶化 ≤1pp。

