# R10 B 接入冻结 R9 经济函数的最小方案（尚未生成候选）

只改变“原未来劳动不足”是否有完整条件路线证明。R9 的原 `goods/work/feed`、net、net/labor、selection_score、现金前缀、市场与执行器均保持原含义。原 current-day 失败、原已可行日期不进入新门；原费用不因路线省工降低。模块静态内联由根负责，本文件不是执行记录。

## 1. 保留原函数，进入失败分支才懒编译

采用根提出的更小接入：`project_calendar`、`investment_quote`、`dated_market_model` 均保持原函数不动，不为每个初始报价建立30日服务状态。只有原未来劳动失败分支真的需要证明时，才编译完整 portfolio。不会从整数 work 倒推服务，也没有父 agent 调用或外部策略包。

当前真实田产由原 obs 的 tile/position、当前 day/hour 输入服务编译器，逐值核同一资产旧 goods/work/feed。q 的生命周期初始 tile 按冻结 `investment_quote` 的确定性定义重建：item、`start_step_model//24` 和 position 唯一确定 crop/animal 类型、出生日期和初始flags；crop 的初始 yield=ongoing时0否则1、dry=1、watered=false、fertilized_until=-1，animal 为 yield=0、fed/cared/fert=false、pending=0。编译 hour 必须是 `start_step_model%24+1`，不能修正成另一时钟。该重建须与冻结源码逐字段核验，任何原 goods/work/feed 不同均 fail closed。

再把 q 的原 `setup_work` 逐值加回编译 work，与 q.calendar 原三个字段核对。启动日集合由 `setup_work` 的非零日期并上 `start_step_model//24` 自动生成，不能由调用者手填空列表。启动日只用原劳动约束；之后才能使用条件激活的田间资产。每次 plan 内缓存已核对的完整当前田产与承诺calendar，已接受 q 才追加；trial 临时列表不修改 baseline。

冻结 compiler 对“已知不可能首水”仍会继续推未来状态，已保留反例。独立 route 绑定层检查该 calendar 初始化日至请求日的全部 `unsupported_by_day`；有明确窗口/状态矛盾则拒绝后续路线证明。只有“尚未证明如何启动”的 `startup_fallback_days` 才只影响本日。后续不得绕开绑定层直接用 raw compile 的 SUPPORTED 当准入。

当前报价如 `start_step_model%24+1 == 24`，必须保留这个原始时钟；不得将它挪到下一日或假设首水成功来获得通过。

## 2. 维护完整的本方原模型义务集合

在 `economic_plan_prefix` 内创建一次独占 context/cache，并维护当前 baseline 的 source list：

- 当前真实本方田块：从本方 observed tiles 独立枚举，再与 dated model 的本方 calendars 按位置、类型和出生日期核对。对手日历只用于原价格模型，不进入本方劳动。
- 旧 PLANT/BUILD 合同对应 q，以及现有在途动物可分配位置的 q：在原代码将其 work/feed 加入时，同步登记相同 q、setup 与是否已有实物，暂不编译服务。不要把同时属于 commitment 与 transit 的同一个 q 登记两次。
- 已许可项目：每次原循环接受 q 后才将它加入 baseline；拒绝报价不能残留。每个待试 q 的 trial 为 baseline 加 q 一次。

`coverage_asset_ids` 应从上述独立来源登记生成，并核对服务编译器输出；不能从待验证列表自己抄一份就声称已覆盖观测。原 R9 无位置可分配的在途资产没有完整未来生命周期日历，此限制应单列；其实际物量继续保守占仓，不假称未来照护已证明。

`pending_animal_units` 只计上述 q 中尚未实际持有、原固定款已列入共享资金账的动物；当前 shed/背包已有动物由实际库存提供，不能再加一次。即使之后条件激活，首版仍保留物理占仓上界，代价是可能多拒绝。

## 3. 只在原劳动失败分支计算路线输入

原 `budget_quote` 已先得到 next_work、原 labor、边际费用与三种分数。原来在 `if not labor['feasible']` 直接返回。接入此分支时：

1. 当前日不足，或原净值非正，保留原拒绝。净值仍使用原劳动费用，不用路线重新算分。
2. 将 baseline 与本 q 的完整来源合并并懒编译服务；构造完整 trial_requirements（含当前一次 buffer），使用原 `funding_trial_model` 与 `funding_cash_book` 计算原粮账。该函数只复制/计算，不提前调用 `apply_project_supply`，因此拒绝没有市场模型副作用。
3. 用原 labor、原总 workload、原 goods/work/feed 聚合和原资金粮账构造两个 portfolio。原 Counter 缺日代表 0，接口所需 dense day map 用查值展开；保留原 sparse 对象/hash作为审计，不修改原对象。
4. `route_admission` 只逐一处理旧失败未来日，固定 12 hand，核原当日 cash=376、原 capacity=298（末日285）。任一证书失败或不支持，整个 q 保留原 labor 拒绝；只在全部失败日都通过时继续原 net 与 prefix_admission 检查。
5. 原 prefix 不过仍拒绝 q。路线存在不提供新现金或经营许可；未来条件销售也不在这里另加收入。

`labor['feasible']`、capacity_by_day、cash_by_day 与 total_cost 保留原值。另加 q/plan 的 `route_feasibility_by_day` 和 `effective_labor_feasible`，不要把原 false 改成 true 混淆证据。下一项目报价仍调用原 labor_schedule；同日证书可由本次 plan cache 命中。

原已可行分支继续走原代码；新模块不介入改进路线、减少雇工或重算费用。

## 4. 资金与物理输入

沿用 `MATERIAL_BINDING.md` 的当前真实粮锚点、future requirements=完整 FEED、逐日 stock 递推与 buffer 两端守恒。start WHEAT=原 stock[d−1]+buffer，终存下限=原 stock[d]+buffer；原 purchases/cash 强制保留。

调用方必须显式选择条件 prior delivery/sale。原日历收益本来假设及时采收交付，首版可明确沿用此前非保留商品及时出售的条件；这不是实际发生，也不保证冻结 R9 市场按该日程执行。当前实际不可售动物、条件待购动物和由实际/已有条件产出支撑的最多 12 肥保留继续占仓。库存超100、h0原采购无法完整入仓、末仓麦下限不足或EOD溢出则不出证。

## 5. 内联、诊断与运行时边界

四模块的全局名称及 stdlib alias 必须分别静态加私有前缀，解析内部引用，不能文本串接覆盖原 R9 的 CROPS/ANIMALS/PRODUCTS/ACCESS。禁止动态 exec 父代码。build 后应核所有原非准入函数 AST 与对应原函数一致，并用纯向量验证模块内联前后结果相同。

缓存只在一次 economic_plan 内生存；完整 DayProblem、资金来源条件、实现身份都进入 key。失败不提交已得到的部分日期结果。可先按原失败日排序，遇失败马上停止；不遍历原可行的未来日，不枚举人数。future state 的服务编译可按同一 observed tile 或重建的 q 初始tile、原三字段与 setup hash 缓存；不能只按 asset_id 缓存而忽略当前 flags、现货、日期与窗口。

逐帧投资收据至少附：原失败日期及need/capacity/cost、新证明成功/失败/unsupported、真实 solver/checker 次数/cache hits、资产覆盖hash、buffer/起存/采购/终存约束、首个拒绝理由。给定来源可离线重建证书；不把预定服务计入真实HARVEST/FEED/PLACE完成数。

## 接入前尚待的工程控制

- 所有当前真实资产、旧合同、在途与已许可 q 的来源恰好一次；新增 rejected q 后 source/model/cache 不变。
- 旧选择关闭消融在相同短实际状态下动作逐字等价 R9；三种分数与所有原 costs 不变。
- 懒编译后 goods/work/feed 与原日历逐值相同，尤其 synthetic q 初态、setup 跨日与 hour24 已知不可行边界。
- 候选单文件静态符号隔离、原执行函数 AST 不变，以及开放旧状态纯经济规划性能。尚未测整候选时间，不能把当前独立模块的测试时长称作 1 秒推理门已过。
- 必须另测冻结执行器是否兑现服务证书；路线存在与实际沿路执行是两个不同命题。
