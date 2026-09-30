# 生产路径精简证据模式：P2 待选设计

仅设计，未实现、未调用任何候选/solver/checker，未做性能验证。必须先取得P1完整工程结果，再决定是否另立P2；不修改P1的19份交付附件。

**单一假设：保留相同的完整求解、独立重演与准入检查，只缩小校验成功后缓存和传递的日志对象，可降低复制成本，同时最终plan、st、许可、三类评分和动作逐值不变。** P0 profile显示route直接调用deepcopy累计11.4356秒，但无法把同函数内staged、evidence与其他复制分开计时；不能据此承诺本设计的省时幅度。

## 已核实的真实消费者

`_r10_integration_compact_result`只读取以下字段。现有consumer没有读取整个problem、certificate、service_receipts或market_events。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/integration_helpers.py:136]

| 来源 | 读取字段 | 最终用途 |
|---|---|---|
| route结果 | status、labor_feasible_after_routes、route_feasibility_by_day、reason、failed_day、trial_legacy_sha256 | 原compact proof逐值保留 |
| 每日evidence | day、problem_sha256、old_need、old_capacity、old_hire_cash、buffer_debit、start_shed、reserved_shed、buy | 原witness逐值保留 |
| checker.stats | completed_service_count | witness.service_count |
| checker.stats | delivered_goods、purchased_goods、terminal_shed | witness中同名字典，逐值与顺序保留 |
| route结果（consumer之外） | scheduler_calls、checker_calls、cache_hits | 原ctx计数及receipt，必须不变 |

`_r10_integration_try_route`还记录status、reason、failed_day、route_days等首16条事件；`finish`记录cache条目数、获准proof和最终劳动状态。不能只比cash或“是否可行”，必须比较这些诊断字段以及完整st。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/integration_helpers.py:168] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/integration_helpers.py:190]

## 最小接口与缓存格式

建议route新增 `evidence_mode="full"`，公开审计默认走P1完整分支，返回字段、错误和完整证据均保持原样。未来生产接入才显式传 `"production_compact_v1"`；整个plan的cache固定一个模式，不在同一cache混跑两种模式。调用参数、helper接入和新源码SHA须在P2另冻结，不能改变P1。

compact首版只适用于冻结默认scheduler/checker；显式hooks继续使用full，compact与自定义hooks同时请求则明确拒绝，不静默切换。模式记在内部cache和外部运行清单，不往现有plan/st/receipt添加字段，避免“日志优化”破坏严格逐值对照。

compact缓存每个成功日只留：

- 身份：mode、summary_schema、完整problem_sha256、三个implementation_ids、admission语义版本、n_hands。保留全部问题内容的摘要；不能仅按日期、产物总数、services数量或删掉conditional来源来增加命中。
- 通过标志与守卫事实：checker_valid、certificate_n_hands、certificate_hire_cost、checker_hire_cost、conditional_eod_overflow。后两项保留已验证的376和零溢出事实。
- 四项消费统计：completed_service_count、delivered_goods、purchased_goods、terminal_shed。

不持久化完整problem、certificate、verification、completed_service_ids、service_receipts、market_events、terminal_inventories等大型记录。**只是在全部校验完成后提取小摘要**，不修改checker去少生成或少验证这些内容；完整对象在当前miss内仍正常生成，再按生命周期释放。原legacy_fields_unchanged快照先保留，避免把另一项接口裁剪混入首个P2。

## miss和hit都不放宽

cache miss仍执行原所有portfolio覆盖、历史状态、startup、粮账、仓容、完整调度与独立checker重演；checker的每单位动作、服务依赖、物料、出生口、期限、来源守恒与EOD检查全部保留。只有原三项后验守卫——12人/376费用、实际终仓WHEAT达到预约、EOD零溢出——都通过后，才把小摘要放进staged。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/route_admission.py:263] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/route_admission.py:268]

每个请求仍先编译完整problem并得到原problem摘要。full保留原key公式；compact在同一完整key材料外增加mode和summary_schema域。on-hit核mode/schema/完整problem摘要/三实现ID/admission版本/12人身份一致，小摘要字段完整合法，才复用。终仓WHEAT和零溢出、费用事实可按同一材料再次核对；不能接受只有valid=True的裸缓存。摘要只是本次plan内受控代码的memo，不是可对外验证的独立证书。

固定模式内，key映射必须保持一一对应，因此P1与P2的miss/hit数量、solver/checker调用次数及cache条目数应完全相同。若出现数量变化，按机制变更或错误处理，不能视为此优化的收益。当前cache以plan_token/current_day/observed_private摘要隔离，继续保留；无跨帧、跨候选或持久缓存。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/route_admission.py:193]

全失败日都通过才commit staged；后续一天失败仍全部丢弃本次staged，失败结果的day_evidence继续原语义。后续现金拒绝与证书memo的关系不变。不得缓存负结果或提前部分commit。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/route_admission.py:285]

## 对象隔离

精简不能简单删除deepcopy并共享原嵌套字典。cache摘要由原stats**新建**：产品和终仓都是商品→标量的平坦字典，逐项复制；元数据也创建自有小容器。对外生成day_evidence时再次创建产品/终仓小字典；start_shed、reserved_shed、buy从本次problem新建小字典。这样compact_result、q._r10_approval和receipt虽保持现有公开proof引用关系，但其中任何可变值都不会指回cache。

保留caller输入、缓存内容与返回对象三方隔离。不能把staged中的problem引用公开后再删掉原第274行复制，也不能把cache.stats直接交给compact_result；原helper是浅层选取字段，会延续嵌套字典引用。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/route_admission.py:274] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/integration_helpers.py:142]

## 进入P2之前的验证要求

1. full默认接口对P1逐值等价；compact经过原compact_result后，与full的proof、ctx诊断和完整plan/st逐值等价，不忽略日志差异。
2. cold/hit、跨多个失败日最终回滚、cash后来拒绝、非法历史/startup/料账/仓容/期限、day29全部沿原拒绝与计数路径。
3. 修改返回的start/reserved/buy、商品统计、terminal_shed，再次hit仍得到原值；反向修改原problem/certificate不能污染已存摘要。模式/schema/完整问题/实现身份错配必须拒绝，不能误命中。
4. 相同fixture下P1/P2预算、分数和最终计划严格一致；再做登记的无profile耗时和内存/输出体积观察。P0/P1/P2源码与记录分开保留，不能用日志体积减少冒充策略强度改善。

本设计仅减少校验后的证据复制和驻留对象；不消费certificate来改执行、不减少solver/checker工作量，也不修改模型或准入集合。实际节省多少仍待P1结果后的独立实验。
