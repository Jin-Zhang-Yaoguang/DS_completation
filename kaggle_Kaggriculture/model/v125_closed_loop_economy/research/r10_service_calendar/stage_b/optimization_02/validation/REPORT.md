# P2 有限验证：等价成立，单次内部规划仍需 13.305 秒

P2 在已登记的 day8、seat0、48 株草莓、足额现金人工初态中，完整内部经济规划用时 **13.305441375006922 秒**，仍超过 1 秒要求。全部计划和状态与已保存 P1 严格相同，11 项纯接口控制通过。结论为 **P2_TIME_THRESHOLD_FAILED**，不能进入完整候选比赛，也不构成 G1/G2 或金牌证据。

唯一执行由根在 session48690 启动，结束 exit1；本子任务没有启动第二次执行。P0/P1均未重跑；本轮只发生 P2 `new_state` 1 次、`economic_plan_prefix` 1 次、11 次纯 route。完整 agent、官方引擎、新完整比赛均为 0。

| 同一人工输入的完整内部规划 | 秒数 | 相对 P1 | 1 秒要求 |
|---|---:|---:|---|
| P1 已保存参照 | 18.025442334008403 | — | 失败，旧结果保留 |
| P2 本次一次 | 13.305441375006922 | 本次观察缩短 26.1852% | 失败 |

两次计时发生在不同执行时段；这是单个固定初态的观察，不能推断所有状态的改善比例。120 秒保护仅用于捕获完整输出，没有放宽 1 秒标准。完整规划不加 profile；纯接口的透明 profile 只用于核调用、对象隔离与回滚，不作性能证据。

P2 的改动是缩小已完整核验的生产缓存和对外 stats，没有减少本次真实求解次数。P1/P2 的整个 typed plan/state 重新离线比较为 0 差异，类型、原字段、字典插入顺序均保留；没有过滤计划字段。模块候选 ID 另列来源元数据。

| 完整内部规划原审计计数 | P1 已保存 | P2 本次 |
|---|---:|---:|
| route_attempts | 342 | 342 |
| actual_calendar_compilations | 48 | 48 |
| quote_calendar_compilations | 312 | 312 |
| scheduler_calls | 1038 | 1038 |
| checker_calls | 926 | 926 |
| cache_hits | 4 | 4 |
| route_successful_quotes | 216 | 216 |
| route_failed_quotes | 126 | 126 |
| quote_calendar_cache_hits | 862 | 862 |

两者都选择 horticulture/MELON，许可 26 个 MELON 项目，模型预留后资金为 97097，不买地。这是模型报价和许可结果，不是实际采购、官方服务或最终比赛现金。

原始 [controls_v1/summary.json](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_02/validation/controls_v1/summary.json) 把结果记为 `EQUIVALENCE_OR_SOURCE_FAILURE`，原因是冻结 [run_validation.py 第 313–315 行](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_02/validation/run_validation.py:313) 从 `r10_future_route` 顶层读取计数，四项得到 null。真实路径为 `state['investment_receipts'][-1]['r10_future_route']['counts']`。原脚本、原 summary 和原紧凑摘要均未修改。

新增 [offline_count_path_correction.json](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_02/validation/offline_count_path_correction.json) 从两份完整输出重新核全部 typed 值和 9 项计数，并核原记录、来源与预算；更正后的等价与来源完整性为 true，性能仍失败。可供后续报告读取的文件是 [corrected_compact_summary.json](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_02/validation/corrected_compact_summary.json)。更正过程新增候选、solver、引擎调用均为 0。

| 纯接口控制 | 实际结果 |
|---|---|
| full cold / hit / custom schedule / custom check | 4 项全部 result、cache 与原有反向别名效果同保存 P1；显式自定义 hook 各执行 1 次，外部 baseline/private/cache 隔离保持 |
| compact cold | 与 full 的共同业务字段、4 stats 和完整守卫事实相同；mode/schema 参与的 key 独立按原序列化规则重算 |
| 修改返回 stats 和 witness 后 hit | 改 4 stats、start_shed、reserved_shed、buy 不污染缓存；再次命中恢复原值，新增 solver/checker 为 0 |
| cache 模式错配 | `CACHE_EVIDENCE_MODE_MISMATCH`，solver/checker 0 |
| cache entry 身份错配 | `COMPACT_CACHE_IDENTITY_MISMATCH`，solver/checker 0，原缓存不变 |
| compact 显式 schedule / check | 均以 `COMPACT_MODE_REQUIRES_DEFAULT_IMPLEMENTATIONS` 拒绝；两个 hook 实际调用均 0 |
| 64 外围草莓多日回滚 | 第 9 天 need392/cap298：真实得到证书、checker 通过，局部 staged 1 条且 admitted={9:true}；第 10 天 need784/cap298：compiler 因事先设置 startup 不支持而拒绝；公开 cache、day_evidence、route_feasibility 均为空 |

回滚用例重新生成 64 份日历并核与保存原劳动/资金字段一致；没有调用新劳动估算器或删减服务。它证明该人工输入上的多日原子提交边界，不能证明自然比赛必达该农场状态。24 MELON 的 full/compact 用例同样是固定人工条件。

独立纯接口实际计数为：route11、直接 fixture calendar88、直接 aggregate2、cache 构造5、compile_day_problem9、native scheduler/checker 各5、full custom schedule/check 各1、compact hooks0。完整内部经济的 1038/926 等后代调用另列，未混入这组纯接口计数。共 2 次独立 P2 模块定义加载、17 条记录；工程调用没有异常、遗漏、来源漂移或预算超限。原 summary 的错误分类属于已单独留证的后处理路径问题。

可复核的关键 SHA：

| 文件/值 | SHA-256 |
|---|---|
| P2 integration_prototype.py | `370063a750dfb8775a155fc9f36bcaff3f8e676795f70c91d8927dec5852e895` |
| execution_release_v1.json | `fdc0121ba3700a9ecfb5473b2caea06f211520c8edb1f27cbf694ce421b93b4b` |
| 冻结 run_validation.py | `63df61521618c180995c9fb082e02595878d6c33da628bb98f742fb2ee6f040f` |
| 原 controls_v1/summary.json | `81d8db688ccad498b72bdf387f39385e2f58a3042d6f44891dba32301a5c30e4` |
| corrected_compact_summary.json | `a6094f375fd86cbc057309d5bbc9a1f441efd7ec8ce58c3e4842dcbef500ad84` |
| offline_count_path_correction.json | `fc150af19dac79c52ddd0ec52997c086abe1dce98e8724aa67844e54e5e70ae3` |
| 两者相同的 typed plan | `c49439dd90d9caa8b3b5e80fca48fb388e3b2e919e21731e69352838bbaef134` |
| 两者相同的 typed state | `1d3b341ec49a288c53269f16772974c8c650a9a9ab0e0fe7636d165c86c9c000` |

82 个预冻结附件、17 条运行记录与只读更正结果均由相应 manifest 串联。最终交付清单另含本报告及独立复核，不回写旧证据。
