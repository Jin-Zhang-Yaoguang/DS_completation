# R20 Stateful Feasible Tile Bundle HMoE

R20 是独立、自包含的五专家 Hierarchical MoE 候选，`STRATEGY_PARENT=None`，运行时只使用 Python 标准库，不导入或包装 R19。

R19 的 Router、五专家表、params、阈值、market、day-8 growth debt 和 `MAX_PARALLEL_PLANT=3` 保持不变。唯一策略改动是 Stateful Feasible Tile Bundle Scheduler：

- 每个坐标维护持久 `TileWork`，记录 owner、ready ops、phase、ready since 与 replacement crop。
- 只根据下一次真实 observation 确认并推进动物、ongoing crop、有限作物原位替换和普通 PLANT→WATER 状态。
- 不在规划期删除任务；一个坐标每个 observation 最多一个 actor，尚未执行的后继跨 observation 保留。
- 先派可行 WATER/FEED，再派可行原 owner 后继，最后按 ready since、raw priority、distance 选择所有存在可行边的 head。
- 不可行 head 只被跳过，不中断其他工作；owner 不可用时由最近可行 actor 接管。
- 多个有限作物替换链和三个普通 PLANT 可并行，没有全局单链。
- typed-safe 最终检查、共享种子预算和原有市场安全保持有效。

验证状态：

- mechanism tests: `PASSED`，14/14
- killfast: `NOT_GOLD_KILLFAST_REJECT`；bank `74,903`、终局资产 `42`、方向移动
  `4,413`、终局 weed `1`
- P2: `NOT_RUN`
- P3: `NOT_RUN`
- Replay: `NOT_RUN`
- gold status: `NOT_GOLD`

R20 使 day9/day12 资产达到 `38/50`，并完整落地 wool 专家的 `6 SHEEP + 4 COW`；但持久
owner 被安全任务带离后仍跨区返回旧坐标，`ready_since` 又让陈旧 head 压住刚确认的原格补种，
累计出现 689 次 owner takeover。后半程 day24--25 动物 CARE/FERT 停摆、资产跌至 42，
因此不进入 P2/P3/Replay。

候选 `main.py` SHA-256：`29a40d9bb751710c50baf5c698d54413928b3227723889ac98203f6138484838`

打包时不得包含 evaluator、`accounting_engine`、对战脚本或 Replay 数据。
