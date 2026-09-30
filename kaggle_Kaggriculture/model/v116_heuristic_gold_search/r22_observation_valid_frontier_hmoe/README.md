# R22 Observation-Valid Frontier HMoE

R22 是独立、自包含的五专家 Hierarchical MoE 候选，`STRATEGY_PARENT=None`，运行时只使用 Python 标准库，不导入或包装 R21。

R21 的 Router、五专家表、params、阈值、market、jobs、Soft Chain Lease 与 observation-confirmed chains 保持不变。唯一策略改动是收紧 `TileWork` 状态边界：

- 已实际发射的 `await_empty`、`await_replacement_plant`、`await_ordinary_plant`、`await_water`、`await_confirm` 等确认态仍按真实 observation 推进。
- 尚未发射的普通 `PLANT`、`BUILD_*`、`PLACE`、`DIG`，只有当前 `_jobs()` 在同坐标继续提供同一 semantic job 时才保留。
- planner 不再提议旧任务时立即删除 bundle 并释放 owner；同坐标改为不同 crop、animal 或 operation 时创建新 bundle，不能继承旧 `ready_since`。
- 同语义任务仅 priority 改变时保持原 bundle 年龄和 lease，并更新当前 priority。
- 因此可并行 BUILD 数量受当前 observation 的真实结构缺口约束，陈旧结构任务不会继续占用 actor。

验证状态：

- mechanism/parity/static tests: `PASSED`，14/14
- killfast: `NOT_GOLD_KILLFAST_REJECT`；bank `94,861`、终局资产 `42`、方向移动
  `3,566`、终局 weed `0`
- P2: `NOT_RUN`
- P3: `NOT_RUN`
- Replay: `NOT_RUN`
- gold status: `NOT_GOLD`

Observation-Valid Frontier 使 pasture 精确为 10、动物目标完全兑现、移动和终局 weed 过门，
CARE+FERT 达 429；但普通 PLANT 必须匹配当前精确坐标，使目标重排时在途意图频繁失效，PLANT
从 R21 的 189 降到 140、PASS 升到 1,869，day12/终局资产只有 35/42。未进入 P2。

当前结果只证明状态边界机制闭环和 R21 非目标机制 parity，不构成强度、金牌或 Replay 泛化证据。

候选 `main.py` SHA-256：`0abdbf4f97749c603a65312936974dab930b54cb56e2a12954b564ec5a8868a6`

打包时不得包含 evaluator、`accounting_engine`、对战脚本或 Replay 数据。
