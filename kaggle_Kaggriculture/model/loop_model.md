> 2026-09-09：本文件保留历史研究协议与机制证据，不是当前金牌候选名单。当前名单仅以 [golden_model.md](golden_model.md) 和 [registry.json](gold_candidates/registry.json) 为准；V120、V123 活动目录已淘汰删除。

# Kaggriculture 金牌模型 Goal-Loop 指挥手册

更新时间：2026-08-29

当前官方 Replay data cutoff：`2026-08-27`；新增日期只能用于后续版本，既有确认结果不回看重算。

## 1. 目标与完成定义

本手册用于执行一个组合式长期 Goal：以第一性原理探索至少 **5 个原创、彼此不同架构谱系的 Hierarchical MoE 金牌模型**。每个候选都必须完整经历“思考 → 构造 → 测评 → 汇报”四阶段，并形成可证伪、可提交、可复算的独立证据链。

本轮默认研究对象仍围绕：商店需求路由、多生产专家、状态安全执行器、商品级出售控制器和对方路径预测。但五个候选不能只是同一 Router 的阈值、窗口、特征、专家数量或父代动作后处理变化；它们必须改变不同的主要因果杠杆，并拥有自己的 Router、专家集合和状态契约。

**V76 只是一条强度比较基线和可复用安全执行器来源，不是候选默认策略主体。** 任何“先完整调用 V76/其他金牌 agent，再对少量动作追加、删除、重排或门控”的 wrapper/overlay，无论离线增益多高，都标记为 `SAME_LINEAGE_PATCH_NOT_COUNTED`，不能占用五个原创配额。V85 已以此口径归档：Confirmation 很强，但本质是 V76 后置肥料收集补丁，金牌计数仍为 `0/5`。

本 Goal 只有一个完成口径：`PORTFOLIO_GOLD_COMPLETE`。必须至少有 **5 个主要因果杠杆不同** 的 Hierarchical MoE 候选分别通过 Development、一次性 Confirmation、原创性消融、工程与延迟全部硬门，并以 `PROMOTE_LOCAL_GOLD` 登记到 `golden_model.md`。

失败、惰性、无效评测、只通过 Development、代码可运行、打包成功、局部金币增加、单一对手胜率高或线上偶然高 Rating，均只增加尝试记录，**不增加金牌产出计数**。V77–V84 均未通过，V85 虽通过策略强度门但属于完整父代后置补丁，因此当前计数仍为 `0/5`，不能以“研究完成”结束 Goal。

失败尝试数量不设上限。每次失败后必须递增版本、提出新的原创主假设并使用新的未暴露 source；只有累计 5 个不同原创谱系的本地金牌后，才能标记整个 Goal 完成。

本地晋级不自动授权 Kaggle 提交。任何远程提交都需要用户单独明确授权。

## 2. 核心原则

1. **一个候选只检验一个主假设。** 每个谱系分别构造和决策；每次只允许一个冻结候选进入自己的确认集，避免从多个参数版本中挑最高分。
2. **先解释机制，再写代码。** 新机制必须说明利用了什么环境规则、使用了哪些合法信息、为何会改变终局胜负，以及什么结果会证伪它。
3. **比较基线固定，但策略主体独立。** Goal 启动时冻结 V76 作为共同强度基线；候选只能复用明确拆出的无策略安全执行器、动作 schema 校验、价格公式和评测工具，不得调用 V76 `agent()` 获取默认动作。即使中途出现新金牌，也不能把它当作后续候选的完整策略父代，否则会把串行补丁伪装成不同模型。
4. **只对原创代表门控。** 不再让候选对战全部金牌版本。Goal 启动时按行为和主要因果机制冻结“小型原创性对照池”，同一谱系只保留一个代表；整个批次不得因中途结果增删对手。
5. **Replay 只提供官方 source。** 使用官方 Replay 的 episode、seed、日期、状态和环境分布；不把历史 Agent 动作固定成 `TraceAgent`，候选、强度比较器和对手必须在本地重新闭环运行。
6. **严格配对。** 候选和冻结强度比较器使用完全相同的 source、对手版本和候选座位。增益不能由两个不配对总体胜率相减得到。
7. **确认集一次性消费。** 任何已查看结果的 source 都写入 exposure ledger，后续版本不得再次充当未见确认数据。
8. **版本不可变。** 一旦开始 Development，任何影响动作、依赖、打包或加载路径的修改都必须递增为新版本。
9. **工程 QA 与策略强度分离。** raw-loader、`DONE/DONE`、动作安全和包等价只证明可运行，不能替代胜率晋级门。
10. **失败证据永久保留。** 失败版本只登记到 `experiments.md`，不得因编号更高、重新打包或线上偶然高分而改写为金牌。
11. **原创性与强度分开判定。** 新颖但不增胜的候选仍淘汰；增胜但只是已有谱系的小参数补丁，只能登记为同谱系优化，不能计入“五个原创谱系”。
12. **共享组件不冒充原创。** 五个候选可以复用从 V76 抽离的无策略安全执行器、打包链和评测器；不得复用 V76 的完整 `agent()`、静态动作表、Router 决策或完整市场动作作为默认专家。这些公共底座不计作任何候选的原创机制。
13. **原创是模型架构，不是增益标签。** 即使候选通过全部胜率门，只要其主体仍是父代加补丁，就只能保留为强补丁证据，不能登记为本 Goal 的原创 Hierarchical MoE 金牌。

## 3. 每轮状态与目录

每轮开始时扫描 `model/` 中全部 `v<number>_*`，分配当前最大整数加一；不得硬编码版本号。当前状态文件已经预约 V86，但实际构造前仍须重新扫描并确认没有编号冲突。

模型目录至少包含：

```text
model/vNN_<short_name>/
├── hypothesis.md
├── main.py
├── submission.tar.gz
├── submission_manifest.json
├── package_qa_results.json
├── action_safety_audit_results.json
├── evaluation_manifest.json
├── development_summary.json
├── confirmation_summary.json
├── decision.json
└── README.md
```

逐局数据、source manifest 和运行日志保存在与 `model/` 同级的 `model_data/`：

```text
model_data/loop_evaluations/vNN_<short_name>/
├── source_manifest.jsonl
├── development_games.jsonl
├── confirmation_games.jsonl
├── official_parity_games.jsonl
└── run_manifest.json
```

全局状态建议固定为：

```text
model/loop_state.json
model/portfolio_state.json
model/originality_registry.md
model/originality_panel.json
model_data/loop_evaluations/exposure_ledger.jsonl
```

`portfolio_state.json` 记录批次 ID、Goal 完成口径、冻结强度比较器、预注册谱系、各谱系候选、当前阶段、有效决策数和晋级数。`originality_registry.md` 记录每个历史原创机制的因果身份、代表版本和证据强度；`originality_panel.json` 冻结本批对照池及 SHA。`loop_state.json` 记录当前 iteration、活动候选、阶段、候选 SHA、数据 cutoff 和最后决策。`exposure_ledger.jsonl` 至少记录 episode ID、seed、source date、用途、版本、attempt、首次暴露时间和 panel SHA。

## 4. 阶段一：思考

### 4.1 必读上下文

每轮必须先读取：

- `golden_model.md`：冻结强度比较器、独立金牌策略及已证伪假设；
- `experiments.md`：历史版本、失败原因和未完成证据；
- 冻结强度比较器的 `main.py`、README、decision 和评测结果，只用于理解比赛强度与安全边界，不得作为候选动作源；
- 最近失败的至少 3 个相邻版本；
- 当前引擎规则、信息边界和 Replay 数据 cutoff。

### 4.2 第一性原理问题

思考必须依次回答：

1. Kaggle 最终优化的是胜/平/负与 Elo 路径，而不是平均金币本身；冻结强度比较器在哪些真实环境状态下会把经济优势浪费为平局或失败？
2. 机制是否来自真实引擎顺序、共享市场、商店需求、生产周期、土地/劳动力约束或部分可观测对手行为？
3. 候选在决策时能够合法看到什么？不得读取对手私有 shed、seed、携带库存、当前未公开动作或环境 seed。
4. 修改如何沿“状态识别 → 动作变化 → 经济变化 → 胜负翻转”传导？
5. 为什么历史 V18、V22–V28 的失败原因不会再次出现？
6. 最小改动是什么？如果复杂 Router 与简单控制器统计同档，优先简单版本。

### 4.3 原创性与谱系预注册

Goal 启动时先冻结不少于 5 个谱系槽位。每个槽位至少写清：主要因果杠杆、Router 输入、专家动作域、状态兼容契约、与既有金牌机制的最近邻、反事实消融和证伪条件。

初始研究组合建议如下；启动前可以替换，但替换后的主要因果杠杆仍必须互不相同：

| 谱系 | 主要因果杠杆 | Hierarchical MoE 形态 | 必须证明的新东西 |
|---|---|---|---|
| A 商店需求—生产契约 | 当前与未来城镇需求、生产依赖和库存缺口 | 需求向量 Router → 多个完整生产专家 → 状态契约切换 | Router 能选择不同完整生产路径，而不是只改出售时点 |
| B 对手信念—最佳响应 | 对手公开路径、土地/动物结构和市场动作的不确定预测 | belief Router → 防守/抢跑/错峰专家 → 低置信回退 | 对手预测在 OOF Replay 上有效，且移除预测后胜率下降 |
| C 现金流—尾部风险 | 破产风险、锁仓周期、未来固定支出和终局兑现概率 | 风险状态 Router → 增长/保本/清算专家 → 安全执行器 | 改善真实胜负而非只抬高均值，并压住 CVaR 与灾难失败 |
| D 空间物流—产能瓶颈 | 单位位置、土地邻接、仓储、运输和劳动力占用 | 拓扑 Router → 扩张/运输/生产调度专家 → checkpoint 切换 | 解决完整状态下的物流瓶颈，不是终局 step 阈值补丁 |
| E 共享市场—商品级 MPC | 商品需求、订单槽位、价格/利润和对手可见队列 | 市场状态 Router → 商品级买卖专家 → 短视界 MPC → 安全下单 | 通过商品级反事实重排改变胜负，不是固定槽位交换 |

判定“不同谱系”必须同时满足：

1. 主要因果杠杆与已登记谱系不同；
2. 至少在 Router 状态表示、专家动作域、状态契约三项中的两项不同；
3. 能设计只移除该原创机制、其余代码保持不变的消融；
4. 不是阈值、比例、seed、窗口长度、产品白名单、执行 step 或专家数量的单独变化；
5. 不是把已有完整专家换名、重新打包或改变版本字符串。

原创性先由文档审查判定为 `NEW_LINEAGE` 或 `SAME_LINEAGE_PATCH`。后者仍可做性能实验，但不占用五个谱系配额。若某槽位在构造后被证明与旧机制同源，必须另开一个真正不同的谱系补足配额。

### 4.4 候选假设预注册

在 `hypothesis.md` 中冻结以下内容后才能进入构造：

- 冻结强度比较器版本及 serving SHA，并明确候选无策略父代；
- 一句话机制假设；
- 预计改变的 step、动作类型和 Replay regime；
- 使用的公开观测字段；
- 预期正向传导链；
- 主要失败模式和安全回退；
- Development 与 Confirmation 的样本量、source cutoff、随机盐和全部门槛；
- 明确证伪条件；
- 与过去失败方案的区别；
- 所属谱系槽位、原创性判定和最近的历史原创代表；
- 主机制消融版的定义，不允许确认后临时设计消融。

不允许先看新 panel 的逐局结果再补写假设或调整门槛。

## 5. 阶段二：构造

### 5.1 版本登记

创建目录后立即在 `experiments.md` 登记：版本、冻结强度比较器、`strategy_parent=null`、谱系槽位、原创性判定、假设、改动范围、当前状态 `BUILDING`、预计评测协议。并行进程必须先完成版本预约，避免两个候选占用同一版本号。

五个谱系候选默认均从独立策略架构开始。允许复制公共安全执行器和工具链，但不得调用冻结基线或同批次另一候选的完整策略层；若确有必要融合，必须作为额外“融合谱系”另行预注册，且不替代五个独立模型。

进入 Development 前必须通过架构原创审计：

1. `main.py` 不得 import/load/call V76 或其他完整 agent 取得默认动作，`strategy_parent` 必须为 `null`；
2. 至少有 3 个语义不同的生产/市场专家，并由候选自己的规则或浅树 Router 选择；
3. 候选自己维护生产状态、切换状态和失败回退，回退只能进入候选自有的保守专家；
4. 主动作域不能只覆盖父代 PASS 或少量市场槽，必须能自主生成生产、劳动力和市场中的至少两个动作域；
5. 架构消融应移除 Router 或某类专家，而不是简单恢复成 V76；
6. **Router 必须优于最佳单专家。** 对候选中每个可独立运行的完整专家做同源闭环评估；组合 Router 的配对得分必须严格高于最佳单专家，或在得分完全相同时严格降低预注册尾部风险。只优于弱消融、却弱于最强专家的方案记为 `EXPERT_DOMINANCE_FAKE_MOE`，不得进入构造或 Development。
6. 源码静态审计与运行时调用图都证明完整父代策略未被调用。

### 5.2 可提交包硬要求

候选在进入正式评测前必须已经是可提交产物，而不是研究函数替身：

- `submission.tar.gz` 根目录包含可被 Kaggle raw-loader 发现的 `main.py`；
- 禁止依赖提交包之外的本地文件、绝对路径、网络或未打包模块；
- manifest 记录版本、`strategy_parent=null`、强度比较器、策略摘要、main SHA、archive SHA、引擎版本、构建时间和远程提交状态；
- 研究入口与打包入口在固定 QA seeds 上动作及奖励完全一致；
- 720-step `DONE/DONE`，无 stdout/stderr 污染；
- market orders 每回合不超过 10，hands 数量对齐，单位动作前置条件 fail-closed；
- 重复运行同一 seed、座位和对手必须得到相同动作与奖励；
- P99 单步 Agent 延迟不超过 250ms，且不超过冻结强度比较器的 1.25 倍；任何单步不得触及官方 1 秒超时。

### 5.3 最小 Smoke

Smoke 只用于发现加载、路径、动作 schema 和引擎错误，不作为效果证据：

- 至少 4 个非正式 QA seed；
- 候选双座位；
- 覆盖冻结强度比较器和至少一个异构金牌对手；
- 全部完成后才允许冻结 Development archive SHA。

## 6. 阶段三：测评

### 6.1 官方 Replay source 池

数据来源固定为 Kaggle `Kaggriculture Episodes Index` 已下载到 `model_data/kaggriculture_episodes_index/` 的官方 Replay。合格 source 必须：

- 双方最终状态均为 `DONE`；
- episode、seed 和 source 文件完整；
- 按 episode/seed identity 去重，同一 identity 不跨 panel；
- 不在 exposure ledger 中；
- 不属于永久保留的 test 数据；
- source date 不晚于预注册 data cutoff。

抽样使用预注册固定盐对 `(episode_id, seed)` 做 SHA256 排序，不接受人工挑 seed。按 source date 和首个解锁商店 regime 分层；双座位始终绑定为同一 source cluster。抽样 manifest 在运行前落盘并计算 SHA256。

严格说明：Replay 提供的是官方 seed 和环境分布。比赛结果来自候选、冻结强度比较器和冻结金牌对手在同一 source 上重新闭环模拟，不是把历史 Replay 的原对局胜负复制为候选成绩。

### 6.2 固定原创性对照池

不再读取 `golden_model.md` 中全部活动金牌作为每轮对手。Goal 启动前，按主要因果机制和 canonical serving fingerprint 去重，冻结以下历史原创性代表：

| 对照身份 | 冻结代表 | 代表机制 |
|---|---|---|
| `OG_DEMAND_TIMING` | V20 | 商店需求驱动的出售时机控制 |
| `OG_PRODUCTION_ROUTER` | V21/V29 | 完整生产专家切换与状态安全执行 |
| `OG_OPPONENT_PREEMPT` | V32 | 基于公开对手距离的多步 premium 前置 |
| `OG_TERMINAL_LOGISTICS` | V54 | 终局物流、回收与无效动作旁路 |
| `OG_MARKET_MICROSTRUCTURE` | V66 | 商品净 margin 门控的市场队列重排 |

另设 `INCUMBENT_GUARD=V76`，用于约束候选不能明显弱于当前最强完整栈。V76 是只读强度比较器，不是策略父代，也不占原创代表名额。若下一批启动时已有更新、更强且证据完整的比较器，必须在打开任何新结果前更新本表并冻结新 `originality_panel.json`；本批不得中途滚动。

每个冻结代表记录：

- submission archive SHA；
- canonical serving fingerprint；
- 原创机制身份；
- 实际加载入口；
- active/retired 状态。

完全相同的行为指纹只保留一个代表，例如 V21/V29 只计一次。本批对照池固定为 5 个原创代表加 1 个强度基线，记去重后数量为 `K`，当前 `K=6`。中途晋级的新模型只登记到批次结果，不能加入本批固定池；下一批再按“一类原创机制一个代表”规则重选，避免候选顺序改变评测难度。

### 6.3 Development 筛选

- 随机分层抽取 64 个未暴露官方 source；
- 候选和冻结强度比较器分别对全部 `K` 个冻结对照运行；
- 每个 source 交换候选座位；
- 总局数为 `64 × K × 2 seats × 2 policies`，当前为 1,536 局；
- 同时运行预注册主机制消融版；消融只需对该候选最近的原创代表和 V76 运行；
- C++ `kagsim` 可用于完整矩阵，但必须固定为与官方环境一致的引擎版本；
- 可以输出聚合到对手谱系、shop regime 和日期的诊断，但不能依据单个 seed 手工打补丁。

Development 同时满足以下条件才冻结候选并进入 Confirmation：

1. 配对原创性增益 `POU > 0`；
2. 候选原创池得分率 `PanelScore >= 50%`；
3. 任一原创代表的配对退化不低于 `-3pp`；
4. 灾难性失败率没有比冻结强度比较器增加超过 `1pp`；
5. 零运行、安全和完整性错误；
6. 相对冻结强度比较器确实产生有效动作变化，且变化来自候选自有 Router/专家而非比较器动作后处理。

Development 未通过即登记 `REJECT_DEVELOPMENT`，不读取 Confirmation，不允许用同一版本改代码后重跑。该候选仍必须进入阶段四并出具失败报告；随后转向下一个尚未探索的谱系，而不是在同一谱系连续搜索参数直到过门。

### 6.4 Confirmation 盲确认

- 至少随机分层抽取 **256 个**从未暴露且与 Development 不重叠的官方 source；
- 候选 archive、serving SHA、`strategy_parent=null`、强度比较器、原创性对照池、引擎、随机盐、指标和门槛必须在抽样前冻结；
- 候选和冻结强度比较器分别对全部 `K` 个冻结对照、双座位运行；
- 总局数为 `256 × K × 2 seats × 2 policies`，当前为 6,144 局；
- 消融版在相同 256 个 source 上仅对“最近原创代表 + V76”运行，行为指纹重复时去重；
- 逐局结果只写 evaluator 数据目录，最终只向下一轮暴露固定聚合报告；
- 按 source cluster、日期和 shop regime 做 20,000 次确定性分层 bootstrap；不得把单场当独立样本。

同一个候选只能消费一次 Confirmation。结果不确定也视为未晋级，不得追加 seed 直到显著；若希望扩大样本，必须在打开结果前预注册更大的固定样本量。

### 6.5 批次内跨谱系复赛

至少 5 个不同原创谱系取得 `PROMOTE_LOCAL_GOLD` 后，再做一次组合级比较：

- 只纳入已经通过全部金牌硬门并登记的 5 个原创本地金牌；失败者保留失败证据，不进入最终复赛；
- 使用至少 128 个与各候选 Development/Confirmation 都不重叠的全新官方 source；
- 任意两个候选双座位对战，形成完整 round-robin；
- 报告逐对 W/T/L、得分率、平均金币差、座位差和谱系间循环克制；
- 复赛不能把已失败候选“捞回”金牌，也不能覆盖各自的盲确认结论；它只用于比较五条原创路线和判断是否值得融合。后续批次可以从 `PROMOTE_LOCAL_GOLD` 中选择更强比较器，但任何新候选仍须 `strategy_parent=null`，不能把比较器改造成完整策略父代。

未累计到 5 个原创本地金牌时，不执行最终组合复赛，也不得借“无足够幸存谱系”提前结束 Goal。

### 6.6 官方引擎一致性

完整矩阵可以使用已经通过版本一致性测试的 `kagsim` 加速，但晋级前还必须从 Confirmation manifest 预先固定至少 16 个 source，在 Kaggle 官方 Python 环境中复算候选和冻结强度比较器的双座位结果：

- raw-loader 选择同一 serving 入口；
- 状态、动作 schema 和终局奖励可重算；
- `DONE/DONE`、零异常；
- C++ 与官方环境不得出现胜负方向不一致；若奖励不能逐局完全一致，必须阻断晋级并先修复模拟器 fidelity。

## 7. 阶段四：指标、原创性与晋级

### 7.1 主指标：Paired Originality Uplift（POU）

单局得分定义为胜 `1`、平 `0.5`、负 `0`。设：

- `s`：官方 source cluster；
- `o`：冻结原创性代表或强度基线；
- `a∈{0,1}`：候选座位；
- `C(s,o,a)`：候选对对照 `o` 的单局得分；
- `B(s,o,a)`：冻结强度比较器 V76 在相同 source、对手和座位的单局得分。

先合并双座位，再对冻结的 `K` 个对照等权；如果两项的 canonical serving fingerprint 相同，运行前去重并重算 `K`：

```text
C_so = mean_a C(s,o,a)
B_so = mean_a B(s,o,a)
C_s  = mean_o C_so
B_s  = mean_o B_so

PanelScore = mean_s C_s
POU        = 100 × mean_s (C_s - B_s)  # 单位 pp
```

POU 是唯一主晋级 KPI。旧报告中的 PGU 只作为历史字段保留，不能与不同对手池下的 POU 直接横比。平均金币差只用于解释和尾部保护，不能替代胜负得分。

主机制消融使用独立指标 `Mechanism Contribution Uplift（MCU）`。在预注册消融对照子集上，对同一 source、对手和座位比较完整候选 `F` 与消融版 `A`：

```text
MCU = 100 × mean_(s,o,a) (F(s,o,a) - A(s,o,a))  # 单位 pp
```

MCU 只回答“新增机制是否有独立贡献”，不替代 POU 的整体强度判断。

对于含两个及以上可独立运行完整专家的 Router，另计算 `Best-Expert Uplift（BEU）`：

```text
e* = argmax_e mean_(s,o,a) F_e(s,o,a)
BEU = 100 × mean_(s,o,a) (F_router(s,o,a) - F_e*(s,o,a))
```

预构造要求 `BEU > 0` 且正翻转多于负翻转；若专家无法逐局同时运行，则使用预注册的 OOF 策略价值估计，并在独立 source 上闭环复核。该门防止“多数时候选择最强专家”被误报为 MoE 创新。

### 7.2 本地金牌硬门

候选只有同时满足以下全部条件，才能判定为 `PROMOTE_LOCAL_GOLD`：

#### 强度门

1. Confirmation `POU >= +1.0pp`；
2. POU 的 source-cluster bootstrap 95% CI 下界严格 `> 0pp`；
3. `PanelScore >= 52%`，且 95% CI 下界严格 `> 50%`；
4. 对冻结强度比较器 V76 的双座位 head-to-head 得分率 `>= 50%`，95% CI 下界 `>= 48%`；
5. 对每个冻结原创代表的候选得分率 `>= 48%`；
6. 对每个冻结原创代表相对冻结强度比较器的点估计退化不低于 `-2pp`；
7. 正向胜负翻转数必须大于负向翻转数。

#### 原创性门

1. 预注册原创性审查结果为 `NEW_LINEAGE`，且不属于阈值/窗口/比例/白名单/step 的单参数补丁；
2. 主机制相对预注册架构消融版确实触发，至少覆盖 8 个 Confirmation source cluster 和 2 个 shop regime；
3. Confirmation `MCU >= +0.5pp`，且 source-cluster bootstrap 95% CI 下界严格 `> 0pp`；否则只可记为 `SAME_LINEAGE_PERFORMANCE_PATCH`，不能占原创谱系配额；
4. 若包含学习型 Router 或对手预测器，必须使用 source-cluster 隔离的 OOF 训练/验证，训练 source 不得进入 Development 或 Confirmation；
5. 专家切换必须满足显式状态契约，不能以公共动作前缀相同替代内部状态兼容证明。

#### 尾部风险门

1. 金币差 `< -10,000` 的灾难性失败率不得超过冻结强度比较器 `+0.5pp`；
2. 最差 10% 金币差均值 `CVaR10` 相对冻结强度比较器的恶化不得超过 `5% × max(|比较器 CVaR10|, 1000)`；
3. 不得出现只靠单一原创代表贡献全部增益、其他代表普遍退化的结构。

#### 真实性与工程门

1. canonical serving fingerprint 必须不同于冻结强度比较器，且静态/运行时调用图证明没有完整比较器或其他完整 agent；
2. 至少 8 个 Confirmation source cluster、且至少 2 个 shop regime 出现有效动作变化；该项与原创性门的机制触发审计使用同一份逐局证据；
3. 全部任务键唯一，reward/margin 恒等式、source/seed/seat 覆盖和预注册矩阵行数均通过；
4. 全部对局 `DONE/DONE`，运行错误、安全违规、market overflow、hands mismatch 均为 0；
5. package parity、确定性和官方引擎一致性全部通过；
6. archive SHA 与 Confirmation 预注册 SHA 完全一致。

任何一项失败都不能用其他指标补偿，不计算加权总分。

### 7.3 决策标签

- `PROMOTE_LOCAL_GOLD`：全部硬门通过；登记到 `golden_model.md`。
- `REJECT_DEVELOPMENT`：开发筛选失败；不消费确认集。
- `REJECT_CONFIRMATION`：确认集任一强度或护栏失败。
- `INCONCLUSIVE_REJECT`：点估计为正但置信区间跨 0；本轮仍淘汰，不追加样本。
- `INVALID_EVALUATION`：数据、引擎、任务矩阵或 SHA 完整性失败；不得引用该轮强度结论。
- `ONLINE_PROBE`：用户明确授权后提交的实验包；不改变本地门控结论。

### 7.4 汇报内容

最终报告必须先给判定，再给证据，至少包含：

1. 版本、`strategy_parent=null`、冻结强度比较器、机制和源码/archive SHA；
2. source 日期、Development/Confirmation panel SHA、是否全部未暴露；
3. 候选与冻结强度比较器总局数、逐局完整性和错误数；
4. W/T/L、纯胜率、PanelScore、POU 及 95% CI；
5. 逐原创代表得分率、配对增益和最差对照；
6. 正/零/负翻转；
7. 平均金币差、P05、CVaR10、灾难性失败率；
8. 原创性审查、动作变化覆盖、触发 regime、消融结果和因果传导是否成立；
9. package QA、官方引擎一致性和延迟；
10. 每一道硬门的 PASS/FAIL；
11. 最终标签和下一步。

当第五个原创本地金牌完成后，另附组合报告：五个金牌谱系的一句话机制、谱系独立性审计、各自四阶段证据、复赛矩阵、全部失败尝试及下一批优先级。不得把失败候选计入五个产出。

## 8. 登记与淘汰

### 晋级

通过后：

1. 在 `golden_model.md` 登记版本、`strategy_parent=null`、冻结强度比较器、策略身份、serving fingerprint、行为谱系、Confirmation 指标、panel SHA 和 `LOCAL_GOLD` 状态；
2. 若新版本与已有金牌完全同指纹，只登记为别名/复验，不增加金牌门控权重；
3. 在 `experiments.md` 将状态改为 `PROMOTE_LOCAL_GOLD`；
4. 将本轮模型、数据和决策文件设为冻结，不再原地修改；
5. 更新批次金牌计数；只有 `promoted_gold_count >= 5` 且五个原创性身份互不重复时才能标记整个 Goal 完成；Kaggle 提交等待用户另行授权。

### 淘汰

失败后：

1. 在 `decision.json` 和 `experiments.md` 保留失败门、完整指标和失败原因；
2. 不写入 `golden_model.md`；
3. archive 与结果只读保留，不删除、不覆盖；
4. 下一轮重新从阶段一开始，使用新版本、新假设和新的未暴露 source；
5. Confirmation 的逐 seed 细节不反馈给下一轮，只允许使用预注册聚合指标和机制级结论。

## 9. Loop 控制流程

```text
读取 portfolio_state / loop_state / golden_model / experiments / exposure ledger
                         ↓
冻结强度比较器、五个不同谱系槽位和 originality panel SHA
                         ↓
为一个谱系提出可证伪机制并预注册原创性
                         ↓
分配新版本 → 构造可提交包 → 工程 QA
                         ↓
64-source Development + 预注册消融
        ├── FAIL → 阶段四失败报告 → 转下一个不同谱系
        └── PASS → 冻结候选 SHA
                         ↓
256-source blind Confirmation + 官方引擎一致性
        ├── 任一硬门 FAIL → 登记该谱系淘汰
        └── 全门 PASS → 注册 LOCAL_GOLD
                         ↓
阶段四报告 → 原创本地金牌数是否达到 5？
        ├── 否 → 递增版本，提出下一原创主假设并重复四阶段
        └── 是 → 五金牌 round-robin → 组合报告 → PORTFOLIO_GOLD_COMPLETE
```

允许暂停的原因只有用户要求暂停、未暴露官方 source 不足、官方引擎/依赖不可用或同一基础设施故障连续出现。不能因为候选难以设计、结果不显著或资源消耗较高而擅自把 Goal 当成完成。

## 10. 当前执行基线

- 当前冻结强度比较器：V76；它不是候选的策略父代，本批中途不滚动更新；
- 当前候选统一要求：`strategy_parent=null`，不得完整调用任何历史 agent；
- 当前固定原创性代表建议：V20、V21/V29、V32、V54、V66；强度基线 V76；启动 Goal 时重新校验 archive SHA、serving fingerprint 和 active 状态；
- 当前 18 个独立金牌策略仍保留在 `golden_model.md`，但不再全部进入每个候选的正式门控；
- 当前原创进度：`0/5`；V85 仅作为肥料机制证据，不占名额；活动候选编号已预约为 V86，构造前仍必须重新扫描；
- 官方 Replay 已下载日期：覆盖 `2026-07-30` 至 `2026-08-27`，共 29 个完整日期；可用前需刷新 sync state 并扣除 exposure ledger；
- 本机近期 C++ 闭环实测吞吐约 17–20 场/秒；按当前 `K=6`，单候选 1,536 场 Development 加 6,144 场 Confirmation 的纯模拟时间约 6.4–7.5 分钟，另加消融、跨谱系复赛、官方引擎一致性、bootstrap、打包和 QA 时间；
- 当前引擎版本基线：`1.32.7`，每轮必须重新验证，不得默认为永远不变。

## 11. 禁止事项

- 不使用 Kaggle 网页代替 CLI/API 获取动态比赛状态；
- 不用线上单次 Rating、早期连胜或重复提交结果覆盖本地失败门；
- 不把 Replay 原 Agent 的固定动作当作候选的闭环对手；
- 不读取或推断环境 seed、对手私有库存及同回合未公开动作；
- 不在看过 Confirmation 后修改门槛、追加 seed 或选择另一个候选；
- 不把别名、版本字符串或重新打包登记为新金牌策略；
- 不把同一父子链上的阈值、窗口、step、产品白名单或队列槽位变化拆成五个原创谱系；
- 不因某个候选先晋级而在批次中途更换冻结强度比较器或原创性对照池；
- 不只看平均金币差，不隐藏平局、尾部失败或逐谱系退化；
- 不自动提交 Kaggle。
