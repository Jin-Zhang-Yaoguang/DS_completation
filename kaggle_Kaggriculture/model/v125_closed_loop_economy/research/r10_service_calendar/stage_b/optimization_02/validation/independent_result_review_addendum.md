# P2 离线计数更正补充核验

更正成立：P1/P2 完整 typed plan/state 全等，9 项计数从两份原始压缩输出重新读取后完全一致；P2 原耗时仍为 **13.305441375006922 秒**，未通过 1 秒要求。

本补充保留已有 40/40 独立审查，不覆盖原报告或原始错误 summary。新增只读核验 **39/39** 通过：82 个预冻结附件、17 条运行记录、离线更正清单的 107 个文件哈希一致，读取结束后再次核全部输入无漂移。更正清单 SHA 为 `4c27862e27241206bd59bf51963d476944fe75f52d742498d797ae8a62850017`。

原 harness 第 313–315 行从 `r10_future_route` 顶层取四项计数，所得 null 已保留。正确路径为 `state['investment_receipts'][-1]['r10_future_route']['counts']`。本次独立读取原始类型编码，确认 route_attempts=342、actual_calendar_compilations=48、quote_calendar_compilations=312、scheduler_calls=1038、checker_calls=926、cache_hits=4、route_successful_quotes=216、route_failed_quotes=126、quote_calendar_cache_hits=862；均与更正附件相同。原冻结 harness SHA、原 summary SHA 与两份完整输出未变。

更正后的 `P2_TIME_THRESHOLD_FAILED` 口径准确。计数是保存的规划审计字段，本补充没有独立运行时采样；11 项纯接口调用与完整规划后代计数分开。现有报告明确限定人工状态、一次内部规划和性能失败，未发现新增阻塞。

本次没有导入或调用候选、调度器、检查器、引擎，也没有新比赛。一次独立读取脚本在解析前因文本编码失败，未执行或写文件；随后以纯 ASCII 脚本完成上述读取和核验，JSON 已留说明。

完整输入哈希与逐项结果见 [补充 JSON](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_02/validation/independent_result_review_addendum.json)。原 [40/40 独立报告](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_02/validation/independent_result_review.md) 保持原样。
