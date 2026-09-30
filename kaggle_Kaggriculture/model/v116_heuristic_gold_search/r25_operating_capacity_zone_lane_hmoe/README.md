# R25 Operating-Capacity Zone-Lane HMoE

R25 是直接基于 R24 源码构造的独立、自包含五专家 Hierarchical MoE 候选，`STRATEGY_PARENT=None`。运行时只使用 Python 标准库，不导入或包装旧策略。

R24 的 Router、五专家 genome、30 天目标、确定性 AnimalSlot/CropSlot、market、params、阈值和 observation-confirmed 原格链保持不变。R25 新增 Operating-Capacity Slot Contract：

- 每个固定 slot 预编译 service zone、连续蛇形 lane 和 circuit ordinal；同 lane 最多五格且相邻。
- 所有新增资产共享同一容量账本：有限作物 `HARVEST→PLANT→WATER`、动物 `BUILD→PLACE→FEED→CARE`/`PLACE→FEED→CARE`、普通 `PLANT→WATER` 都进入 shed 闭环路线与 actor 装箱证明。
- slot expansion 只能截短稳定前缀，不能跳过冲突/不可执行 slot 后改种或改建后续坐标。
- 调度使用多项式 min-cost maximum-flow：完整 finite frontier、每 actor 最多一项、每坐标最多一 actor、按 crop seed quota 限流；安全风险和 deadline 优先，owner 只在同等安全可行时保留，并在日切释放。
- FEED 按全局未喂数量减所有 actor 已携带 WHEAT 计算批量预留。
- 所有 unit verb 最终经过 exact arity、合法枚举、tile state、库存/seed/shed resource 的 fail-closed 检查。
- 终局有限作物同时受资产 floor、seed、原格闭环和共享工时容量约束。

验证状态：

- static/parity/mechanism tests：`PASSED`，32/32（5 static + 4 parity + 23 mechanism）
- 独立压力复审：11 actors、14 PLANT、45 WATER、10 CARE，共 69 tasks / 759 edges，约 0.0042 秒
- killfast：`REJECTED`
- P2：`NOT_RUN`
- P3：`NOT_RUN`
- Replay：`NOT_RUN`
- gold status：`NOT_GOLD`

唯一 seed7100/router/seat0/idle killfast 结果：移动 `2,518` 通过，但 PASS 增至 `3,506`、
PLANT 降至 `79`；bank `49,166`、step144/day9/day12/终局资产 `11/19/17/26`、
CARE+FERT `339`、终局 weed `2`，严格判 `NOT_GOLD_KILLFAST_REJECT`。完整生命周期容量
证明过度冻结扩张和可用任务，故未运行 P2/P3，也未把该结果送入任何 Replay 面板。

结果后只读反例还发现三项原 32 项测试未覆盖：跨 tick 移动会删除未发射的 finite
`replacement_plant` 并释放 seed；共享 PASTURE deficit 可被已满足物种的早序 slot 消耗；
FEED 只计算全局携粮量、不证明携粮 actor 能在 deadline 前到达。因此 32/32 只表示已登记
夹具通过，不表示机制完备。

当前结果只证明机制闭环、R24 非目标 parity、复杂度上界和审计反例通过，不证明对战强度、75% 胜率或 Replay 泛化。

## Replay 协议偏差记录

2026-08-31（Asia/Taipei）查找 `PICKUP`/inventory capacity 源码语义时，误执行了范围过宽的命令：

```text
rg -n "inventory.*capacity|capacity.*inventory|HAND_CAP|PICKUP" kaggle_Kaggriculture | head -80
```

该命令意外命中
`kaggle_Kaggriculture/model/v12_incumbent_r002/online_failure_55713101/episode-97566763-replay.json`
的一行压缩 JSON。终端输出片段包含 configuration、description、id/info、module_version、schema/specification、steps/observation，并包含 `action` 字段；文件内容未提供可据此确认的对局日期。此文件没有被再次打开、解析、汇总或用于场景建模、调参、机制测试、强度评测或决策。R25 候选源码和测试均无 Replay 路径、Replay 导入或 Replay 数据依赖；后续 PICKUP 校验只依据 official rules 源码。

候选 `main.py` SHA-256：`573b24a8169e9dcb0446c27c80e365c07f1018e4ba5bc71574b12f28ff84b71f`

打包时不得包含 evaluator、`accounting_engine`、对战脚本或 Replay 数据。
