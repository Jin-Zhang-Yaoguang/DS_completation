# 配对开发校验器验证

脚本 SHA256：`02c3041d3c3e34e7d5c9d2cf712e01522e70b563912b72b7d6444ef0e5737f0c`。

12 项只读/内存故障注入测试全部通过。候选调用 0，引擎步进 0，新增独立比赛 0，所有原始比赛与来源文件 SHA 未改变。

真实 fixture 为 seed 1950905001 的四个固定方案 × 两席位，对手均为 V120。以 horticulture 为算式候选，两个席位的结果相同：

| 参照 | 自方现金变化 | 对手现金变化 | 分差变化 |
|---|---:|---:|---:|
| balanced | +7,999 | +7,726 | +273 |
| dairy | +14,637 | +12,605 | +2,032 |
| fiber | +14,860 | +407 | +14,453 |

各组均有 2/2 个严格正分差，N=2 所需阈值为 2。此处只验证算式，没有从 2 对外推到正式 6 对、没有合并不同对手组。

真实 fixture 评估的顶层 `data_integrity_pass=false`、`development_strength_guard_pass=false`。预期问题恰为 1 个 `POSTHOC_FIXTURE_NOT_DEVELOPMENT_EVIDENCE` 和 8 个 `GAME_PRECEDES_PLAN_FREEZE`；完整性、SHA、工程记录和收益算式没有额外问题。

测试另在内存给算式候选的自方现金加 1,000、对方加 3,000，并同步该内存副本的 rewards、margin 和 summary。其 balanced 配对分差由 +273 变为 −1,727，即使自方现金仍比参照更多，也必须 `development_strength_guard_pass=false`。这验证护栏判断的是双方分差。

产物：`posthoc_fixture_plan.json` 为明确事后的计划；`posthoc_formula_check/` 为真实只读重算及其来源 SHA；`contract_tests.json` 和 `contract_test_log.txt` 为 12 项测试结果。纯内存测试不作为比赛或门控证据。

本工具不核验投资等待等主机制，不代替 G1/G2/Gold。冻结时间和种子开放历史仍需父任务的外部预注册证据；本地工具不能自行证明从未查看或伪造时间不存在。
