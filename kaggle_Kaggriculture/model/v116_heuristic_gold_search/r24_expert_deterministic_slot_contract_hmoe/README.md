# R24 Expert Deterministic Slot Contract HMoE

R24 是直接从 R22 派生的独立、自包含五专家 Hierarchical MoE 候选，`STRATEGY_PARENT=None`，运行时只使用 Python 标准库，不导入或包装旧模型，也不包含 R23 Intent Ledger。

R22 的 Router、五专家 genome、30 天聚合目标、market、params、阈值、exact semantic frontier、Soft Chain Lease 与 observation confirmation chains 保持不变。唯一重大机制是 Expert Deterministic Slot Contract：

- 从五专家 genome 预编译不可变 `AnimalSlot` 与 `CropSlot`，不读取 observation、Replay、unit 位置或 `crop_cursor`。
- 土地使用固定前缀 `NW25 → NW+NE50 → NW+NE+SW75`；每阶段先分配新增动物波，再分配 crop block，坐标由现有 `PLACEMENT_RING/_placement_key` 和稳定 tie 决定。
- AnimalSlot 固定耦合 structure 与 animal；crop/animal 坐标全局互斥。五专家 stage-0 均为相同的 `WHEAT 8 + MELON 7 + SHEEP 4`。
- Router 未 commit 时仅开放 common slots；commit 后保持 common 坐标并追加选中专家已经激活的 slots。fixed 模式从 step 0 使用对应专家 contract。
- BUILD、PLACE、普通 PLANT 只在 active slots 生成；全局观察缺口为零时不会超建、超放或超种，错误占位 fail closed 并记录诊断。
- 普通 PLANT 坐标不受 actor、maintenance、`crop_cursor` 影响，稳定顺序最多 admission 3；growth debt 只把首个固定候选改成 priority 1。
- 有限作物只在匹配的 active crop slot 收割，seed/容量按原坐标核验，并沿用原格 `HARVEST→PLANT 同 crop→WATER` 确认链。

验证状态：

- mechanism/parity/static tests: `PASSED`，19/19
- killfast: `REJECTED`
- P2: `NOT_RUN`
- P3: `NOT_RUN`
- Replay: `NOT_RUN`
- gold status: `NOT_GOLD`

唯一 seed7100/router/seat0/idle killfast 结果：bank `95,263 < 105,000`、终局资产
`41 < 58`、方向移动 `3,935 > 3,600`、day12 资产 `44 < 50`、CARE+FERT
`401 < 430`。719 calls、零 runtime/schema/invalid、零终局 weed，且 wool 专家动物目标
`COW 4 + SHEEP 6` 完成，但任一失败门已足以淘汰。没有运行 P2/P3，也没有读取 Replay steps。

当前结果只证明确定性槽位、R22 非目标机制 parity 与边界闭环，不构成强度、金牌或 Replay 泛化证据。

候选 `main.py` SHA-256：`6969291a22ce8212cc169ad7c877f98fb231bef3a96220dfe9d2de510e3da16b`

打包时不得包含 evaluator、`accounting_engine`、对战脚本或 Replay 数据。
