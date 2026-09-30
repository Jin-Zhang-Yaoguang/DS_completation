# 后续备选机制：每帧只给一个新增项目做最终服务准入

仅静态研究，不实现，不运行候选、报价函数、solver或引擎。依据是已存P1完整经济输出、P0一次profile和冻结源码；不读取或预判正在验证的P2结果。只有P2仍失败且根另行批准，才可进入新机制实验。

## 证据与复杂度

已打开人工day8/seat0、48草莓、现金100000的P1完整结果：342次route尝试、1038次scheduler、926次checker、4次证书缓存hit；312个不同报价服务日历、862次报价日历缓存hit。最终许可26个MELON，选择horticulture，原拒绝计数labor217，内部经济耗时18.025442334秒。**许可不是播种或成交**。来源：`../optimization_01/validation/compact_summary.json`的P1完整字段。

所以每个最终许可平均对应13.15次route与39.92次scheduler；请求日总数为1038+4=1042，证书缓存命中率仅0.384%。这些比值描述这一个人工状态，不外推自然状态。P0 profile中copy自身48.27%、scheduler自身16.25%；即便P2减少日志复制，也不会自行消除这1038/926次完整调用。

源码先对每个候选位置跑所有专家品种，每个budget_quote可能调用route；选专家后又按更新过的组合重算报价。即使只最终买一种作物，其他路线也先付出求解费用。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_01/integration_prototype.py:2256] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_01/integration_prototype.py:2284]

设F为未预留空地/杂草格数，S为可用空建筑格数，D=max(0,29−today)。四专家共5作物、2动物，初报价不超过7F+2S；选中专家复查不超过max(3F,F+S)。所以budget_quote上界为max(10F+2S,8F+3S)，合法10×10棋盘上不超过1000。每次最多一个route、每route最多D个未来失败日，因此旧宽上界为1000D次scheduler和不多于该数的checker。实际会因日期、现金、在途或早失败大幅减少，不能把这个宽上界说成每帧实际耗时。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_01/integration_prototype.py:2213] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_01/integration_prototype.py:2235]

## 主提案

**把“所有报价先获证，再批量许可”改成“估值选出一个待验证新增项目，再对它与全部存量义务整体获证”。每帧最多新增一个q项目；NO_CERT时本帧不新增，下一帧依据新观测重评。** 这是投资节奏与可行性查询顺序变化，不是P1/P2等价优化。

1. 原样建立全部在田、在途、已发合同与既有build-first承诺；这些不受“新增一个”限制。未表征义务、重复/缺失来源、已知不可能历史仍fail closed，不能为了少调用只送新项目或忽略待投放动物。
2. 用原净现金、净值/劳动、逐日现金前缀、当前日劳动和订单槽模型生成**估值报价**，但此阶段不调用未来路线证明。保留原四专家品种集合和排序公式；adaptive仍按各专家最高估值选专家，固定专家开关仍保留。报价明确标 `UNCERTIFIED_FUTURE_LABOR`，不能写为“可行报价”。
3. 在所选专家中，按原selection_score及原位置tie-break选一个通过非路线门的最高估值q。原未来labor可行时可沿旧准入；原未来labor失败时仅调用一次完整route，输入是全部baseline+该q，费用、资料、源覆盖与独立checker要求不降。
4. 只有完整未来证明及原现金前缀通过，才提交新增permit/seed/animal/build-first订单与资金、劳动状态；不能先把影子报价写入真实许可再撤销。失败仍照顾存量、执行已存在合同，新增q为0。本帧不尝试第二个q，不加失败跨帧memo；因此不存在隐藏的重试搜索。

这里的一个项目指投资报价q（作物、动物或其build-first项目）。雇工和原基础设施扩地启发式继续各走同一共享现金与市场槽门；若也要把BUY_LAND算进“一项”，必须另明确规则，不能用含糊的总投资上限偷偷取消原扩地能力。

该机制最多1次route、D次scheduler及D次checker。day8的D=21，与该人工结果的1038次scheduler相比，上界减少97.98%；route上界从实际342降到1。**这是源码可证明的调用上限，不是运行时间预测。** 原逐报价价值/现金计算仍可能遍历O(F+S)个候选，完整服务编译只需baseline与最多一个新q。若预算本身就慢，1秒门仍可能失败。

## 为什么选这一项，而不是先做四组合或严格等价lazy

| 方案 | 每帧route上界 | 原行为等价 | 主要风险 |
|---|---:|---|---|
| P2小证据/保留全字段lazy与精确缓存 | 原Q | 可要求逐字段相同 | 完整报价分类、rejected_types、route计数仍要取得；不同完整问题不能靠弱键合并 |
| 每专家构造一个组合，各做整体证明 | ≤4 | 否 | 批次一项不合格可使全组拒绝；专家比较容易从最高单项净值变成组合净值，扩大机制范围 |
| 先选一个多项目组合，再整体证明 | ≤1 | 否 | 保留批量扩张，但整个影子批次失败时必须全部回滚；部分删减重试会重新引入搜索调用 |
| **每帧一个最高估值q再证明** | **≤1** | **否** | 最小、调用上限清楚；可能新增节奏过慢或最高估值候选反复失败 |

全字段等价lazy尤其受既有诊断约束：专家分数与crop_scores只来自原已通过报价，rejected_types统计全体失败，随后复查的组合又不断变化。若不查询其余候选就返回这些字段，可能改变值或只能标PENDING；若为补齐字段仍在后台完成全部查询，无法从算法上保证更少调用。P1完整状态只有4次证书hit，也不支持先验假定精确memo就能省掉绝大多数求解。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_01/integration_prototype.py:2266]

## 不能忽略的结构性缺点

**最高估值候选的连续阻塞。** 若A估值高但完整路线失败，B估值较低却可行，单候选策略本帧仍不选B；下一帧若排序和相关条件未变，可能再次失败。P1已有同位置WHEAT/CARROT通过而COW/SHEEP因ENDING_WHEAT_RESERVED_SOURCE_SHORTFALL失败的记录，但记录没有同时保存这些失败报价的净值，**不能据此假称这个自然排序反例已成立**。后续应构造可核查A>B且A失败/B成功的控制，连续两帧观察无新增是否发生；不事后加第二候选或负缓存来掩盖反例。

**许可节奏可能压低增长。** 原26项许可并非26个即时动作。官方最多12雇工加农夫共13个单位；这个人工h0状态只有农夫已到场，当帧HIRE次帧才能动。数量差值得研究，但本身不证明批量许可无效。许可可以支持后续并行启动、批量买种或仓内资源准备；每帧只增一个可能错过h<8雇工窗口、首水窗口、成熟日期或早期回款。

**估值与任务价值耦合。** 原st.crop_scores从已通过报价取最高net/labor，并在make_tasks生成已许可种植任务时影响value。跳过其他候选路线会改变其来源。建议继续明确区分“估值”与permit，保留ratio公式，允许预筛估值用于任务价值但绝不据此授予permit；这会改变既有PLANT合同的相对优先级，必须在设计与评价中承认，不能声称只改诊断计数。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_01/integration_prototype.py:2274] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/optimization_01/integration_prototype.py:2614]

**证明仍是条件存在性。** 原executor不消费certificate；少做证明不等于实际执行更好。存量无法获证也不能删除资产或不照护。该设计的“安全准入”只指不把未经完整门控的新增q标可行，实际首水、喂养、交付与现金兑现仍要官方动作验证。

## 会变化的字段与重新检验门

预期变化：expert_quote_scores及selected expert、st.crop_scores/crop_choice、admitted_investments数量和位置、plant/build permits、种子/动物订单、planned_work、labor_plan与hire_target、现金前缀/余粮预约、扩地触发、全部拒绝与route计数、后续合同竞争与实际动作。这些是新机制结果，不再要求P1/P2完整plan/st等价。原单q净值/ratio定义、日历物量、共享账和完整checker本身则继续保持可核对。

实施前应先锁：

- **工程与真实安全：** 每帧最多1次route/≤D次solver和checker；所有新许可均有原门证据，未表征义务/NO_CERT/现金拒绝不产生新订单；保存官方无profile完整入口时间及资源限制，不能把内部函数时间当完整入口G0。
- **机制代价：** 新许可数、实际启动率、许可到真实PLANT/PLACE时间、最高估值连续失败帧、替代可行候选被挡数量、工人时槽空闲、当日首水和喂养遗漏。没有真实启动的许可不得记产出。
- **经济与强度：** 全新冻结块重新比较R0及新机制父版本；现金/胜率、early days0..9自产非麦成交、动物真实采购到投放等待、首产、旱死/逃逸、溢出及终局余值均保留。原R10“解除未来劳动拒绝”的主机制可能因许可节流而失效，必须在看新结果前重新明确主指标及其护栏，不能只用调用量下降宣布成功。

主提案值得进入反例设计，因为它把证明次数与本帧一个不可逆新增决定对齐，拥有明确源码上界。它尚不能保证投资质量、1秒性能或金牌；若连续阻塞或早期现金部署显著退化，应据失败证据改下一机制，而不是临时增加搜索次数。
