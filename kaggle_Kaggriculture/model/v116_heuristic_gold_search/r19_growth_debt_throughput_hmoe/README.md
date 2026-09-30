# R19 Growth-Debt Throughput HMoE

R19 是独立、自包含的五专家 Hierarchical MoE 候选，`STRATEGY_PARENT=None`，运行时只使用 Python 标准库，不导入或包装旧候选。

核心机制：

- 保留 R17 的 Router、五个生产专家、cap11、需求出售控制、频率布局及 step 696 禁购。
- `_jobs` 为纯规划函数；semantic target 不含 priority。只有通过 typed-safe 检查且实际发出的 `PLANT` 才递增 cursor，并记录 crop、zone、shed distance。
- 不在规划期合并或删除同格任务。分配器先找到可执行任务，再锁定坐标，保证单观察同格只有一个 owner。
- 所有 WATER/FEED 全局 maintenance-first。
- day 8 起计算 growth debt；总 PLANT admission 保持 3，仅最近一株提升为全局 P1 growth lane。
- growth debt 存在时，有限作物 HARVEST 必须同时具备对应种子、空位和 PLANT+WATER 容量。
- primary 生产任务先于 secondary 维护任务；primary 内不使用 raw priority 压制 PLACE/BUILD。

验证状态：

- mechanism tests: `PASSED`，18/18
- killfast: `NOT_GOLD_KILLFAST_REJECT`；bank `77,471`、终局资产 `45`、方向移动
  `3,739`、终局 weed `2`
- P2: `NOT_RUN`
- P3: `NOT_RUN`
- Replay: `NOT_RUN`
- gold status: `NOT_GOLD`

逐日诊断显示 day9--12 每日都生成大量 CARE/FERT，但两类动作连续四天发出 0；调度器先按
任务“存在”选择 primary tier，再检查可执行边，遇到不可执行 PLACE 时会直接退出，而不会
回退到可执行 CARE/FERT。R19 因此淘汰，不进入 P2/P3/Replay。

已知评测合约问题：`terminal_cows_ge_6` 假定了 dairy 路由，但本局实际路由为 wool；该项不作
R19 失败依据。R19 在与路由无关的 bank、终局资产、移动、day12 资产、终局 weed 和维护吞吐门
已经失败，淘汰结论不受影响。下一版改用实际专家的逐动物目标兑现率。

候选 `main.py` SHA-256：`45e48f244123334329e9f35dd01d461ffc2919eac0ffaff4ce7d471cdb802ed7`

打包限制：只打包候选运行代码；不得打包 evaluator、`accounting_engine`、对战脚本或 Replay 数据。
