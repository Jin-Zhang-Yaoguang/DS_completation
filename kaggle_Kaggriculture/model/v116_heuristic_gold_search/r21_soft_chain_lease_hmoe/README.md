# R21 Soft Chain Lease HMoE

R21 是独立、自包含的五专家 Hierarchical MoE 候选，`STRATEGY_PARENT=None`，运行时只使用 Python 标准库，不导入或包装 R20。

R20 的 Router、五专家表、params、阈值、market、jobs、状态确认链、day-8 growth debt 与 `MAX_PARALLEL_PLANT=3` 保持不变。唯一策略改动是 Soft Chain Lease：

- `ready_since` 只在新建 tile bundle 时写入；动物四阶段、有限作物原位替换链及普通 `PLANT→WATER` 的 phase/head 变化继承原始年龄。
- 保留可行 `WATER/FEED` 安全阶段；其余工作不再单独执行 owner-first pass，而是先选最老可行 bundle，再为该 bundle 选择最近可行 actor。
- 旧 owner 只在距离完全相同时作为 tie-break，远端 owner 不会迫使 actor 跨区返回。
- 每个 actor 最多持有一个 lease；actor 接受新坐标时会释放其旧坐标 ownership，owner 不可用或不是最近 actor 时自然 handoff。
- 保留 finite frontier、不可行任务跳过而不终止 scheduler、单坐标单 actor、三个 growth bundle 并行及 typed-safe 最终检查。

验证状态：

- mechanism tests: `PASSED`，15/15
- killfast: `NOT_GOLD_KILLFAST_REJECT`；bank `86,130`、终局资产 `48`、方向移动
  `4,233`、终局 weed `3`
- P2: `NOT_RUN`
- P3: `NOT_RUN`
- Replay: `NOT_RUN`
- gold status: `NOT_GOLD`

软租约使 R20→R21 的 bank `+11,227`、CARE+FERT `+62`、移动 `-180`、takeover
`692→379`，但未发射的普通 BUILD/PLANT 仍跨观察持久。day9→10 pasture 从 6 直接建到 13，
终局共 14 个，超过 wool 目标 10；陈旧普通任务继续占用链龄、地块和路程，故未进入 P2。

当前结果只证明机制闭环与 R20 非目标部分保持一致，不构成强度、金牌或 Replay 泛化证据。

候选 `main.py` SHA-256：`19804af6270c00f40122be668c78d4fad71d96f2ec980e54a70d3aa2cd95b98f`

打包时不得包含 evaluator、`accounting_engine`、对战脚本或 Replay 数据。
