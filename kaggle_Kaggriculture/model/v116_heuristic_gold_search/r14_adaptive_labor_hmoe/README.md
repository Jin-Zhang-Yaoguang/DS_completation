# R14 Adaptive Labor HMoE

状态：`NOT_GOLD_KILLFAST_REJECT`。

R14 是 `strategy_parent=null` 的自包含规则/浅树 Hierarchical MoE，保留五个完整生产专家、商店 Router、全局任务拍卖、动作类型 guard、收据安全、并行 plant-water admission、有限 replacement continuity、批量交付与终局 58 生产资产下限。运行时不导入或包装 R13、RC8、R12 或历史金牌模型。

## 原创增量

R13 的 P2 证据显示所有模式都在终局达到 14 hands；Router 均值 76,393、CVaR 55,153，约 1,500 unit PASS。R14 因此取消固定 14 hands 目标，按当日关键任务、到任务点的移动预算、未完成生产缺口和当日剩余有效工时推导 hands 目标，并设置硬上限 10、仅允许 0-8 时招聘。每日诊断记录目标 hands、实际 hands 峰值、工资预算、实际发出的招聘单与工资。

## 门控结果

静态检查 8/8 通过；机制检查 13/14 通过。失败项为 `labor_target_tracks_workload_and_caps_at_ten`：既定高负载夹具没有把目标推到 cap=10，无法证明上限由工作量触发而非仅存在常量。按照一次性 kill-fast 规则，未运行 seed7100，也未运行 P2、P3 或 Replay。

该版本不得注册 golden_model，不得提交 Kaggle。
