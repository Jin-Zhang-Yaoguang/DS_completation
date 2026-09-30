# P2 保存结果独立复核

结论：**完整计划与状态等价，性能门失败。** 本次独立只读复核 40/40 项通过；原始 summary 的 `EQUIVALENCE_OR_SOURCE_FAILURE` 来自计数层级读取错误，不能据此判定策略输出不等价。P2 实际内部经济函数耗时 **13.305441375 秒**，超过预登记 1 秒阈值，仍不可进入新完整对局。

## 证据与范围

| 检查 | 独立结果 |
|---|---|
| 冻结输入 SHA | 82 份全部匹配，无漂移 |
| 原始 gzip 结果 SHA | 17 份全部匹配，无漂移 |
| P2 源码 | `370063a750dfb8775a155fc9f36bcaff3f8e676795f70c91d8927dec5852e895` |
| 完整带类型、有序编码的 plan / state | 直接与保存的 P1 原始编码比较，均完全相等 |
| 完整规划内审计计数 | route 342、scheduler 1038、checker 926、cache hit 4 |
| 有限纯接口 | 11 项通过；原四类 full 接口结果、缓存及引用行为与 P1 相同 |
| compact 隔离与拒绝 | 修改返回值不影响缓存；模式、身份或显式 hook 不符时拒绝且不修改缓存 |
| 部分成功后回滚 | day 9 已经完整 checker 通过并进入 staged；day 10 编译器拒绝，最终缓存和准入均为空 |
| 实际工程计数 | 仅 P2 new_state 1、内部 economic 1；没有新 P0/P1 调用、完整 agent、官方步骤或完整比赛 |

完整 plan 编码 SHA：`c49439dd90d9caa8b3b5e80fca48fb388e3b2e919e21731e69352838bbaef134`。完整 state 编码 SHA：`1d3b341ec49a288c53269f16772974c8c650a9a9ab0e0fe7636d165c86c9c000`。未通过删除诊断字段、忽略字典顺序或抹平数值类型来制造等价。

## 原始后处理错误

`run_validation.py:313–316` 先取最后一行 `r10_future_route`，随后用 `audit.get(k)` 取四个计数。实际计数在 `audit['counts'][k]`，所以四项被错误读为 null，触发第 327 行的等价失败标签。原始结果、harness 和 summary 均保留原字节；本报告只是独立更正其解释，没有回写或重跑。

这四项是完整规划保存的审计计数。纯接口另有实际调用预算记录：11 次 route、9 次日编译、5 次原生 scheduler、5 次原生 checker；没有超出登记预算。两组计数口径不可混用。

## 回滚断言的精确边界

多日反例的第一日（day 9）确实完成 `SUPPORTED → FEASIBLE → checker valid=true`，且失败前 staged 已有一条、admitted 已含 day 9。第二日（day 10）因 `UNSUPPORTED_STARTUP_FRONTIER` 在编译器入口拒绝。最终返回 `labor_feasible=false`，`route_feasibility_by_day={}`、`day_evidence=[]`、缓存为空。该反例验证了**后一日编译失败时不提交前一日成功证据**，未覆盖“后一日 solver 运行后失败”的不同分支。

## 性能解释

保存的 P1 同一人工初态内部经济调用为 18.025442334 秒，P2 为 13.305441375 秒，单次观察降幅约 26.19%。这是各版本一次无 profile 的内部函数结果，不是完整 agent 性能，也不能外推其他状态。性能阈值不变，P2 仍失败；完整输出等价和 11 项接口通过不能替代耗时门或比赛强度门。

本次独立审查只读取冻结文件与 gzip 数据，使用独立的数据解码、投影和 SHA 计算；未导入候选、原验证 harness 或调用 solver/checker。完整 40 项布尔检查、原始 SHA、执行计数和回滚事件见同目录 `independent_result_review.json`。
