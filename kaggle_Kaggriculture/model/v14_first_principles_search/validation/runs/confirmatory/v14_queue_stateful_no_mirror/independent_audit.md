# V14 confirmatory 独立审计

结论：**GO_SUBMIT**。纯胜率严格为 wins/all；平局不算胜。

## 结果

| 对手 | W/T/L | 纯胜率 | 计分率 | 平均 margin | 日期分层 source-cluster 95% CI（纯胜率） |
|---|---:|---:|---:|---:|---:|
| v12_incumbent_r002 | 156/0/44 | 78.0000% | 78.0000% | +210.0800 | [72.5000%, 83.5000%] |
| v12a2_no_shop_gate | 149/18/33 | 74.5000% | 79.0000% | +715.1600 | [68.0000%, 80.5000%] |

Bootstrap 独立执行 10,000 次：按日期分层，在每个日期内重采样 100 个 source cluster，并始终保留同一 source 的双席。独立 seed 与落盘审计不同，所以区间不要求逐端点相同。

## 完整性

- 原始任务 400/400；唯一 task_id 400；缺失 0；逐行错误 0。
- DONE/DONE：{'DONE/DONE': 400}；schema、engine、pair、双席、error、reward、margin、score 均从原始行复算。
- run fingerprint：`51e837bc8634046f7c5f00c22670bd5e629fe8384a42c4c439ff519c2436f17f`；manifest、consume lock 和全部 400 行一致。
- confirm panel：100 sources，日期 34/33/33；test=0；与 screen seed 交集 0；与既有 exposure seed 交集 0。
- finalist seal：`030d75bb6e431a4378e0fd8ee07056e7b793e80bb76d5bab803f377e761067ad`；所有绑定检查 True。
- 候选 archive：`d7d2e8210041d695a10ddc7797efbfd5c4ca3a0f8c33c70e0fd5d597fd4d4f9f`；tar、clean closure、registry binding 均通过。
- 落盘 audit 点估计一致：True；confirm recovery 哈希链：True；分析前后输入未变：True。

## 日期与候选席位

### v12_incumbent_r002

| 分层 | games | W/T/L | pure | score | margin |
|---|---:|---:|---:|---:|---:|
| 2026-08-18 | 68 | 53/0/15 | 77.9412% | 77.9412% | +165.9412 |
| 2026-08-19 | 66 | 52/0/14 | 78.7879% | 78.7879% | +225.8485 |
| 2026-08-20 | 66 | 51/0/15 | 77.2727% | 77.2727% | +239.7879 |
| candidate seat 0 | 100 | 76/0/24 | 76.0000% | 76.0000% | +435.6400 |
| candidate seat 1 | 100 | 80/0/20 | 80.0000% | 80.0000% | -15.4800 |

### v12a2_no_shop_gate

| 分层 | games | W/T/L | pure | score | margin |
|---|---:|---:|---:|---:|---:|
| 2026-08-18 | 68 | 45/12/11 | 66.1765% | 75.0000% | +574.9118 |
| 2026-08-19 | 66 | 49/6/11 | 74.2424% | 78.7879% | +558.7273 |
| 2026-08-20 | 66 | 55/0/11 | 83.3333% | 83.3333% | +1016.0909 |
| candidate seat 0 | 100 | 73/9/18 | 73.0000% | 77.5000% | +940.1200 |
| candidate seat 1 | 100 | 76/9/15 | 76.0000% | 80.5000% | +490.2000 |

## Gate

- 400-task/hash/schema/engine/seat/DONE/error/reward 完整性：`True`
- A2 纯胜率 >=65%：`True`
- r002 纯胜率 >50%：`True`

独立审计未运行环境、未调用候选、未修改协议/候选/原始结果；只写本报告 JSON/MD。
