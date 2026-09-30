# R23 Deficit-Backed Intent Ledger HMoE

R23 是独立、自包含的五专家 Hierarchical MoE 候选，`STRATEGY_PARENT=None`，运行时只使用 Python 标准库，不导入或包装 R22。

R22 的 Router、五专家表、params、阈值、market、jobs、Soft Chain Lease 与 observation-confirmed chains 保持不变。唯一策略改动是 Deficit-Backed Intent Ledger：

- 每次从当前 `_jobs()` 统计未发射意图配额：`PLANT` 按 crop、`PLACE` 按 animal、`BUILD_*`/`DIG` 按 operation 分 key 计数。
- 每个 key 先保留结构仍有效且最老的既有 lease，最多保留到当前配额；超额、结构非法或 quota 为零的未发射 lease 立即删除并释放 owner。
- planner 新坐标只能填补 `quota - confirmation reservations - retained leases`，同 key 的活跃意图不会因坐标变化膨胀，不同 crop、animal、operation 相互隔离。
- 已发射的确认链不受 quota 清理；它会先借记对应 key 的配额或种子缺口，避免确认期间在其他坐标重复开普通 lease。
- 同坐标确认链优先保留；若 generic action 尚未被 observation 确认，可在 planner 改坐标后继续用旧 lease 重试。
- R21/R22 的 oldest-first Soft Lease、nearest feasible actor、finite frontier、单 actor 单 lease 与 typed-safe 发射保持不变。

验证状态：

- mechanism/parity/static tests: `PASSED`，18/18
- killfast: `NOT_GOLD_KILLFAST_REJECT`；bank `92,336`、终局资产 `39`、方向移动
  `3,810`、终局 weed `0`
- P2: `NOT_RUN`
- P3: `NOT_RUN`
- Replay: `NOT_RUN`
- gold status: `NOT_GOLD`

缺口账本通过全部机制测试，但实测只把 PLANT `140→149`，同时 CARE+FERT `429→394`、移动
`3,566→3,810`、bank `94,861→92,336`。在意图抖动与旧坐标返程之间重新分配损失，未恢复
增长吞吐，因此淘汰，不进入 P2。

当前结果只证明意图配额、确认借记和 R22 非目标机制闭环，不构成强度、金牌或 Replay 泛化证据。

候选 `main.py` SHA-256：`5936491ce7ea99239afbaba67de0da0b8a718f5ff60f19fc376aa66ea0412b2f`

打包时不得包含 evaluator、`accounting_engine`、对战脚本或 Replay 数据。
