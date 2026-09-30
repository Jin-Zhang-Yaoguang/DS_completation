# R26 Persistent Feasible Option Graph HMoE

R26 是直接基于 R25 源码构造的独立、自包含五专家 Hierarchical MoE 候选，
`STRATEGY_PARENT=None`。运行时只使用 Python 标准库，不导入或包装旧策略。

R25 的 Router、五专家 genome、30 天目标、R24 确定性 slot、market、params、阈值、
多项式 min-cost maximum-flow 与 typed fail-closed 安全层保持不变。R26 的唯一研究假设是
Persistent Feasible Option Graph：

- 有限作物闭环跨 observation 持久保留 `HARVEST→确认空格→原格同作物 PLANT→确认存在→WATER`；
  seed 从闭环准入起独占，确认种植成功或冲突取消后才释放。
- MCMF 只使用当前网格内可达边，并直接保存、发射同一次 BFS 的首步；官方规则允许移动进入
  网格内 `LOCKED`，仅越界被拒绝。
- 普通扩张按 service lane 各自的固定 slot 顺序推进，一条 lane 的冲突、weed 或 seed 缺口
  不会冻结其他 lane；全局仍最多并行 3 个普通 PLANT。
- 合同 crop slot 的 weed 是高风险依赖链 `DIG→确认空格→PLANT→确认存在→WATER`；没有对应
  seed 或无法完成当前必要后继时不启动 destructive head。
- BUILD 只在对应 animal species 仍有缺口时产生，且 option 将 slot、structure 与 species 固定
  绑定，外部新增其他动物不会重解释已启动结构。
- feeder 只用 deadline 前可到达具体 FEED 目标的携粮 actor 抵扣缺口；近 shed actor 可并行
  PICKUP，并按实际可闭环数量预留 WHEAT。
- terminal floor 使用公开 `max_lifespan_step`：终局前必衰变的 finite crop 不再被资产 floor
  错误扣留，但 HARVEST、seed、原格 PLANT、WATER 和严格 deadline 仍须共同成立。
- step 696 后普通购买继续关闭；仅当一名最小新增 hand 可支付且严格提高 deadline 闭环最大基数
  时，允许一次安全 HIRE。
- 删除 R25 对每个新增 slot 预收完整未来 shed/FEED/CARE 生命周期工时的 capacity gate；只约束
  当前安全 option head 与必要后继资源，保持当前 frontier work-conserving。

验证状态：

- static/parity/mechanism tests：`PASSED`，36/36（5 static + 5 parity + 26 mechanism）
- 独立只读机制复审：`PASSED`（36/36，约 0.3 秒，无机制冻结阻断）
- killfast：`REJECTED`
- P2：`NOT_RUN`
- P3：`NOT_RUN`
- Replay：`NOT_RUN`
- gold status：`NOT_GOLD`

唯一 seed7100/router/seat0/idle killfast 结果：bank `79,264`、终局资产 `34`、移动
`4,397`、CARE+FERT `340`、day12 资产 `37`，并发生 5 次漏水成 weed；只有终局 weed、
step144、动物目标与基础安全门通过。PICKUP `246`（R24 为 51）暴露 feeder 无持久批量补给
角色，当前 work-conserving 匹配把任务恢复成了补给往返洪泛。决策
`NOT_GOLD_KILLFAST_REJECT`，未运行 P2/P3/Replay。

当前结果只证明候选自包含、R25 非目标配置 parity 与已登记机制反例通过，不证明对战强度、
75% 胜率或 Replay 泛化。R26 实现过程未读取或使用 Replay；引擎语义只核对公开 official rules 文件。

候选 `main.py` SHA-256：`b3d38f2235ef2cdc35bbec951e36a6da336435f96349743fd8811bfa104e8fc0`

打包时不得包含 evaluator、`accounting_engine`、对战脚本、测试文件或 Replay 数据。
