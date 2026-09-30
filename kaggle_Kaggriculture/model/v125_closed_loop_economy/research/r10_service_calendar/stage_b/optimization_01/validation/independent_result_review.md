# P1 完整结果独立复核

结论：保存结果支持 P0/P1 在本次限定场景的完整等价；P1 仍未通过 1 秒耗时门槛。没有新候选、纯策略函数、引擎或比赛调用。本审查只读取现存 JSON/gzip，逐字节核 SHA，并独立比较保存的完整 typed 数据。

实际执行 release SHA：`3bcbd28bf9fb5d68bc872ce74d6b1c117f30a5db6d3a9e26f451b01fda56ea2d`。它绑定预执行 v2 freeze `9a2e4a00859c93aff25cf22bb60960a746b5735fb10e41d7a4ceea1b58595a42`；v1 是未执行的旧 oracle，不混用。

- 32 份冻结附件、12 份 run 的 SHA 全部相符，复核前后无输入漂移；12 份 run 均无异常，摘要检查项与原始 run 一致。
- 四组接口×P0/P1 共 8 次：修改前完整 result/cache、外部原始 P/C 快照、hook 记录、修改后的 result 与反向别名变化均逐值相同。
- 两份完整 economic 均返回，plan 的 31 个顶层字段、state 的 14 个顶层字段及全部嵌套 typed 表达相同。类型、dict 顺序、tuple/set/Counter 和浮点 hex 由冻结编码保留，没有过滤计划或状态字段。plan SHA `c49439dd90d9caa8b3b5e80fca48fb388e3b2e919e21731e69352838bbaef134`，state SHA `1d3b341ec49a288c53269f16772974c8c650a9a9ab0e0fe7636d165c86c9c000`，均独立重算吻合。
- P0 用时 21.198174458 秒；P1 用时 18.025442334 秒。本次差值 3.172732124 秒，约 14.97%。这是每版一次、同一人工状态的内部调用观测，不能估计方差或替代完整 agent 耗时。P1 明确大于 1 秒；120 秒保护仅用于保存完整诊断。

别名修正口径正确：原 P0 的 evidence 就引用编译 problem 的部分字段。8 次接口记录都显示外部 problem 的 start_shed.WHEAT 从 3 改为 888 时，result 对应字段也变化；P0/P1 的变化路径与值完全相同。v2 不再要求这个原本不存在的 result 全隔离，但仍核原始 P/C 在 hook 内部修改下不受污染、baseline/private/cache 保持隔离。修改前快照用于完整等价比较，未用被恶意改动后的结果代替。

计数复核：4 次定义加载；48 calendar、2 aggregate、6 cache 构造、8 route、8 compile_day_problem、native scheduler/checker 各 6、custom schedule/check 各 2；另 new_state 与完整 economic 各 2。route/日历/引用/hook 数由原始记录重算；checker 数同时对成功 route 计数，new_state/internal 数由完整输出记录和冻结单调用位置核对，并非另开运行时 profiler。完整 agent、官方引擎、新完整比赛均为 0。

可将本次已保存 P1 完整输出作为后续优化的冻结参照；不能据此追认金牌或整局执行通过。
