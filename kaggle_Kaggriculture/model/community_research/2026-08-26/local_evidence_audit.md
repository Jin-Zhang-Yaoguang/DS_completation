# Kaggriculture 社区建议 × 本地 V12–V15 证据审计

> 审计日期：2026-08-26（Asia/Taipei）  
> 范围：`model/community_research`、V12–V15 历史实验及本轮已下载公开 Notebook/仓库。  
> 动作边界：只读检查；未运行比赛、未修改模型、未提交 Kaggle。  
> Notebook 是单行 JSON，以下按 `cell` 与标题定位；本地 Markdown/Python 按稳定行号定位。

## 结论先行

1. **不应再包装成“新发现”**：按商店布尔节流、全局 no-WOOL、公开银行领先门、step 716 清仓、静态专家混合、exact-A2 队列换序、库存中性 WHEAT squeeze、固定延迟/长期 hold、端到端低层 PPO/BC，以及“把自己下一回合卖单提前一回合”的简单 front-run。
2. **最值得继续研究的策略空白**有四个：
   - 不依赖既有强路线的 **owned base schedule search**，但目标必须是异质对手胜率，而不是只看 idle bank；
   - 面向未知谱系的 **行为指纹 + 对手供给区间解码**，替代 V14 的 exact-A2 身份假设；
   - 具备因果时间约束的 **完整路线第二次决策/动态 replanning**，而不是静态 mixture 或不兼容动作拼接；
   - 在路线现金义务、仓容和供给区间约束下的 **有限动作反事实市场 MPC**，而不是观测式未来价格树。
3. **最值得引入的代码是基础设施，不是现成高分 Agent**：`kaggriculture-island-ga` 可提供搜索骨架，`kaggriculture-cppsim` 可扩大 seed panel；二者都必须适配我们的 V15 clean-room 与异质谱系评测，不能原样把社区自报结果当通过。
4. V15 已经建立正确的防过拟合门，但只验证过一个独立候选；`attempt_001` 对 A2、r002 和模型池均为 0，说明“有独立生成流程”不等于“已经有强独立策略”。权威结果是 `score_only_feedback.json`，不是 `PROTOCOL.md:9` 中已经过时的“尚未运行真实比赛”。

## 证据分级

| 级别 | 含义 | 本报告如何使用 |
|---|---|---|
| A | 本地封存候选、fresh source、双席位、闭环、完整性审计和 source-cluster CI | 可称“在该实验分布有效/无效” |
| B | 已暴露 screen、消融、机制覆盖或线上事后诊断 | 只用于机制判断，不外推成泛化胜率 |
| C | 社区作者自报、公开代码/Notebook、无我方复跑 | 只生成假设或提供代码骨架 |
| D | 由以上证据推出但尚未实现 | 明确标记“未验证” |

状态词含义：

- **已实现—有效**：至少有 A 级本地证据，但结论只覆盖相应对手/面板。
- **已实现—局部**：有代码与 B 级信号，但未过最终门或覆盖不足。
- **已证伪**：同一机制在有效实验中未过预设门、产生明确回撤或零覆盖。
- **未验证**：本地没有等价实现与可信胜率证据，仍可作为新方向。

## 社区建议 → 本地状态映射

| 社区建议/公开代码 | 本地对应实验 | 审计状态 | 证据与边界 |
|---|---|---|---|
| 根据 shop demand hole 调整 WOOL/MILK/STRAWBERRY；公开 `room_for` 计算 town 容量 | V12A shop-product throttle；A2 删除该 gate；V13A/C no-WOOL | **布尔出售节流已证伪；容量式路线选择未验证** | V12A 的 WOOL/MILK 路径产生可复现 W→L，删 gate 后修复（`../../v12a_terminal_branch_guard/MECHANISM_DIAGNOSIS.md:3-31`）。V13 全局 no-WOOL 对 A2 仅 50%，只有 V8 分支 no-WOOL 有效（`../../v13_dual_anchor_search/FINAL_VALIDATION.md:20-27`）。这不否定把完整 shop 组合、需求分布或 worst-case room 用于**生产路线**；busyaprime 的 `room_for` 在 `live_cli/kernels/busyaprime__one-town-in-three-has-no-yarn-store-at-all/one-town-in-three-has-no-yarn-store-at-all.ipynb` cell 30，尚未进入本地 pool 评测。 |
| 通过空地数量改变 weed RNG，进而影响 shop draw | V14 G10 已做机制审计 | **拒绝** | 社区 Notebook 证明 shop draw 与双方空地耦合，但仍均匀且事前不可预测；V14 已据此拒绝主动操纵 RNG（`../../v14_first_principles_search/community_frontier.md:145-156`）。“耦合存在”不等于“可获利控制”。 |
| 价格深度、town demand、未来价格树；当前价达到预测未来最高价就卖 | V12B 市场反馈；V14 G4 robust MPC 设计 | **观测式树未验证；粗反馈局部失败** | MELON 浅树只用 step/current price/stock，标签来自原策略继续行动后的未来，不是动作反事实（`../../v14_first_principles_search/community_frontier.md:76-92`）。V12B-v1 金币增加却得分率下降 1.19pp、4 个 W→L；v2 仅在同一暴露 source 得到 +0.40pp 且 55/57 次为 MILK（`../../v12b_market_feedback_router/README.md:26-43`）。 |
| 从公开市场差分恢复 opponent inventory/sell，并维护不确定性 | V12B lower-bound estimator；V14 exact-A2 shadow | **部分实现；未知对手版本仍空白** | V12B 已扣 own sale 与确定 town demand，并用公开动物产能给供给下界，但没有可靠 upper bound/interval coverage（`../../v12b_market_feedback_router/main.py:184-219,270-354`）。V14 forward/flow shadow 在 13,581 个 exact-A2 机会达到 100% queue/shed exact，但报告明确只对封存 A2 成立（`../../v14_first_principles_search/shadow_calibration/SHADOW_CALIBRATION_REPORT.md:5-17,108-114`）。 |
| Premium Queue Split / RobustMarketLead：把下一回合 premium SELL 提前并下一回合偿还 | V14 exact queue best response | **不是新方向；公开版本更粗** | 本轮 `V24-RobustMarketLead` 与 `Premium Queue Split` 都读取**自己的下一回合计划卖量**，在当前 town demand 为 0 时提前卖，再从下一回合扣回；没有识别对手 queue。V24 只额外加每次最多 4 单位与安全 fallback（`live_cli/kernels/lixiuqixiaoke__v24-robustmarketlead/v24-robustmarketlead.py:1-16,138-231,234-265`）。本地 V14 已用 exact opponent shadow、官方 slot/unit 语义和同量换序做了更强实现（`../../v14_first_principles_search/prototype_queue_solver.py:1-16,196-237,514-584,587-765`）。 |
| Product-aware counter-slot / 抢高价槽位 | V14 Q2b | **已实现—对 exact A2 有效；对未知池未泛化** | fresh confirm 对 A2 149/18/33，纯胜率 74.5%，CI `[68.0%,80.5%]`；对 r002 78%（`../../v14_first_principles_search/validation/runs/confirmatory/v14_queue_stateful_no_mirror/independent_audit.md:3-22`）。线上 87 局中 0 局保持 exact-A2，只有 8 局、10 步换序，99.984% 动作仍等于 A2（`../../v14_online_diagnosis/reporting/technical_report.md:34-44`）。剩余研究问题是**身份无关的 queue 预测**，不是继续打磨 exact-A2 shadow。 |
| 主动供给干扰/价格挤压 | V14 S1 WHEAT squeeze；Q1+S1 | **已实现—局部，未过门** | 已证明 4,001 个价格点和 31,160 组库存中性交易不变量；暴露 screen 对 A2 纯胜率 62.5% `<65%`，对 r002 73.61%（`../../v14_first_principles_search/alternatives/DECISION.md:36-109`）。与 queue 组合没有增加胜场（`../../v14_first_principles_search/decision_log.md:50-56`）。 |
| 六专家非传递；用混合策略或 portfolio | V12D static minimax mixture；V12C shop-aware complete expert router | **静态 mixture 已证伪；条件 portfolio 未验证** | V12D 三折 LOO 和加入 r002 后均退化成 100% 单一专家；强制 r002/V8 50/50 使总体下降 3.93pp、worst 下降 7.63pp（`../../v12d_static_minimax_mixture/README.md:10-38`）。V12C 直接 V8 得分率 55.56%，但对 baseline_v1 -5.56pp，按门槛否决（`../../v12c_yarn_complete_router/SCREEN_DECISION.md:7-30`）。尚未验证的是 `Q(own route, opponent behavior, context)` 的条件选择。 |
| Public-state multi-route：早期开局分类、首次分歧时整局承诺、只混合市场 delta、无 hindsight route repair | 本地固定 step72 Router、V12C、V14 exact-A2 | **架构有局部前例；公开完整实现未做本地 pool 验证** | 下载的 `Adaptive Public-State Multi-Route` 明确使用 Moon/Mutoy/Munib、早期开局签名、first-divergence route commit、市场分量叠加和第二 YARN 的因果修复（`live_cli/kernels/yamakawanin__kaggriculture-adaptive-public-state-multi-route/kaggriculture-adaptive-public-state-multi-route.ipynb` cells 0–8）。本地尚无“未知谱系 + 多完整路线 + causal second decision”通过 V15；不能把公开 Notebook 的结构说明当本地胜率。 |
| Week-four X-ray：Top-5 从 day 3–9 开始 plan-mobile；固定底盘上的 market layer 成为主要差异 | 本地 learned Router 仅 step72 选一次完整专家；V14 仅稀疏 market overlay | **重要未验证方向，但社区证据是观察性** | 社区快照对当前 Top-12 的 144 episodes 报告 Top-5 plan agreement 低、6–12 名存在 episode-level route switching、8–9 名固定开局配 live tail；还指出高价 tomato/egg/carrot window（`live_cli/kernels/destbreso__a-week-four-x-ray-of-the-top-twelve/a-week-four-x-ray-of-the-top-twelve.ipynb` cells 0、10、13、24、52、60）。这支持动态路线假设，不证明“多切换本身”因果增益。 |
| Newsvendor、Cournot、Real Options 等单体经济模型 | V12B；V13D public-bank win-risk gate | **按原形式有负证据** | 社区 Notebook 作者自报这些模型把对手供给误当外生需求、或因等待价值而错失复利（`live_cli/kernels/mansiaggarwal88__when-smart-math-fails-in-adversarial-games/when-smart-math-fails-in-adversarial-games.ipynb` cells 3–9）。V13D 对 r002/A2 得分率仅 38.19%/48.61%（`../../v13_dual_anchor_search/FINAL_VALIDATION.md:20-27`）。未来只能做对手响应、时间衰减和路线义务约束后的窄 MPC，不能直接搬 textbook formula。 |
| terminal liquidation / work-conserving repair | V12 terminal 718、V13 terminal 716、V14 S0 EOD fertilizer | **具体版本已证伪或零覆盖** | terminal 718 在 576 条候选轨迹零新增，716 在 18 个末段状态零新增；S0 在真实 smoke 中零 eligible actor（`../../v12a_terminal_branch_guard/MECHANISM_DIAGNOSIS.md:28-31`；`../../v13_dual_anchor_search/FINAL_VALIDATION.md:24-25`；`../../v14_first_principles_search/alternatives/DECISION.md:8-34`）。只应保留“先测覆盖再实现”的方法，不应再立相同动作。 |
| Island GA 搜索自己的底盘 | V15 attempt_001 为独立手写底盘，但没有 GA 搜索 | **真正未验证，P0** | 公开仓库提供 12-number genome、compiler、reference executor、island GA、CRN screen/confirm、pool/arena（`live_cli/external_repos/kaggriculture-island-ga/README.md:1-28,51-78,103-119`，commit `be23b55...`）。本地没有对这套搜索做任何运行；V15 attempt_001 只是手写混合农牧路线，A2/r002/pool 全为 0（`../../v15_cleanroom_search/candidates/attempt_001/strategy_note.md:3-24`；`../../v15_cleanroom_search/evaluator/runs/attempt_001/development/score_only_feedback.json:2-11`）。 |
| 24,000 eps/s bit-exact C++ simulator | V12–V15 主要使用官方 Python engine | **有价值的评测/搜索基础设施，不是策略** | 仓库声称 1.32.7、6 条 trace 719-step exact、L0 fixed-stream 和 L1 live-agent step mode；要求每次安装跑 golden test，并把公开结论回到真实环境复算（`live_cli/external_repos/kaggriculture-cppsim/README.md:1-15,31-47,49-106,108-132`，commit `812e50c...`）。未在本项目验证前不得称 bit-exact。 |
| Rating convergence 看 episodes 而非小时；同时 field 两版本 | V14 online diagnosis、同 A2 复投 | **已知评测问题，不是模型改进** | 本地已观察相同 A2 两份 active submission 同时点相差 243.9 Rating，且没有配平游戏数（`../../v14_online_diagnosis/reporting/technical_report.md:5-13`）。社区 Notebook 建议固定 submission id、过滤 episode count 不变的采样、同一窗口并行比较（`live_cli/kernels/destbreso__rating-convergence-episodes-not-hours/rating-convergence-episodes-not-hours.ipynb` cells 0、6、9、14）。重复提交能估计路径方差，但会占 active 槽并可能分流 episode；不能修复策略过拟合。 |
| Head-to-head runner 的 seat-1 `step` workaround | 本地 canonical pairwise runner 使用 `env.run` | **工具提示；未发现会自动推翻现有 env.run 结果** | 当前安装的 `core.py` 确实只把存储态 `step` 写到 state0，但 `env.run` 在调用 agent 前通过 `__get_shared_state` 把 shared 字段复制给每个 seat（`../../../../.venv/lib/python3.12/site-packages/kaggle_environments/core.py:621-626,722-768`）。本地 `../../v10_replay_lolo_router/pairwise_evaluate.py:305-348` 使用 `env.run`。手工 `env.step` 后直接把 `env.state[1].observation` 交给 agent 时才需显式修复；社区 Notebook 适合作为手工 runner 的防错参考，不能据标题判定 V12–V15 全部无效。 |
| tar.gz、root-level `main.py`、raw-loader QA | A2/V13/V14/V15 已有 package QA | **已实现，不是策略空白** | V13 最终包已做 raw-loader、双席、720 states/719 calls、动作等价和线上 Validation（`../../v13_dual_anchor_search/FINAL_VALIDATION.md:39-48`）。无需因社区再次提到包装而重做模型方向。 |
| 端到端 PPO / BC 扩数据 | 本地 V3/PPO 失败；V14 已禁止重复 | **不立项** | 2026-08-23 社区快照也给出 BC 同质化、长时序信用分配和 OOD 负证据（`../2026-08-23/INDEX.md:35-38`）；V14 明确列为不应重复（`../../v14_first_principles_search/community_frontier.md:212-222`）。Fast sim 可降低成本，但不会自动解决表示、奖励和对手非平稳性。 |

## 明确不能当作新发现的本地机制

以下主题若再次出现，应先引用已有结论，而不是另起版本：

| 主题 | 已有结论 |
|---|---|
| “无商店就少卖 WOOL/MILK” | V12A 的布尔 shop gate 是 A2 修掉的主要失败源。 |
| “所有分支都取消 WOOL throttle” | V13A 对 A2 50%；只有 V8 分支版本 V13C 有效，且对 A2 纯胜率仍只有 47.5%，得分率 61.25%。 |
| “公开银行领先就降风险/取消节流” | V13D 双锚失败；bank 不是 liquidation-adjusted wealth。 |
| “末段 716/718 多塞一笔 SELL” | 已探测状态零新增订单。 |
| “多个强专家 step0 随机混合” | V12D 退化为单一专家，强制混合回撤。 |
| “预测 exact A2 后重排 SELL queue” | V14 已完成且 fresh confirm 过 65%；真正缺口是未知对手覆盖。 |
| “提前买 WHEAT、下一回合卖回干扰对手” | S1 已实现，A2 62.5% 未过门；Q1+S1 没有新增胜场。 |
| “下一回合要卖，所以本回合先卖并偿还” | 本轮两个公开 Agent 已实现，但比 V14 queue 机制更粗。 |
| “未来绝对最高价树” | 仍是原策略条件下的观察预测，不能替代反事实动作选择。 |
| “原子动作 PPO 再训一轮” | 本地与社区都有负证据。 |

## 仍值得研究的空白与最小验证方式

### P0-A：Owned base schedule search，但把评测人口改正确

**为什么是空白**：V12–V14 都是在既有 replay expert 上做 Router/残差；V15 attempt_001 是一次手写独立策略，没有系统搜索。`island-ga` 的 genome/compiler/search/arena 是本轮唯一真正提供完整可运行优化管线的公开代码。

**应复用的代码**：

- `islandga/genome.py`：独立先验与宏观变异；
- `islandga/compiler.py`：融资链、sell/purchase slot 顺序与完整市场通道；
- `islandga/search.py`：islands、migration、stagnation/cataclysm、disjoint confirm；
- `islandga/arena.py`：双席位 head-to-head 与 Bradley-Terry；
- `islandga/executor.py` 只作参考，不应假定其 greedy dispatcher 已足够强。

**必须改的目标**：公开 repo 的 stock search 先对 idle 选 rich schedule，之后才在 top-N arena 排名。repo 自己也承认 bank-vs-idle 与 shared-market ranking 会冲突（`README.md:57-68`）。我们的版本应在不泄露 V15 私有池构造的前提下，以以下三轴筛选：

1. 广 seed 的空市场健康度仅作 guard；
2. 对独立生成的多种固定/自适应 public baselines 做双席位胜率或平滑胜率代理；
3. 对生成器自己产生的不同 schedule 做 self-play/arena，避免只优化一个 donor。

最终候选仍只接收一次 V15 development 匿名标量反馈；不得把 V15 private lineage、败因或 raw games 喂回搜索。V15 当前硬门与容量见 `../../v15_cleanroom_search/evaluator/PROTOCOL.md:33-55,95-137`。

### P0-B：未知对手行为指纹 + 供给区间 + conditional route

**为什么是空白**：V14 证明 exact-A2 shadow 能赢，但线上 exact-A2 coverage 为 0；V12D 证明无条件 mixture 不行；社区 week-four X-ray 与公开 multi-route 说明强策略越来越依赖 episode-level route switching。

**最小实现**：

1. 只从 public farm、money、shop、market-flow 构建早期行为 embedding；不使用 submission id，也不命名真实谱系；
2. 每回合维护 `opponent_sell[item]` 的点值或 `[lower, upper]`，floor/drop/overflow 时扩大区间；
3. 只在拥有共同合法前缀的完整路线间，在预注册的 divergence checkpoint 选择一次；未知/低置信度回退父路线；
4. market overlay 只在 worker/hands 与父路线兼容时启用；
5. 评测必须做 opponent-lineage-held-out、行为分类校准、coverage、错误干预率和 V15 pool gates。

这与 V14 exact-A2 shadow 的关键区别不是“模型更复杂”，而是**身份不可知、谱系留出、低置信回退**。

### P1-A：有限动作、区间稳健的市场 MPC

**候选动作集合**应很小：父 queue、同量 permutation、`half`、`hold one tick`、`demand-sized clip`、必要时一次小额 split。对每个动作模拟 4/24 回合：

- 当前 engine price curve；
- 已解锁 shop 与 town center 的确定需求；
- 自己固定路线下一次 sell/buy/land/hire 义务；
- opponent supply interval；
- shed + carried 的 worst-case 占用；
- 不确定性下的 worst-case margin/胜率代理。

硬约束：不破坏市场订单融资顺序、不让固定购买失约、不把仓容风险推过 guard、置信不足回父策略。它同时避开 MELON 绝对价格树的反事实缺口、V12B 的粗 gate、Newsvendor 的外生需求假设。

### P1-B：Shop-demand quantile 进入路线，不回到布尔 throttle

busyaprime 的新增价值是 6,435 种 town 组合的需求分布、single-product shop 双倍需求、`room_for` 与等待信息的机会成本；不是“没有 yarn 就少卖一次”。可研究：

- step 72/144 的路线产能上限使用 demand quantile 或 worst-case room；
- 将 WOOL/CARROT/MILK 的需求集中度作为路线风险，而非 late sell 布尔门；
- GA species 或 conditional route 的 crop/animal cap 随已见 shops 更新；
- shop draw 虽受空地 RNG 耦合，仍按不可预知分布处理，不尝试 seed exploit。

### P2：评测与算力基础设施

`kaggriculture-cppsim` 值得先做独立 fidelity gate，再用于：

- 数千 seed 固定流筛选，降低小 panel winner's curse；
- owned schedule search 内环；
- 模型池 all-vs-all 与触发覆盖统计。

接入前最低门：固定 commit、跑 bundled golden、用我方 A2/r002/V14 新鲜 traces 做逐步 money/market/observation diff、故意用 1.32.6 控制版本确认 harness 会失败、最终候选在官方 engine 复算。它不能替代 V15 fresh-source 与谱系留出。

## 本轮公开代码的采用建议

| 代码 | 建议 | 原因 |
|---|---|---|
| `kaggriculture-island-ga` | **重点研究并改造** | 提供真正新的底盘搜索能力；但 stock executor/idle objective 不能直接满足金牌目标。 |
| `kaggriculture-cppsim` | **先验证，再作为基础设施** | 可把 seed panel 扩大几个数量级；不是策略，版本/trace fidelity 是前置条件。 |
| busyaprime `room_for` | **静态提取并引擎常数复核** | 可用于 route cap/风险，而不是恢复 V12A 布尔 gate。 |
| `Adaptive Public-State Multi-Route` | **研究架构，不复制压缩 payload** | causal route commitment、component-level mixing 值得借鉴；公开阈值和 donor traces 可能高度 meta-specific。 |
| `Adaptive Shop Guard` V44 | **只做模块级静态拆解** | 外层暴露 `route_memory_search / market_impact / state_encoder / simulator / planner / market_maker / gold_floor` 及大量 clone/shop gate，但主体压缩、审计困难，且本地无模型池结果。 |
| `V24-RobustMarketLead` / `Premium Queue Split` | **不作为新主线** | 只是 own-next-tick front-run/repay；没有对手行为识别，且自报 v22 仅 1230.8。 |
| Head-to-head runner | **保留为手工调试参考** | 双席位、可视 replay、raw state `step` 防错有用；canonical `env.run` 已有 shared-state 注入，不需盲目替换。 |
| “When Smart Math Fails” | **保留为负例清单** | 提供诊断动机，没有可直接验证的强对手代码。 |

## 关键证据边界

1. **V13C 不能写成“对 A2 纯胜率超过 50%”**：它是 95/55/50，纯胜率 47.5%，得分率 61.25%（`../../v13_dual_anchor_search/FINAL_VALIDATION.md:7-14`）。
2. **V14 线上不是“胜率坍塌”**：线上纯胜率 75.86%，低的是 Rating；对手日程完全不配对，且机制只有 8/87 局短暂覆盖（`../../v14_online_diagnosis/reporting/technical_report.md:5-13,34-44`）。
3. **V14 的 74.5% 只证明 exact-A2 matchup**：confirm 留出环境 source，但没有留出 opponent lineage（`../../v14_online_diagnosis/reporting/technical_report.md:5-9`）。
4. **V15 协议文档有时序漂移**：`PROTOCOL.md:9` 的“未运行比赛”在写协议时成立；当前 `attempt_001` 已有真实 development 反馈，后者为权威状态。
5. **社区代码全部是 C 级证据**：下载成功与源码存在只证明“可审阅”，不证明 score、胜率、兼容性或无恶意；本轮没有执行任何下载 Agent。
6. **截至协议盘点，fresh 完整 attempt 容量有限**：V15 记录最多 4 个完整 fresh attempt（`PROTOCOL.md:118-130`）。因此搜索应主要使用独立随机 seed/fast sim，正式 source 只做一次性验收。

## 最终审计判断

如果目标是避免再次过拟合 A2，下一位独立策略生成 agent 最不应做的是把 V14 exact-A2 queue、V13C no-WOOL 或社区 front-run 换个阈值再交卷。最有信息增益的路线是：

1. 用 island-GA/等价搜索生成**不依赖既有 donor 的新底盘**；
2. 为新底盘加**公开行为驱动、低置信回退的 conditional route/market layer**；
3. 使用经我方 traces 验证的 fast sim 扩大 screen，但保留官方 engine confirm；
4. 最终严格走 V15 的 A2、r002、谱系等权 pool、source-cluster CI 和 paired uplift 门。

这四步对应的是“换底盘 + 换泛化假设 + 换评测人口”，而不是再优化已经证明只在 exact A2 上高覆盖的局部残差。
