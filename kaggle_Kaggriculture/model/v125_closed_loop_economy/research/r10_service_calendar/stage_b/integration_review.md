# R10 静态集成独立审查

结论：对当前 `integration_prototype.py` SHA `940a7438f57d10978ef93ee2eb4168a04e644f0fa8531180f1c960719f5471f0` 的有界静态审查未发现剩余阻塞，可进入已授权工程控制。此结论不是候选行为等价或强度通过；本代理未加载、调用完整候选或官方引擎。

首稿 c33 已保存在 `prototype_c33_pre_unrepresented_guard/`。本次读取并独立重算 AST，结果见 [review_integration_940_static.json](review_integration_940_static.json)。原 45 个顶层函数只有 `economic_plan_prefix` 改变；legacy 副本恢复原函数名后 AST 与冻结 R9 一致；最后静态函数仍为 `agent`。源码三处 quote 登记和一处未表征合同登记均已确认。

## 完整来源与条件日历

- 实际在田资产由观测 tiles 独立枚举 PLANT/animal，随后与旧 `model.calendars` 本方 position 集合精确比对，并拒绝重复位置。每个增强日历的 goods/work/feed 与旧实际日历逐值比较。
- 原经济中三处 `workload.update(q.calendar.work)`——有效未完成合同、独立在途项目、正式接受报价——同位置登记 source。它没有从 commitment/transit 两个列表重复拼装，因而同一既有动物兼属两个分类时不会重复登记。
- 有库存的动物按所有私有仓/包数量，与来源中 `fixed_cash == 0` 的动物报价数逐品种精确对齐。未分配在途动物会拒绝路线准入，不能因为旧经济漏掉它就当作零义务。
- 报价增强日历按原 `start_step_model` 的日与 `hour+1`、原 crop/animal 合成字段重建，再加回原 `setup_work`，最后精确比较原 goods/work/feed。只要重建时钟或旧字段不符便拒绝；启动工作涉及日与激活日均进入逐日 fallback。
- baseline 是实际资产加已登记来源，trial 在此基础上只多本次 q；全部来源共同进入原字段聚合和 route 验证。pure 编译缓存不自动进入来源集合。

## 首稿未表征合同缺口已封闭

首稿 c33 中，free 格上的未完成 PLANT/BUILD 合同若原 `investment_quote(..., committed=True)` 返回 None，既不进入旧 workload，也不进入新增来源。因此“增强日历与旧 workload 相等”本身不能证明完整合同覆盖；无现货的合同也不受动物库存对齐检查保护。

这是一项结构性覆盖缺口，**没有证明它会在自然轨迹造成完整路线假通过**。远途启动超过末局窗口通常出现在较晚日期，而新报价本身也受种植截止和成熟窗口限制；不能把未经验证的时钟例当作已发生缺陷。

940 版本在原 qNone 分支保留 target/item/剩余 stages 至 `unrepresented_commitments`，仅在 `_r10_integration_rows` 尝试路线时拒绝 `UNREPRESENTED_COMMITMENT_WITHOUT_CALENDAR`。旧 workload、原执行动作及原本可行路径均未因此重写；日志保留缺口内容。此修复闭合的是新增证书的完整来源前提。

## 资金、评分与许可

- 只有原 labor 不可行、当前日原 workload 未超 capacity、且原 net>0 的报价尝试新路线。当前日不足和非正净值仍在前面退出。
- funding trial 仍使用原 `funding_trial_model`、共享 requirements、原 labor、原 fixed cash、信用批与 ceiling；只是在未来劳动失败分支提前计算，后续复用同一个纯结果。原 `prefix_admission` 仍逐报价执行，没有用路线成功替代资金条件。
- 原 net、执行 score、selection score 的计算未改变。原劳动费用和 capacity 原样传入，仅用另一字段记录有效路线可行性，未把旧 `labor.feasible` 改真。
- 正式接受报价前会重新调用预算过程；通过后才登记来源并更新 `last_accepted_proof`。报价扫描中的成功/失败不会直接成为经营许可。最终 proof 覆盖最后一次被接受报价时的完整组合；最终原失败日仍逐日核其证书。
- 原 make_tasks、market_orders、allocate、收据确认、资金辅助函数 AST 均未改变。本次静态隔离不证明实际执行器会沿新证书行动。

## 纯缓存的准确口径

当前 ctx 只在一次 `economic_plan_prefix` 调用内创建。quote 编译缓存、完整 DayProblem 路线缓存、sources 都没有作为可复用缓存存入持久 state；计划只留下压缩证明及计数。

route 内如果某日失败，不提交该次 trial 已计算的其它成功日期。若路线全部通过、但 q 随后被原资金前缀拒绝，纯路线 memo 可以保留：它证明的是物量和日程条件，q 的 fixed cash 不是该命题变量。以后命中 memo 仍必须重新过原资金前缀。

因此不需要为了资金拒绝清掉纯路线 memo，但不能称“所有被拒报价的缓存都回滚”，也不能把该 memo 解释为已融资或已许可。q 未正式接受就不进入 sources，`last_accepted_proof` 也不会被其覆盖。日志已区分报价尝试与真实许可。

## 内联器与既有纯对照

已读取 `inline_modules_initial_verification.json` 的 12 组逐值对照，以及 `inline_route_tests_20260905T130513688154Z.json` 的 15/15 检查和对应 harness，未重复执行。后者用原模块/内联模块各自的 PlanRouteCache 类，覆盖真实成功、缓存命中、startup 拒绝、锚点拒绝；原/内联各 4 次 route，总 scheduler/checker 各 2 次。全量输出、缓存内容和输入保持比较均具体存在，未将两套类交叉混用。父级 globals 哨兵也保持原值。

独立 AST 扫描当前四个冻结模块，未发现参数以外的 class 方法、except 绑定或嵌套函数与映射全局名冲突。内部 imports 指向正确前缀；自有模块变量与标准库 imports 均与父策略隔离。当前类的 `__init__` 不在模块映射中，不会被错误改名。

内联器仍不是通用 Python 词法变换器。已保留一个与当前冻结模块无关的人工反例：顶层 `worker` 与 `Box.worker` 同名时，方法定义被重命名，`self.worker()` 不变，原结果 3 变 AttributeError。见 [review_inline_and_integration_static.json](review_inline_and_integration_static.json)。此人工控制只有 2 次定义 exec 和 2 次人工方法调用，route/候选/官方均为 0；不影响当前四个已检查模块，但未来变更输入模块不能直接继承本次证明。

## 入口证据与后续验证边界

已有 `prototype_entry_20260905T131055960552Z.json` 用真实 loader 验证的是 c33：返回 agent、定义加载后 `_STATES` 为空，未调用 agent。940 保持相同的“helpers 在父首个函数前插入、agent 最后定义”结构，本代理只验证 AST，没有把 c33 的加载结果冒充 940 的运行检查。

940 源、helper `c72310cbfcfb7a8bac2d107cbf630fe9d5becf27f03608b9620d55c7d111f130`、builder `4ad28fb247d4ca58fb26be57359b47f848b50b2815158e13a8d4784b78d65fbb` 的工程控制仍需按对应 SHA 登记。后续尤其要验证完整旧路径对照、合同/在途混合来源、失败报价不生成许可及真实 runtime 预算，不能把纯模块对照升格为完整候选通过。
