# 940 单次内部经济函数性能归因

本次唯一调用在 **30.0022607 秒**保护点中断，未返回计划。原始 pstats、堆栈及异常已保存，7 份冻结文件无漂移。实际为定义加载1、new_state1、内部 economic_plan_prefix1、完整 agent0、引擎0、新比赛0，未重试。profile 耗时不能代替无 profile 性能门；以下仅描述这一次已执行前缀。

原始证据：`run_once/raw.pstats` SHA `f12a462010a2482fb49a384c9a814c688704fdb1e8110740af8273728fa1f702`；`run_once/summary.json`、`run_once/interrupted_stack.txt`。父调用边另存 `parent_edges.json`，由 `analyze_saved_pstats.py` 只读导出，未再加载候选。

## 已确认的热点

pstats 记录总 self 时间29.996985秒，166,522,707次函数调用（144,081,212次非递归调用）。互斥 self 分类如下；这些百分比可相加，后面的累计时间不可以跨层相加。

| self 归属 | 秒 | 占比 |
|---|---:|---:|
| copy.py 的5个函数 | 14.4804 | 48.27% |
| scheduler，含嵌套函数/推导式 | 4.8732 | 16.25% |
| checker，含嵌套函数/推导式 | 1.7425 | 5.81% |
| JSON 编码 | 0.6149 | 2.05% |
| route_admission 本体 | 0.3276 | 1.09% |
| calendar_compiler 本体 | 0.1189 | 0.40% |
| integration 本体 | 0.0554 | 0.18% |
| 两类 canonical_sha 包装函数本体 | 0.0050 | 0.02% |
| 其他（包括 dict.get、id 等内建函数） | 7.7790 | 25.93% |

`deepcopy` 入口总19,198,314次（非递归379,628次），累计18.8977秒，即整个已观测前缀的63.00%。这个累计值包括它调用的 dict.get、id 等，**不是**在48.27%之外再增加63%。

最有区分力的父调用边如下。每行是该父函数直接调用 deepcopy 的累计成本；递归 copy.py→copy.py 边已剔除，未重复相加。

| 直接父函数 | 外部 deepcopy 次数 | deepcopy 累计秒 |
|---|---:|---:|
| route_admission | 2,081 | 11.4356 |
| checker.check_day | 770 | 3.3855 |
| compile_day_problem | 62,878 | 1.8638 |
| checker._validate_problem | 56,176 | 1.2945 |
| checker._run | 236,642 | 0.7466 |
| 其他直接父函数合计 | 21,081 | 0.1717 |

调用次数不等于不同对象数量。全部非copy.py父边累计恰好闭合18.897692763秒，逐项原值见JSON。route_admission 的11.4356秒包含多处复制；pstats按父函数聚合，无法把它精确拆到第1223、1226、1232、1235等不同源码行。因此不能宣称11.44秒全部可省。

scheduler共422次，累计6.9367秒；其中 free_assignment 81,351次、remaining 3,738,499次、projected_group_cost 516,840次。其确定性逐工人扫描仍是第二类实际工作量。checker共385次，累计8.3473秒，已经包含其内部复制，不能与上述copy累计时间相加。

JSON dumps共2,565次累计0.6168秒；其中compiler/hash包装1,758次、scheduler hash422次、checker hash385次。服务日历生成182次仅累计0.1840秒（48个已在田资产、134个报价）；按请求日compile422次累计2.0524秒，其中1.8638秒来自直接复制。证据不支持把第一次完整服务日历编译或SHA当作本次首要热点。

## 前缀走到了哪里

记录156次 budget_quote、134次 route_admission、268次实际资产日历缓存查询。已在田的48份日历只生成一次，说明现有懒编译确实生效。堆栈仍在原经济函数第2264行的初报价循环；register_quote、finish没有记录到调用，状态中投资收据0条。这里没有完整计划、新增许可或实际成交结论。

请求日compile和scheduler都是422次。结合每次compile后只有cache miss才调用scheduler的控制流，可判断这个前缀没有命中证书缓存；这不说明缓存键错误，也不能区分唯一报价、来源字段差异与后续失败丢弃staged各自贡献。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/performance_940/prototype_940.py:1217]

中断栈直接停在route第1226行，向checker传参之前的deepcopy；这与累计热点一致，但栈本身不用于量化。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/performance_940/prototype_940.py:1226]

## 最小下一步

首轮只优化默认实现的三个外层复制：第1223行给默认scheduler的problem副本，以及第1226行给默认checker的problem、certificate副本。默认scheduler只读输入，构造独立工作状态；默认checker第1019行已经各做一份输入复制。这三处可静态证明重复，独立对象审查见上级 `copy_safety_review.md`。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/performance_940/prototype_940.py:1223] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/performance_940/prototype_940.py:1019]

修改必须用**原调用参数是否为None**识别默认路径，显式注入schedule/check继续原深拷贝语义。保留checker内部资产/service副本、证书返回隔离、staged提交、cache stats输出和legacy快照；这些保护输入、缓存与公开证明对象互不污染，不能按热点大小直接删除。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/performance_940/prototype_940.py:1231]

可证伪假设是：仅消除默认边界重复复制，返回路线/拒绝原因/现金评分与动作不变，原输入/缓存/公开结果隔离仍成立，并降低相同输入的工程耗时。尚未实测省时幅度，不承诺能从10秒超时直接进入1秒要求。若这一轮不足，才另审证据布局或共享日历缓存；不得把少校验、放宽拒绝或提前丢失败证据当作等价优化。
