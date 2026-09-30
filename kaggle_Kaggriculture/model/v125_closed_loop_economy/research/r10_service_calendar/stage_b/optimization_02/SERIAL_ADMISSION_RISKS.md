# 每帧单一新增项目：静态反例与边界

仅设计审查，不授权改变 P2。没有导入或调用策略、日历、solver、checker、引擎，也没有执行微场景。依据冻结 R9 `e7f1fd54…` 与 P2 初稿 `370063a7…` 的现有源码；下述 A/B 数字是解释性反例，不是实测收益。

结论：每帧最多完整验证一个新增项目，可以限制项目级试算次数，但属于新的准入策略，不能作为 P2 等价优化。它会改变投资顺序、专家选择、许可速度及可能的资产组合。即使只剩一次完整检查，该检查仍包含多日、全部资产的调度和重演，加上全部候选的报价与基线日历，不能静态承诺降到 1 秒。

## 现有路径中不能直接截断的部分

R9 先汇总己方在田日历，登记未完成 PLANT/BUILD 合同、消耗对应种子/在途动物额度，并给其余在途动物分配结构或空地；之后建立共享粮账、劳动账、资金前缀。[R9:622–715](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r9_cash_prefix/main.py)

当前 `budget_quote` 先算新增项目的边际雇工、现金饲料和自有粮机会成本，再产生 `net_cash_model`、执行 `score=net/labor` 与选择 `selection_score`。P2 在原未来劳动不通过时才尝试完整组合路线，现金前缀仍单独核；当前日劳动失败不会获救。现有扫描把**已通过这些门的报价**用于 expert_scores/crop_scores，再对选中专家的报价重新检查和逐项提交。[P2 integration_prototype.py:2266–2365](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_02/integration_prototype.py)

因此，“便宜评分”应先界定精确性：保留原边际雇工和机会成本、仅暂不做 route/资金前缀，可称当前模型的未准入净值；若只取 investment_quote 的 net_before_hiring_model，便已省掉边际雇工及共享自有粮账，不能再称原 net_cash_model。原始报价本身也计算生命周期和逐单位售价，并非免费操作。[R9:313–401](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r9_cash_prefix/main.py)

## 必须在实现前解决的风险

| 风险 | 最小反例或直接影响 | 必须保持的边界 |
|---|---|---|
| 最高项反复失败使其它项目饥饿 | A 未准入净值 200，B 为 150；A 每帧都得到 NO_CERT，B 实际可过。若每次从同一最高项开始，只验证 A，B 永无机会。NO_CERT 仅表示当前构造器没给出证书，不是全局无解。 | 需要跨帧的确定性失败排除规则；不能靠旧 PASS 放行，也不能把一次失败永久认定为不可行。 |
| “最高”评分口径变化 | 原预算后净值扣边际雇工、自有粮机会成本；原 q.score 则按劳动归一。拿便宜的 gross 或 net_before_hiring 排序会重新偏好耗工项目。 | 临时排序值独立命名；最终门和提交必须使用当前观测重新计算的原成本与现金前缀。 |
| 错误 expert/crop_scores 泄漏到执行 | A 属 horticulture 但最终不通过，却先写 expert_scores 并选 horticulture，可能排除可行 B。未准入的高 crop_score 还会放大同品种已许可/承诺播种任务的权重。 | 未检查或被拒报价不得写入“已准入”评分字典、许可、订单或 source registry。`st.forecasts` 仍用真实当前报价。若只剩一个通过报价，专家记录应对应实际结果；无通过时的专家/评分回退要明确登记，不能伪称完整扫描最优。 |
| 旧承诺被“一项目”额度截掉 | 两个旧 PLANT 合同或已有动物在途，同时本帧选了一个新 q。把其它目标排除会漏算未来工作、饲料或固定现金，还可能重复给相同空格许可。 | 一项目限制只作用于新许可。所有在田、旧 PLANT/BUILD、在途、已确认启动义务必须先完整进入基线和 reserved；原合同确认、续行与必要 FEED/WATER 不受该额度排除。 |
| 拒绝后提前返回破坏经营 | 选中 q 失败便返回空计划/全 PASS，旧动物失喂、旧合同停止；或者保留了 q 的 hire/material slots，却没获许可。 | 失败只移除本次 q 的试算增量，仍返回完整基线 plan，照常生成既有任务、原补粮和雇工目标。trial 不得先改 shared funding/model/sources 再靠不完整回滚。 |
| 许可与实际采购/落地混淆 | q 获准 BUY_SEED，但实际市场因现金/槽位未成交；下一帧转选其它 q。或 q 先 BUILD，建筑完成后原合同消失，下一帧只看最高项而不再继续对应动物采购。 | 当前 observed cash、真实采购容量/槽位和下一帧确认仍是唯一执行依据；许可不计作已买或已落地。必须准确称“每帧最多一个新许可”，不能据此声称只有一个完整启动链。 |
| 同格与在途动物重复 | 挑选发生在 reserved 汇总前，空格同时被旧 PLANT 和新 COW 选中；或购买第二只动物时第一只仍在包里。 | 保留 R9 的 reserved/plant_permits/used_structures 和有在途时不新增动物的过滤；选择前、完整验证前、提交时都以同一最新基线识别目标。 |
| 土地与新许可额度脱节 | 原 BUY_LAND 在农业项目循环后独立执行；一个作物 q 加 BUY_LAND 仍是两项新增投资。 | 若约束仅是“一个农业项目 q”，须如此命名。若约束所有新增投资，土地必须另定归属；不能默默保留并声称所有新增只有一项。 |

执行影响的精确来源：make_tasks 的旧植物/动物照护直接用 forecasts；plant 任务在 R9:1178 读取 crop_scores，最低权重虽有 floor，仍会改变匹配排序。expert 字段主要用于选择与记录，并非所有旧资产照护的统一开关，不能夸大为“换专家就必停养旧资产”。[R9 make_tasks:1063–1179](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r9_cash_prefix/main.py)

旧承诺与启动范围也需如实说明：当前 R9:649–676 保留活动 PLANT/BUILD 合同；678–692 汇总已购在途动物。但空结构本身并不是持久的“原动物采购承诺”，先前未实际启动的 PLANT 许可也不自动等同活动合同。若下一机制还要保证 BUILD→BUY→PICKUP→PLACE 或 BUY_SEED→PLANT 的跨帧目标不变，需要另外明确这种持久承诺；它超出“只限一次新增验证”的自然等价范围，不能假定现有状态已经全部表达。[R9:647–692](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r9_cash_prefix/main.py)

P2 组合路线的覆盖防线应完整保留：未能表征的旧合同硬拒、在田集合与模型集合核同、在途实物数量与已分配日历核同、所有 q 旧 goods/work/feed 等值、startup 与已知不可能历史拒绝。单项目不能通过漏掉基线来降低工作量。[P2 integration_helpers.py:34–134](/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_02/integration_helpers.py)

“完整 route”沿用现有准入含义：对触发原未来劳动失败的日，使用完整组合义务做条件证书；原当前日失败仍拒绝。若改成所有未来日都强制 12 工证书，是另一种劳动/费用机制，不应混入本设计。

## 一个最小防反复机制：一轮内失败候选排除表

只增加一个不携带成功证明的排除集合。每个座位的新状态中记录当前轮号与该轮已被完整门拒绝的候选 key；可同时保存失败理由和 step 供诊断，但不保存可复用的 PASS、现金许可或路线证书。

1. 先按真实观测重建全部既有/合同/在途基线和候选池。候选 key 为 `(item, position, target_identity)`；target_identity 取目标的 kind 与已有资产出生身份。空地用固定 EMPTY，WEED/空结构用其稳定身份。**key 不包含 step、hour、报价、净值、工人位置或 q.start_step_model**，否则每帧都是新 key，排除表失效。
2. 在当前有效、便宜评分为正、未被本轮排除的池中，按 `(-临时净值, 距仓口, position, item)` 确定唯一项目。每帧至多一次完整项目验证；原一次扫描及许可提交两处重调 budget_quote 不能原封保留，否则仍会验证两次。
3. 使用本帧真实观测，对该 q 加全部基线义务完整检查。通过才原子提交到共享资金/物料/workload/sources 与许可；失败仅把 key 加入本轮集合，当帧不再验证第二项，也不新增该项目。既有经营继续。
4. 普通时钟推进、day 切换、报价变化、工人移动或其它资产收到 WATER，都**不清空**排除表。当前有效池仍有未试项时，不能重试旧失败 key。只有当前有效池全部已经失败时，结束本轮，从下一帧开始新轮；空池不做昂贵验证。座位重置/新对局时清零。

在上述 A/B 反例中，第一帧 A 失败，第二帧会尝试未排除的 B；如果 B 通过，使用的是第二帧重新验证的结果。对一个保持有效的有限候选池，这避免同一失败最高项阻挡所有未试项目；不保证任意动态候选池都能在截止日前逐一试完，也不保证多个高分坏位置不会消耗剩余窗口。

安全性来自排除表只影响“暂不考虑”，不会授予许可。现金、价格、服务或仓容变化以后，任何重新尝试仍从当前观测完整检查，绝不跨帧复用旧 PASS。代价是 A 可能下一帧已变得可行，却要等这一轮其它候选处理完才重试；最高净值即时性与吞吐下降，截止窗口也可能错失。不能把这种有意的机会损失称为错误已消除或必然增益。

排除表不应用于旧合同/真实在途/必要经营，避免把维持已有资产当成可跳过的新候选。它也不单独解决采购尚未成交、启动链丢失或返回阈值问题；这些必须按上文准确限定本轮目标，不能借防饥饿机制夹带改变。

## 决策与证据边界

若进一步授权，应把该方案作为新机制单独冻结：临时评分定义、一项目额度含义、拒绝原因与轮切换规则、无新增时的完整基线返回、专家及crop_scores写入时点都需先写清。最少保存“本轮排除key、唯一尝试key、门拒绝原因、既有义务数、最终实际订单/确认”的可核对记录。不能继续要求它与 P2 所有 plan/st 相同，也不能只据规划耗时宣布经营质量不变。

本文件不改 P2，也不构成新策略或场景执行授权。
