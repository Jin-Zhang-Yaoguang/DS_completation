# R10 B 独立只读审查

本轮审查对象是新增劳动准入绑定与已冻结的日历、生成器、检查器。未运行候选、官方引擎、完整比赛或新 Replay。只为根指定的已知不可能历史运行一次纯日历反例，调用量为 project 1、纯 next-day helper 1、compile 2。

首版绑定源码 SHA：`d728d483c0ef28f90595fb5c8f90ecf1ffe767c840870828b0374515d43ba49d`；首版 MATERIAL_BINDING SHA：`11c7fc54352b34f1ab7496067a34cb3338ffc1ea8d4840aae90c9f5bdb40a278`。以下行号对应这份首版，不代表后续修订。

## 阻塞：已知不可能历史被作为后续存活条件

冻结 `calendar_compiler.py:265` 将首日 WATER 的 `release > deadline` 记入该日 unsupported，但 `:281` 仍调用 `_apply_model_service`，然后推进以后状态。`compile_day_problem:343` 只读取请求日的 unsupported；`route_admission.py:246` 也只要求该请求日 SUPPORTED。

人工例：day 0、hour 24、新 WHEAT、`consecutive_unwatered=1`、`yield_units=1`，首水窗口为 `[24,23]`。模型先应用这次不可能首水，因此 day 1 仍为 PLANT；同一个纯 next-day helper 若不应用首水，结果为 WEED。将启动 fallback 仅设为 `[0]`，day 1 和 day 2 都仍可 compile SUPPORTED。

证据：[纯反例结果](review_impossible_history_probe_20260905T125932437784Z.json)，脚本 [review_impossible_history_probe.py](review_impossible_history_probe.py)。编译器 SHA `c908e47fed9236d9c74359e27758a0af237ece2a9da6993aed5e72c69764b402` 前后相同。这不是官方执行证据，也未用假路线制造端到端准入结论；它直接证明后续 DayProblem 来源可能包含已知不可能的历史。

最小修复应在新增绑定层核来源历史：请求日之前已有窗口/寿命不可能或模型状态冲突的日历，不得据其后续状态解除劳动拒绝。冻结核心及旧官方结果不回写。未知启动路线与已知不可能服务必须区分：前者可只对尚未表达的启动日 fallback；后者不能靠跳过一天重新获得有效存活来源。

## 已核对的绑定行为

| 项目 | 首版代码证据 | 结论 |
|---|---|---|
| 完整旧字段 | `route_admission.py:90–101` | 日历 goods/work/feed 聚合与独立旧值、workload、labor feasible/total 一致；没有降低旧 need。 |
| 当前粮源锚点 | `:108–116` | 从实际仓库及全部背包 WHEAT 出发，核当前与未来每一日 `held + buy - req = stock`；缺日、负数与现金/数量零值冲突拒绝。 |
| buffer | `:109–114,145–146` | `req[current] - complete_feed[current]` 同量增加未来期初与最低终存；未来 req 必须等完整 FEED，不增加现金信用。 |
| 其它物理占仓 | `:137–175` | 当前动物与显式待购动物继续占仓；肥料来自实际量及过去条件产出，清至最多 12 须显式 prior sale 条件；其它可售品无该条件则全保留。 |
| 当前失败保持 | `:229–236` | 当前日原失败直接返回；原本可行不新增证书。 |
| 旧劳动上限保持 | `:238–244` | 只尝试原失败未来日，费用必须 376、capacity 必须普通日 298 / 末日 285。新路线固定 12 hand，实际 h0 9 hire / h1 3 hire 的较少动作槽由 checker 逐步核。 |
| 原采购保持 | `:177–182,246–249` | 原买粮量及 estimated_cash 原样传入问题；无自生产量抵减原 BUY。 |
| 末存与溢出 | `:260–265` | 通过 checker 后仍要求 pre-EOD 仓粮至少旧末存加 buffer，并要求零 EOD 溢出；比只看背包+仓总量更保守，不会把未有效入仓的粮冒充后续来源。 |
| trial 回滚 | `:237,267,278–282` | 新缓存只暂存到本地 staged；全部失败日通过后一次提交。中途拒绝不向共享缓存写入已成功的部分日期。 |
| 缓存隔离 | `:186–217,251–252` | 当前 plan token/day/private 上下文及完整 DayProblem、实现身份、12 hand 构成键；正常内部使用下，改变资源、服务、期限或身份不能命中旧键。 |

## 必须保留的调用方责任

- `coverage_asset_ids` 与 calendars 相等只能核相互一致，不能证明调用方没有同时漏掉一只实际资产或承诺。接入必须从实际在田资产、已承诺项目、在途资产与 trial 项目独立枚举，并与旧 workload 来源核对。
- 启动工作只存在于原 `q.setup_work` 和 `q.calendar.work` 时，编译器不会从标量 work 反推路线。接入必须完整加入每个启动日期至 `startup_fallback_days`，尤其仅有 work、尚无 state/services 的日期。不能以空列表冒充已证明启动。
- 缓存是本次规划内部独占、只由准入函数写入的对象；首版命中后不重新执行 checker。不得从外部反序列化或允许其它模块写 `cache.entries` 后继续视为可信已验证缓存。结果中的 stats 已 deepcopy，不会因修改返回日志污染内部缓存。
- 未来 estimated_cash 只是外部资金前缀条件。此模块不验证未来实际价格/成交；prior delivery/sale 也只是明示条件，未对过去所有日期证明路线，不能称为真实未来状态。

## 生成器与官方短控复核

静态阅读冻结生成器后，没有发现绕过独立 checker 的成功路径。田间产物按来源绑定 delivery，未交付 WHEAT 不作为免费可用粮；全部服务完成才输出 FEASIBLE。按整组贪心接任务、先 BUY 后 SELL、先接下一组后交货会漏掉某些可行路线，属于保守 NO_CERTIFICATE；不能由 60 个组合或一份 NO_CERTIFICATE 推断调度完备/无解。

官方短控 harness 对实际 `_apply_unit_action/_commit_unit/_do_hire/_end_of_day` 前后状态留证，核动作、flag、真实物量差、成交数量与价格、出生位置、费用、pre-EOD 仓包/位置与 EOD 后状态。已读的首轮 352 步没有发现将请求当成功的实质缺口；未重跑。结论仍限人工条件服务日。根已独立复核保存文件与计数，并披露跨象限逐 tile 注入未同步土地元数据的边界；不能称这些人工状态均可从标准开局到达。

首轮结果不证明冻结 R9/R10 实际执行器沿证书行动，也不证明已救劳动失败会提高全局胜率。

## 对新增纯控制的建议

优先保留上述不可能首水来源反例，并验证修复后过去不可能窗口不能通过后续日；另对当前锚点加一粒、未来 req 漏一次 FEED、同一 plan 改一份资源/服务、首日成功后次日失败，分别核拒绝/缓存不命中/零部分提交。保留无 prior sale 时产品与肥料占仓、末麦只在背包或有 EOD 溢出的拒绝边界。无需重跑已冻结官方短控。
