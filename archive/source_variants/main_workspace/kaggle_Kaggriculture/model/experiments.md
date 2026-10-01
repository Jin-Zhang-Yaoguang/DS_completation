> 2026-09-09 当前决策：仅保留线上 2408.7 的 Player A H3 与 2043.0 的 Claude rb7925；V120/V123 对战淘汰并删除。详见 [当前登记](golden_model.md)。本文以下旧活动金牌表述均为历史记录。

# Kaggriculture 实验记录

## 2026-08-30 V114：数据规则口径硬切换

- 用户确认官方规则/数据口径已调整；自本记录起，训练、开发、门控、晋级只接受实际对局日期
  `>=2026-08-20` 的官方每日 Replay 与 Kaggle CLI 下载的我方线上 Replay/log。
- 全局键固定为 `episode_id + replay_sha256`；官方索引与提交目录的同局只能计一次。
- 最新完整日期冻结为 Blind、次新完整日期为 Dev，其余 8/20+ 完整日期为 Train，禁止跨日期泄漏。
- 旧 V2/V8 Replay、其直接派生 BC/AWR/PPO checkpoint，以及截至切换时的 V12 unit/event-market
  checkpoint/评测全部降级为 `STALE_RULE_DISTRIBUTION_NOT_PROMOTABLE`；保留文件但不能作为
  Foundation、incumbent、门控、晋级或金牌证据。
- V12 旧 L1 大评测已在运行中终止，预留的 seed 标记 exposed；无结果用于裁决。
- 下一步：CLI 增量补齐我方 8/20+ 提交记录，建立 `recent_official_replay_registry`，先报告样本量、
  日期覆盖、版本覆盖、重复、失败和 SHA，再从随机初始化重建 unit/market expert 与 checkpoint。
- 未经用户授权不提交 Kaggle。

## 2026-08-30 V115：Contractual Path Forest Hierarchical MoE（构造前淘汰）

- `strategy_parent=null`；V76 只作冻结强度比较器，候选不导入或调用任何历史完整 agent。
- 主机制：首店需求 Router 在共享前缀边界一次性承诺完整生产专家；滞后公开市场冲击浅树只路由逐商品出售时点；自有状态契约和安全执行器保持生产—融资协同。
- 与 V86/V90/V97 的区别：不做回合级生产修复，不用浅树预测单位动作，不依赖单生产蓝图。
- 预注册主指标：POU；原创性指标 MCU、BEU。构造前先做 synthetic 专家资格/尾部门，失败即淘汰且不消费 official Replay。
- 可提交包与工程 QA 通过；672 局 synthetic 矩阵全部 719 calls、零违规、full 零 fallback。
- full 8.33%，消融 9.38%，最佳固定 dairy 专家 89.58%；`BEU=-81.25pp`、`MCU=-1.04pp`、直接 V76 6.25%。
- 决策：`REJECT_PRECONSTRUCTION_BEST_EXPERT_DOMINANCE_AND_STATE_DRIFT`；未消费 official Replay，未注册 `golden_model.md`，未提交 Kaggle。

## 2026-08-30 V116：原创启发式 Hierarchical MoE（已停止，未达金牌）

- 金牌口径由用户冻结为：对行为去重金牌池双座位纯胜率 `>=75%`；平局和 ERROR 均按未胜；
  Router 必须严格优于最佳固定专家，否则不能登记 Hierarchical MoE。
- 原创性硬门：`strategy_parent=null`，禁止 Replay 的动作、逐步位置、玩家状态/成交/市场轨迹
  和等价开环蓝图；2026-08-30 修订后 Replay 只可提供合格的外生商店顺序/时点、完整配置及
  派生城镇需求，所有单位和市场动作由当前状态规则生成。
- 教师上界只作研究参照：V88 在 16 个已暴露分层 source、18 金牌、双座位共 576 局中
  `576/0/0`，零错误；V88 自身仍直接执行动作流，不能冒充 V116 原创成绩。
- R0 的 719 逐步目标原型为 `0/12`，且属于等价开环蓝图，原创性和强度双失败，永久淘汰。
- R1 只保留 30 个日级聚合目标，商店 Router 的 balanced/wool/dairy/orchard 四专家均触发；
  8 seed × V20/V21/V32/V54/V66/V76 × 双座位共 96 局，全部 719 calls、零 schema 违规、
  零 fallback，但结果 `0/0/96`，候选均值 `16,747.99`、对手均值 `129,927.84`。
- R1 失败归因为小时级资本/市场闭环缺失与任务路由低效：96 局累计 move 304,369 次、idle
  188,914 次。决策 `REJECT_R1_EXECUTION_HEALTH_AND_GOLD_SCREEN`，不注册 `golden_model.md`。
- R2 按失败证据重写为日级聚合 genome、状态差任务图、sticky role、全局劳工拍卖和独立商品
  市场控制器。4 个未见 seed × 双座位共 8 局对 idle 为 `8/0/0`、每局 719 calls、零 schema
  错误，但平均 bank `67,603 < 70,000`，日目标兑现率 `80.62% < 90%`，两个冻结健康门均失败。
  决策 `FAILED_IDLE_STRENGTH_AND_TARGET_REALIZATION_GATE`，未进入金牌 arena。
- 商品市场控制器的 13 项机制测试通过；9 商品 × 11 库存点共 99 次公开引擎定价对照零差异。
  该证据只证明部件语义，不证明完整策略强度。
- R3 按 R2 尾部失败新增首店需求 Router、四个紧凑 genome、公平补种和动态商品融资控制。
  同一冻结 4 seed × 双座位对 idle 为 `8/0/0`、零错误；四专家最终作物目标均为 59，末局
  绝对生产资产最低 63。但平均 bank `69,882.125 < 70,000`、平均日目标兑现率
  `89.9222% < 90%`，严格判 `FAILED_RC3_HEALTH_GATE_DO_NOT_RUN_GOLD_ARENA`。
- R4 只允许两个失败驱动机制：day4/day8 的 24 小时阶段预建/预购，以及 balanced_root 的
  通用首店商品需求投影；禁止改融资折价、出售地板或缩目标。已暴露面板只作回归，另用按
  shop 类别预注册的 4 个新 PET 与 4 个新非 PET seed 双座位确认，全部健康门通过后才允许
  进入金牌锚点。
- R4 回归 8 局平均 bank `74,030.625`、最低末局生产资产 58、719 calls/零错，但平均日目标
  兑现率 `87.4618% < 90%`；决策 `FAILED_RC4_REGRESSION_GATE_STOP`，按顺序门未运行 fresh
  或金牌 arena。当前只在已暴露面板做 staging-only / projection-only 因果消融，结果不得用于
  晋级。
- 2×2 消融确认 staging-only 虽使 bank `+7,592.875`，却使兑现率 `−2.5203pp`，永久淘汰；
  projection-only 使 bank `+5,308.375`，兑现率仅 `−0.1546pp`，且只改变两局 PET_CAFE，
  其余六局逐局不变。R5 只继承 projection，并针对生产连续性修复最低末局资产 57；消融数据
  只用于机制选择，不作晋级证据。
- R5 的 harvest-coupled replacement 在 8 局累计创建 1,119 条补种 claim；平均 bank
  `76,164.875`，但兑现率 `89.8232% < 90%`、最低末局生产资产 52。每回合上限没有阻止跨季
  任务洪泛，决策 `FAILED_RC5_REGRESSION_GATE_STOP`。R6 回到 projection-only，只对首店
  公开需求中的一次性作物启用 live/day/TTL 三重有界补种 option。
- R6 将 claim 收窄到两个 PET_CAFE 局，共 64 条，live/day/TTL 与 scope 均合规；平均 bank
  `70,291.25`、最低末局生产资产 62 通过，但兑现率 `89.9565% < 90%`，严格判
  `FAILED_RC6_REGRESSION_GATE_STOP`。PET 兑现改善伴随约 1.8万–2.2万 bank 损失，R7 不再
  增加 claim 数，而要寻找低机会成本的极小兑现修复。
- R7 删除坐标 claim，只在真实需求作物收获同轮预购替换种子；平均 bank `70,566` 通过，
  兑现率 `89.7796%`、最低末局生产资产 55 失败，决策 `FAILED_RC7_REGRESSION_GATE_STOP`。
- R3–R7 的单点手调已在收益、目标占用与劳动路径间反复转移损失。R8 改为参数化启发式搜索：
  搜索紧凑 genome、任务拍卖权重、市场阈值与首店浅树；以金牌锚点纯胜/分差为主要目标，idle
  只作灾难护栏；仍禁止 Replay/逐步坐标/父 agent，并保留 18 金牌双座位 75% 最终口径。
- R8 首代完成 2,048 局 R1 与 1,536 局 R2，均零错误；R2 的 12 个候选全部胜 idle，最优
  平均 bank `78,806.65`、CVaR25 `65,832`。但 R3 的 12×18×2×2=864 局金牌 scout 为
  `0/0/864`，候选均值 `52,875.13`、对手 `154,089.43`，最佳中位分差仍 `−73,081`，
  决策 `FUTILITY_ALL_CONFIGS_FAILED`，未启动R4/dev/confirm。
- R9 启动同 seed/seat 的 idle 与金牌公开状态配对诊断，目标是构造只读公开对手作物、动物、
  土地和市场库存变化的深度2反碰撞浅树；predictor 必须通过关闭消融产生正翻转，禁止读取未来、
  私有状态或调用对手 agent。
- R9 诊断的 8 局全部 719 calls、候选零错。V21 相对 idle 使候选自身 bank 平均
  `-31,779.75`、分差 `-157,823.50`，并让两 seed 的首店分别发生
  `ICE_CREAM->FARMERS`、`PIZZA->BAKERY` 变化；首店因此只能作为运行时公开状态，不能作为
  seed 外生标签。市场残差改为 demand-corrected 且污染样本不参与不可逆决策。
- 同一 p0064 的五个固定生产专家各跑 72 局金牌 scout，全部 `0/0/72`、零错误。最佳平均
  自身 bank 为 dairy `52,449.25`，最佳平均分差为 root `-71,627.21`；这否证了“只修 Router
  即可”的假设，RC9 若无真实胜局即淘汰，下一轮重构程序化劳动/生产闭环。
- 正式金牌评测口径改为两个独立 Replay 场景面板：本账号 2026-08-20+、版本/配置匹配的线上
  Replay 为主面板，官方按日合格 Replay 为独立确认；按 `episode_id+replay_sha256` 去重，
  Development/冻结测试按 episode/seed/scenario hash 隔离。两面板分别纯胜率 `>=75%` 才可
  登记，禁止合并分母或用官方数量覆盖主面板失败；synthetic 只保留为机制诊断。
- RC9 自包含候选和 8 个 mode 机制测试通过；随后在已暴露 R3 面板运行 7 模式 × 72 局，共
  504/504 局，全部 719 calls、候选零错，但总计 `0/0/504`。FULL 相对 BASE 的自身 bank
  `-1,185.75`、平均分差 `-1,944.10`；MARKET_ONLY 逐局结果完全不变；FULL 72/72 落入
  scarcity 叶，且不如固定 liquidator。决策
  `REJECT_NO_WIN_NEGATIVE_TARGET_OVERLAY_ROUTER_COLLAPSE`，未消费 Replay Development。
- R10 按失败证据转向 `strategy_parent=null` 的程序化空间工作队列：三个完整企业专家分别拥有
  布局 compiler、资本账本、actor 分区、持久任务链和市场闭环。底层未见 idle 平均 bank 未达
  100k、或已暴露金牌 scout 仍无真实胜局时，禁止训练 Router 或打开 Replay frozen 面板。
- R10 P0/机制 smoke 通过，但 P2 六 seed×四 mode×双座位 `48/48` 局数量级失败：
  Router bank 均值 `682.67`、CVaR25 `237.67`，三固定专家均值仅
  `201.17/1,958.58/469.42`，末局资产最低 0。全部 719 calls/零错误不能抵消经济失败；
  决策 `REJECT_P2_ECONOMIC_HEALTH`，未运行 P3/Replay。
- R11 修复 daily/orphan ticket、HARVEST 误判和 tranche 准入后，唯一 seed7100
  kill-fast 仍只有 bank `14,288`、step144 资产 5、终局资产 12，且漏水转 weed 23；
  `NOT_GOLD_KILLFAST_REJECT`，未跑 P2/P3/Replay。
- R12 把 PLANT→WATER 绑成同 owner 安全 bundle，加入扩产降档和局部路由。机制
  `16/16` 通过；漏水 weed `23→0`、方向移动 `3,013→1,077`、nonprogress
  `31→6`，但 627 次 PASS 暴露全局串行过强；bank `13,994`、step144/终局资产
  `5/7`，仍为 `NOT_GOLD_KILLFAST_REJECT`，未跑 P2/P3/Replay。
- R13 保留零漏水、零 orphan/expired 不变量，改为有同日服务预算证明的有界并行
  bundle，并把有限作物收获后的 replacement backlog 纳入实现产能；同时以 R8
  约 7–8 万 idle bank 的自研执行器作反证基线，不继续在低收益队列上只调 Router。
- 实际构造时否决继续修补 R12，改用 RC8 已证明的“每步重算 + 全局拍卖”吞吐主干，
  并加入工时预算的最多 3 个并行 PLANT→WATER、有界补种连续性、typed guard 和批量
  携带回仓；仍为自包含 `strategy_parent=null`，五个完整生产专家。
- R13 唯一 seed7100/router/seat0/idle kill-fast 通过：bank `95,060`、step144 资产 22、
  终局资产 67，719 calls，runtime/schema/invalid/漏水 weed 均为 0；`DROP/HARVEST=21/302`，
  避免 R12 的逐次回仓。该结果只授权 P2，不是金牌证据。
- R13 P2 六 mode×6 seed×双座位 `72/72` 完成，全部 719 calls、零 ERROR/schema，最低终局
  资产 62，对 idle `72/0/0`。但 Router 均值/CVaR25 仅 `76,393/55,153`，五 fixed 均值
  `64,781–84,604`，全部低于 90k；严格判 `REJECT_P2_ECONOMIC_HEALTH`，不跑 P3/Replay。
- P2 所有 mode 终局均为 14 hands，Router 平均方向移动 4,782，unit PASS 约 1,572；
  R14 只允许修改劳工经济与局部调度，用 critical-job/移动预算导出不高于 10 的
  hands 上限，不调低 P2 门槛。
- R14 静态 8/8，但机制仅 13/14：预注册高负载夹具下劳工目标仍未到 cap=10，
  说明工作量映射没有通过自身合约。决策 `NOT_GOLD_KILLFAST_REJECT`，未跑 kill-fast/P2。
- R15 回到可审计的硬 cap=10，并仅修复三个 P2 已确认结算错误：step696 后终局
  止买、WHEAT 逐单位购入报价/精确扣款、真实调用同轮收获补种预留。
- R15 机制 24/24 通过，但唯一 kill-fast 仅 bank `96,287 < 100k`、终局资产
  `52 < 58`；说明 cap10 已挤掉必要生产动作。决策 `NOT_GOLD_KILLFAST_REJECT`，未跑 P2。
- R16 使用 P2 完整动作容量可支持的 cap11，将 PET/PIZZA 暴露弱尾的首店路由改为
  dairy/wool，同时要求五个 fixed 保留独立商品配额，只共享高价值 MELON+羊毛/乳品骨架。
- R16 机制 27/27 通过，唯一 kill-fast 的 step144/终局资产为 `22/63`，零错，但
  bank `97,030 < 105k`；决策 `NOT_GOLD_KILLFAST_REJECT`，未跑 P2/P3/Replay。
- R17 不再调 hands 或首店映射，改做设施布局 + actor/zone 局部巡回 + 跨回合短任务束，
  目标在 cap11 下把 R13 P2 每局 4,558–4,844 次方向移动降低至 `<=3,600`，再重建
  分商品产出/成交/丢弃账本。
- R17 静态/机制 `40/40` 通过；唯一 seed7100 kill-fast 的 bank `106,891` 首次达到
  `>=105k`，且 719 calls、runtime/schema/invalid/漏水均为 0。但移动 `3,949 > 3,600`、
  终局资产 `42 < 58`，严格判 `NOT_GOLD_KILLFAST_REJECT`，未跑 P2/P3/Replay。
- evaluator-only `kagsim_accounting` 当前源码验证 `6/6` 通过，原/增强引擎 observation 与
  reward 等价，真值不进入候选 observation。精确对照显示 R16→R17 的 sell revenue
  `118,034→126,172`、spend `24,004→22,281`，但 planted seeds `207→146`；R18 因此保留
  高价值产品收益，只修 planning cursor、exact target、同格任务束和 day27 有预算资产恢复。
- R18 预注册门仍为 bank `>=105k`、移动 `<=3,600`、终局资产 `>=58`、719 calls 与零安全
  错误；唯一 kill-fast 任一失败即淘汰，不运行 P2 或 Replay。
- R18 机制 `22/22`，但唯一 kill-fast 退化为 bank `91,959`、移动 `3,981`、终局资产 40，
  决策 `NOT_GOLD_KILLFAST_REJECT`。删除式同格过滤让 jobs 减少约 35%，HARVEST/FEED/CARE/FERT
  全面下降；普通 WATER 局部丢弃和单链硬 owner 既未省移动，也造成终局 5 weeds。
- R19 撤销 R18 的删除式 bundle、普通 WATER 丢弃和串行 hard chain；保留 pure cursor 与语义
  target，从 day8 用单 growth lane + 总并行3恢复资产，并用“生产资本/低价值维护”两层调度同时
  保护 PLANT/HARVEST 与 PLACE/BUILD。仍先跑唯一 kill-fast，失败不消费 P2/Replay。
- R19 机制 `18/18`，但唯一 kill-fast 仅 bank `77,471`、day12/终局资产 `45/45`、移动
  `3,739`、终局 weed `2`；day9--12 虽持续生成 CARE/FERT，却连续四天发出 0。根因是先按
  任务存在选 tier、再检查可行边，遇到不可执行 primary 会直接 break。决策
  `NOT_GOLD_KILLFAST_REJECT`，未跑 P2/P3/Replay。
- R19 evaluator-only 精确账本 6 局守恒、5/5 测试通过；相对 R17 双座位均值少花 `556`、
  少收入 `23,189`，FERTILIZER/MILK 少产 `114.5/84.5`，而 PLANT/WATER 更多，进一步支持
  动物收益链被 tier 调度阻断。跨版本实际 Router 分支不同，该对照只作根因支持，不冒充因果 A/B。
- R20 预注册为状态化可行坐标任务束：不改 Router/专家/市场/阈值，只保留同格 owner 与经观察
  确认的后继；WATER/FEED 优先，其余只在 finite feasible frontier 上按 ready_since/raw
  priority/distance 派工。固定 COW 数门改为实际专家逐动物目标兑现门。
- R20 机制 `14/14`，day9/day12 资产 `38/50`、实际 wool 动物目标完全兑现，但 kill-fast
  bank `74,903`、终局资产 `42`、移动 `4,413`、终局 weed `1`，严格淘汰。owner assignment/
  takeover 达 `2,280/689`；远距返程与陈旧 head 压住新确认补种，是下一轮唯一调度根因。
- R21 只改链龄继承软租约：bundle 后继不重置 ready_since；最老可行 bundle 选择最近 actor，
  owner 仅作等距 tie-break；每 actor 最多一个 lease。Router、专家、市场、阈值和状态链不变。
- R21 使 bank `74,903→86,130`、CARE+FERT `261→323`、移动 `4,413→4,233`，但仍未
  过 kill-fast。未发射普通 BUILD/PLANT 被错误持久化，导致 pasture `6→13→14`、超过目标10；
  R22 只允许已发射等待确认的后继链持久，普通意图必须仍在当前 planner 前沿。
- R22 使 pasture=10、动物目标完成、终局 weed=0、移动 `3,566` 过门，bank `94,861`、
  CARE+FERT `429`；但精确坐标前沿令 PLANT `189→140`、PASS `1,869`，资产 `35/42`。
  R23 改为按同语义缺口 quota 保留最老意图，兼顾坐标稳定与绝不超额。
- R23 机制 `18/18`，但 PLANT 仅 `149`，bank/资产/移动/CARE+FERT 为
  `92,336/39/3,810/394`；语义 quota 只在抖动与返程间交换损失，严格淘汰。R24 停止租约
  微调，改为由专家 final goal 预编译不重叠的确定性地块契约，阶段只追加固定槽位。
- R24 机制/parity/static `19/19` 通过，固定槽位使 PLANT `140→159`、day12 资产
  `35→44`；但 bank/终局资产/移动/CARE+FERT 为 `95,263/41/3,935/401`，仍未过
  killfast。安全、终局 weed 和实际动物目标通过；决策 `NOT_GOLD_KILLFAST_REJECT`，不运行
  P2/P3、不读取 Replay。R25 不再调槽位或 lease 参数，改查全局 oldest-first 派工的结构性
  机会成本与终局并发收割债务。
- R25 机制/parity/static `32/32`，多项式全边匹配压力样例约 `0.0042s`；但完整生命周期
  capacity gate 把移动降至 `2,518` 的同时，把 PASS/PLANT 推至 `3,506/79`，bank/终局资产
  只有 `49,166/26`，终局 weed 2。严格判 `NOT_GOLD_KILLFAST_REJECT`，不运行 P2/P3/Replay。
  R26 不调容量阈值，改为保留 work-conserving 当前任务前沿，仅对资源与观察确认链做硬预留。
- R26 机制/parity/static `36/36`，持久 finite option、seed reservation、LOCKED 移动语义与
  expiry-aware floor 均通过反例；但 killfast 的 bank/终局资产/移动/CARE+FERT 为
  `79,264/34/4,397/340`，PICKUP `246` 且漏水 weed 5。严格淘汰，不运行 P2/P3/Replay。
  R27 转向持久批量 Supply Lane 与 WATER 硬 deadline，停止用逐观察 feeder override 反复取粮。
- 2026-08-31 用户要求停止。R27 仅留下未冻结的 `main.py/test_r27.py` 草稿，未运行测试、
  killfast、P2/P3 或 Replay；正式双面板胜率均为 `NOT_RUN`，未注册金牌、未提交 Kaggle。
- 研究协议、谱系/社区报告、逐局结果与停止总结位于 `model/v116_heuristic_gold_search/`。

## 2026-08-29 V113：Simulator-trained Full-action Hierarchical MoE PPO（执行中）

- `strategy_parent=null`；Actor 将自行生成 `farmer / hands / market` 全动作，提交端不导入任何既有模型。
- 1.32.7 Replay 只用于引擎校准、离线预训练、专家发现和对手蒸馏；现有金牌只作为闭环对手及门控。
- 六个可学习 latent experts，由日级 Router 选择；回合级 Worker 在合法 candidate-action 空间中生成结构化动作。
- 门控冻结为：Development 256 个全新 seed、Confirmation 512 个再次全新 seed、双席位并对全部可执行金牌；pooled 胜分率与逐金牌护栏同时通过才登记金牌。
- 当前阶段：`SPECIALIST_SEPARATED_ON_POLICY_PPO / IN_PROGRESS`；未构建 challenger，未提交 Kaggle。完整协议见 `v113_simulator_hmoe_ppo/TRAINING_PLAN.md`。
- 引擎门已完成：100 Replay、72,000 状态精确一致；Codec 动作闭包 100%。
- 五个从零训练的单地块商品专家已形成闭环。冻结动作专家的 Router PPO 在 16 局全新 seed 双座位中，对 Starter 从 87.5% / `+120.375` 提升到 100% / `+1512.75`。
- 金牌门仍远未通过：PPO Router 对 V76 的 4 局为 0%，平均金币差 `−173,605`。
- 原创 8 hands / 9 地块 Scale Curriculum 已完成；加入现金、雇工和种子容量安全约束后，五个规模化作物 specialist 全部独立通过闭环。组合对 Starter 4/4、平均金币 24,105；对 V76 0/2、平均金币 16,623、平均差 `−151,547.5`。
- 完整动作 PPO 最多使用 32 场、23,008 transitions、10 epoch、KL `0.00206`；温度 0.05/0.30/0.50 与动作 head 0.1 校准分支在全新种子确定性闭环中均未改变 argmax 行为，全部判为 `REJECT_BEHAVIOR_INERT`。
- Role-Target Option Worker 已完成；同时修复训练允许精确数量 3/5、推理 mask 却禁止它们的动作契约错误。加入 option 语义安全执行器后，EGG/MILK/WOOL 在全新 4 seed × 双座位中均 8/8 战胜 pass，平均金币 5,708/24,356/20,966。
- 三专家对 V76 各 2 局均 0%；最强 MILK 平均金币 24,284、平均差 `−157,970`，仅通过课程门，不具备金牌强度。
- 联合 Manager/Worker PPO 第 1 轮 5,752 transitions 后部署行为完全不变；第 2 轮扩大 option 探索后 rollout 仅 1/8 胜，更新 checkpoint 在配对 8 局中平均比 BC 低 32.75，均否决。采样器已改为持续 option 和边界决策，但三固定生产格课程缺少规模先验。
- 直接 6/9/12 格与分期扩产规则实验失败，9 格以上现金归零。下一阶段从高分 Replay 蒸馏阶段 option 与商品需求，再以独立 Actor 继续 fresh-seed PPO；Development/Confirmation 仍未消费。
- Replay 蒸馏首轮：12 场多玩家、17,256 状态，原轨迹金币均值 106,893；混合 24 个玩家后闭环 0/8。第二轮固定 Thomas Tschinkel 单一玩家 16 场、11,504 状态，原轨迹均值 95,228，但蒸馏模型对 pass 仍 0/8。
- 单玩家模型验证集角色/目标/单位/市场准确率约 96.3%/54.3%/73.2%/63.5%；失败轨迹存在错误建造和跨回合重复买卖。下一结构门改为多阶段 option + 读取前序 token 与影子状态的自回归 market decoder；旧并行 market checkpoint 不继承。
- Stage 17 联合自回归 timed action 已完成：256 新 seed × 双座位，共 512 局、368,128 状态；6 epoch BC 最终验证 unit/market/market-quantity 准确率 99.09%/97.95%/91.95%。
- 大样本 BC 对 PASS/Starter 各 16/16，平均金币 108,164/85,654，较旧基座配对平均 `+84,241/+68,410`，95% CI 下界均显著为正；对 V76 仍 0/16、自身均值 11,543，因此只作为课程基座。
- 32 局 V76 on-policy、23,008 transitions 的 joint-ratio PPO 已测试 enterprise potential、pure own-score 和 smooth margin 三种回报；1e-7/3e-7 候选均未在独立 seed 形成稳定正增益，全部 `REJECT_NOT_GOLD`。下一步转低维跨日 option 与多专家 PPO，不再给单 expert 高维联合策略打补丁。
- Stage 18 职责分离后，market expert 2 与 unit expert 3 分别形成独立正向证据；unit3+market2 合并对旧基座 24 局自身 `+2,292`、分差 `+12,744`，仍 0/24 战胜 V76。
- Stage 19 否证 DAgger：V76 在未执行自身动作的候选状态上内部路线失同步，PASS 标签从正常闭环 5.47% 升至 39.66%，所有 DAgger BC 分支经济坍塌，永久否决该标签路线。
- Stage 20 直接 simulator on-policy PPO 只更新 unit expert 3。相对合并基座的 V76 独立 24 局，自身 `+4,748`、95% CI `[+1,655,+7,772]`，分差 `+22,224`、CI `[+10,731,+34,276]`；Starter 8/8。该 checkpoint 晋级为训练 incumbent，但 V76 仍 0/24，不能称金牌。
- Stage 21 checkpoint self-play rollout 为 9/0/7；更新后对 incumbent 确认仅 8/0/8，对 V76 自身 `+304`、分差 `-633` 且 CI 均跨 0，淘汰。当前转向 V76 对抗分布的 own-score、unit-only PPO。
- Stage 22 V76-only own-score PPO 使用 16 局、11,504 transitions；`5e-7/1e-6` 两分支在新 4 局中自身分别 `-4,460/-5,286`、分差 `-13,893/-15,777`，均 0/0/4，淘汰。下一步冻结独立专家，训练 opponent-conditioned unit/market Router。

## 2026-08-29 V102：公开比分—效用状态 Hierarchical MoE（构造前淘汰）

- `strategy_parent=null`；公开现金差和可变现资产路由增长、追平、领先锁定和终局专家。
- 预构造 576 局零错误、四专家均覆盖；灾难率从基准角度降到 0。
- 但 full 29.17%，固定增长专家 97.40%；MCU `−68.23pp`、`0/61/131`。
- 决策：`REJECT_PRECONSTRUCTION_PREMATURE_LIQUIDATION`；未消费 official Replay，未提交 Kaggle。

## 2026-08-29 V101：合法性共识否决 Hierarchical MoE（构造前淘汰）

- `strategy_parent=null`；主专家合法动作原样执行，非法时至少两个独立专家同意同一合法替代才恢复。
- 预构造 576 局零错误；主专家得分率 81.77%，但 30,558 次非法动作没有一次形成共识恢复。
- full/ablation `0/192/0`，机制完全惰性；灾难率仍为 9.38%。
- 决策：`REJECT_PRECONSTRUCTION_CONSENSUS_INERT`；未消费 official Replay，未提交 Kaggle。

## 2026-08-29 V100：因子化可行域—专家仲裁 Hierarchical MoE（构造前淘汰）

- `strategy_parent=null`；生产与市场 Router 在四条公开高分专家间按不同状态距离独立选择，整日冻结。
- 预构造 576 局零错误、全部专家覆盖；full 74.48%，固定完整专家消融 90.63%。
- MCU `−16.15pp`、`0/161/31`；跨域分别最近不等于联合可行，组合破坏生产—融资协同。
- 决策：`REJECT_PRECONSTRUCTION_CROSS_DOMAIN_INCOHERENCE`；未消费 official Replay，未提交 Kaggle。

## 2026-08-29 V99：成熟时钟—Temporal Petri Hierarchical MoE（构造前淘汰）

- `strategy_parent=null`，无 Replay 动作流；显式按作物年龄和首次成熟日路由建田、维护、成熟收获、再播种。
- 预构造 576 局零错误，成熟收获和四类作物专家均覆盖；full 平均金币 3,067，高于消融 0，但面板仍 0%。
- 结论：规则语义正确不等于经济规模可竞争，继续调整雇工/种子比例无法跨越约 9.7 万金币强度差。
- 决策：`REJECT_PRECONSTRUCTION_ECONOMIC_SCALE`；未消费 official Replay，未提交 Kaggle。

## 2026-08-29 V98：随机扰动—状态图生产 Hierarchical MoE（构造前淘汰）

- `strategy_parent=null`，提交包无 Replay 动作流；所有单位和市场动作由当前状态生成。
- 预构造 576 局零运行错误，但 full/ablation 均 0%，候选平均最终金币 0。
- 根因：非多年生作物播种即显示 `yield_units=1`，但成熟日前 HARVEST 不可执行；即时图重复发出无效收获，现金先耗尽。
- 决策：`REJECT_PRECONSTRUCTION_RULE_SEMANTICS_FAILURE`；未消费 official Replay，未提交 Kaggle。

## 2026-08-29 V97：对手市场冲击—槽位节奏 Hierarchical MoE（构造前淘汰）

- 公开冲击浅树按 seed 分组 OOF balanced accuracy 98.04%，去冲击消融 92.37%，预测力门通过。
- 独立候选包 `strategy_parent=null`；生产三域专家、三类市场节奏专家和自有执行器全覆盖，576 局零错误。
- MCU `+3.125pp`、`6/186/0`，但 PanelScore 59.90% 且灾难率恶化 `+18.75pp`。
- 决策：`REJECT_PRECONSTRUCTION_STRENGTH_AND_TAIL_RISK`；未消费 official Replay，未提交 Kaggle。

## 2026-08-29 V96：座位优先权—稳健路线 Hierarchical MoE（构造前淘汰）

- `strategy_parent=null`；step0 按公开 seat 一次性选择完整路线，整局不拼接。
- 独立 source audit 768 局发现 seat×route 交互；正式门改用 16 个全新 seed。
- 预构造 576 局：full 81.25%，MCU `+2.60pp`、`5/187/0`，直接 V76 81.25%；但灾难率恶化 `+9.38pp`。
- 决策：`REJECT_PRECONSTRUCTION_TAIL_RISK`；未消费 official Replay，未提交 Kaggle。

## 2026-08-29 V95：路径不变控制屏障 Hierarchical MoE（构造前淘汰）

- `strategy_parent=null`；只做同位置前置修复、资源封顶和终局兑现，禁止改道、手位交换和延期任务。
- 修复同回合 DROP/PLACE 投影工程错误后，预构造 576 局零错误；full 67.19%，MCU `+0.52pp`、`35/123/34`。
- 灾难率 21.88%，V76 为 0；单参考路径本身不稳，轻微平均增益不能补偿尾部风险。
- 决策：`REJECT_PRECONSTRUCTION_TAIL_RISK`；未消费 official Replay，未提交 Kaggle。

## 2026-08-29 V94：市场交易依赖图 Hierarchical MoE（构造前淘汰）

- `strategy_parent=null`；生产动作完全冻结，仅由现金/库存依赖图重排市场意图。
- 预构造 576 局、零错误；192/192 局发生市场变化，四类专家均全覆盖。
- full 56.77%，固定顺序消融 85.42%；MCU `−28.65pp`、`0/137/55`，灾难率恶化 `+6.25pp`。
- 决策：`REJECT_PRECONSTRUCTION_ORDER_VALUE_DESTROYED`；未消费 official Replay，未提交 Kaggle。

## 2026-08-29 V93：语义作物组合—空间动作原语 Hierarchical MoE（构造前淘汰）

- `strategy_parent=null`；候选只复用无商品标签的空间动作原语，作物由公开商店、价格和成熟期 Router 重建。
- 预构造 576 局、零错误；192/192 候选局发生改种，共 11,712 个 PLANT 被改路，5 类专家均触发。
- full 得分率 0%，相对固定作物消融 `−57.81pp`，灾难率 100%；作物标签与后续浇水、成熟、出售时钟不能独立替换。
- 决策：`REJECT_PRECONSTRUCTION_CROP_SEMANTIC_NONINTERCHANGEABILITY`；未消费 official Replay，未提交 Kaggle。

## 2026-08-29 V92：事件期权—资源 Petri 网 Hierarchical MoE（构造前淘汰）

- `strategy_parent=null`；Replay 在构建期编译为任务、前置资源和市场承诺，运行时不调用历史 agent。
- 预构造 576 局、零错误；延期任务在 144/192 候选局完成，共完成 336 个 token。
- full 得分率 76.56%，相对固定时钟消融 MCU `+4.69pp`、配对 `9/183/0`；但灾难率 6.25%，V76 为 0，恶化 `+6.25pp`。
- 决策：`REJECT_PRECONSTRUCTION_TAIL_RISK`。机制有正增益但违反尾部风险硬门，整条谱系停止；未消费 official Replay，未提交 Kaggle。

## 2026-08-29 V91：置换不变劳动力匹配 Hierarchical MoE（构造前淘汰）

- `strategy_parent=null`；参考 Replay 只提供任务集合和目标状态，不调用历史完整 agent。
- 预构造 576 局、零错误；动态匹配在 192/192 候选局触发，共 8,730 回合、30,522 对 worker-task 被重分配。
- full 得分率 75.00%，对 V76 71.88%，但相对固定 hand-index 消融 MCU `−1.04pp`，配对 `0/190/2`；动态分配没有产生正翻转。
- 决策：`REJECT_PRECONSTRUCTION_TASK_NONEXCHANGEABILITY`。任务序列隐含 hand 身份和协同依赖，整条谱系停止；未消费 official Replay，未提交 Kaggle。

## 2026-08-29 V90：因子化浅树行为克隆 Hierarchical MoE（构造前淘汰）

- `strategy_parent=null`；50 个 episode 隔离训练，首店 Router 下分别输出角色条件单位动作树和 10 槽市场动作树，不含 Replay 动作流或完整历史 agent。
- 5-fold episode OOF：单位动作 91.33%，市场槽 94.63%，非空市场槽 64.98%；训练证据本身通过，但不替代闭环。
- 576 局合成闭环中 full/global-tree 消融均为 0% 得分率，灾难率 100%；累计 162,002 次单位动作因状态漂移被安全执行器丢弃。
- 决策：`REJECT_PRECONSTRUCTION_COMPOUNDING_IMITATION_ERROR`。逐动作分类误差在 719 步闭环累积后离开训练流形，不消费官方 Development/Confirmation，金牌仍为 0/5。

## 2026-08-29 V89：日级案例检索 Option Hierarchical MoE（构造前淘汰）

- `strategy_parent=null`；从 lucaskna 高分 submission 的 50 场公开胜局学习日级案例库，两级 Router 在日边界按商店序列与状态距离选择 24 步 option。
- 可提交包只含一个 `main.py`，37 个案例专家和 8 个训练首店 regime 在 576 局合成审计中真实触发，零运行错误、零 schema 违规。
- full/单母带/V76 得分率 65.10%/87.50%/78.65%；full 相对消融 MCU `−22.40pp`，`15/119/58`。
- 灾难性失败率比 V76 恶化 `+15.10pp`；结论是按日拼接仍破坏跨日资产、劳动与市场共同适配。
- 决策：`REJECT_PRECONSTRUCTION_OPTION_STITCHING_DESTRUCTIVE`；不消费官方 Development/Confirmation，金牌仍为 0/5。

## 2026-08-29 V88：参考轨迹—状态管道 Hierarchical MoE（Development 淘汰）

- `strategy_parent=null`；以 lucaskna 公开强轨迹作为训练先验，候选自有轨迹、空间回归、库存回归、资本回归四类 option，不调用任何完整历史 agent。
- 构造前 576 局通过：full/纯母带/V76 得分率 90.63%/83.85%/81.25%；full 相对消融 `+6.77pp`，`13/179/0`，零错误。
- Development 使用 64 个未暴露官方 source、八类首店各 8 个；主矩阵 1,536 局，加消融 512 局，共 2,048 局。
- 强度与原创贡献均强：POU `+11.52pp`，95% CI `[+6.45,+16.28]pp`，PanelScore 93.75%；MCU `+10.94pp`，`28/228/0`，64 source、8 regime 全触发。
- 尾部风险门失败：灾难性失败率 5.47%，V76 为 2.08%，恶化 `+3.39pp`，超过 Development 上限 `+1pp`；风险主要集中于 YARN，其次为 BAKERY/PIZZA/SMOOTHIE，但不据此修改 V88。
- 决策：`REJECT_DEVELOPMENT_TAIL_RISK_GATE`；不读取 Confirmation、不做同版本阈值补丁，金牌仍为 0/5。

## 2026-08-29 V87：跨团队行为簇整段续航 MoE（构造前淘汰）

- `strategy_parent=null`；五条专家母带来自当前前五高分槽的公开 Replay，V76 只作为强度比较器。
- 先证伪“开局市场种子指纹”：固定开局下 5,000 个合成种子的 step 1–48 市场向量没有区分度，首店预测约为八分类随机水平。
- 专家池审计：5 条路线 × 6 个冻结对手 × 16 个全新合成 seed × 双座位，共 960 局，零运行错误；路线间动作不一致率 98.75%–100%。
- 只有 lucaskna 路线达标：面板得分率 67.71%，对 V76 为 65.63%；第二名 Milan 仅 41.15%，其余三条不高于 6.25%。
- 决策：`REJECT_PRECONSTRUCTION_WEAK_OR_COLLAPSED_EXPERT_POOL`。可用专家 1/3，不把单条强母带包装成跨队 MoE，不消费官方 Replay Confirmation，金牌仍为 0/5。

## 2026-08-29 V86：多时间尺度需求—任务 Hierarchical MoE

- `strategy_parent=null`；静态审计确认无完整历史 agent 调用，wool/dairy/smoothie 三生产专家均真实触发。
- 构造前 576 局：full/ablation/V76 面板得分率分别为 2.08%/13.54%/83.85%；full 相对 ablation `−11.46pp`，直接对 V76 0%。
- 719 calls 与 action schema 安全通过，但 full 累计 40,902 次 fail-closed；事件恢复与市场重组破坏了共适应的生产/融资时序。
- 决策：`REJECT_PRECONSTRUCTION_ARCHITECTURE_DESTRUCTIVE`；未消费 official Replay，金牌计数仍为 `0/5`。

## 2026-08-29 V85：肥料副产品收集补丁（不计原创金牌）

- Development 1,536 局：POU `+7.68pp`，`100/668/0`，零错误；Confirmation 6,144 局：POU `+7.42pp`，95% CI `[+6.75,+8.11]pp`，`386/2686/0`。
- 策略强度门通过，但源码完整调用 V76 agent 后只修改父代 PASS，属于后置 overlay，不是独立 Hierarchical MoE 模型。
- 决策：`SAME_LINEAGE_PATCH_NOT_COUNTED`；不登记 `golden_model.md`，Goal 仍为 `0/5`，官方 Python 复算在原创口径更正后终止。

## 2026-08-29 V84：首店条件完整专家 Router

- 使用已暴露 Gold18 256-source 全循环结果作训练诊断；按 8 类首店 regime 分层，V76 得分率 84.93%–95.13%，8/8 均排名第一。
- 旧专家池不存在 regime 正优势，继续做 hard Router 只能选择被支配专家。
- 决策：`REJECT_PRECONSTRUCTION_DOMINATED_EXPERT_POOL`；未消费新的官方 Replay，不计入金牌产出，Goal 仍为 `0/5`。

## 2026-08-29 V83：联合棚容量—现金仲裁 Hierarchical MoE

- 合成 QA 审计六个冻结对手、4 seed、双座位，共 48 局、34,512 次父代决策。
- 预注册所需 `BUY_ANIMAL → BUY_PRODUCT` 与反向相邻结构均为 0，Router 不可能触发。
- 决策：`REJECT_PRECONSTRUCTION_INERT`；未消费官方 Replay，不计入金牌产出。

## 2026-08-29 V82：价值感知、可恢复任务编排 Hierarchical MoE

- 严格金牌 Goal `hier-moe-gold-5-20260829` 的第 6 次尝试；当前金牌计数 `0/5`，失败版本不计数。
- 父代冻结为 V76；原创身份预注册为 `OG_VALUE_AWARE_CHOREOGRAPHY`。
- 主假设：只在父动作 PASS、脚下维护合法、对应产物仍有公开商店需求且能够在终局前兑现时，才从父代回退切换到 WATER/FEED/CARE 专家。
- 当前状态：`THINKING / SYNTHETIC_EXPERT_SCREEN`。筛选仅使用非 Replay QA seed，不消费 Development；远程提交未授权。
- 合成筛选结论：WATER/CARE 虽产生大量动作变化，但 192/192 局收益不变；所有包含额外 FEED 的有效组合均为 `0/164/28`、`−13.02pp`。
- 决策：`REJECT_PRECONSTRUCTION_SYNTHETIC`。没有可用专家池，不构造提交包、不消费官方 Replay，金牌计数仍为 `0/5`。

## 2026-08-29 V81：共享市场商品级一步 MPC

- 批次 `hier-moe-originality-5-20260829`，谱系槽位 E；共同根父代 V76。
- 主假设：clone-like 局面中，以父市场序列预测对手下一队列，用官方逐单位价格反事实在父序、循环移位、逆序和冲击排序专家中选择相对净现金最优者。
- 工程结果：冻结包 SHA256 `ac32dc82423daf8ac4cca41113a82b4b6ecf79bf02dbd49a133cc4412b816098`；package QA 16/16 一致。Smoke `0/58/38`、`−33.33pp`。
- Development：64 个未暴露 source、6 对照、双座位，1,536/1,536 场完成、零错误；PanelScore `51.76%`，POU `−33.40pp`，95% CI `[−37.63,−28.91]`，`6/455/307`；对 V54/V66 分别 `−75.00/−75.78pp`。
- 延迟补审计：P99 `1.155ms`，绝对门通过，但为父代 `1.451×`，违反 `≤1.25×` 相对门。
- 决策：`REJECT_DEVELOPMENT_AND_LATENCY_GATE`。求解器精确，但“父队列等于对手队列”的结构预测错误，且相对延迟门失败；不消费 Confirmation。

> 组合批次结论：V77–V81 五条原创谱系均完成可提交构造和 64-source Development，5/5 取得有效阶段四决策，0 条通过 Development，0 条登记本地金牌。按 `PORTFOLIO_RESEARCH_COMPLETE` 口径结束；因幸存谱系少于 2 条，跳过 round-robin，下一批继续使用 V76 为共同根父代。

## 2026-08-29 V80：空间物流—闲置劳动力工作窃取 MoE

- 批次 `hier-moe-originality-5-20260829`，谱系槽位 D；共同根父代 V76。
- 主假设：V76 给出 PASS 且执行单元脚下存在可验证维护任务时，路由到 WATER、FEED、CARE 或 COLLECT_FERTILIZER 本地专家。
- 工程结果：冻结包 SHA256 `f398e7b55e84fd8b8d348cedbf45f2004ba17783c3fe8f5f4be7275bba41f7b7`；package QA 16/16 一致。Smoke `12/84/0`、`+6.25pp`，平均 margin `+55.06`。
- Development：64 个未暴露 source、6 对照、双座位，1,536/1,536 场完成、零错误；总体 POU `−2.21pp`，95% CI `[−6.77,+2.21]`，`62/643/63`。直接对 V76 `+15.63pp`，但对 V32 `−13.28pp`、V54/V66 各 `−7.81pp`。
- 决策：`REJECT_DEVELOPMENT`。本地维护有真实产出，但改变后续开放路线后呈强烈对手依赖；不消费 Confirmation。

## 2026-08-29 V79：现金流—尾部风险 Hierarchical MoE

- 批次 `hier-moe-originality-5-20260829`，谱系槽位 C；共同根父代 V76。
- 主假设：对紧邻的“固定投入 → 商品采购”做克隆抢购压力测试；现金能同时覆盖两笔承诺才采购抢先，否则保全固定投入。
- 状态契约：共享 V76 的完整生产、安全执行和出售控制；只路由相邻市场顺序，不改数量，不使用对手私有状态。
- 工程结果：冻结包 SHA256 `5c9df0bc01b94ca9a00828f78fde7f0b9ff863a3cc52f23a567b23e5bcb8477e`；package QA 16/16 逐动作、奖励一致。Smoke `0/96/0`，无收益变化。
- Development：64 个未暴露 source、6 对照、双座位，1,536/1,536 场完成、零错误；PanelScore `80.73%`，POU `0pp`，95% CI `[0,0]`，`0/768/0`；有效变化 0。
- 决策：`REJECT_DEVELOPMENT_INERT`。冻结真实样本中未出现 V76 的联合偿付冲突；不消费 Confirmation，不登记金牌。

## 2026-08-29 V78：对手供给信念 Hierarchical MoE

- 批次 `hier-moe-originality-5-20260829`，谱系槽位 B；共同根父代 V76。
- 主假设：用对手公开作物、动物和商店状态预测下一主售商品，高置信时选择该商品同回合抢跑专家，低置信回退 V76。
- 状态契约：每天只更新一次信念；仅在连续 SELL 区间内重排，不改变数量、不跨任何买入或固定支出。
- 当前状态：`BUILDING`；原创性预判 `NEW_LINEAGE`；远程提交未授权。
- 工程结果：冻结包 SHA256 `1a2136ce3a2e7574d59e676bae983e7faa22b907f44b037dd0b527e83a343b64`；package QA 16/16 逐动作、奖励一致。非官方 Smoke `0/54/42`，`−40.63pp`。
- Development：1,536/1,536 场完成、零错误；PanelScore `29.69%`，POU `−51.56pp`，95% CI `[-56.64,-46.22]`，`1/319/448`；灾难失败率增加 `2.08pp`。
- 决策：`REJECT_DEVELOPMENT`。资产存量不是下一市场槽预测，错误信念破坏 V66 精确 margin 排序；不消费 Confirmation。

## 2026-08-29 V77：需求—库存契约 Hierarchical MoE

- 批次 `hier-moe-originality-5-20260829`，谱系槽位 A；共同根父代 V76。
- 主假设：step 216 用剩余商店需求向量与我方库存缺口，在 YARN、liquidity、throughput 三个状态兼容完整生产专家间一次性路由。
- 当前状态：`BUILDING`；原创性预判 `NEW_LINEAGE`。
- 评测协议：固定 V20、V21、V32、V54、V66 和 V76；64-source Development，只有通过后才消费 256-source Confirmation；另对冻结 V76 消融计算 MCU。
- 远程提交：未授权，不提交。
- 工程结果：冻结包 SHA256 `dffadab0373582189e5ca8f106538abae7c538b6091feaf8d947aec8ef4c2e64`；package QA 16/16 逐动作、奖励一致。非官方 Smoke 为 `0/81/15`，`−14.58pp`。
- Development：64 个未暴露 source、6 对照、双座位，1,536/1,536 场完成、零错误；PanelScore `72.66%`，POU `−11.20pp`，95% CI `[-16.28,-6.51]`，`0/672/96`；六个对照全部退化，最差 V54 `−17.97pp`。
- 决策：`REJECT_DEVELOPMENT`。Router 有动作覆盖但弱专家的生产代差无法由需求匹配补偿；不消费 Confirmation，不登记金牌。

> 2026-08-28 重新提交：V19 新 Submission `55843998`、V20 新 Submission `55844004`；均复用原冻结归档，提交后初始状态为 `PENDING`。新旧 Submission 的线上 Episode 分目录存储，不混用 80 场窗口。

> 最新状态：2026-08-24 的 V14 第一性原理队列 best-response、全新双锚点确认与提交状态统一以本文末尾“2026-08-24 V14”一节为准；V13、V12 仍分别以对应历史权威节为准。历史快照保留用于审计，不与最新 Rating 混用。

## 记录原则

- 每个可提交方案建立独立子目录，代码与提交包放在同一目录。
- 每次实验固定随机种子，并记录对手、对局数、胜率、最终金币与运行错误。
- 本地评测至少覆盖 `random`、`starter`、自身镜像以及历史版本。
- 排行榜评级会随匹配池变化，本地结果与线上评级分开记录。
- **全谱系验收口径（2026-08-20 修订，针对「过拟合单一参照」教训）**：最终 Rating ≈ 对「该分段对手池」保持过半胜率的最高分段。因此任何候选必须测三池而非单一强参照：
  - 下界池（600–2000 分段）：`starter`/`random`/`pass`/v0 + 线上真实对手 TraceAgent；要求胜率 ≥99%，任何一场负局必须逐场审计；
  - 中段池（2000–2600）：V1–V7 一代；要求 >60%；
  - 上界池（2600+）：当前最强公开代（如 V20）；要求 >55%。
  只报「对 V20 胜率」与只报「对 V1 胜率」是同一类错误（上界/下界过拟合）。PPO v2 的失败即下界未测、上界过拟合 V1。
- **Kaggle serving fail-closed 门（2026-08-23 新增）**：干净归档必须用真实 `kaggle_environments.agent.get_last_callable` 执行 raw-loader QA；`agent` 必须是最后一个顶层 callable；代码不得假设 raw globals 含 `__file__`；双席位均须 720 states / 719 calls、`DONE/DONE`、动作严格为 `farmer/hands/market`、存在非 no-op、零 stdout/stderr，并与正式评测 factory 逐动作及终局 reward 完全一致。普通 `importlib` smoke 不能替代该门。

## 线上比赛过程数据存储规则

- 所有已提交 Agent 的线上 Episode 数据统一保存到与 `model/` 同级的 `model_data/`，按每个实际 Submission/版本分别建目录；不再限定为 `v0`–`v5`。
- 每个版本至少保存 Kaggle Episode 元数据、完整 Replay、我方 Agent Log 和 `sync_manifest.json`；Validation Episode 也保留，但统计胜率时仍排除 Validation。
- 第一次同步执行全量抓取；以后以 Episode ID 为主键增量抓取，已存在且校验通过的 Replay/日志不得重复下载，新 Episode 自动补齐。
- 原始数据不得只保存在 `/tmp`；临时目录只能作为下载缓存，长期数据必须落到 `model_data/`。
- Replay、日志和派生统计分离保存：原始过程文件不覆盖，胜负、金币差和 1–40/41–80 阶段统计写入独立报告。
- Kaggle API 限流、权限错误或日志不可访问时，必须写入对应版本的 `sync_manifest.json`，保留已完成文件，下一次同步继续重试。
- 具体目录结构、同步命令和增量规则见 [`../model_data/README.md`](../model_data/README.md) 与 [`../model_data/sync_competition_data.py`](../model_data/sync_competition_data.py)。

## Kaggriculture Episodes Index 定时存储规则

- Kaggle 数据集 `kaggle/kaggriculture-episodes-index` 的总索引保存为 `model_data/kaggriculture_episodes_index/manifest.csv`。
- 每个新增 `date` 依次保存到 `model_data/kaggriculture_episodes_index/date=YYYY-MM-DD/data/`，并在同目录保存 `dataset_metadata.json`；下载状态、文件数和时间写入 `sync_state.json`。
- 默认同步只下载当前已保存日期之后的新日期；首次没有状态时只下载索引最新日期，避免一次性回补历史数百 GB。已完成日期不得重复下载，失败日期下次继续重试。
- 每天 20:00（Asia/Taipei）由 Codex 定时任务执行 `python model_data/sync_kaggriculture_index.py`；该任务只负责索引检查和原始数据落盘，不覆盖已有 Replay 或派生统计。

## 线上策略验收口径

- 每个线上策略必须至少完成 **80 场公开 Episode** 才能形成正式胜率结论；Validation Episode 不计入。
- **本地验收必须双侧测量（2026-08-20 增补；吸取 PPO v2 过拟合 V1、以及 v8 初版只测上界的教训）**：任何候选提交前必须同时通过 ① **下界池**（近期线上真实对手 trace + 内置 starter/random，双席位，胜率 ≥98% 且无 margin < −10,000 的惨败）与 ② **上界池**（当前一代公开 agent 同源，配对胜率 ≥90%）。只测上界会过拟合强参照物、爬坡期对弱对手失血；只测下界则无法突破代差。Rating 的目标函数是沿匹配池路径的期望增量积分：早期「不输给低分对手」的权重大于「赢高分对手」，后期相反。
- **多模型反过拟合硬门（2026-08-27 增补）**：后续任何过程版本在本地开发阶段必须与至少 3 个不同谱系模型做固定 seed、双座位配对；正式晋级确认默认覆盖 7 个现有本地对手族，并逐族设置不低于 `−2pp` 的胜率护栏。只在单一模型或单一谱系上提升的规则不得称为金牌候选、不得据此替换父代。
- 对局按 `endTime` 从早到晚排序，固定使用前 80 场作为标准比较窗口：
  - 第 1–40 场为**爬坡期**，用于观察新提交从初始 Rating 进入相近强度匹配池的过程。
  - 第 41–80 场为**稳定期**，作为版本间主要线上比较区间。
- 爬坡期和稳定期必须分别报告胜/平/负、纯胜率和平均金币差；不可只报告 80 场合计结果。
- 纯胜率定义为 `胜场 / 总场数`；若出现平局，另行报告 `得分率 = (胜场 + 0.5 × 平局) / 总场数`，不得把得分率标成纯胜率。
- 少于 80 场的版本只记录阶段性结果并标记为**未达验收门槛**，不得据此宣布正式胜负；若稳定期不足 40 场，必须注明缺口。
- 超过 80 场后的对局作为扩展/稳态跟踪单列，不回写或改变第 1–80 场标准窗口。
- Rating 只作辅助观察；正式比较优先看第 41–80 场胜率，同时记录对手 Rating 分布，避免把爬坡期弱对手红利误认为策略提升。

## 方案路线

`Tag=无价值` 表示不再把该整包作为竞争提交或继续调参；其中仍可保留代码作为失败夹具。`研究资产` 表示只保留可迁移组件，不代表整包值得上线。`未达门` 表示机制可能有研究价值，但当前完整候选不具备提交资格；`有价值·已提交待线上` 只表示本地冻结门通过且已上传、尚未通过 Kaggle validation；`有价值·已提交` 表示 validation 已完整通过，仍不代表已取得稳定线上增量。

| 版本 | 状态 | Tag | 目标 / 当前判断 |
| --- | --- | --- | --- |
| `v0_api_smoke` | 本地与线上接口通过 | 基础设施 | 只用于观察、动作、720 回合和提交格式回归 |
| `v1_adaptive_market` | 历史线上强基线 | 基线 | 接入公开双路线并适配 1.32.7；保留为控制组，不再把历史高分当当前强度 |
| `v2_survival_guard` | 已完成 80 场窗口 | 安全组件 | 保留牲畜/种子安全修复；全局强度未证明优于 V1 |
| `v3_bc_ppo_hybrid` | 已完成 80 场窗口 | **无价值** | BC 五个常量头、动作标签仅两种，离线同族提升未迁移线上 |
| `v4_rule_hybrid` | 已完成 80 场窗口 | 研究资产 | 保留冠军公开路线；整包存在同源/开环过拟合 |
| `v5_rule_hybrid` | 历史线上规则候选 | 研究资产 | 保留 V1 回退与路线组件；已知 Replay 安全回归不消失 |
| `v7_premium_lead2` | 历史提交 | 研究资产 | 保留 two-turn preempt wrapper；整包不再作为奖牌候选 |
| `v8_kawa_lead2_slot` | 历史提交 | 研究资产 | 保留 Kawa 完整生产专家；旧“金牌候选”判断已被线上表现否定 |
| `v9_demand_delay` | 未提交、已否决 | **无价值** | 两回合等待无法抵消一次数百单位 dump，机制尺度错误 |
| `v9_anti_mirror` | 历史提交、验收失败 | **无价值** | 检测器无法识别真实镜像，设计样本增量未迁移 |
| `v5_ppo_v2_league` | top-days 曾上线 | **无价值** | 收益来自硬编码 residual，不是 PPO；线上稳定期无增量 |
| `v6_ppo_v3_moe_router` | Router 正式通过；PPO 仅 pilot | 研究平台 | 保留反事实数据、完整专家 Router、NumPy 服务与门禁；不可声称 PPO 完成 |
| `v10_replay_lolo_router` | 2,090 官方 Replay 索引、LOLO Router 已完成 | 值得保留 | 以 V1/V2/V5/V8 完整专家做规则与学习 Router，建立无泄漏评测基础 |
| `v11_iterative_league` | Round 1–3 已完成 | 值得保留 | 16 模型联赛筛出 `r002`，候选必须在下一轮新 panel 首评 |
| `v12_incumbent_r002` | 修复后 Submission `55713359` 已上线 | **值得保留** | V11 Round 3 冠军；完整 learned Router + 第 10/17/24 天动物品节流 |
| `v12a_terminal_branch_guard` | 两轮 screen 后否决 | **无价值** | shop-product gate 造成特定 WOOL 路径 W→L，最差对手 −2.78pp |
| `v12a2_no_shop_gate` | 修复后 Submission `55713355` 已上线 | **值得保留** | A 的因果单组件修复；移除 shop-product gate，正式验证优于 r002 |
| `v13a_a2_no_wool_throttle` | 双锚点 screen 否决 | **无价值** | 全局取消 WOOL 节流，对 A2 得分率仅 50%，没有形成升级 |
| `v13c_a2_v8_no_wool_throttle` | Submission `55719781` 已上线 | **值得保留** | 只在 V8 分支取消 WOOL 节流；对 r002/A2 得分率 77.50%/61.25%，两者 CI 下界均高于 50% |
| `v13d_a2_public_winrisk_gate` | 双锚点 screen 否决 | **无价值** | 公开金币领先时取消节流，对 r002/A2 得分率仅 38.19%/48.61% |
| `v13b_a2_terminal_clearance_716` | 打包前否决 | **无价值** | 18 个末段探测状态零新增订单，机制在可观测样本中不产生动作 |
| `v14_s0_eod_fertilizer` | 已暴露开发 smoke 后停止 | **无价值** | 8 局真实轨迹触发 0 次；机制虽满足静态不变量，但父路线没有可利用覆盖 |
| `v14_s1_inventory_neutral_wheat_squeeze` | 已暴露开发 screen 未达门 | 未达门（研究资产） | 对 A2 45/12/15、纯胜率 62.50%，低于 65% 硬门；只保留交易不变量资产 |
| `v14_q1_stateful_queue_best_response` | 已暴露开发 screen、被 Q2b 支配 | 研究资产 | 对 A2 47/10/15、纯胜率 65.28%，但只是已暴露开发结果，且覆盖被冗余 public-equality 门压缩 |
| `v14_queue_s1`（QS1 / Q1+S1） | 已暴露开发 screen 后否决 | **无价值** | 对 A2、r002 的 W/T/L 与 Q1 完全相同，只增加 margin，没有新增胜场；未进 finalist |
| `v14_queue_stateful_no_mirror`（Q2b） | Submission `55722630` 已 `COMPLETE`；Validation Episode `97822469` | **有价值·已提交** | 只移除冗余的完整 public-production equality，保留 clone≤4 与全部 fail-closed 门；fresh confirm 对 A2/r002 纯胜率 74.50%/78.00% |
| `v12b_market_feedback_router` v1 | screen 否决 | **无价值** | 金币略增但得分下降，市场冲击门控不能转化为胜局 |
| `v12b_market_feedback_router` v2 | screen 通过但未进 formal | 研究资产 | 领先保护后无 W→L，但正增量仅来自一个已见 source，证据太弱 |
| `v12c_yarn_complete_router` | screen 否决 | **无价值** | 平均为正但对 baseline V1 −5.56pp；step72 无法识别该风险 |
| `v12d_static_minimax_mixture` | 分析后不实现 | **无价值** | LOO/maximin 权重退化为 100% 单一 incumbent，混合没有增量 |
| `v1_wheat_loop` / `v2_daily_scheduler` / `v3_roi_planner` / `v4_market_adaptive` | 早期路线图占位、无独立目录证据 | **无价值** | 不再与真实可提交版本混合计数 |

## 实验表

| 日期 | 版本 | Tag | 环境/对手 | 局数 | 胜/平/负 | 胜率 | 平均最终金币 | 错误率 | 线上评级 | 结论 |
| --- | --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| 2026-08-17 | `v0_api_smoke` | 基础设施 | Py3.12 / KE 1.32.2；`pass`、`random`、`starter` 双席位 + 自博弈 | 7 | 6/1/0 | 85.7% | 5545.7 | 0% | 304.9（历史 CLI publicScore） | 线上运行通过；策略强度需升级 |
| 2026-08-17 | `v1_adaptive_market` | 基线 | Py3.12 / KE 1.32.7；v0、`random`、`starter` 双席位 | 6 | 6/0/0 | 100% | 150871.3 | 0% | 2727.5（原提交历史 publicScore） | 完整双路线基线稳定运行；hinge 修正收益很小 |
| 2026-08-17 | `v2_survival_guard` | 安全组件 | Py3.12 / KE 1.32.7；v0、`random`、`starter` 双席位；11 场公开轨迹配对 | 17 | 17/0/0 | 100% | 153523.3（6 场 smoke） | 0% | 2576.9（历史 publicScore） | 公开轨迹 10 场持平、1 场 +6,585；激进 WHEAT 裁剪因 −9.5k 被否决 |
| 2026-08-18 | `v3_bc_ppo_hybrid` | **无价值** | 1,000 个未见 seed 对 v2 双席位；6 类对手池 1,200 场；11 场 Replay | 3200+11 | — | 84.55%（对 v2 得分率） | — | 0% | 2261.1（历史 publicScore） | 离线同族提升未迁移；线上标准 80 场为 62/0/18 |
| 2026-08-18 | `v4_rule_hybrid` | 研究资产 | 1,000 个未见 seed 对 V1 双席位；200 个独立 seed 对 V2 双席位；11 场 Replay | 2400+11 | 1781/0/619 | 74.21% | — | 0% | 2295.3（历史 publicScore） | 对 V1/V2 的直接结果不能证明排行榜泛化 |
| 2026-08-18 | `v5_rule_hybrid` | 研究资产 | V4 四层结构；R4 改为 V1；11 场 Replay 回归；8 场 smoke | 11+8 | — | — | — | 0% | 2368.6（历史 publicScore） | Replay 总金币 −6,585、动物损失 5 对 2；保留组件而非整包结论 |
| 2026-08-19 | `v5_ppo_v2_topdays` | **无价值** | 4,662 场 G5 扩展池；11 场 Replay；干净归档 smoke | 4,662+11 | — | — | — | 0% | 2219.4（历史 publicScore） | 线上稳定期得分率 50%，手工 residual 没有形成竞争增量 |
| 2026-08-19 | `v1_adaptive_market`（重提交） | 基线 | 原始 V1 归档；本地 smoke | 6+1 | 6/0/0 | 100%（本地） | 143,336.5（6 场） | 0% | 2488.0（历史 publicScore） | 同一归档重投显著波动，证明 Rating 路径依赖 |
| 2026-08-20 | `v7_premium_lead2` | 研究资产 | V5 + two-turn premium lead；30 seed × 双席位对 V5；11 Replay；3 smoke | 60+11+3 | 53/0/7（对 V5） | 88.33%（对 V5） | — | 0% | 1978.9（历史 publicScore） | 保留 wrapper，整包不再作为奖牌候选 |
| 2026-08-24 | `v13a_a2_no_wool_throttle` | **无价值** | 未暴露 screen36；同 source 双席位直接对 r002 与 A2 | 144 | r002 53/0/19；A2 27/18/27 | 得分率 73.61% / 50.00% | — | 0% | 未提交 | 全分支取消 WOOL 未优于 A2，淘汰 |
| 2026-08-24 | `v13c_a2_v8_no_wool_throttle`（screen） | **值得保留** | 与 A/D 完全相同的未暴露 screen36；双锚点 | 144 | r002 53/0/19；A2 27/26/19 | 得分率 73.61% / 55.56% | — | 0% | 后续提交 `55719781` | 唯一通过预注册 screen，封存为 finalist |
| 2026-08-24 | `v13d_a2_public_winrisk_gate` | **无价值** | 未暴露 screen36；同 source 双席位直接对 r002 与 A2 | 144 | r002 27/1/44；A2 15/40/17 | 得分率 38.19% / 48.61% | — | 0% | 未提交 | 双锚点均失败，淘汰 |
| 2026-08-24 | `v13c_a2_v8_no_wool_throttle`（confirmatory） | **值得保留** | 一次性未暴露 100 source；r002/A2 双锚点、双席位 | 400 | r002 155/0/45；A2 95/55/50 | 得分率 77.50% / 61.25% | — | 0% | `55719781` 初始 600.0 | 两个得分率 CI 下界均 >50%；A2 纯胜率为 47.50%，不得混称 |
| 2026-08-24 | `v14_s0_eod_fertilizer`（开发） | **无价值** | 已暴露 V13 screen 的 2 source smoke；A2/r002 双锚、双席 | 8 | — | — | — | 0% | 未提交 | `s0_eligible_actors=0`，无真实覆盖，未消耗完整 screen |
| 2026-08-24 | `v14_s1_inventory_neutral_wheat_squeeze`（开发） | 未达门（研究资产） | 已暴露 V13 screen36；A2/r002 双锚、双席 | 144 | r002 53/0/19；A2 45/12/15 | 纯胜率 73.61% / 62.50% | —（margin +70.88 / +5.11） | 0% | 未提交 | A2 纯胜率低于 65%，整包不提交 |
| 2026-08-24 | `v14_q1_stateful_queue_best_response`（开发） | 研究资产 | 已暴露 V13 screen36；A2/r002 双锚、双席 | 144 | r002 53/0/19；A2 47/10/15 | 纯胜率 73.61% / 65.28% | —（margin +173.35 / +400.11） | 0% | 未提交 | 已暴露点估计过线，不是新鲜确认；随后被 Q2b 支配 |
| 2026-08-24 | `v14_queue_s1`（QS1 / 开发） | **无价值** | 已暴露 V13 screen36；Q1 + S1 对 A2/r002 | 144 | r002 53/0/19；A2 47/10/15 | 纯胜率 73.61% / 65.28% | —（margin +178.46 / +405.22） | 0% | 未提交 | 相对 Q1 零新增胜场，拒绝包只保留为工程夹具 |
| 2026-08-24 | `v14_queue_stateful_no_mirror`（Q2b 开发） | **有价值** | 已暴露 V13 screen36；只删除 public equality 单变量门 | 144 | r002 55/0/17；A2 52/10/10 | 纯胜率 76.39% / 72.22% | —（margin +220.35 / +662.60） | 0% | 后续提交 `55722630` | 达到已暴露 causal-oracle outcome ceiling，晋级冻结打包 |
| 2026-08-24 | `v14_queue_stateful_no_mirror`（fresh screen） | **有价值** | 全新 36 source；A2/r002 双锚、双席 | 144 | r002 61/0/11；A2 59/8/5 | 纯胜率 84.72% / 81.94% | —（margin +260.97 / +789.32） | 0% | 后续提交 `55722630` | 两个 screen 硬门均通过，唯一 finalist 进入 confirmatory |
| 2026-08-24 | `v14_queue_stateful_no_mirror`（fresh confirmatory） | **有价值·已提交** | 另 100 个全新 source；A2/r002 双锚、双席 | 400 | r002 156/0/44；A2 149/18/33 | 纯胜率 78.00% / 74.50% | —（margin +210.08 / +715.16） | 0% | `55722630`：`COMPLETE`；Validation `97822469` | A2 纯胜率 CI `[68.0%,80.5%]`、r002 `[72.5%,83.5%]`；平局不算胜，全部提交硬门通过；validation 为 720 states、DONE/DONE、零 stdout/stderr |

## 历史线上 80 场分阶段统计（截至 2026-08-20）

历史快照：2026-08-20（Asia/Taipei）。公开局数和金币差来自 `model_data/*/episodes.json` 及对应 Replay，排除 Validation，按 `endTime` 升序取前 80 场。Rating 是当日截面，不是当前值；最新状态见本文末尾 V12 小节。

| 版本 | Submission | Kaggle 状态 | publicScore | 公开局数 | 爬坡期胜率 | 稳定期胜率 | 稳定期平均金币差 | 标准 80 场窗口胜/平/负 | 验收 |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `v0_api_smoke` | 55574764 | 下线 | 304.9 | 12 | 33.33% | — | — | 4/0/8（12 场） | 未达 |
| `v1_adaptive_market`（原提交） | 55575950 | 下线 | 2727.5 | 78 | 92.50% | 73.68%（38 场） | +2,839.7 | 65/0/13（78 场） | 未达，缺 2 场 |
| `v1_adaptive_market`（重提交） | 55612135 | 当时上线 | 2482.3 | 116 | 70.00% | **65.00%**（40 场） | +995.1 | 54/0/26 | 已达；跨时段对手未控制，不作显著性声称 |
| `v2_survival_guard` | 55578745 | 下线 | 2576.9 | 90 | 80.00% | 77.50%（40 场） | +3,936.0 | 63/0/17 | 已达 |
| `v3_bc_ppo_hybrid` | 55585467 | 下线 | 2261.1 | 81 | 85.00% | 70.00%（40 场） | +3,286.2 | 62/0/18 | 已达 |
| `v4_rule_hybrid` | 55592200 | 下线 | 2295.3 | 81 | 77.50% | 70.00%（40 场） | +3,886.9 | 59/0/21 | 已达 |
| `v5_rule_hybrid` | 55593180 | 下线 | 2368.6 | 79 | 90.00% | **84.62%**（39 场） | +5,386.6 | 69/0/10 | 未达，缺 1 场 |
| `v5_ppo_v2_topdays` | 55612090 | 下线 | 2219.4 | 92 | 80.00% | **50.00%**（40 场） | +44.4 | 52/0/28 | 已达，**正式结论：无增量** |
| `v7_premium_lead2` | 55628597 | 上线 | 1984.2 | 102 | 85.00% | **80.00%**（40 场） | +4,198.5 | 66/0/14 | 已达；4 场惨败（−20k~−49k）暴露旧路线对私有新一代对手的代差 |
| `v8_kawa_lead2_slot` | 55647343 | 上线 | 1658.8 | 17（爬坡中） | — | — | — | 14/0/3（未达验收） | 早期信号积极：镜像 83.3%/非镜像 80%、**0 惨败**；待 80 场 |

2026-08-20 截面结论：V2/V7 的稳定期点估计高于 V1 重提交，topdays 为 50%；但不同版本不在同周期、没有保存 match-time 对手 Rating，40 局区间大量重叠，不能写成统计显著。V5 只有 39 场稳定期，仍未达门槛。所有已统计对局均无平局。

### V1 重提交与 V7 的线上反思（2026-08-20，基于 98/112 场 Replay 的动作级分析）

**V1 重提交（稳定期 65.0%，Rating 2482.3）的问题：**

1. **接近局转化失败是主因**：112 场中 54 场 margin 绝对值 ≤3000（48%），其中只赢 27 场（50%）——接近局等于抛硬币。对比之下 V7 的接近局 24 场赢 16（67%）。V1 的路线本身没问题，输在「同路线对决的最后一击」上。
2. **镜像战打不过带 wrapper 的对手**：99 场镜像（top-meta 同族）只赢 59.6%。公开 meta 已普遍带 one-turn premium shift / slot sniper（调研 2026-08-20 确认），V1 没有任何反制层，在镜像战里系统性让出先手。接近负 35 场中我方 premium 出售 831 单位 vs 对手 1066 单位——对手卖得更多且更早，我方被抢先压价。
3. **结论**：V1 作为「无 wrapper 的纯路线基线」在当前 meta 下已无竞争力；其 2727.5 的历史高分来自早期 meta 未装备 wrapper 的窗口。保留价值仅为对照，不应再占用提交窗口。

**V7（稳定期 80.0%，但 Rating 仅 1983.4）的问题：**

1. **胜率不弱，Rating 偏弱——问题在 margin 结构而非胜负**：V7 稳定期 80% 与 V5（84.6%）同档，但 Rating 爬坡慢。margin 分布显示 p10 = −3,275、接近局占比 24/98：V7 赢的局平均 margin +7,319 并不差，但**输的局里镜像对手靠先手把差距咬得很紧**，而 Rating 只看胜负，V7 在镜像局的 75.4% 胜率低于非镜像的 89.2%——镜像局是 Rating 的主要失血点。
2. **two-turn lead 在镜像局被对手的 slot 级反制抵消**：我方 premium SELL 的 hour<12 占比 64.7% 已高于对手的 52.2%（证明 preempt 在生效），但对手总出售次数 11,599 > 我方 9,744——对手（更新一代的公开 wrapper，如 slot sniper 与更激进的 shift）在**同回合槽位**上仍能把部分出售压在我方之前。V7 的 2 回合视野解决了「跨回合」先手，没解决「同回合槽位」先手。
3. **非镜像局优势巨大但无法变现为 Rating**：非镜像 37 场 89.2%、平均 margin +11,898——这些局 Rating 涨幅受对手低评级限制（击败低分对手涨分少），而镜像局的窄负又扣分，导致 Rating 爬升慢。

**修正方向（v8 候选）**：在 V7 基础上补「同回合槽位排序」层（andrewsokolovsky V16 slot sniper 思路：把 premium SELL 移到队列最前、同商品合并数量、不改总量），预期直接攻击镜像局失血点；本地验收口径改为「镜像对手族配对胜率 + 接近局转化率」，不再只看总胜率（nekkon 2026-08-20 已证实 starter/总金币口径不迁移）。

### `v8_kawa_lead2_slot`

- 代码目录：`model/v8_kawa_lead2_slot/`（单文件 `main.py`，94,490 bytes 归档）
- 第一性原理推导（2026-08-20）：Rating 只计胜负 → 要到 2850（top 20）必须击败当前 ~2850 的对手 = 新一代公开 agent。本地配对验证 V7/V5 对 boatlee V20（Kawa 5 路线 + wrapper 栈）仅 **25% 胜率、−8,000 margin**，根因是**生产路线代差**（旧单路线 vs 新 Kawa 5 路线），wrapper 层我们反而更强（V20 的 preempt 为 1 回合/FRACTION 1.0/BATCH 12，弱于我们的 2 回合版）。同时验证 Kaito v27 是失败实验（V20 对其 8/8、V7 对其 88%），真实天花板是 V20 一代。
- 方案构成：以 V20 的 Kawa 5 路线生产（按 YARN_STORE 时机选 6c12s_4q/6c8s_3q/10c4s_3q/8c6s_3q + legacy layout 回退）为基座，把 preempt 升级为已验证的 2 回合版（FRACTION 2.0 / BATCH 30 / 多步偿还账本），并新增 slot sniper（premium SELL 移队列最前、同商品合并、总量不变）。
- 本地验证（双席位配对，seed 980001–980010）：
  - 对 V20：**19/20（95%），平均 margin +1,158**（V7 同口径为 25%/−7,970）
  - 对 V27：20/20（100%），+12,398
  - 对 V7：11/20（55%），+5,594（超过自身前代）
  - 对 starter smoke：720 回合 DONE/DONE，164,005/3,549；干净目录解包复验一致
- 全谱系验收（2026-08-20，目标函数修正后；16 核并行，`evaluate_spectrum.py`，双席位）：
  - 下界池（pass/random/starter/v0，24 局）：**24/24（100%）**，平均 margin +154,740 → 爬坡段不失血；
  - 中段池（V1–V7，48 局）：**45/48（93.8%）**，平均 +4,341（v1 7/8、v2 7/8、v3 7/8、v4 8/8、v5 8/8、v7 8/8）→ 远超 60% 门槛；
  - 上界池（V20/V27，24 局）：**24/24（100%）**，平均 +5,578（v20 12/12 +847；v27 12/12 +10,308）；
  - 真实线上对手池（v7 线上 Replay 的 20 个去重对手，TraceAgent + 原始 seed，40 局）：**40/40（100%）**，平均 margin +76,536（含 FilipJ +7,394、hnhyhj +9,243、ΛYMΞNRH +10,080 等弱/中型对手，零负局）；
  - 结论：v8 三池谱系健康（下界 64 局 100% / 中段 93.8% / 上界 100%），无「上界过拟合」（与 PPO v2 过拟合 V1 结构性不同：生产层开环 tape 保下界，微结构层带 clone 门控保上界、对非镜像自动退化）。
- 提交包：单文件 `main.py`；归档 SHA256 `f8f188e6d470809f3e2a14741f0daef075739922804988450e8b279922e2829f`
- Kaggle 结果：Submission `55647343`，描述 `v8 kawa lead2 slot: new-gen 5-route production + two-turn lead + slot sniper`，提交时 PENDING
- 已知失败模式：Kawa 路线来自公开 Replay 的开环动作，对非镜像/陌生对手无自适应；若场上出现比 V20 更新一代的生产路线（如 Kaito v28+），代差会再次出现——需保持每日巡视与路线刷新节奏
- 下一步：等 Validation 与公开局；按 80 场窗口验收；若稳定期胜率 ≥85% 且对镜像对手族配对胜率 ≥90%，视为金牌线候选并保留为最终提交之一。注意提交窗口：最新两个提交持续参赛，V8 上线后 V7 将退出窗口

### `v6_ppo_v3_moe_router`（MoVE，实现与小样本闭环）

- 代码目录：`model/v6_ppo_v3_moe_router/`
- 状态：已实现本地训练/部署闭环；未通过正式 D1、D2、D4 或 G1/G2 门槛，未上传 Kaggle，不能与现有线上版本比较
- 设计：生产层为平铺专家 `E_V1/E_HIGH`，市场层为 `M_NONE/M_ANIMAL_HALF/M_PREMIUM_FIRST/M_WHEAT_RESERVE`；V1 是候选、比较锚点和异常回退，而不是监督教师。市场每个日初可选，生产只在第 3 天第 72 步作整季承诺；共享的仅是动作编译、合法性与终局清仓
- 专家资格修正：`E_LOW` 是 V1 冻结动作表的精确别名，保留为可执行对手族，但从学习动作空间移除，避免“两个 ID、一个动作”的假多样性
- D2 数据正确性：每日公开 97 维特征；按 `source + strategy_family + lineage + episode_group_id + seed` group split，双席位绑定。分叉显式深复制 `env.info/state/steps/logs/configuration`，并恢复专家内部状态；这是为规避 Kaggle `env.clone()` 丢失随机 seed 的必需修正。非默认专家若没有实际 action footprint，训练器直接拒绝标签
- 小样本 D2：12 个去重真实状态、96 条终局分叉，零错误。有效标签计数：生产 `E_HIGH=4`；市场 `M_ANIMAL_HALF=2`、`M_PREMIUM_FIRST=4`、`M_WHEAT_RESERVE=4`。合并器校验专家顺序、特征形状和 `state_id` 唯一性；这只验证数据协议，远低于正式 20,000–50,000 状态目标
- Router 小样本：JAX/Flax 训练后导出 NumPy，最大预测误差 `2.38e-7`。验证集只有 2 行，任何 loss 或选择结果均不具有统计含义；权重只存于临时目录，未写入版本根目录或提交包
- PPO 小样本：用该 Router 对 V1 跑 2 seed、双席位，得到 120 个日级 D3 token，实际动作变化率 42.5%；两 epoch PPO 的近似 KL 为约 `0` 和 `-3.85e-5`，JAX/NumPy 导出误差 `3.58e-7`。这是接口与 loss/GAE/logprob/mask 闭环测试，不是“PPO 有效”的证据，也不得提交
- 部署验证：以 PPO 小样本权重构建干净 archive；成员为 `main.py/catalog.py/experts.py/action_compiler.py/features.py/router_numpy.py/v1_agent.py/router_weights.npz`，清洁环境对 starter 的 719 次调用完成 `DONE/DONE`，奖励 `27405/3622`。本地打包不等于上线授权
- 已知限制与下一步：当前只有少数 seed、两类可执行对手，生产标签集中在 4 个 day-3 状态；必须先扩大 D1 专家资格、D2 分层反事实数据和 24–32 对手/至少 12 有效族群，再冻结 validation、最后仅一次运行 D4。Router 未通过 G1 前，不扩大 PPO，也不把此 pipeline 输出称为候选模型

## 单次实验模板

### `<version>`

- 代码目录：`model/<version>/`
- Git 提交：
- 环境版本：
- 随机种子：
- 对手及局数：
- 核心策略：
- 相比上一版的变化：
- 本地结果：
- Kaggle 结果：
- 已知失败模式：
- 下一步：

### `v0_api_smoke`

- 代码目录：`model/v0_api_smoke/`
- Git 提交：未提交
- 环境版本：Python 3.12.13；`kaggle-environments==1.32.2`；Kaggriculture spec `0.1.0`
- 随机种子：短局 100–105；完整局 200–205；自博弈 300；文件加载 401；高杂草压力 501；干净归档 601。内置 `random` 自建未播种 RNG，因此该对手的结果会随重跑波动
- 对手及局数：48 回合短局 6 局；720 回合完整局 6 局；720 回合自博弈 1 局
- 核心策略：初始解锁区 3 块近仓小麦；买种、种植、每日浇水、成熟收获、入仓、出售；终局按可变现时间过滤任务
- 相比上一版的变化：首个版本
- 本地结果：所有完整局均为 `DONE/DONE`，每个 Agent 719 次调用，动作合法性审计零失败。首次完整矩阵最终金币：`pass` 5646/5545，`random` 5756/5371（重跑会波动），`starter` 5481/5349，自博弈 5672/5672；`weedSpawnChance=0.2` 压力局 5654；从干净目录解压归档后对 `starter` 为 5572/3491
- Kaggle 结果：提交 `55574764`，状态 `COMPLETE`。Validation Episode `93864357` 自博弈 5430/5430，双方 `DONE`；首场公开 Episode `93864896` 对 `Ornaat`，5888/51097 落败，双方 `DONE`。早期 2026-08-17 08:56 UTC 快照为 482.4 分；当前 CLI `publicScore=304.9`，评级会随持续匹配变化
- 已知失败模式：策略仅覆盖小麦与单农民，不使用临时工、动物、扩地和价格自适应；本地 PyPI 环境与比赛最新说明在部分高级规则上存在版本差异
- 下一步：提交 v0 验证线上加载，再实现 `v1_wheat_loop` 的收益与调度改进

### `v1_adaptive_market`

- 代码目录：`model/v1_adaptive_market/`
- Git 提交：未提交
- 环境版本：Python 3.12.13；`kaggle-environments==1.32.7`；Kaggriculture spec `0.1.0`
- 随机种子：正式验收 v0 8100–8101、`random` 8200–8201、`starter` 8300–8301、自博弈 8400、干净归档 8500；定价消融 75101–75120，全部交换双席位
- 公开基线来源：Tetsutani 的 `Adaptive Farming Strategy for Kaggriculture`。采用其两条完整 720 回合路线、168 回合城镇需求选择器和局部执行保护；来源与官方平衡说明已写入版本 README
- 核心策略：共享开局后根据已解锁商店在平衡路线和羊毛友好路线之间选择；路线内协调土地、临时工、作物、牛羊、物流和市场；运行时修复杂草、喂养、仓容、出售排序、种子冗余与终局清仓
- 相比上一版的变化：从单农民三块小麦升级为完整多工人、多地块、作物与畜牧协同；CARROT、TOMATO、EGG 的内部估价更新为 1.32.7 `hinge` 曲线，`HINGE_GAIN=8.0`，并逐点对齐官方 `market_price`
- 基线筛选结果：原始 Adaptive 在 KE 1.32.7 下对 E283 为 19/0/1、平均金币差 +2819.4；对公开“2883 score”为 17/0/3、平均金币差 +8068.1。该结果用于选择起点，不等同于线上评级
- 本地验收结果：对 v0 双席位最终金币 146422/148983，平均优势 +142109；对 `random` 为 175062/158649；对 `starter` 为 190921/85191；所有外部对局 6/0/0。自博弈 143171/145246；从干净目录解压归档后对 `starter` 为 164174/3600。全部 720 回合 `DONE/DONE`，无超时或运行错误
- 1.32.7 定价消融：修正版对未修改公开基线 40 场为 20/10/10，平均金币 87088.88 对 87084.98，平均差 +3.9，范围 -2338 至 +2342。说明修正改变了部分同类商品的市场抢先次序，但不是主要强度来源
- 提交包：归档根目录仅 `main.py`；32,869 bytes；SHA256 `918509335c5bd09c6e816c22a42275d81b3bb2c686666963237dc9c63d93eacf`
- Kaggle 结果：原提交 `55575950`（`v1 adaptive market routes + KE 1.32.7 hinge pricing`）状态 `COMPLETE`；当前 CLI `publicScore=2727.5`，原提交公开局 78 场，标准窗口缺 2 场。2026-08-19 又用完全相同的原始归档重新提交 `55612135`（`V1 adaptive market baseline: preserve silver medal candidate`），当前状态 `COMPLETE`、`publicScore=834.1`；新提交的公开 Replay 尚未同步，834.1 不能当作线上胜率
- 已知失败模式：主体仍是 replay-derived 开环路线；新 hinge 机制下没有专门的 TOMATO/EGG 生产路线，CARROT 产能也很少；公开同源对手会造成高度镜像的市场竞争；本地金币不代表 Kaggle 评级
- 下一步：同步 `55612135` 的公开 Replay，并重新积累 80 场；在新窗口完成前，不把原提交的 78 场结果外推为新版本表现

### `v2_survival_guard`

- 代码目录：`model/v2_survival_guard/`
- Git 提交：未提交
- 环境版本：Python 3.12.13；`kaggle-environments==1.32.7`；Kaggriculture spec `0.1.0`
- 随机种子：正式 smoke 沿用 v1 的 v0 8100–8101、`random` 8200–8201、`starter` 8300–8301、自博弈 8400、干净归档 8500；公开轨迹使用各 episode 原始 seed 与席位
- 核心策略：保留 v1 两条生产路线；18 点后只在最后安全时刻派遣携带小麦的最近工人救援连续未进食动物，第 672 步后保留原路线终局减产；对 CARROT、TOMATO、STRAWBERRY、MELON 做未来种植前缀裁剪，WHEAT 仅保留终局安全裁剪
- 相比上一版的变化：关键线上败局 Episode `93891282` 暴露 5 头牛在终局前逃走；保护器在固定轨迹回放中把损失降到 2 头。曾测试把同一裁剪推广到 WHEAT，但 Episode `93902833` 回撤约 9.5k，因此未纳入
- 本地结果：对 v0 双席位 146422/148983；对 `random` 170867/178756；对 `starter` 190921/85191，6/0/0，平均 153523.3。自博弈 143171/145246；干净解包后对 `starter` 164174/3600。11 场公开对手轨迹配对中 10 场与 v1 完全一致，Episode `93891282` 为 114762→121347（+6585），总金币差 +6585、总 margin 差 +6577
- 提交包：归档根目录仅 `main.py`；32,910 bytes；源码 SHA256 `dadc0b09eb16a0528553fbf00dd826fff8efbc826d3ef5864b1cbf6dea5d2a70`；归档 SHA256 `dc7dbd150dbebbad88686d75242f377e87f020eba67b9a3f5163059e82bd655e`
- Kaggle 结果：提交 `55578745`，描述 `v2 survival guard + safe seed pruning`，状态 `COMPLETE`；当前 CLI `publicScore=2576.9`，本地同步到 90 场公开局，标准前 80 场为 63/0/17，爬坡期 32/0/8、稳定期 31/0/9。Validation Episode `93918092` 为 720 回合自博弈，双方 `DONE`、零错误，奖励 53251/54369
- 已知失败模式：固定轨迹回放不会随我方新动作自适应，因此只用于局部回归；关键回放仍有 2 头牛因可用携粮工人距离不足而逃走；主体仍是 replay-derived 开环路线
- 下一步：作为 V1 的安全对照保留；不再扩大 WHEAT 裁剪，后续只在新候选出现安全回归时复用该基线

### `v3_bc_ppo_hybrid`

- 代码目录：`model/v3_bc_ppo_hybrid/`
- Git 提交：未提交
- 环境版本：Python 3.12.13；`kaggle-environments==1.32.7`；JAX/Flax/Optax 训练，NumPy-only 提交推理
- 数据：本地自动生成 10,000 场 v2 教师数据，双席位各 5,000 场，10 个压缩分片共 31.2 MB；训练/验证/测试按 seed 哈希 80/10/10 隔离；线上 Replay 只用于最终回归
- 模型：180 维日级特征，`Linear(128) → GRU(64) → MLP(128)`，六个因子化离散头；底层土地、工人、牲畜与安全修复全部由冻结 v2 执行
- BC：5 epoch，独立 test 的路线准确率和六头宏动作准确率均为 100%；导出 NumPy 与 JAX logits 最大误差 `7.15e-7`
- PPO：50 轮 × 2,048 场，共 102,400 场；使用固定对手池与每 5 轮联赛快照；第 40 轮以小验证得分率 92.97% 被选中，第 50 轮为 89.06%，未用 test 选择模型
- 验收中修正：原候选虽对 v2 为 84.55%，但 11 场 Replay 总金币 -225,044。消融定位为陌生开局上的路线/出售残差过拟合；加入第 3 天公开农场结构门控。同族样本距离 0–1，Replay 最小 9，阈值取 4；不使用用户名、episode ID 或对手私有信息
- 最终本地结果：对 v2 的 1,000 个未见 seed、双席位 2,000 场得分率 84.55%，paired bootstrap 95% CI `[82.925%, 86.175%]`，平均金币差 +855.69；六类留出对手池综合得分率相对 v2 +13.92pp，任何单类均无下降
- V3 对 V1 的独立 1,000 seed × 双席位 2,000 场：`1683/0/297`，得分率 84.65%，paired bootstrap 95% CI `[83.05%, 86.25%]`，平均金币差 +873.9；这是离线配对证据，不等同于线上 Rating
- Replay 回归：11 场总金币差 0、总 margin 差 0；牲畜损失 2/2、最大仓库溢出 0/0、终局未售 16/16，所有门槛通过
- 提交包：根目录仅 `main.py`、`base_agent.py`、`policy_weights.npz`；307,379 bytes；SHA256 `c6eaae2bb494da9bbab745bdf8cd2988b4f9638230179b32027b0e4b979905de`
- Kaggle 结果：提交 `55585467`，描述 `v3 BC+PPO hybrid: round-40 policy + v2 safety executor`，状态 `COMPLETE`；当前 CLI `publicScore=2261.1`。公开局已累计 81 场，按标准前 80 场为 62/0/18：第 1–40 场 34/0/6（85.00%），第 41–80 场 28/0/12（70.00%），第 81 场只作为扩展跟踪。此前 78 场阶段快照（Rating 2256.7）已过时，不再作为当前值
- 已知失败模式：结构门控有意让陌生策略完全回退 v2，因此提升集中在 v1/v2 同族及强制路线对抗；Replay 是固定对手动作轨迹，不能替代线上自适应匹配；本地得分率不等同于 Kaggle 评级
- 下一步：保留 V3 作为已完成 80 场窗口的 BC+PPO 对照；后续只在新候选与 V3 同 seed 或同期公开池对照时使用，不能用 PPO 训练曲线替代线上证据

### `v4_rule_hybrid`

- 代码目录：`model/v4_rule_hybrid/`
- Git 提交：未提交
- 环境版本：Python 3.12.13；`kaggle-environments==1.32.7`；提交端纯 Python，无模型和 NumPy/JAX 依赖
- 数据来源：第一名 Submission `55540317` 的 139 场公开 Replay；抽取 5 条可复现路线资产，记录 Episode、席位、动作数和 SHA256。公开动作只作规则研究，不使用 agent log、用户名或私有信息
- 多层消融：R1 仅替换第 72–87 步，单独总体中性；R2 合并冠军默认整季路线；R3 按 `YARN_STORE` 的第 1–4 次出现时机选择普通/早期/中期/晚期羊毛路线；R4 在第 72 步用公开农场结构门控，距离大于 4 的陌生开局整局回退 V2
- 层级筛选：80 个 seed、双席位下，R2 对 R1 为 102/0/58、63.75%；R3 对 R2 为 63/68/29、得分率 60.63%、平均金币差 +4,270.5；原单样本陌生路线虽不影响同族胜率，但使弱对手金币优势下降约 3k–7.6k，因此被 V2 安全回退取代。另测 V1 语义回退：11 条 Replay 总金币 −6,585、动物损失 5 对 2，未通过门槛
- 最终本地结果：R4 对 V1 使用 1,000 个独立 seed、双席位 2,000 场，1487/0/513，纯胜率 74.35%，paired bootstrap 95% CI `[71.75%, 76.85%]`，平均金币差 +1,219.4；R4 对 V2 使用另 200 个 seed、双席位 400 场，294/0/106，纯胜率 73.50%，95% CI `[67.50%, 79.00%]`，平均金币差 +1,379.2
- Replay 回归：11 场相对 V2 的总金币差 0、总 margin 差 0；牲畜损失 2/2、最大仓库溢出 0/0、终局未售 0/0，全部门槛通过
- 运行验收：R1–R4 共 8 场完整冒烟均为每个候选 719 次调用、720 状态、双方 `DONE/DONE`；源码通过 `py_compile`；干净目录解包后对 `starter` 为 134844/3520
- 提交包：根目录仅 `main.py`、`base_agent.py`、`routes.py`；78,889 bytes；SHA256 `9c82f7311a2b3bf0c1686ed27c361214257739e1edc2c54355f0ad769be95b70`
- Kaggle 结果：提交 `55592200`，描述 `v4 rule hybrid: champion route layers + V2 safe gate`，状态 `COMPLETE`；当前 CLI `publicScore=2295.3`。本地公开 Replay 已覆盖 80 场，标准窗口为 59/0/21：爬坡期 31/0/9（77.50%），稳定期 28/0/12（70.00%），稳定期平均金币差 +3,886.9。Validation Episode `94119640` 双方 `DONE`、奖励 `32153/32153`
- 已知失败模式：同源识别依赖第 72 步公开结构距离，可能把共享开局但后续不同的对手归为同族；冠军路线是公开 Replay 的开环动作，不会动态重规划；对 V1/V2 的直接提升不能证明对全排行榜泛化
- 下一步：80 场窗口已完成；V4 作为冠军路线规则对照保留。它的线上稳定期胜率与 V3 相同为 70%，不能只凭本地 74.35% 对 V1 的结果宣称泛化更强

### `v5_rule_hybrid`

- 代码目录：`model/v5_rule_hybrid/`
- 环境版本：Python 3.12.13；`kaggle-environments==1.32.7`；线上归档纯 Python
- 相比 V4：R1（第 72–87 步）、R2（冠军默认路线）、R3（按 `YARN_STORE` 时机切换）保持不变；R4 陌生结构改为回退 V1。V1 执行器从第 0 步并行预热，切换时不会丢失内部状态
- 本地验证：8 场完整冒烟均为 719 次调用、720 状态、`DONE/DONE`；干净解包对 `starter` 奖励 `134844/3520`
- Replay 回归：相对 V2 的 11 场夹具总金币差 `−6,585`、总 margin 差 `−6,577`；动物损失 `5` 对 `2`；安全回归门槛未通过，这是将 R4 改为 V1 的已知风险
- 提交包：`main.py`、`base_agent.py`、`routes.py`、`v1_fallback.py`；111,950 bytes；SHA256 `982ba04e20c28a6f949fe00d778c2d2d5170ee526d6220271130af1dd49a314c`
- Kaggle 结果：Submission `55593180`，描述 `v5 rule hybrid: champion layers with V1 R4 fallback`，状态 `COMPLETE`；当前 CLI `publicScore=2368.6`。公开局已累计 77 场：爬坡期 36/0/4（90.00%），稳定期目前 37 场为 31/0/6（83.78%），稳定期平均金币差 +4,762.6；尚缺 3 场，不能形成正式 80 场结论
- 下一步：继续观察并补齐 80 场；在缺 3 场期间，不用当前高稳定期数字替代正式窗口。Replay 回归中的 −6,585 金币风险仍然有效，不能因线上 Rating 上升而删除

### `v7_premium_lead2`

- 代码目录：`model/v7_premium_lead2/`
- 环境版本：Python 3.12.13；`kaggle-environments==1.32.7`；线上归档纯 Python
- 调研依据：2026-08-20 公开方案调研（见 `competition_description/public_solutions_survey.md`）。榜首 meta 已收敛为 replay 重建军备竞赛，市场时机 wrapper 是唯一持续产生增量的创新点；其中 C45（Rayk findings 日记 4.7）把合格 premium 出售提前 2 回合并记账偿还，达到 3085.4 / rank 9。V5 的 `base_agent.py` 已有一回合 preempt 机制（`_preempt_shift`），本版本把视野扩展到 2 回合
- 相比 V5 的变化：仅改 `base_agent.py` 的 preempt 子系统——`_SHIFT_STATE` 账本从单一 `(due_step, due)` 升级为 `{到期步: {商品: 数量}}` 多步账本；`_future_sells` 改为 `_future_sells_at(future_step)`；`_preempt_shift` 按 horizon 1→2 逐步检查未来 premium 出售，已被先前 preempt 记账的数量从未来量中扣除，保证同一笔计划出售不被重复提前；库存边界、价格下限保护、clone 距离门控（≤6）、批次上限（30）、窗口（120–680 步）全部不变。R1–R4 层、V1 回退、安全守卫、终局清仓均未改动
- 本地验证：
  - 对 V5 的 30 seed × 双席位 60 场配对：53/0/7，胜率 88.33%，平均 paired margin +922.9，bootstrap 95% CI [+649.2, +1197.8]（产物 `evaluation_paired_v5_report.json`）
  - 11 场 Replay 回归：与 V5 逐场完全一致（总金币差 −6,585、动物损失 5 对 2 均为 V5 的已知 R4-V1 回退风险，非 v7 新增；overflow/终局未售 0/0 持平）
  - 对 starter 3 场 smoke：134844/3520、173696/3530、193655/3509，全部 720 回合 `DONE/DONE`
- 提交包：根目录 `main.py`、`base_agent.py`、`routes.py`、`v1_fallback.py`；112,828 bytes；SHA256 `34abaecfe3ed1617a2f7f638df38fc38127847dcbf376636d233d460701b356c`；干净目录解包对 starter 为 134844/3520
- Kaggle 结果：Submission `55628597`，描述 `v7 premium lead2: V5 layers + two-turn premium sell lead (C45-style)`，状态 `COMPLETE`（Validation 通过），初始 publicScore 600.0，公开局尚在爬坡，需按 80 场窗口建立正式结论
- 已知失败模式：继承 V5 的全部已知风险（R4-V1 回退的 −6,585 Replay 回归、开环路线不动态重规划）；two-turn lead 在对手不同源时由 clone 距离门控抑制，收益仍集中在镜像战
- 下一步：等待 Validation 与公开局产生；按标准 80 场窗口（前 40 爬坡 / 41–80 稳定期）建立结论；同步公开 Replay 到 `model_data/v7_premium_lead2/`

### `v5_ppo_v2_league`

- 代码目录：`model/v5_ppo_v2_league/`
- 状态：PPO v2 已按第三方审查修订，top-days residual challenger 已构建并上传；线上需完成 80 场监控后再评价
- G0：V1 固定为唯一主基线，V2 为安全回归对照；目标 28 个对手、允许 24–32 个；当前 manifest 记录 12 个可执行族群，榜一/前十 replay 标记为外部缺口，不能用于最终声称
- G0 数据审计：旧 V3 10,000 场 shard 的 group hash 分区无泄漏（train 7,993 / validation 984 / test 1,023），但因缺少 lineage 字段标记为必须重生成；11 个本地公开 replay fixture 已记录 SHA256
- G1：V1/V2 对 v0、starter、random、forced-low、forced-high 的 400 场双席位矩阵已完成；两者胜负计数一致，V2 仅有小额金币差异
- G2：已启动新的 20,000 场 BC 生成，新增 source、strategy_family、episode_id、lineage 字段；训练完成前不使用旧 V3 PPO 结果作为证据
- G2 结果：20 个 shard、train/validation/test 为 15,954/1,954/2,092，group leakage 0；BC 测试路线与宏动作准确率均 100%，JAX/NumPy parity `5.96e-7`
- 奖励修订：PPO v2 使用 `sign(win/loss) + 0.02*tanh(gold_diff/25000)`，每日 30 个宏步，势函数严格按 `gamma*Phi(next)-Phi(current)`；旧 V3 的 0.1 权重不沿用
- G3 第一轮结果：5×1,024=5,120 场 rollout；iter5 多族群 validation 448 场得分率 75.89%，但确定性入口实际动作变化率 3.25%，非默认宏为 0，未通过 5% 干预门槛。对 V1 小型 paired 100 场得分率 50.0%，相对 V1 对手池 delta 0
- 修正实验：固定特征哈希采样把动作变化率升到 5.41%，但对 V1 100 场得分率降到 37.0%、V1 族群 −7.5pp，已回滚；证明人为随机扰动不是安全修复
- G3 残差 pilot：新增同 seed/席位/对手的一日单头反事实审计，448 条、0 错误；仅筛选 head3=value0（第 10/17/24 天动物产品出售倍率 0.5），uplift 均值 +1,541、bootstrap 95% CI [+287,+3,129]。端到端候选对 V1 的 100 场得分率 65.5%，CI [55.0%,75.5%]；240 场对手池综合提升 +6.25pp，无单类下降超过 2pp；实际动作变化率 5.605%、无错误，residual gate 11/11 通过。该反事实只有 2 个 seed，暂定为 G3 pilot evidence，不替代 G4/G5
- 三独立 PPO pilot（seed 17/29/41，5×1,024）均已完成；每条 448 场多族群资格得分率 81.25%、通过。独立 100 场 V1 配对均为 65.5%（bootstrap CI [55.0%,75.5%]），240 场对手池综合提升均为 +6.25pp；三条导出权重的行为指标相同，按预注册“相同则取最小 seed”选 seed17。该结果仍是 G3 pilot evidence，不等于 G5 独立 2,000 场证明
- 训练 rollout 使用同一安全残差；full28 PPO 主线没有通过 hard-V3 单对手门槛，因此没有直接把 full28 checkpoint 替换根权重。后续改走经过反事实筛选的 `topdays` residual challenger，单独打包并提交，旧权重和旧版本均保留
- G4 纠偏记录：首批 `full_s17/29/41` 仅实际轮转 16 个对手名称，低于 24–32 活跃池门槛，已停止且不纳入证据；补充 12 个可执行市场/供给/清仓变体后，正式训练改为 `full28_s17/29/41`，固定池 28 个、唯一名称 28 个，重新从 BC checkpoint 启动
- G4 当前进度（历史快照，已被下方更新覆盖）：`full28_s17/29/41` 曾完成 3/60 轮；第 3 轮胜率分别 81.64%/81.59%/81.64%。
- G4 资格器纠偏（已完成）：第 5 轮旧 7 对手资格器结果未纳入证据；资格器已扩充为与训练一致的 28 个名称，并从第 4 轮断点续跑。有效 28 池结果见下方运行更新；full28 仍未通过 hard-V3 门槛。
- 产物：`g0_audit_report.json`、`opponent_manifest.json`、`training_config.json`、`baseline_matrix_report.json`、`counterfactual_audit_report.json`、`residual_gate_report.json`；后续按 G3–G5 门槛逐项更新

#### 2026-08-18 G4 运行更新（修订后正式线）

- `full28_s17/29/41` 已从修复后的第 4 轮断点续跑；第 5 轮首次使用与训练完全一致的 28 对手资格器，三条线均完成 `3,584 = 28 × 64 × 2` 场完整验证，结果已写入各自 `snapshot_qualifications.jsonl`。
- 第 5 轮资格结果：seed17 总得分率 87.08%、seed29/41 均为 86.72%，平均金币差约 60.6k；但三条线对 `v3` 的得分率均约 17.19%，低于预注册的单对手最低 48% 门槛，因此三条 checkpoint 均明确拒绝，未加入联赛池。
- 第 6–7 轮继续训练中；第 7 轮 rollout 得分率为 seed17 83.84%、seed29 83.59%、seed41 83.59%，平均金币差约 59.8k–60.1k。当前尚未有通过资格的快照，不构建 challenger、不上传 Kaggle。

#### G4 诊断与配额修正

- 第 10 轮完整资格结果与第 5 轮完全一致：三 seed 总得分率均 87.08%，对 v3 均 17.19%，因此在第 10 轮一致断点停止继续烧算力。iter5/iter10 权重数值有变化，但 20 场确定性动作审计逐字节一致；有效非默认宏仍只有预注册动物产品残差，说明 BC 策略过度集中、PPO 未改变线上 argmax。
- 温度 1.5 三 seed pilot（5×1,024、28 池、16 验证 seed）提高了随机策略熵至约 1.40，但 rollout 胜率仅约 72.4%–72.8%，第 5 轮资格总得分率 89.06%、对 v3 仅 9.375%，仍拒绝；确定性动作变化没有改善。该温度方案不进入正式线。
- 实现修正：28 个唯一对手仍保持不变，但每个 2,048 场 rollout 采用可审计配额：普通对手各 64 场，v1/v2/v3/market_priority_tomato 各 128 场；此前等权轮转不满足修订计划的困难对手 100–160 场约束。正式线应从 BC checkpoint 重新启动并使用默认温度 1.0。

#### 2026-08-19 G4 结构性消融（gate 与部署闭环）

- 在同一 `full28q_s17/policy_iter_005.npz`、同一 16 个 validation seed、同一 28 对手和双席位下，执行 family gate A/B 配对消融。A 保留 `family_distance <= 4`，B 通过 `KAGGRICULTURE_DISABLE_FAMILY_GATE=1` 强制启用神经宏策略；两者均保持温度 1.0、V1 低层执行器和预注册 SAFE_RESIDUAL 不变。
- A 与 B 的 896 场结果完全一致：总得分率 89.0625%，平均金币差分别 58,915 与 59,260；V3 得分率均 9.375%，V1/V2 均 68.75%，`market_priority_tomato` 均 65.625%。因此在此 checkpoint/seed 片上，取消 gate 没有带来可检测的 V3 改善，不能把 full28 的 V3 低分归因于 family gate。
- 10 个 seed、20 场动作审计在 gate 开启与关闭时也一致：实际动作变化率 5.716%、非默认宏率 6.667%、错误 0；`neural_days=540`（每局第 3 天后 27 个宏日）。非默认宏变化来自手工 SAFE_RESIDUAL，而非 PPO argmax 学到的新宏动作。
- 结论：G4 暂停原目标的继续 warm-start/加轮数。主要风险收敛为 BC 标签塌缩与“训练采样动作→确定性部署 argmax”闭环断裂：20,000 场 BC 的 19,998 行重复、仅 2 个 exact action sequence。A/B/C 和路线扩展均未形成可攻击 hard-V3 的 PPO 候选；因此没有直接提交 full28 checkpoint，改用独立的 top-days residual 作为线上 challenger。
- 追加部署闭环对照：同一 10-seed/20-game 审计关闭 `SAFE_RESIDUAL` 后，宏非默认率为 0、实际动作变化率降至 3.185%、neural_days=540、错误 0；开启 residual 时分别为 6.667% 和 5.716%。因此当前达到 5% 门槛的动作变化完全由手工 residual 提供，不能当作 PPO 学习证据。产物为 `action_audit_no_residual.json`。
- C 单头消融：固定仅在第 10 天启用 `head3=value0`，其余宏头、日期和低层 V1 执行器不变；同一 16-seed/28-opponent/双席位资格集 896 场的总得分率 85.379%、V1/V2 各 50.0%、V3 为 0%，因此该单日干预不能作为 targeted PPO 的正向入口。产物为 `qualification_day10.json`；在扩大动作空间或重构标签前不再继续 warm-start。
- 训练→部署闭环审计：在同一 20 场 V1 环境状态上，对 `policy_iter_005.npz` 同时请求 stochastic rollout 动作和 deterministic argmax，600 个宏决策中 39 个不同（6.5%）。但确定性部署宏仍全部为默认序列；结合 `action_audit_no_residual.json` 的非默认宏率 0，说明探索确实存在，却没有被部署路径采用。产物为 `action_closure_audit.json`；后续必须采用可部署动作的行为/优势标签再训练。
- G4d 路线反事实 pilot：新增 `collect_route_cf.py`，只在 V1 已有 low/high 路线间做成对对局，不使用冠军 Replay。64 seed × 4 对手 × 双席位生成 512 条 deployable route labels，高路线比例 44.73%；仅用该小集训练的 BC 候选对 V1 128 场得分率 52.73%、CI [42.58%,62.89%]，故拒绝直接纳入。
- hard-V3 单日市场反事实：`counterfactual_v3_4seed.json` 共 224 条、0 错误；head3=value0 平均 uplift +41.7、bootstrap CI [+16.6,+73.7]。但固定三日 residual 的端到端 64 场对 V3 仅由 12.5% 升至 14.06%，CI [0,+4.69]，不足以通过 G4。该结果只说明存在弱的局部信号，不能当作最终策略证据。
- 机制型开局 pilot：仅在第 72/73 步增加“买一头牛+三次雇工”的独立规则，保留 V1 的其余动作；64 场跨 V1/V2/V3/starter 的 paired 对照中，总得分由 59.38% 降至 25.0%，平均金币差变化 −11,820，明确拒绝该模板。产物为 `cow_opening_eval_8.json`。
- 路线反事实 PPO pilot：使用 512 条 V1 low/high 路线成对标签（64 seed × 4 对手 × 双席位；高路线标签 44.73%），先训练 BC，再进行 3 轮 × 512 场 PPO。训练 rollout 胜率为 69.53%→72.27%→69.73%，并非单调提升；第 3 轮 28 对手资格得分率 89.29%，但 V3 仅 18.75%，未通过单对手门槛。独立 V1 配对 128 场得分率 52.73%，bootstrap 95% CI `[42.58%, 62.89%]`，平均金币差 −4,333；虽然小型对手池加权分数相对 V1 为 +4.17pp，但直接胜率和 CI 门槛均失败。该候选拒绝，不替换线上权重。产物为 `data/route_cf_512.npz`、`checkpoints/bc_route_cf_512/`、`checkpoints/ppo_route_cf_512/`、`evaluation_ppo_route_cf_512.json`。
- 结论：扩大 low/high 路线标签仍不足以攻击 hard-V3；下一轮必须扩展可部署的开局/整季路线模板，并以同 seed 双席位的 paired uplift 作为筛选目标，不能继续在当前两路线动作空间上增加 PPO 轮数。
- 机械路线切换搜索：在不使用冠军 Replay 的前提下，枚举 V1 low/high 路线在第 168、240、312、384、480、576 步单次切换的双向模板，共 12 个候选、768 场完整双席位对局、0 错误。所有候选均劣于 V1：最佳为 `high_to_low@168`，得分率 37.50% 对基线 54.69%，平均金币差 −6,504；`low_to_high@168` 为 34.38%、−12,075。其余切换点得分率 25.00%–34.38%、金币差 −7,607 至 −33,555。该结果拒绝“仅改变现有路线切换时点”的扩展，说明需要真正新的可部署开局/生产动作模板，而不是对 low/high 做时序拼接。产物为 `search_route_switch.py`、`route_switch_search_8.json`。
- 机制型早期市场筛选：先用 2 seed/4 对手筛选 4 个只移动市场订单的候选；`cow_delayed`（第 74 步买牛）在 16 场得到 75.0%，但扩大到 16 seed、4 对手、双席位的 128 场后为 53.91% 对 V1 的 56.25%，平均金币差 −4,508，0 错误，故拒绝。其余候选没有进入扩展验证。产物为 `v5_ppo_v2_league/search_early_market.py`、`early_market_search_2.json`、`early_market_cow_delayed_16.json`。
- hard-V3 全天单头扫描：2 seed、双席位、22 个生产日的 head3 反事实共 176 条、0 错误；在真实可售日筛出的 `[12,15,18,20,23,24,28]` 统一取动物产品出售倍率 0.5，28 条干预的平均金币差 uplift +251，bootstrap CI `[+185,+326]`（该 CI 是 pilot，日期共享 seed，不能视作独立最终证据）。
- `topdays` 残差候选：同 seed/席位/对手的 1,000 seed、双席位 2,000 场 V1 配对得分率 71.425%，bootstrap CI `[69.20%,73.70%]`，平均 margin +496；V2 独立 2,000 场得分率 78.10% vs V1 基线 50.05%，score delta +28.05pp，CI `[26.25%,29.80%]`。64 seed × 6 对手池（1,536 场）中 V1 +25.78pp、V2 +25.78pp、forced-low +22.66pp、forced-high +3.91pp，starter/random 不下降，所有对局 `DONE/DONE`、零错误；硬 V3 128 场提升 +28.91pp，CI `[19.53%,38.28%]`。
- `topdays` 动作审计：20 seed、40 局、28,760 次调用，实际动作变化率 9.492%、非默认宏率 20.0%、错误 0；干净归档 smoke 通过，推理门槛通过。11 条公开 Replay 回归总金币/总 margin 变化 0，牲畜损失、仓库溢出、终局未售均未恶化。产物为 `evaluation_topdays_2000.json`、`evaluation_topdays_v2_2000.json`、`evaluation_topdays_pool_64.json`、`evaluation_topdays_v3_64.json`、`action_audit_topdays.json`、`replay_regression_topdays.json`、`topdays_gate_report.json`。
- G5 扩展池：333 seed × 7 对手 × 双席位共 4,662 场完整配对（报告按每族 666 场），全部 0 错误。相对 V1，v1 +28.68pp、v2 +28.68pp、forced-low +21.47pp、forced-high +6.91pp，v0/starter/random 不下降；所有族群 95% bootstrap 下界均不低于 0，`topdays_gate_report.json` 14/14 gates 为 true。该证据支持构建 challenger，随后已获授权提交线上 `55612090`。
- 当前候选已复制为 `v5_ppo_v2_topdays/` 并完成独立归档（仅 `main.py`、`base_agent.py`、`policy_weights.npz`，308,221 bytes）；归档 SHA256 为 `819443380c8fffbe4f8befd7e6c75daba52958d8bcac41407f88dc3d36ad7696`。
- 2026-08-19 已经用户授权上传 Kaggle：Submission `55612090`，描述 `PPO v2 top-days residual challenger: audited animal-sale schedule`，状态 `COMPLETE`，当前 CLI `publicScore=938.3`；公开 Replay 尚未同步。提交包使用既有 PPO `policy_weights.npz`，并在 `main.py` 默认启用经筛选的动物产品出售 residual；这不是一套重新导出的全新 PPO 权重。V1/V2/V3/V4/V5 保留不变，当前候选作为独立 challenger 观察，须重新累计 80 场线上窗口。

### `v6_ppo_v3_moe_router`

- 状态：PPO v3 已从零实现为 D1/D2/Router/D3 流水线；尚未构建或上传 Kaggle 包。
- D1：首轮 100 seed、6,400 场拒绝 `E_HIGH` 与三个整季残差（相对 V1 的胜分 CI 均为负）。经因果审计定义的 `M_ANIMAL_HALF_TOPDAYS`（仅第 10/17/24 天）在 100 seed、1,600 场中相对 V1 `+9.75pp`，95% CI `[+7.13,+12.50]pp`，平均金币边际 `+356`，零编译器回退，获得 D2 准入。
- D2：首次 2,174 状态通用日采样因漏掉第 17/24 天而产生零有效动作，被 coverage gate 正确拒绝并保留。修正后 2,304 个唯一同状态反事实，split 为 train/validation/test=`1826/250/228`，有效 TOPDAYS 干预 1,312 条（正/负 uplift=`184/137`），全部覆盖、指纹和 split 门槛通过；数据 SHA256 `40d8f04085702d38aafedd4316a5155b6d42eed1f1b328a4b1085ea8e9960a87`。
- Router：5-member bootstrap ensemble，纯 NumPy 服务。正式独立 D4：1,000 seed 双席位、2,000 场直接对 V1 得分率 `75.45%`，bootstrap CI `[73.65%,77.28%]`，平均金币差 `+95.8`；17 个对手族群平均相对 V1 `+4.66pp`、无族群低于 `-2pp`、`DONE/DONE` 2,000/2,000、推理 P95 小于 5ms。初版评测器发现 ensemble 特征轴和 cleanup 对手 no-op 两处问题，均在独立筛选中修复后重跑，不影响服务端权重。
- D3 PPO pilot：256 场 on-policy 轨迹、4 epoch，KL=`0.0013–0.0019`，未触发早停，JAX/NumPy parity `2.38e-7`。100 seed 独立筛选对 V1 为 `80.0%`，CI `[74.5%,85.0%]`，对手池相对 V1 `+4.78pp`、零安全回归；但仅为 256 场 pilot，未完成 PPO 对冻结 Router 的完整独立 D4/D5，不可作为上线候选或声称 PPO 优于 Router。

## 2026-08-23 V12 金牌冲刺：社区输入、两候选、正式验证与上线

本节是当前权威状态。上文的 Rating、公开局数和“上线/下线”均为历史快照；不得用它们覆盖本节，也不得把不同时间的 Rating 横向当作同周期实验。

### 当前排名与社区输入

- 启动调研快照（08:29 UTC）：`datatuu` 第 581/5952、Rating 2010.0；榜首 Ryo Hasegawa 3124.8。修复包上线后的冻结 CLI 快照（19:40:21 Asia/Taipei）：`datatuu` 第 **2338/5977**、团队 Rating **1022.2**；同一时段榜首 **3134.9**，Top 10 第十名 **2834.8**。名次骤降来自最新两个 Agent 从 600 初始 Rating 重新爬坡，不是 7 场证据证明策略崩溃。完整榜单 CSV 已落盘到 `community_research/2026-08-23/leaderboard/final_live_snapshot/`。
- Kaggle 规则页/CLI 没有给出可核验的“金牌 Rating cutoff”；Top 10 是奖金名次，不等于已确认的金牌线。目标可以是金牌，但任何当前版本都不能提前宣称已达到。
- 原始榜单、`new/active/top` 各三页讨论列表、11 个重点主题全文/评论与复现命令统一保存在 [`community_research/2026-08-23/INDEX.md`](community_research/2026-08-23/INDEX.md)。全程使用 Kaggle CLI/API，没有使用浏览器。

重点社区结论及本轮落地：

| 讨论 | 可检验启发 | 本轮处理 |
| --- | --- | --- |
| [737027](https://www.kaggle.com/competitions/kaggriculture/discussion/737027) 对手库存估计 | 只在公开市场冲击且不确定性可控时改变出售 | 形成 V12B；v1 得分下降，v2 仅微弱 screen 信号，未提交 |
| [736439](https://www.kaggle.com/competitions/kaggriculture/discussion/736439) 六专家循环克制 | 完整专家之间可能非传递，优先完整专家 Router/混合而非单一路线平均分 | 用于 V10/V11 Router、V12C/D；C/D 均被留出反例否决 |
| [734412](https://www.kaggle.com/competitions/kaggriculture/discussion/734412) 商店需求洞 | 商店组合可能影响动物品出售时机 | 初始 V12A 的逐商品 shop gate 产生 W→L；因果消融后改为 A2 删除该门 |
| [736219](https://www.kaggle.com/competitions/kaggriculture/discussion/736219) 榜首实验建议 | 保留 incumbent + 真正异质 challenger；按相同局数观察 60–100 局 | 最终上线 r002 incumbent 与 A2 challenger；线上仍按固定 80 场窗口验收 |
| [734212](https://www.kaggle.com/competitions/kaggriculture/discussion/734212) 单机制迭代 | 每次只改一个可证伪机制并保留失败证据 | A→A2 只删除一个已定位的 shop-product gate；没有采用事后更高分的 no-WOOL 版本 |
| [736567](https://www.kaggle.com/competitions/kaggriculture/discussion/736567)、[736917](https://www.kaggle.com/competitions/kaggriculture/discussion/736917) BC/RL 负面经验 | 同质 BC、长时序低层 PPO 很容易失效 | 不再扩训旧 PPO；本轮使用完整专家、规则/学习 Router 与低频可审计 residual |

### V10/V11 基座与 V12 候选淘汰

- V10 将 2026-08-18/19/20 官方 Episodes Index 的 697/695/698 场整理为 2,090 个唯一 seed，全部 720 步、`DONE/DONE`；按 identity group 拆为 train/validation/test=`1670/210/210`。官方 Replay 只提供真实 seed/日期/provenance，所有评测均由本地真实环境闭环重跑，不把历史对手 tape 当作自适应对手。
- V11 以 V1/V2/V5/V8 四个完整专家、8 个规则变体、规则 Router 和学习 Router 起池。Round 3 使用 100 个新 source、16 模型、120 个无序 pair、双席位共 24,000 场；全部唯一、`DONE/DONE`、零错误。`r002_learned_router_topday_animal_throttle` 排名第 1，直接对 learned Router 为 128/0/72、得分率 64.0%；对 13 个共同对手的配对增量 +3.00pp，95% CI `[+1.63,+4.37]pp`。

| 方案 | Tag | 开发结论 | 决策 |
| --- | --- | --- | --- |
| `v12_incumbent_r002` | 值得保留 | V11 Round 3 冠军原样物化，不重新调参 | 作为 formal 主检验与线上 incumbent |
| `v12a_terminal_branch_guard` | **无价值** | 新 screen 直接亲子 69.44%，共同 +3.968pp，但 `baseline_v8` 最差 −2.778pp；shop-product 条件化造成 WOOL 路径 W→L | 淘汰 |
| `v12a2_no_shop_gate` | 值得保留 | 只删除 shop-product gate；开发两轮 direct=77.78%/75.00%，共同增量 +3.97/+6.35pp，最差均 0 | 进入 formal |
| `v12a2_no_wool_throttle` | **无价值** | 事后看商品级结果后选择，尽管开发分更高，选择偏差不可接受 | 不进入 formal |
| V12B 市场反馈 v1 | **无价值** | 共同得分 −1.1905pp、4 个 W→L；金币略增却更常输 | 淘汰 |
| V12B-v2 领先保护 | 研究资产 | 新 screen 共同 +0.397pp、W→L=0，但唯一翻胜来自 1 个 source，EGG 无覆盖 | 不进入 formal、不提交 |
| `v12c_yarn_complete_router` | **无价值** | 总体共同 +2.78pp，但对 baseline V1 −5.56pp、2 个 W→L；step72 公开特征无法识别风险 | 淘汰 |
| `v12d_static_minimax_mixture` | **无价值** | 三折 LOO 均退化为 learned Router 100%；Round 3 退化为 r002 100%；强制 r002/V8 各半使总体 −3.93pp、worst −7.63pp | 不实现、不提交 |

### frozen_v5 正式验证

- 固定协议使用 100 个未参与上述设计的官方 source，日期分层 34/33/33，split 为 train 94 + validation 6、test 0；23 个预注册 pair × 100 source × 双席位，共 **4,600 场**。
- 完整性为 4,600/4,600 个唯一 task，全部 `DONE/DONE`、零错误；固定顺序要求 r002 主检验全部通过后，才解释 A2 的 confirmatory 结果。

| 候选 | 直接父对战胜/平/负 | 纯胜率 | 得分率（95% CI） | 7 个共同对手得分增量（95% CI） | 最差单对手增量 | 结论 |
| --- | --- | ---: | --- | --- | ---: | --- |
| `v12_incumbent_r002` vs `learned_router` | 125/0/75 | 62.50% | 62.50% `[54.50%,70.50%]` | +4.821pp `[+2.179,+7.393]pp` | −2.00pp | 全门通过，边界 caveat 为 `v8_conservative` 恰好 −2pp |
| `v12a2_no_shop_gate` vs `r002` | 159/2/39 | 79.50% | 80.00% `[74.50%,85.50%]` | +5.786pp `[+4.536,+7.036]pp` | 0pp | 全门通过 |

权威工件：[`audit.json`](v12_validation/runs_v5/formal/audit.json) SHA256 `93319f9800a1f371c2ad7054b56ef602765ef8acbdfce7d92f8307149914cd6c`；[`games.jsonl`](v12_validation/runs_v5/formal/games.jsonl) SHA256 `0d622a3a7154b74ab3e222fadbdd356d917feaf0f8aa84e4bf2bd7e44ad7588e`；run fingerprint `3ccb7c391af0109c79d2041245a962346daacd15a5642017a6111b5cfa8a38ae`。

### 线上 serving 事故、修复与最终提交

首次上传暴露了本地 package QA 没覆盖的 Kaggle raw-loader 语义；失败记录永久保留：

| Submission | 模型 | 线上现象 | 根因 | 状态 |
| ---: | --- | --- | --- | --- |
| `55713093` | A2 旧包 | Validation `97566762` 为 720 states、3000/3000，实际全程 no-op | 文件中最后 callable 是 `model_status`，Kaggle 没有选择 `agent` | 无效，禁止复用旧 SHA `53fda5ec…` |
| `55713101` | r002 旧包 | Validation `97566763` 仅 2 states、双方 `ERROR` | raw exec globals 不含 `__file__` | 无效，禁止复用旧 SHA `453df6ee…` |

根因、Replay 与双方日志见 [`ROOT_CAUSE.md`](v12_raw_loader_redteam/online_failures/ROOT_CAUSE.md)。修复只改变 serving 入口：A2 让 `agent` 成为最后 callable；r002 在缺少 `__file__` 时从 raw-loader 注入的解包路径定位 bundled runtime。策略函数、动作和正式结果没有修改。

正式 formal closure 绑定旧归档字节；修复包没有伪称重新跑过 formal，而是通过真实 raw-loader 与 formal/source factory 的逐动作、逐 reward 等价性继承策略资格。独立红队结论见 [`GO_NO_GO.md`](v12_raw_loader_redteam/GO_NO_GO.md)：两包均在 3 个既有 QA seed × 双席位上完成 720/719、`DONE/DONE`、非 no-op、动作 schema 合法、零 stdout/stderr、无项目源码 import，并逐步完全等价。

| 最终模型 | 修复后 Submission | 当前归档 SHA256 / 大小 | 线上状态（2026-08-23 19:40:21 Asia/Taipei） |
| --- | ---: | --- | --- |
| `v12a2_no_shop_gate` | `55713355` | `e4c8e07fc607ccff3d9592c5774cbd866a11de096a7b12a7c3c642eda76adbf8` / 292,557 B | `COMPLETE`；Validation `97575885` 完整；公开局 4，4/0/0；Rating 1022.2 |
| `v12_incumbent_r002` | `55713359` | `6ff786cbba1a6440f844f9c77da934f6dd10b55e43f57b2bd852753cd21ae136` / 289,074 B | `COMPLETE`；Validation `97575887` 完整；公开局 3，3/0/0；Rating 885.7 |

- 两个修复版 Validation 均为 720 states、`DONE/DONE`、奖励 27,827/27,966，719 条我方日志无 stderr；线上确实执行了真实策略而非 no-op。
- 首批七场公开局为 A2 4/0/0、r002 3/0/0，全部 `DONE/DONE`；我方每场 719 条日志且 stdout/stderr 为空。Replay 和我方日志已保存到 [`../model_data/v12_online_live_2026-08-23/`](../model_data/v12_online_live_2026-08-23/)。这只是 7 场运行证据，不构成胜率结论。
- 2026-08-23 共使用 4/5 次提交额度；最新两个有效槽位为 A2/r002，旧 V1/V2 仍是历史 `COMPLETE` 记录，但不再是最新两席。
- 下一决策固定为等局数观察：每个版本至少 80 场，前 40 场爬坡、后 40 场稳定。未达到门槛前只报告状态、公开局数与 Rating，不因单场输赢调参；达到门槛后再比较稳定期得分率、对手强度和 W/L 转移。金牌目标保留，但当前只有“正式本地增量 + 线上可运行”证据，尚无线上金牌证据。

## 2026-08-24 V13：A2 后续机制搜索与双锚点确认

### 第一性原理与候选冻结

A2 的正式增量来自删除错误的 shop-product 门，但其固定第 10/17/24 天动物品节流仍把不同生产专家视为同一种库存链。本轮只提出可证伪的低频残差，不改变 learned Router、完整生产专家、工人、hands 或安全回退；所有候选在读取新 screen 前固定。

| 候选 | 单一变化 | 事前依据 | Tag / 决策 |
| --- | --- | --- | --- |
| `v13a_a2_no_wool_throttle` | A2 的 V5/V8 分支都取消 WOOL 节流 | 旧消融显示 WOOL 是 A 的主要 W→L 首分歧 | **无价值**：新 screen 对 A2 仅 50.00% |
| `v13c_a2_v8_no_wool_throttle` | 仅 V8 分支取消 WOOL，V5 保持 A2 | 保留 V5 已验证节流收益，修复 V8 的现金/库存链 | **值得保留**：唯一通过 screen 与 confirmatory |
| `v13d_a2_public_winrisk_gate` | 公开金币严格领先时取消 A2 节流 | 避免在领先局为增加方差而继续囤货 | **无价值**：对 r002/A2 仅 38.19%/48.61% |
| `v13b_a2_terminal_clearance_716` | 把末段补单由 step718 提前到716 | 检查节流是否制造终局残货 | **无价值**：18 个末段状态零新增订单，未进入比赛 |

旧 `v12a2_no_wool_throttle` 不是 A2 的真实子代：它仍继承了旧 V12A 的 shop gate，因此本轮没有复用其结果，而是重新实现、重新打包、重新隔离验证。

### 无泄漏双锚点协议

- 官方数据范围为 2026-08-18 至 2026-08-20；只使用 `train/validation`，`test=0`。
- 暴露清单排除 Router-fit、V11 Round 1–3、V12 全部 screen/formal/QA/消融及 V13 既有 QA，共 652 个 source。
- screen 固定 36 个 source（12/12/12），A/C/D 每个均为 `36 × r002/A2 × 双席位 = 144` 场；三名候选完全同周期、同 source。
- 预注册 screen 门：对 A2 得分率 ≥53%、对 r002 ≥55%、A2 最差日期与最差席位均 ≥45%；固定排序只在全部门通过者中选唯一 finalist。
- confirmatory 固定另 100 个 source（34/33/33，train/validation=88/12），与 screen 和全部暴露 source 互斥；唯一 finalist 只允许运行一次 400 场。
- confirmatory 门：对两个锚点得分率与按日期分层、source-cluster bootstrap 95% CI 下界都严格高于 50%；所有任务 `DONE/DONE`、零错误，A2 最差日期/席位 ≥45%。
- 红队在开赛前实际构造 144 行伪造任务与矛盾 reward；旧审计器会错误接受，修复后 resume/audit 均在第 1 行拒绝。最终协议重新 seal 后才启动真实比赛。

### screen 结果

| 候选 | 对 r002 W/T/L | r002 得分率 / margin | 对 A2 W/T/L | A2 得分率 / margin | 结论 |
| --- | ---: | ---: | ---: | ---: | --- |
| A：全分支去 WOOL | 53/0/19 | 73.61% / +85.60 | 27/18/27 | 50.00% / +25.06 | A2 点门失败 |
| C：仅 V8 去 WOOL | 53/0/19 | 73.61% / +94.68 | 27/26/19 | 55.56% / +34.06 | 唯一全门通过 |
| D：公开领先保护 | 27/1/44 | 38.19% / −129.50 | 15/40/17 | 48.61% / −17.58 | 双锚点失败 |

432/432 行均为 exact task，全部 719 次调用、`DONE/DONE`、零错误、零 fallback；独立红队从原始行重算与落盘审计完全一致。C 对 A2 的 screen 纯胜率为 37.50%，55.56% 是含 26 场平局的 Kaggle 得分率，只用于获得 confirmatory 入场资格。

### C 的 100-source confirmatory

| 对手 | 胜/平/负 | 纯胜率（95% CI） | Kaggle 得分率（95% CI） | 平均 margin（95% CI） |
| --- | ---: | ---: | ---: | ---: |
| `v12_incumbent_r002` | 155/0/45 | 77.50% `[71.50%,83.00%]` | 77.50% `[71.50%,83.50%]` | +97.72 `[+81.30,+114.50]` |
| `v12a2_no_shop_gate` | 95/55/50 | 47.50% `[40.00%,55.50%]` | 61.25% `[56.00%,66.50%]` | +33.735 `[+20.75,+48.235]` |

- 对 A2 三天得分率为 61.03% / 56.06% / 66.67%，三天 margin 均为正；两个候选席位得分率为 66.50% / 56.00%。
- 400/400 任务闭合，100 source × 2 anchor × 2 seat；全部 `DONE/DONE`、719 calls，零错误、零 residual fallback。
- 所有预注册 gate 为 true。独立红队绕开既有统计函数，从 400 行原始数据重做 10,000 次 bootstrap，逐值复现。
- 严格结论：C 已按 Kaggle 对局得分口径显著优于 A2 与 r002；由于对 A2 有 55 场平局，不得写成“纯胜率显著超过 50%”。该结论仍只覆盖两个预注册锚点，不等于已经证明对当前完整线上 meta 或金牌分段泛化。

### 工件与提交状态

- 完整报告：[`v13_dual_anchor_search/FINAL_VALIDATION.md`](v13_dual_anchor_search/FINAL_VALIDATION.md)。
- 协议 seal SHA256：`010e63413f67a90203c0b153ce46fe79d3a0be7d880ec19bd9ce9300cee63613`。
- finalist seal SHA256：`192002b85d645eee2875d7994e4497208bcce5a04e289fd4477f37308a53f742`。
- confirmatory `games.jsonl` SHA256：`7a17d2effe873d8258c7e58e5e53b8250111b46c73ef10f3a3185c75893af36c`；`audit.json` SHA256：`9aae4c0d87fcd76e991e25061bde13cba8cadf076229f2ea8b6be3fdd7b081e8`。
- 独立复算报告：[`POST_CONFIRM_REDTEAM.md`](v13_dual_anchor_search/POST_CONFIRM_REDTEAM.md)，SHA256 `9a413e581b35854d308b8f85cd9444fbe6348d7b22985f4241868e3f10962c60`；它不调用既有审计器统计函数。
- C 提交归档：`v13c_a2_v8_no_wool_throttle/submission.tar.gz`，293,034 bytes，SHA256 `ef279bbc937c73027ce17293aba19eeaa419563d2093880487ec9849400af0c1`。
- 归档已通过真实 Kaggle raw-loader、干净解包、双席位、720 states / 719 calls、动作 schema、非 no-op、零 stderr/fallback 与逐动作等价 QA。
- 2026-08-24（Asia/Taipei）经用户授权提交：Submission `55719781`，描述 `v13C: A2 + V8-only no-WOOL throttle; dual-anchor confirmed`，状态 `COMPLETE`，初始 Rating 600.0。
- Validation Episode `97749443` 为 720 states、双席位 `DONE/DONE`、奖励 27922/28061；双方各 719 条动作与日志，动作键固定为 `farmer/hands/market`，stdout/stderr 均为空。Replay 与日志保存于 [`../model_data/v13c_online_validation_2026-08-24/`](../model_data/v13c_online_validation_2026-08-24/)。
- 提交后最新两席为 r002 + V13C，A2 转为历史 `COMPLETE` 记录。V13C 仍需按 80 场（40 爬坡 + 40 稳定）口径验收，初始 600.0 不是强度结论。

## 2026-08-24 V14：第一性原理队列 best-response 全链路

本节是 V14 的当前权威记录。核心指标一律采用**纯胜率 `wins / all games`**：平局保留在分母且不算胜；Kaggle 得分率单列，不能替代“对 A2 纯胜率至少 65%”的提交硬门。oracle、已暴露开发集、fresh screen、fresh confirmatory 和线上状态是五个不同证据层，不得相互冒充。

### 证据层级与社区输入

| 层级 | 用途 | 能否支持提交 |
| --- | --- | --- |
| 社区/引擎事实 | 生成可证伪机制 | 否 |
| perfect-information oracle（已暴露） | 判断机制上限；允许读取现实 agent 不可见真值 | 否 |
| exposed development | 消融、工程调试和唯一 finalist 选择 | 否 |
| fresh screen | 36 个新 source 的晋级门 | 只能进入 confirmatory |
| fresh confirmatory | 另 100 个新 source、一次性消费的最终本地门 | 是；仍不等于线上或金牌证明 |
| Kaggle online | 实际匹配池、serving 与 Rating | Validation 已通过；当前 0 场公开对局，尚无稳定 V14 Rating 结论 |

社区复核统一见 [`community_frontier.md`](v14_first_principles_search/community_frontier.md)，SHA256 `35fa152779db4ce850b00ca3cc6c2593a05c39d71ae71e6bc3365fe99350d0ee`。本轮没有复制论坛模型，而是把四类线索改写成引擎内可验证机制：

- 737128 的 MELON 树是原策略条件下的观测预测，不能回答“改变订单后会怎样”，因此不直接移植；
- 737027 支持对手供给的可识别区间，但价格地板、DROP、overflow 时不能伪装成精确库存；
- 736439 的非传递专家结果支持条件 payoff / best response，不支持静态混合；
- 734412 与官方 1.32.7 引擎共同确认，市场库存、确定需求钟和 SELL slot 顺序是双方最直接的交互通道。

第一性原理结论是：A2 的生产与 Router 基座已经较强，最小可控增量不是重写生产，也不是再做全局出售倍率，而是**在不改变出售总量的前提下，利用对手同回合 SELL 队列对共享价格曲线的冲击，重排我方既有 SELL slot，最大化本回合相对收入**。

### 实现边界与 fail-closed 设计

最终 Q2b 继承完整 A2，并从已知零私有初态运行 opposite-seat A2 shadow；每步用官方 1.32.7 的单位、市场、城镇需求、衰减与日界转移推进对手私有状态。下一 observation 同时核对双方 money、完整 market inventory 与非日界公开农场，任何不一致都会永久回退 A2。

候选只允许重排父策略已有的**全 SELL**订单：商品数量、farmer、hands、槽数和生产专家均不改变；V8/V8、step≥72、clone distance≤4、same-turn transfer、流动性和“我方模拟收入不得下降”等门继续保留。Q2b 名称中的 `no_mirror` 只表示删除冗余的“双方完整 public-production 必须逐字相等”条件，**不表示删除 clone cap 或身份核验**。

exact-A2 shadow QA 在 3 个已暴露 seed × 双席位的 4,314 次决策上，private state、预测动作、174 次日界全部与真实 A2 一致；共 76 次重排，0 fault / update error。这个结论只覆盖绑定的 A2，不证明任意未知线上对手身份可识别；未知对手仍依靠下一步 conformance 失败后回退。

### Oracle 与已暴露开发链路

Oracle 只证明“队列排序是否足以跨过 65%”，不具备部署资格：

| Oracle | 对手 | 局数 | W/T/L | 纯胜率 | 得分率 | 平均 margin | 决策 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| V13C parent perfect-info queue | A2 | 200 | 151/20/29 | 75.50% | 80.50% | +822.565 | 机制上限足够；现实不可见真值，不能部署 |
| A2 parent perfect-info queue | A2 | 72 | 52/10/10 | 72.22% | 79.17% | +672.31 | 证明无需依赖 V13C parent 也可过门 |

Oracle 报告见 [`ORACLE_CEILING_REPORT.md`](v14_first_principles_search/oracle/ORACLE_CEILING_REPORT.md)，SHA256 `f1c2334c4fa24ce08d7f36a60275a5251818d5bd7d520aa5b37e041f1e613c2f`；oracle-gap 单变量归因见 [`ORACLE_GAP_REPORT.md`](v14_first_principles_search/oracle_gap/ORACLE_GAP_REPORT.md)，SHA256 `738d1a71c7756eaadb86508588dd839dd57b2402b336e1f747d1ffbfb3f54310`。

所有下列结果均来自已经暴露的 V13 screen36，只能用于机制选择：

| 候选 | 对 r002 W/T/L / 纯胜率 | 对 A2 W/T/L / 纯胜率 | Tag | 决策依据 |
| --- | --- | --- | --- | --- |
| S0 hour23 fertilizer | smoke 8 局、触发 0 次 | smoke 8 局、触发 0 次 | **无价值** | 静态机制成立但真实路线无覆盖；停止完整 screen |
| S1 WHEAT squeeze | 53/0/19 / 73.61% | 45/12/15 / 62.50% | 未达门（研究资产） | 交易闭环有效，但 A2 纯胜率不足 65% |
| Q1 stateful shadow + public equality | 53/0/19 / 73.61% | 47/10/15 / 65.28% | 研究资产 | 已暴露点估计过线，但不是 fresh 证据，且被 Q2b 支配 |
| QS1 / Q1+S1 | 53/0/19 / 73.61% | 47/10/15 / 65.28% | **无价值** | 相对 Q1 没有增加任何胜场；只提高平均 margin |
| Q2b no-public-equality | 55/0/17 / 76.39% | 52/10/10 / 72.22% | **有价值** | 单变量删除错误代理门，达到 causal-oracle 的 W/T/L 上限，晋级冻结 |

S0/S1 的静态闭环、覆盖与 144 场结果见 [`alternatives/DECISION.md`](v14_first_principles_search/alternatives/DECISION.md)，SHA256 `dcad8b15351fd46676bec924d9a0a83f753af823cc8d6f71d853a8a2f38903c0`；完整候选演进见 [`decision_log.md`](v14_first_principles_search/decision_log.md)，SHA256 `60622a87007d1524ca47be58213c930ee216f91bede8f9c6ad927644211e7667`。oracle-gap 逐任务追踪显示 Q1 漏掉的 85/85 个可利用机会都只被 exact public equality 阻断；clone distance、step、V8/V8、strict SELL、own-revenue 与同回合转移门均不是漏点根因，因此 Q2b 没有连带放宽这些安全条件。

### Fresh screen：只决定是否进入 confirmatory

正式协议先登记 788 个已暴露 source；fresh screen 固定 36 source（18–20 日各 12），fresh confirm 固定另 100 source（34/33/33），两者彼此、与 exposure、与 test 的交集均为 0。候选归档和 panel 在开赛前封存；screen 为 `36 source × 2 anchor × 双席位 = 144` 场。

| 对手 | W/T/L | 纯胜率（独立 95% CI） | 得分率 | 平均 margin | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| `v12_incumbent_r002` | 61/0/11 | 84.72% `[75.00%,93.06%]` | 84.72% | +260.97 | `>50%`，通过 |
| `v12a2_no_shop_gate`（A2） | 59/8/5 | 81.94% `[70.83%,93.06%]` | 87.50% | +789.32 | `>=65%`，通过 |

144/144 任务唯一且完整，全部 `DONE/DONE`、零错误。独立复算见 [`screen independent_audit.md`](v14_first_principles_search/validation/runs/screen/v14_queue_stateful_no_mirror/independent_audit.md)，SHA256 `91fbf5b8ec91f2bbc29ed42d663bd2d090aec70d220833e82b316fb19dd9f733`；原始 [`games.jsonl`](v14_first_principles_search/validation/runs/screen/v14_queue_stateful_no_mirror/games.jsonl) SHA256 `100ec0b80af0f435a3f654c5b23ff0326eebb209c5116ebe247c16a12f00e65b`。

### Fresh confirmatory：最终本地硬门

唯一 finalist 一次性消费 100 个全新 source，执行 `100 × 2 anchor × 双席位 = 400` 场：

| 对手 | W/T/L | 纯胜率（独立 95% CI） | 得分率 | 平均 margin | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| `v12_incumbent_r002` | 156/0/44 | **78.00%** `[72.50%,83.50%]` | 78.00% | +210.08 | `>50%`，通过 |
| `v12a2_no_shop_gate`（A2） | 149/18/33 | **74.50%** `[68.00%,80.50%]` | 79.00% | +715.16 | `>=65%`，通过 |

- A2 的 18 场平局没有计入 149 场胜利；`149/200=74.50%` 是满足用户目标的纯胜率，不是得分率换名。
- 400/400 原始任务、task_id、engine/schema、双席位与 reward/margin 全部闭合，均为 `DONE/DONE`，零运行错误。
- 两个候选席位对 A2 分别为 73/9/18 与 76/9/15；三天分别为 45/12/11、49/6/11、55/0/11，没有靠单一日期或单一席位过门。
- screen 后原审计器的 consume-lock 校验暴露了审计层 bug；恢复脚本只修补审计校验并复用已经完成的原始对局，没有重跑 games，immutable input 前后哈希一致。最终独立审计绕开既有统计函数重新读取 400 行、执行 10,000 次日期分层 source-cluster bootstrap。

独立结论为 `GO_SUBMIT`，见 [`confirm independent_audit.md`](v14_first_principles_search/validation/runs/confirmatory/v14_queue_stateful_no_mirror/independent_audit.md)，SHA256 `ebbfc2487ff738a6471e20f6a3a57937a80cdeca7da1da13644a8beae5ce9d5c`；原始 [`games.jsonl`](v14_first_principles_search/validation/runs/confirmatory/v14_queue_stateful_no_mirror/games.jsonl) SHA256 `3e604b3f601d268f659bc8d6add42eb4b7ec06ae9717f88fe1b78d0cc386d5f9`。

### 冻结包与线上状态

- Panel seal SHA256：`b2297db28b77f9e8f6f94780404c7b8c72ff2bc83235a5ac316d24c1c3ac8aff`；finalist seal SHA256：`030d75bb6e431a4378e0fd8ee07056e7b793e80bb76d5bab803f377e761067ad`。
- 最终提交包：[`v14_queue_best_response/submission.tar.gz`](v14_queue_best_response/submission.tar.gz)，311,699 bytes，SHA256 `d7d2e8210041d695a10ddc7797efbfd5c4ca3a0f8c33c70e0fd5d597fd4d4f9f`。
- Package QA SHA256：`5486afdf762c71087ece7a90f7ebe1a41f975704c8a4ccc07617d7bf2fc36414`；submission manifest SHA256：`bb6ef857ba21a0bc0428b8b0648a66824c8c1febc87726bb16dda8bc12a2b379`。真实 raw-loader、干净解包、双席位 720/719、动作/reward 等价、最后 callable、无 `__file__` 依赖与零 stderr 均已通过。
- 经用户授权提交 Kaggle：Submission `55722630`，归档 SHA256 `d7d2e8210041d695a10ddc7797efbfd5c4ca3a0f8c33c70e0fd5d597fd4d4f9f`。状态已为 **`COMPLETE`**；Validation Episode `97822469` 为 720 states、双席 `DONE/DONE`、719 calls/seat、零 stdout/stderr，reward `[27827,27966]`。当前显示 `600.0` 且公开 Episode 为 0，因此它只是 validation 完成后的初始值，不是稳定线上 Rating；不得用本地 74.50% 推断线上分数。
- 当前 Tag 为 **有价值·已提交**。本地双锚点证明它在冻结的 A2/r002 威胁模型上通过硬门，且线上入口与运行时已验证；但未知线上对手身份和完整 meta 泛化仍未证明，更不能据此宣称已经获得金牌。

## 2026-08-27 V19/V20：Hierarchical MoE 与需求时点出售控制

- V19 继承 V17 安全执行器：YARN 首店保留 YARN 完整专家，其余路线在 step 360 切换到 `Kronki::99108392` 后缀。7 模型族、128 seed、双座位确认相对 V17 为 `+1.79pp`，95% CI `[+0.61,+3.18]pp`，`32/1760/0`；Submission `55819961` 已完成 Validation，公开局由用户监控。
- V20 保留 V19 的生产、购买和出售总量，仅把符合安全条件且同回合随后会被城镇需求消费的商品出售量延后 25% 到下一回合。
- 反过拟合开发门覆盖 5 个近代本地模型；正式确认覆盖 7 个模型、全新 seeds `96000–96127`、双座位，父代/候选各 1,792 场。V20 相对 V19 为 `+6.53pp`，seed-bootstrap 95% CI `[+5.19,+7.92]pp`，平均金币差 `+91.44`、自身金币 `+34.82`，翻转 `220/1556/16`，逐模型 `−2pp` 护栏全部通过。
- 16 次负翻转的父代均为平局；正翻转 220 次，说明收益来自受控打破同类模型对称性。研究/包 8/8 精确一致，官方/C++ 4/4 精确一致，224 场安全审计覆盖 1,495,967 条单位动作且非法数为 0。V20 晋级为**离线金牌候选**，线上成绩仍需独立验证。
- V20 已通过 CLI 提交：Submission `55821249`，时间 `2026-08-27 15:14:33`，初始状态 `PENDING`。同一 CLI 快照中，父代 V19 Submission `55819961` 已为 `COMPLETE`、公开分 `2098.0`；这支持 V19 的线上强度，但 V20 仍需独立累计公开比赛。

## 2026-08-27 V21：Top-Meta step-216 生产专家

- 从排行榜前五 Replay 提取 5 条完整路线并统一套入状态安全执行器。4 条路线在 5 个近代本地模型上退化；完整 `lucaskna::100485613` 虽总体比 V20 高 `+19.38pp`，但对 V13/V16/V19 分别下降 `12.50/12.50/9.38pp`，未直接照搬。
- 固定为层级 MoE：首店 YARN 保留 YARN 专家；非 YARN 路线先走 V20 开局，step 216 切入 lucaskna 生产专家，继续复用 V20 需求延迟出售控制器和状态安全执行器。5 模型时点开发筛选中该方案为 `+18.75pp`、`30/130/0`，而 step 432/504 均为 `-4.38pp`。
- 扩展开发集覆盖 12 个本地模型、seeds `97400–97463`、双座位，父代/候选各 1,536 场：`+9.24pp`，95% CI `[+7.16,+11.26]pp`，`142/1394/0`，12 族无负向退化。
- 独立确认集覆盖 8 个本地模型、全新 seeds `98200–98327`、双座位，父代/候选各 2,048 场：V20 得分率 `71.46%`，V21 `85.67%`；提升 `+14.21pp`，95% CI `[+12.13,+16.33]pp`，平均金币差 `+872.33`、自身金币 `+382.48`，翻转 `293/1755/0`，逐模型护栏全部通过。
- 研究/包 8/8 逐动作与逐奖励一致；官方 Python 1.32.7/C++ 4/4 一致；224 场安全审计覆盖 1,501,217 条单位动作，非法动作、market 超限、hands 错配均为 0。V21 晋级为**离线金牌候选**，真实金牌 Rating 仍需线上公开局验证。
- V21 已通过 CLI 提交：Submission `55821671`，时间 `2026-08-27 15:38:38`，初始状态 `PENDING`。提交快照显示 V20 为 `COMPLETE/1200.1`、V19 为 `COMPLETE/2305.5`；线上 Rating 会继续变化，但该反差足以触发下一层对 V20 需求延迟控制器的直接消融，V21 当前只标记为过程诊断版。
- 增量 Episode 审计显示 V20 初始 7 场公开局为 `7/0/0`，平均自身金币约 `99,977`；`1314.6` 左右的低 Rating 属于低分对手池中的早期 ELO 爬坡，不是 7 场连败。V21 同期只有 1 场 Validation、公开局为 0。

## 2026-08-27 V22：移除需求延迟控制器消融

- 固定 V21 的 YARN/非 YARN Router、step-216 lucaskna 生产专家和状态安全执行器，仅移除 `demand_delay_25`。
- 12 个本地模型、seeds `98400–98431`、双座位的 768 个配对单元中，V22 相对 V21 为 `-1.43pp`，翻转 `0/751/17`，平均金币差 `-45.51`、自身金币 `-16.57`，逐模型护栏失败；相对 V19 虽仍有 `+10.16pp`，但弱于 V21 的 `+11.59pp`。
- 结论：`REJECT_KEEP_LOCAL_PACKAGE`。V22 保留自包含可提交包与证据，不上线，不列为金牌候选。

## 2026-08-27 V23：需求延迟比例搜索

- 冻结 V21 Router、生产专家与安全执行器，只比较 `0/12.5/25/37.5/50%` 一个自由度。12 模型、seeds `98600–98615`、双座位，每个比例 384 场。
- 12.5/25/37.5% 的胜负完全一致；37.5% 相对 25% 仅平均自身金币 `+6.62`、margin `+2.99`，新增胜局为 0。0% 为 `-1.82pp`、50% 为 `-0.78pp`，均出现负向翻转并触发护栏失败。
- 结论：`REJECT_NO_WIN_UPLIFT_KEEP_LOCAL_PACKAGE`。保存 37.5% 自包含过程包，V24 父代继续使用 25%。

## 2026-08-27 V24：首商店定向 Crop 专家

- 8 条 Crop Dusta 首商店代表路线分别只替换对应商店分支，其余分支保持 V21；5 个近代本地模型、seeds `98800–98831`、双座位，每候选 320 场。
- 8 条路线在目标商店子集全部下降 `67–100pp`，总体下降 `6.88–13.13pp`，没有任何正向翻转。代表性最小损失 `crop_yarn` 仍为 `0/298/22`，目标 YARN 子集 `-78.57pp`。
- 根因是 step-216 前生产资产状态不兼容；状态安全执行器只能阻止非法动作，不能补齐路线所需资产。结论：全淘汰，保存 `crop_yarn` 自包含代表性失败包；V25 只允许前缀兼容路线进入筛选。

## 2026-08-28 V25：前缀兼容路线挖掘

- 扫描 959 份前五 Replay、909 个有效前五视角，按“前 216 步至少 175 步匹配 V21，后 503 步至少 120 步不同于 lucaskna”筛得 131 条路线。
- 7 条 Milan 首商店代表路线前 72 步均为 `72/72` 完全一致，前 216 步为 `208/216`；5 模型、seeds `99000–99031`、双座位的 step-216 定向筛选仍全部退化，总体 `-1.25pp` 至 `-5.00pp`，目标商店子集 `-11.76pp` 至 `-33.33pp`。
- 保存最小损失 `Milan Leonard::99922362` smoothie 代表包。结论：step-216 仍太晚；V26 将利用 `72/72` 的精确公共前缀在首商店揭示时立即切换。

## 2026-08-28 V26：精确前缀 step-72 Milan Router

- 7 条 Milan 路线均与 V21 前 72 步 `72/72` 完全一致，在首商店首次公开时定向切换；5 模型、seeds `99400–99431`、双座位，每候选 320 场。
- 7 个目标分支仍全部退化，目标商店子集下降 `30–59.09pp`，逐模型护栏全部失败；总体最小损失 PET 分支为 `-0.625pp`，但仅 4 个影响单元且其中 2 个负翻转。
- 结论：相同请求动作前缀不等于同一隐藏状态演化。保存 PET 代表包；V27 生产专家必须来自 lucaskna 同一策略谱系，而不是仅依赖跨团队动作相似度。

## 2026-08-28 V27：同源 lucaskna 商店专家

- 仅筛选 lucaskna 自身的 Smoothie、Ice Cream、Bakery、Pizza、Brunch 路线；5 模型、seeds `99600–99663`、双座位，每候选 640 场。
- Smoothie 专家 `lucaskna::100501596` 唯一通过：总体 `+0.3125pp`，目标子集 `+4.17pp`，翻转 `2/638/0`，目标子集平均 margin `+89.90`、自身金币 `+55.00`，逐模型护栏通过。Pizza 完全不改变胜负；其余三条退化。
- V27 保存自包含可提交包并晋级 V28 广谱面板；因有效正翻转仅 2 个，当前不是金牌候选，也不提交。

## 2026-08-28 V28：Smoothie 广谱面板

- 12 模型、冻结 seeds `101000–101127`、双座位，父代与候选各 3,072 场；候选相对 V21 为 `+0.1302pp`，95% CI `[0,+0.3255]pp`，翻转 `4/3068/0`。
- 471 个 Smoothie 影响单元为 `+0.8493pp`，逐模型护栏通过，但 4 个正翻转全部集中在 V17 对手族；总体 CI 下界等于 0，主门失败。
- 结论：`REJECT_CI_TOUCHES_ZERO_KEEP_LOCAL_PACKAGE`。保存可提交过程包，V29 冠军赛回到 V21 父代，不叠加该微专家。

## 2026-08-28 V29：四臂冠军选择

- 12 模型、冻结 seeds `103000–103063`、双座位，V19/V20/V21/V27 每个模式 1,536 场。
- V21 相对 V19 为 `+14.06pp`，95% CI `[+11.72,+16.67]pp`，翻转 `271/1265/0`；相对 V20 为 `+9.57pp`，CI `[+7.03,+12.37]pp`，`147/1389/0`，逐模型护栏全部通过。
- V27 相对 V21 为 `0pp`、`0/1536/0`，仅平均自身金币 `+3.74`。按“统计同档选择更简单模型”，V21 胜出并封装为 V29 离线金牌候选包，进入 V30 独立确认。
## V30 — Offline-Gold Hierarchical MoE RC1

- 冻结 V21 策略，使用全新 `104000–104127` 种子、8 类本地对手、双座位独立确认；V19/V20/V21 各 2,048 局，总计 6,144 局。
- V21 得分率 `83.45%`；相对 V19 `+19.19pp`（95% CI `[+17.04,+21.29]pp`），相对 V20 `+14.40pp`（`[+12.26,+16.50]pp`），逐族群 `-2pp` 护栏均通过。
- 决策：`OFFLINE_GOLD_LEVEL_QA_PASS`。研究/提交包 8/8 完全一致，官方/C++ 4/4 一致，224 局动作安全审计零违规；包已就绪但不自动提交。

## 2026-08-28 V22–V29 统一复赛：首次同面板详细测评

- 更正此前证据边界：V22–V27 只有分散筛选，V28/V29 虽有较宽面板，但 V22–V29 从未在同一批对手、种子和座位上做过可配对的完整比较。本轮是首次统一详细测评。
- 固定候选 V22–V29、对手 V17–V21、全新 seeds `106000–106127`、双座位；每个候选/对手 256 场，每候选 1,280 场，总计 10,240 场，零运行错误。
- 总体得分率：V22 `64.84%`、V23 `69.92%`、V24 `68.20%`、V25 `69.30%`、V26 `66.95%`、V27/V28 `74.84%`、V29 `75.23%`。
- V22–V26 相对 V29 配对得分率均显著下降 `5.31–10.39pp`。V27/V28 相对 V29 为 `-0.39pp`，95% CI `[-1.09,+0.31]pp`，没有可确认增益；两者对 V21 得分率均为 `47.66%`。
- V24 平均金币差 `-6,913.31`，且 1,280 场中有 120 场金币差低于 `-10,000`，属于被聚合胜率掩盖的高尾部风险方案。
- V29 得分率 `75.23%`、seed-cluster 95% CI `[72.11%,78.13%]`，逐对手最低为对 V21 的 `50%`；但源码审计确认 V29 只是 V21 加版本字符串，不能算新策略。
- 决策：V22–V29 中没有新的真正金牌策略；V21/V29 仅保留为当前本地强基线，V22–V28 均不晋级、不提交。完整证据见 [`v29_champion_selection/v22_v29_rematch_20260828/REPORT.md`](v29_champion_selection/v22_v29_rematch_20260828/REPORT.md)。

## 2026-08-28 V31：V21 镜像影子 SELL 队列最优响应

- 父代 V21；冻结机制只在 V21 对手影子连续 216 步逐字段一致后，重排父代已有 SELL 顺序，不改变生产、购买、出售商品和数量。
- 机制烟测固定 seeds `31001/31002`、双座位，共 4 场 V31 对 V21；每场影子最终连续符合 718 步，零 shadow fault、零更新错误。
- 4 场安全重排总数为 0，候选与父代逐局金币差均为 0。严格影子门在其他策略上会回退，因此该机制没有真实动作覆盖。
- 决策：`REJECT_MECHANISM_INERT_WITHOUT_CONSUMING_DEVELOPMENT`。不消费官方 Replay Development/Confirmation，不加入 `golden_model.md`，不提交 Kaggle；保留自包含可提交包和完整失败证据。

## 2026-08-28 V32：同质对手三步 premium 出售前移

- 父代 V21；唯一机制是把 `_clone_distance<=6` 时的 premium 计划出售前看窗口从 1 步扩成固定 3 步，按未来回合逐商品偿还；生产 Router、V20 需求延迟与安全执行器保持不变。[VERIFY: v32_clone_horizon_preempt/main.py:188] [VERIFY: v32_clone_horizon_preempt/main.py:237]
- 机制烟测覆盖 V19/V20/V21、8 seeds、双座位，候选/父代共 96 场：相对父代 `+12.5pp`，翻转 `9/39/0`，平均 margin `+843.81`，触发 1,606 次前移。
- Development 使用 64 个未暴露官方 source，候选/父代对三条金牌谱系共 768 场：PGU `+18.49pp`，95% CI `[+17.19,+19.79]pp`，逐谱系 `+3.13/+6.25/+46.09pp`，`114/270/0`，零错误。
- 单次 Confirmation 使用另 256 个官方 source，共 3,072 场：PoolScore 96.35%，PGU `+18.03pp`，95% CI `[+17.06,+19.01]pp`，逐谱系候选得分率 96.68%/96.48%/95.90%，翻转 `456/1080/0`；灾难失败率与 CVaR10 均改善。
- 研究/解包版 16/16 场逐动作、逐奖励一致；官方 Python 1.32.7 对 16 source、候选/父代、三条谱系、双座位复算 192 场，全部精确一致、`DONE/DONE`、719 calls、零错误。
- 决策：`PROMOTE_LOCAL_GOLD`。加入 `golden_model.md`，成为 V33 父代和活动门控；本轮 8 个新金牌目标已完成 1 个，未自动提交 Kaggle。

## 2026-08-28 V33：无需求间隙第 4 步 premium 前移

- 父代 V32；完整保留 horizon 1–3，只在 horizon 4 前没有该商品已知需求且不跨未知商店解锁时提前出售，并按原 future step/item 偿还。[VERIFY: v33_demand_gap_horizon4/main.py:237] [VERIFY: v33_demand_gap_horizon4/main.py:272]
- 机制烟测对 4 个金牌门、8 seeds、双座位共 128 场：`+9.375pp`，`11/53/0`，horizon-4 触发 200 次。
- Development 为 64 个新官方 source、1,024 场：PGU `+6.25pp`，95% CI `[+5.66,+6.84]pp`，`63/449/0`，零错误。
- 单次 Confirmation 为另 256 source、4,096 场：PoolScore 90.53%，PGU `+5.62pp`，95% CI `[+4.93,+6.25]pp`，`223/1825/0`；对 V19/V20/V21 胜负不变，对 V32 提升 `+22.46pp`，直接父代 CI 下界 69.73%。
- 包内外 16/16 场逐动作一致；官方 Python 1.32.7 对 16 source、候选/父代、4 个门、双座位复算 256 场，全部精确一致、零错误。
- 决策：`PROMOTE_LOCAL_GOLD`。本轮已完成 2/8，V34 父代改为 V33，未自动提交 Kaggle。

## 2026-08-29 V34：需求边界前动态 premium 前移

- 父代 V33；完整保留 horizon 1–4，只把同一无需求安全条件推广到下一个已知需求/未知商店解锁边界，最长 23 步，不在 Replay 上搜索窗口。
- 机制烟测对 5 个金牌门、8 seeds、双座位共 160 场：`+3.75pp`，`5/75/0`，horizon>=5 触发 592 次。
- Development 为 64 个新官方 source、1,280 场：PGU `+5.70pp`，95% CI `[+4.92,+6.48]pp`，`65/575/0`，零错误。
- 单次 Confirmation 为另 256 source、5,120 场：PoolScore 87.30%，PGU `+5.20pp`，95% CI `[+4.57,+5.82]pp`，`234/2326/0`；直接父代得分率 73.83%，CI 下界 71.29%，灾难率不变、CVaR10 改善。
- 包内外 16/16 场逐动作一致；官方 Python 1.32.7 复算 320/320 场完全一致、零错误。
- 决策：`PROMOTE_LOCAL_GOLD`。本轮已完成 3/8，V35 父代改为 V34，未自动提交 Kaggle。

## 2026-08-29 V35：全商品需求边界前置

- 父代 V34；保留 premium 前置优先级，只在剩余订单槽内将相同需求边界机制推广到其余 5 种可售商品。
- 当前状态：`BUILDING / FROZEN_BEFORE_MECHANISM_SMOKE`。
- 预注册：内部烟测 192 场；通过后 Development 1,536 场、Confirmation 6,144 场；不按 Replay 结果筛选商品。
- 烟测结果：非 premium 前置 117,168 单位，但相对 V34 `-58.33pp`，`6/25/65`，平均 margin `-4607.82`。
- 决策：`REJECT_MECHANISM_SMOKE`。未消费官方 Replay；保存 SHA256 `3aca98f367d26f026ce1ba662c8ae6e5abaa78f8fbbed07fc1e74e48239b3ee7` 的可提交失败包。

## 2026-08-29 V36：前置出售价格地板上限

- 父代 V34；只限制前置数量不越过官方 1 金币价格地板，避免没有共享市场外部性收益的提前卖出。
- 当前状态：`BUILDING / FROZEN_BEFORE_MECHANISM_SMOKE`。
- 预注册：内部烟测 192 场；通过后 Development 1,536 场、Confirmation 6,144 场。
- 烟测结果：价格地板上限触发 911 次，配对增益 `0pp`，`4/90/2`，违反零负翻转门。
- 决策：`REJECT_MECHANISM_SMOKE`。未消费官方 Replay；保存 SHA256 `9631b5fef986dff641991a7be71f8217a8956be46d057520f7c2a332fa4bc9ad` 的可提交失败包。

## 2026-08-29 V37：终局清仓前需求边界前置

- 父代 V34；只开放原固定 stop=680 到终局清仓 step=716 之间的安全区，且所有偿还必须在 716 前完成。
- 当前状态：`BUILDING / FROZEN_BEFORE_MECHANISM_SMOKE`。
- 预注册：烟测 192 场；通过后 Development 1,536 场、Confirmation 6,144 场。
- 烟测：192 场，late event 192 次，PGU `+10.42pp`，`20/76/0`。
- Development：64 个新 source、1,536 场，PGU `+10.03pp`，95% CI `[+8.72,+11.20]pp`，零错误。
- Confirmation：另 256 source、6,144 场，PoolScore 92.61%，PGU `+10.87pp`，95% CI `[+9.77,+11.98]pp`，`617/2435/20`；直接 V34 得分率 83.79%，CI 下界 80.86%，尾部护栏通过。
- 包内外 16/16；官方 Python 384/384 一致。决策：`PROMOTE_LOCAL_GOLD`，本轮 4/8，V38 父代改为 V37。

## 2026-08-29 V38：Router 后需求边界前置

- 父代 V37；只把固定 start=120 提前到首商店与 Router 已公开完成的 step 72。
- 当前状态：`BUILDING / FROZEN_BEFORE_MECHANISM_SMOKE`。
- 预注册：烟测 224 场；通过后 Development 1,792 场、Confirmation 7,168 场。
- V46 Development：1,792 场 PGU `+5.64pp`，95% CI `[+4.85,+6.42]pp`，`89/807/0`。
- V46 Confirmation：7,168 场 PoolScore 90.79%，PGU `+5.36pp`，95% CI `[+4.88,+5.86]pp`，`356/3228/0`；直接 V37 82.81%，CI 下界 80.27%。
- package 16/16、官方 448/448 一致。决策：`PROMOTE_LOCAL_GOLD`，当前 5/15，V47 父代改为 V46。

## 2026-08-29 V47：终局清仓抢跑到 step 714

- 父代 V46；仅将完整终局库存前置从 715 移到没有中间需求的 714。
- 当前状态：`BUILDING / FROZEN_BEFORE_MECHANISM_SMOKE`。
- 预注册：烟测 256 场；通过后 Development 2,048 场、Confirmation 8,192 场。
- V49 Development：PGU `+0.684pp`，95% CI `[+0.488,+0.879]pp`。
- V49 Confirmation：PGU `+0.684pp`，95% CI `[+0.439,+0.952]pp`，低于 +1pp；决策 `REJECT_CONFIRMATION`。

## 2026-08-29 V50：终局 carried goods 同回合变现

- 父代 V46；step 715 仅对仓库入口且当前 PASS 的 actor，把价值最高的携带商品 PLACE 并同回合 SELL。
- 机制烟测 256 场：`terminal_units=0`，PGU `0.00pp`，`0/128/0`，零错误。
- 轨迹审计：step 715 仓库入口 carried actor 全部已执行 DROP，V46 projected shed 已覆盖；不存在入口且 PASS 的目标 actor。
- 决策：`REJECT_MECHANISM_INERT`；未消费 Replay，不进入 Development/Confirmation。

## 2026-08-29 V51：终局同回合入仓补卖

- 父代 V46；step 716–718 在安全执行器完成后，以 projected shed 减去既有 SELL，为当回合 DROP/PLACE 的新增库存补卖。
- 烟测 256 场：补卖 3,744 单位，PGU `+6.25pp`，`15/113/0`，通过。
- Development 2,048 场：PoolScore 94.63%，PGU `+5.81pp`，95% CI `[+5.57,+6.10]pp`，`111/913/0`，零错误，强度门通过。
- Confirmation 8,192 场：PoolScore 93.09%，PGU `+6.14pp`，95% CI `[+5.59,+6.71]pp`，`426/3670/0`；直接 V46 得分率 85.74%。
- package 16/16、官方 512/512 一致，零错误；决策 `PROMOTE_LOCAL_GOLD`，当前 6/15，V52 父代改为 V51。

## 2026-08-29 V52：终局携货路线加速

- 父代 V51；只把 step 714 距仓库 1 格且携货的 `COLLECT_FERTILIZER` actor 提前送入仓库，step 715 DROP+SELL。
- 烟测 288 场：机制触发 108 次、1,296 单位，PGU `+2.78pp`，`8/136/0`。
- Development 2,304 场：PoolScore 93.66%，PGU `+3.69pp`，95% CI `[+3.26,+4.12]pp`，`87/1063/2`，零错误。
- Confirmation 9,216 场：PoolScore 90.07%，PGU `+2.70pp`，95% CI `[+2.34,+3.06]pp`，`268/4320/20`；直接 V51 得分率 74.12%。
- package 16/16、官方 576/576 一致，零错误；决策 `PROMOTE_LOCAL_GOLD`，当前 7/15，V53 父代改为 V52。

## 2026-08-29 V53：终局入口立即清货

- 父代 V52；step 716 对仓库入口携货且原计划 `COLLECT_FERTILIZER` 的 actor 改为 DROP+SELL。
- 烟测 320 场：触发 120 次、1,080 单位，PGU `+5.00pp`，`14/146/0`。
- Development 2,560 场：PoolScore 89.22%，PGU `+3.52pp`，95% CI `[+3.05,+3.98]pp`，`85/1195/0`，零错误。
- Confirmation 10,240 场：PoolScore 90.90%，PGU `+3.87pp`，95% CI `[+3.48,+4.27]pp`，`350/4770/0`；直接 V52 得分率 79.10%。
- package 16/16、官方 640/640 一致，零错误；决策 `PROMOTE_LOCAL_GOLD`，当前 8/15，V54 父代改为 V53。

## 2026-08-29 V54：终局无回收浇水旁路

- 父代 V53；step 712 对已携货、距仓库 3–4 格且原计划 WATER 的 actor 改为立即最短返仓，到达即 DROP+SELL。
- 烟测 352 场：触发 176 次、2,288 单位，PGU `+3.98pp`，`14/162/0`。
- Development 2,816 场：PoolScore 90.63%，PGU `+3.91pp`，95% CI `[+3.41,+4.40]pp`，`100/1308/0`，零错误。
- 当前状态：`CONFIRMATION_FROZEN`；预注册 Confirmation 11,264 场。
- 抽样前资源调整：90/date 候选池因 2026-08-21 仅剩 81 个未暴露 source 而未生成 manifest；在未查看任何结果、未写 exposure ledger 前冻结为 70/date，正式 256 source 配额与门槛不变。
- Confirmation 11,264 场：PoolScore 91.29%，PGU `+4.61pp`，95% CI `[+4.23,+4.99]pp`，`455/5177/0`；直接 V53 得分率 83.59%。
- package 16/16、官方 704/704 一致，零错误；决策 `PROMOTE_LOCAL_GOLD`，当前 9/15，V55 父代改为 V54。

## 2026-08-29 V55：并行终局浇水旁路

- 父代 V54；继续接管 V54 处理后剩余的同条件 WATER carriers，并行最短返仓、到达即 DROP+SELL。
- 烟测 384 场：触发 168 次、1,008 单位，但 PGU `-17.71pp`，`0/155/37`。
- 决策：`REJECT_MECHANISM_SMOKE`；剩余 WATER 的产量可被其他 actor 回收，未消费 Replay。

## 2026-08-29 V56：step 712 fertilizer carrier 返仓

- 父代 V54；step 712 对距仓库 4 格、携货且原计划 COLLECT_FERTILIZER 的 actor 改为最短返仓，到达即 DROP+SELL。
- 烟测 384 场：触发 24 次、264 单位，PGU `+2.08pp`，`4/188/0`，通过。
- Development 3,072 场：PoolScore 87.57%，PGU `+0.13pp`，95% CI `[-0.13,+0.39]pp`，`7/1526/3`，零错误；点估计通过 Development，但证据很弱。
- Confirmation 12,288 场：PoolScore 85.11%，PGU `0.00pp`，95% CI `[-0.15,+0.15]pp`，`18/6108/18`；直接 V54 得分率 50.39%。
- 决策：`REJECT_CONFIRMATION`；未过 `+1pp` 与 CI 下界硬门，不做 package/官方引擎 QA。
- 预注册：烟测 384 场；通过后 Development 3,072 场、Confirmation 12,288 场；Replay 日期固定 08-20/08-27。

## 2026-08-29 V57：终局小麦无回报支出清零

- 父代 V54；仅把 step 712 固定 `BUY_PRODUCT WHEAT` 数量置零并保留 slot，避免为终局后无法兑现的 FEED 支付成本。
- 烟测 384 场：触发 192 次、清零 7,296 单位，PGU `+1.04pp`，`8/180/4`，平均 margin `+4.46`。
- 决策：`REJECT_MECHANISM_SMOKE`；4 个负向翻转证明其仍有小麦价格支撑作用，未消费 Replay。
- 预注册：烟测 384 场；通过后 Development 3,072 场、Confirmation 12,288 场；所有硬门不变。

## 2026-08-29 V58：37.5% 需求延迟复验

- 父代 V54；仅把同回合需求后的出售延迟比例从 25% 调为 37.5%，复验 V23 的小额金币优势能否在当前窄 margin 金牌池转为胜局。
- 烟测 384 场：146 场奖励变化，PGU `-5.47pp`，`1/175/16`，平均 margin `-14.72`。
- 决策：`REJECT_MECHANISM_SMOKE`；固定增大延迟导致弱需求状态过度等待，未消费 Replay。
- 预注册：烟测 384 场；通过后 Development 3,072 场、Confirmation 12,288 场。

## 2026-08-29 V59：需求强度自适应延迟

- 父代 V54；需求强度至少 2 时延迟 37.5%，强度为 1 时保留 25%，避免 V58 对弱需求的过度等待。
- 烟测 384 场：192 场奖励变化，PGU `0.00pp`，`6/182/4`，平均 margin `-3.99`。
- 决策：`REJECT_MECHANISM_SMOKE`；需求强度单独不足以决定更高延迟，未消费 Replay。
- 预注册：烟测 384 场；通过后 Development 3,072 场、Confirmation 12,288 场。

## 2026-08-29 V60：premium 强需求自适应延迟

- 父代 V54；只对强需求的 premium 商品提高延迟到 37.5%，非 premium 保持 25%。
- 烟测 384 场：146 场奖励变化，PGU `+1.04pp`，`6/184/2`，平均 margin `-1.73`。
- 决策：`REJECT_MECHANISM_SMOKE`；仍有 2 个负向翻转，未消费 Replay。
- 预注册：烟测 384 场；通过后 Development 3,072 场、Confirmation 12,288 场。

## 2026-08-29 V61：WOOL 强需求延迟

- 父代 V54；只对 WOOL 且需求强度至少 2 的回合提高延迟到 37.5%。
- 烟测 384 场：142 场奖励变化，PGU `-0.52pp`，`3/183/6`，平均 margin `+2.61`。
- 决策：`REJECT_MECHANISM_SMOKE`；均值改善未转化为稳定胜局，未消费 Replay。
- 预注册：烟测 384 场；通过后 Development 3,072 场、Confirmation 12,288 场。

## 2026-08-29 V62：MILK/STRAWBERRY 强需求延迟

- 父代 V54；只对 MILK/STRAWBERRY 且需求强度至少 2 的回合提高延迟到 37.5%。
- 烟测 384 场：120 场奖励变化，PGU `-1.04pp`，`2/184/6`，平均 margin `-4.48`。
- 决策：`REJECT_MECHANISM_SMOKE`；商品限定后仍退化，需求延迟分支停止，未消费 Replay。
- 预注册：烟测 384 场；通过后 Development 3,072 场、Confirmation 12,288 场。

## 2026-08-29 V63：末三日动态溢出变现

- 父代 V54；step 648 后只在强制防溢出时，按公开当前价格重排原安全商品集合，总出售量不变。
- 烟测 384 场：奖励变化 0，`0/192/0`，机制惰性。
- 决策：`REJECT_MECHANISM_INERT`；末三日无可改变的强制溢出选择，未消费 Replay。
- 预注册：烟测 384 场；通过后 Development 3,072 场、Confirmation 12,288 场。

## 2026-08-29 V64：全赛季动态溢出变现

- 父代 V54；在所有 room guard 强制防溢出状态中按公开当前价格重排安全商品，总出售量不变。
- 烟测 384 场：奖励变化 0，`0/192/0`，机制惰性。
- 决策：`REJECT_MECHANISM_INERT`；原首选商品已覆盖全部强制出售量，未消费 Replay。
- 预注册：烟测 384 场；通过后 Development 3,072 场、Confirmation 12,288 场。

## 2026-08-29 V65：异商品 SELL 跨 BUY_PRODUCT 前移

- 父代 V54；clone-like 局面允许 SELL 跨越不同商品的 BUY_PRODUCT，保留同商品屏障与 SELL 相对顺序。
- 烟测 384 场：144 场奖励变化，PGU `-1.04pp`，`2/184/6`，平均 margin `-2.33`。
- 决策：`REJECT_MECHANISM_SMOKE`；出售抢先不足以覆盖延后购买成本，未消费 Replay。
- 预注册：烟测 384 场；通过后 Development 3,072 场、Confirmation 12,288 场。

## 2026-08-29 V66：净 margin 门控的异商品队列交换

- 父代 V54；按官方逐单位报价预测交换后的买卖双方 margin，只在严格正收益时跨越不同商品 BUY_PRODUCT。
- 烟测 384 场：192 场奖励变化，PGU `+3.65pp`，`14/178/0`，平均 margin `+8.10`，通过。
- Development 3,072/3,072 场、零错误：PGU `+2.279pp`，95% CI `[+1.823,+2.734]pp`，`68/1468/0`；12 条金牌谱系最差增益 `0pp`，通过。
- Confirmation 12,288/12,288 场、零错误：PGU `+2.759pp`，95% CI `[+2.523,+2.987]pp`，`332/5812/0`；12 条谱系均非负，直接对 V54 得分 `81.25%`，强度门通过。
- 工程门：提交包 16/16 场逐动作与奖励完全一致；官方 Python 1.32.7 复算 768/768 场奖励精确一致、零错误。
- 决策：`PROMOTE_LOCAL_GOLD`，本轮第 10/15 个新金牌；V66 成为后续冻结父代。
- 预注册：烟测 384 场；通过后 Development 3,072 场、Confirmation 12,288 场。

## 2026-08-29 V67：固定支出槽位上的 BUY_PRODUCT 抢价

- 父代 V66；clone-like 队列仅在现金、容量与官方逐单位买价均证明安全且严格正收益时，将第 2 槽 WHEAT/FERTILIZER 购买跨过第 1 槽固定支出。
- 当前状态：`FROZEN_BEFORE_MECHANISM_SMOKE`；候选包先冻结，再运行 416 场 Smoke。
- 预注册：Smoke 416 场；通过后 Development 3,328 场、Confirmation 13,312 场。
- Smoke 416 场：奖励变化 0，`0/208/0`；决策 `REJECT_MECHANISM_INERT`，未消费 Replay。

## 2026-08-29 V68：近似同构对手的 margin 门控交换

- 父代 V66；只把 V66 队列交换的公开 farm clone distance 从 6 放宽到 12。
- 当前状态：`FROZEN_BEFORE_MECHANISM_SMOKE`；预注册 Smoke 416 场，通过后 Development 3,328 场、Confirmation 13,312 场。
- Smoke 416 场：奖励变化 0，`0/208/0`；决策 `REJECT_MECHANISM_INERT`，未消费 Replay。

## 2026-08-29 V69：全局严格正 margin 队列交换

- 父代 V66；保留逐单位净 margin 门，只移除 clone-distance 限制。
- 当前状态：`FROZEN_BEFORE_MECHANISM_SMOKE`；预注册 Smoke 416 场，通过后 Development 3,328 场、Confirmation 13,312 场。
- Smoke 416 场：奖励变化 0，`0/208/0`；决策 `REJECT_MECHANISM_INERT`，未消费 Replay。

## 2026-08-29 V70：重复 WHEAT 购买的 25% 抢价

- 父代 V66；把第二笔相邻 WHEAT 购买的 25% 提前并入第一槽，总购买量与槽位保持不变。
- 动作审计：208 场发现 468 次相邻重复 WHEAT 购买。
- Smoke 416 场：148 场奖励变化，PGU `+2.404pp`，`9/199/0`，平均 margin `+6.57`，通过。
- Development 3,328/3,328 场、零错误：PGU `+2.614pp`，95% CI `[+2.193,+3.035]pp`，`79/1585/0`；13 条谱系全部非负，通过。
- Confirmation 13,312/13,312 场、零错误：PGU `+2.622pp`，95% CI `[+2.381,+2.855]pp`，`328/6328/0`；13 条谱系均非负，直接对 V66 得分 `79.49%`，强度门通过。
- 工程门：提交包 16/16 场逐动作与奖励完全一致；官方 Python 1.32.7 复算 832/832 场奖励精确一致、零错误。
- 决策：`PROMOTE_LOCAL_GOLD`，本轮第 11/15 个新金牌；V70 成为后续冻结父代。

## 2026-08-29 V71：重复 WHEAT 购买累计 50% 抢价

- 父代 V70；第二笔相邻 WHEAT 购买的提前比例由 25% 增至 50%，总购买量与槽位不变。
- Smoke 448 场：144 场奖励变化，PGU `+1.786pp`，`7/217/0`，平均 margin `+3.72`，通过。
- Development 3,584/3,584 场、零错误：PGU `+2.567pp`，95% CI `[+2.175,+2.958]pp`，`84/1708/0`；14 条谱系均非负，通过。
- Confirmation 14,336/14,336 场、零错误：PGU `+2.246pp`，95% CI `[+2.037,+2.455]pp`，`309/6859/0`；14 条谱系均非负，直接对 V70 得分 `78.91%`，强度门通过。
- 工程门：提交包 16/16 场逐动作与奖励完全一致；官方 Python 1.32.7 复算 896/896 场奖励精确一致、零错误。
- 决策：`PROMOTE_LOCAL_GOLD`，本轮第 12/15 个新金牌；V71 成为后续冻结父代。

## 2026-08-29 官方 Replay 全量回填

- Kaggle CLI 索引仍截止 `2026-08-27`，无新增日期；对本地缺失的 `2026-07-30` 至 `2026-08-19` 共 21 个日期执行串行回填。
- 结果：29/29 个索引日期状态均为 `complete`，本地索引目录约 632GB；后续候选按不同日期对消费未暴露 source。

## 2026-08-29 V72：重复 WHEAT 购买累计 75% 抢价

- 父代 V71；第二笔相邻 WHEAT 购买累计提前比例由 50% 增至 75%，总购买量与槽位不变。
- Smoke 480 场：112 场奖励变化，PGU `+2.50pp`，`11/229/0`，平均 margin `+2.20`，通过。
- Development 3,840/3,840 场、零错误：PGU `+1.615pp`，95% CI `[+1.250,+1.927]pp`，`62/1858/0`；15 条谱系均非负，通过。
- Confirmation 15,360/15,360 场、零错误：PGU `+1.680pp`，95% CI `[+1.484,+1.882]pp`，`248/7432/0`；15 条谱系均非负，直接对 V71 得分 `72.85%`，强度门通过。
- 工程门：提交包 16/16 场逐动作与奖励完全一致；官方 Python 1.32.7 复算 960/960 场奖励精确一致、零错误。
- 决策：`PROMOTE_LOCAL_GOLD`，本轮第 13/15 个新金牌；V72 成为后续冻结父代。

## 2026-08-29 V73：重复 WHEAT 购买完全合并

- 父代 V72；第二笔相邻 WHEAT 买量 100% 并入第一槽，第二槽保留零量占位。
- Smoke 512 场：84 场奖励变化，PGU `+1.172pp`，`6/250/0`，平均 margin `+1.35`，通过。
- Development 4,096/4,096 场、零错误：PGU `+1.318pp`，95% CI `[+1.001,+1.660]pp`，`54/1994/0`；16 条谱系均非负，通过。
- Confirmation 16,384/16,384 场、零错误：PGU `+1.062pp`，95% CI `[+0.891,+1.239]pp`，`172/8020/0`；16 条谱系均非负，直接对 V72 得分 `66.41%`，强度门通过。
- 工程门：提交包 16/16 场逐动作与奖励完全一致；官方 Python 1.32.7 复算 1,024/1,024 场奖励精确一致、零错误。
- 决策：`PROMOTE_LOCAL_GOLD`，本轮第 14/15 个新金牌；V73 成为后续冻结父代。

## 2026-08-29 V74：全局重复 WHEAT 购买完全合并

- 父代 V73；唯一改动是移除 clone-like 距离门，把完全合并扩展到所有出现相邻重复 WHEAT 买单的公开局面。
- Smoke 544 场：29 场奖励变化，PGU `0pp`，`0/272/0`，平均 margin `+1.39`；无负翻转，按预注册机制门通过。
- Development 4,352/4,352 场、零错误：候选与 V73 完全同动作，PGU `0pp`，`0/2176/0`；决策 `REJECT_DEVELOPMENT_INERT`，不消费 Confirmation。

## 2026-08-29 V75：压缩重复 WHEAT 零量槽

- 父代 V73；重复 WHEAT 完全合并后删除第二个零量订单，使后续有效订单提前一个市场槽位，总 WHEAT 买量不变。
- Smoke 544 场：奖励变化 0，PGU `0pp`，`0/272/0`；决策 `REJECT_MECHANISM_INERT`，未消费 Replay。

## 2026-08-29 V76：动态买单跨一个安全固定支出槽

- 父代 V73；clone-like 局面中将 WHEAT/FERTILIZER 买单向左跨过一个相邻 HIRE、BUY_LAND 或 BUY_SEED，不跨动物订单。
- Smoke 544 场：272 场奖励变化，PGU `+2.941pp`，`15/257/0`，平均 margin `+18.64`，通过。
- Development 4,352/4,352 场、零错误：PGU `+2.872pp`，95% CI `[+2.298,+3.447]pp`，`110/2066/0`；17 条谱系均非负，通过。
- Confirmation 17,408/17,408 场、零错误：PGU `+3.401pp`，95% CI `[+3.010,+3.803]pp`，`543/8157/4`；直接对 V73 得分 `81.54%`，最低逐金牌得分 `81.54%`，强度门通过。
- 工程门：提交包 16/16 场逐动作与奖励完全一致；官方 Python 1.32.7 复算 1,088/1,088 场奖励精确一致、零错误。
- 决策：`PROMOTE_LOCAL_GOLD`，本轮第 15/15 个新金牌；当前 Goal 完成，未自动提交 Kaggle。
- V48 Development：PGU `+0.684pp`，`12/1012/0`。
- V48 Confirmation：PGU `+0.635pp`，95% CI `[+0.391,+0.903]pp`，低于 +1pp；决策 `REJECT_CONFIRMATION`，不追加样本。

## 2026-08-29 V49：713/714/715 三阶段终局抢跑

- 父代 V46；在最近一次 step 712 demand 之后，于 713/714/715 逐步出售当步可执行终局余量。
- 当前状态：`BUILDING / FROZEN_BEFORE_MECHANISM_SMOKE`。
- 预注册：烟测 256 场；通过后 Development 2,048 场、Confirmation 8,192 场。
- V47 烟测：PGU `-10.94pp`，`0/102/26`；step 715 新增库存导致“移动而非追加”退化，决策 `REJECT_MECHANISM_SMOKE`。

## 2026-08-29 V48：714/715 两阶段终局抢跑

- 父代 V46；保留 step 715 补卖，同时新增 step 714 第一阶段，避免 V47 丢失新到库存。
- 当前状态：`BUILDING / FROZEN_BEFORE_MECHANISM_SMOKE`。
- 预注册：烟测 256 场；通过后 Development 2,048 场、Confirmation 8,192 场。
- V45 Development：1,792 场 PGU=0，`0/896/0`，平均 margin +1.66；决策 `REJECT_DEVELOPMENT`，不消费 Confirmation。

## 2026-08-29 V46：完整终局库存抢跑

- 父代 V37；step 715 前置 `_terminal_liquidation` 在 716 必然处理的完整 9 商品可执行余量。
- 当前状态：`BUILDING / FROZEN_BEFORE_MECHANISM_SMOKE`。
- 预注册：烟测 224 场；通过后 Development 1,792 场、Confirmation 7,168 场。
- V44 烟测：CARROT preempt units=0，决策 `REJECT_MECHANISM_INERT`，未消费 Replay。

## 2026-08-29 V45：动态终局库存抢跑

- 父代 V37；step 715 对 clone-like 对手前置当前动作后剩余的 premium shed，覆盖冻结路线之外的动态终局清仓。
- 当前状态：`BUILDING / FROZEN_BEFORE_MECHANISM_SMOKE`。
- 预注册：烟测 224 场；通过后 Development 1,792 场、Confirmation 7,168 场。
- V43 烟测：EGG preempt units=0；冻结路线 SELL 审计确认无 EGG 计划，决策 `REJECT_MECHANISM_INERT`，未消费 Replay。

## 2026-08-29 V44：CARROT 需求边界前置

- 父代 V37；按“冻结路线实际存在且非生产投入”的规则，唯一新增 CARROT，排在 premium 后。
- 当前状态：`BUILDING / FROZEN_BEFORE_MECHANISM_SMOKE`。
- 预注册：烟测 224 场；通过后 Development 1,792 场、Confirmation 7,168 场。
- V42 烟测：late delay event=112，PGU `-6.25pp`，`0/100/12`；决策 `REJECT_MECHANISM_SMOKE`，未消费 Replay。

## 2026-08-29 V43：EGG 需求边界前置

- 父代 V37；只将纯销售型动物产物 EGG 加入既有需求边界前置集合，premium 仍优先。
- 当前状态：`BUILDING / FROZEN_BEFORE_MECHANISM_SMOKE`。
- 预注册：烟测 224 场；通过后 Development 1,792 场、Confirmation 7,168 场。
- V41 烟测：oversize event=0，候选与父代完全相同；决策 `REJECT_MECHANISM_INERT`，未消费 Replay。

## 2026-08-29 V42：终局前需求延迟

- 父代 V37；只把 V20 的固定 delay stop 从 672 延伸到可在 718 前偿还的 step 717。
- 当前状态：`BUILDING / FROZEN_BEFORE_MECHANISM_SMOKE`。
- 预注册：烟测 224 场；通过后 Development 1,792 场、Confirmation 7,168 场。
- V40 烟测：非 clone supply event=0，112 个配对单元全部相同；公开 tile schema 核对通过，机制与既有 clone 门冗余。
- 决策：`REJECT_MECHANISM_INERT`。未消费 Replay；失败包 SHA256 `62749c547e5257c7d27672fd89fe457f8357370a3987011efa1fdd440199df6b`。

## 2026-08-29 V41：棚容量约束的完整前置量

- 父代 V37；用官方棚容量 100 替换无规则依据的 30 单位前置上限，仍受实际库存与未来原出售量约束。
- 当前状态：`BUILDING / FROZEN_BEFORE_MECHANISM_SMOKE`。
- 预注册：烟测 224 场；通过后 Development 1,792 场、Confirmation 7,168 场。
- 烟测结果：early event=0，候选/父代 112 个配对单元全部相同。
- 决策：`REJECT_MECHANISM_INERT`。未消费 Replay；失败包 SHA256 `66fccd75e6bef1866438506e9b066b2884f13f920e0723da0d4f66f4ea2e1632`。

## 2026-08-29 V39：最后三个可行动步的需求边界前置

- 父代 V37；只纳入原计划位于 step 716-718 的 premium SELL，禁止创建 future step>=719 的偿还。
- 当前状态：`BUILDING / FROZEN_BEFORE_MECHANISM_SMOKE`。
- 预注册：烟测 224 场；通过后 Development 1,792 场、Confirmation 7,168 场。

> Goal 更新：用户将本轮新增本地金牌目标由 8 个扩大为 15 个。已晋级的 V32、V33、V34、V37 计为 4/15，后续门槛与一次性确认规则不变。

- V39 Development：1,792 场 PGU `+0.223pp`，`4/892/0`，按点估计门进入确认。
- V39 Confirmation：7,168 场 PGU `+0.809pp`，95% CI `[+0.530,+1.116]pp`，`50/3534/0`；因低于 `+1pp` 硬门，决策 `REJECT_CONFIRMATION`，不追加样本。

## 2026-08-29 V40：逐商品公开供给信号

- 父代 V37；保留 clone 门，并在非 clone 局面以对手公开作物/动物资产作为逐商品 premium 竞争信号。
- 当前状态：`BUILDING / FROZEN_BEFORE_MECHANISM_SMOKE`。
- 预注册：烟测 224 场；通过后 Development 1,792 场、Confirmation 7,168 场。
# 2026-08-29 V86：多时间尺度需求—任务 Hierarchical MoE

- `strategy_parent=null`；V76 仅为冻结强度比较器。
- 自有 Regime Router 在 wool、dairy/fruit、smoothie 三个生产蓝图专家间按状态契约切换；自有 Event Router 处理 on-plan、weed、inventory、fertilizer；自有 Product Market Router 负责融资、需求时机、对手供给和终局兑现。
- 不调用任何历史完整 agent；蓝图 payload 只包含生产/市场目标动作序列及来源 SHA。
- 主消融移除 Router、两类生产专家和动态事件/市场专家，退化为单一 standalone dairy/fruit 蓝图，不恢复 V76。
- 当前状态：`THINKING / PRECONSTRUCTION_ARCHITECTURE_AUDIT`；构造前门通过前不消费 official Replay。
### V103：Supply-Shock Product Execution MoE（思考阶段否决）

- `strategy_parent=null`，原计划按实时商品供给冲击路由立即出售、过供给等待与需求后释放专家。
- 原创性审计发现其主要因果杠杆仍是“需求前后改变出售时点”，与 V20/V33/V34 同构；库存阈值只是 Router 条件变化，不构成新谱系。
- 决策：`REJECT_THINKING_SAME_LINEAGE_PATCH`；未创建提交包、未运行对局、未消费官方 Replay。

### V104：Global Demand Graph Commitment MoE（来源资格否决）

- `strategy_parent=null`；同一冻结前缀运行至 step 216，再以完整商店需求图、席位与双方公开状态选择一个整段 continuation 专家。
- 3,072 场 synthetic source qualification：固定专家与交叉验证 Router 都为 85.9375%，配对 `0/384/0`；Router 平均金币差低 30.23。
- 决策：`REJECT_SOURCE_QUALIFICATION_NO_LEARNABLE_ADVANTAGE`；没有构造 submission，没有消费官方评测 Replay。

### V105：Trajectory Committee Consensus MoE（来源资格否决）

- `strategy_parent=null`；策略的 farmer、hand 与 market queue 均由 3/5/8 条独立强轨迹的确定性多数共识生成，不存在固定父代默认动作。
- 768 场 synthetic 闭环：固定专家 87.50%；top-3 5.21%、top-5 59.38%、top-8 21.35%，最好仍低 28.13pp。
- 决策：`REJECT_SOURCE_QUALIFICATION_TEMPORAL_CONTRACT_DESTROYED`；不调权重、不构造 submission、不消费官方评测 Replay。

### V106：Conformal Support Risk Option MoE（预构造否决）

- `strategy_parent=null`；1,152 局风险探针在 step 576 达到 OOF balanced accuracy 92.03%、precision 91.67%、recall 84.62%。
- 提交就绪包 SHA256 `130f1e5419281290dbb011be4cce34abfeb34a6cf64a2bc4e62c97860c912e38`；576 场预构造 full/ablation 均 100%，配对 `0/192/0`，风险 option 0 局。
- 决策：`REJECT_PRECONSTRUCTION_RISK_OPTION_INERT_NO_SCORE_CONTRIBUTION`；风险可识别不等于策略贡献，未消费官方评测 Replay。

### V107：Hidden RNG Posterior MoE（可预测性否决）

- 4,096 个 synthetic seed；用前三商店和双方公开杂草位图预测第四商店，前 3,072 训练、后 1,024 留出。
- 深度 8 浅树留出准确率 11.13%、macro-F1 7.03%，低于 12.5% 多数/均匀先验。
- 决策：`REJECT_PREDICTABILITY_PUBLIC_RNG_LEAKAGE_INSUFFICIENT`；不构造 submission、不消费官方评测 Replay。

### V108：Evolutionary Macro Option MoE（Option 资格否决）

- 140 个整日 option 变体、8 个 synthetic seed、V20/V76、双席位，共 4,512 场；固定基准 75.00%、尾部 12.50%。
- 最佳变体配对 `0/32/0`，仅平均金币差 +84.16；无任何变体满足正胜负翻转与尾部门。
- 决策：`REJECT_OPTION_SOURCE_QUALIFICATION_NO_SCORE_ADVANTAGE`；不做组合搜索、不构造 submission。

### V109：Phase-Synchronized Automaton MoE（预构造否决）

- RC1 发现共同执行器漏计同回合 DROP/PLACE，证据作废；只修规则语义并更换 seed，RC2 包 SHA256 `f978ca37dad302ac990562773a2c80e5cfd3fd16c23f7e926fc6b11873a09ae1`。
- RC2 576 场：full 82.29%、固定相位消融 84.90%、直接 V76 81.25%；配对 `0/187/5`，灾难率较 V76 +12.50pp。
- 决策：`REJECT_PRECONSTRUCTION_PHASE_RETIMER_DESTRUCTIVE`；三相位均激活，但跳过/重复不可逆承诺。

### V110：Fitted-Q Continuation MoE（来源资格否决）

- 140 条日边界后完整 continuation、8 个 synthetic seed、V20/V76、双席位，共 4,512 场。
- 固定 base 100%；所有 continuation 均 `0/32/0`，最好平均金币差仍 −35.69，没有正 Q 原语。
- 决策：`REJECT_CONTINUATION_QUALIFICATION_NO_POSITIVE_PRIMITIVE`；不训练 Router、不构造 submission。

### V111：CVaR Recovery Portfolio MoE（专家支配否决）

- 96 个 synthetic seed、六对手、双席位、增长/恢复两完整 option，共 2,304 场；按 seed 六折 OOF。
- Router 相对增长 +9.29pp，但 selected 87.24% 低于始终恢复 88.28%，尾部 6.25% 也差于 5.73%。
- 决策：`REJECT_EXPERT_DOMINANCE_FAKE_MOE`；同步把“Router 必须优于最佳单专家”的 BEU 门写入 `loop_model.md`。

### V112：Recovered Expert Manifold MoE（专家支配否决）

- 8 个恢复后完整 continuation、32 个 synthetic seed、V20/V76、双席位，共 1,024 场。
- 最佳固定专家 `100439801` 93.75%；OOF Router 93.75%、BEU 0、配对 `0/128/0`，尾部完全相同。
- 决策：`REJECT_EXPERT_MANIFOLD_BEST_EXPERT_DOMINANCE`。累计 36 个谱系决策后仍为 0/5，Goal 进入 `BLOCKED_ARCHITECTURAL_IMPASSE`，详见 `original_moe_goal_blocker_20260829.md`。

### V113 Stage 23–25：Simulator HMoE PPO 延迟 Router 与阶段 Option

- `strategy_parent=null`；V76 只作为冻结对手，动作由 timed autoregressive PPO experts 直接生成。
- Stage 23：确认 step 0 跨 seed 完全同态，step 72 才首次可见商店；整局浅树 Router 在独立 16 局相对最佳固定专家自身金币 `-1,787.7`，否决。
- Stage 24：只在 step 72–215 路由，M2/M5 逐局完全相同；unit Oracle 空间复现，但浅树在独立 16 局相对最佳固定专家 `-2,142.2`，否决。
- Stage 25：U4 enterprise 与 U5 liquidity 各用 16 局、2,304 phase transitions 做 unit-only PPO；32 seed × 双座位确认中，主指标增益分别为 `+1,238.5` 和 `+7,813.8`，seed-block CI 下界 `-1,614.7/-955.5`。
- 决策：`REJECT_PHASE_OPTION_PPO_UNSTABLE_ACROSS_SEEDS`；仍 0/64 战胜 V76，不登记金牌、不打包、不提交。

### V113 Stage 26–27：Opponent-impact、历史状态与混合对手联赛

- Stage 26：U5 opponent-impact PPO 在 32 seed × 双座位确认中，自身金币 `+803.8`
  （CI `[-1509.3,+3159.3]`）、分差 `+1246.1`（CI `[-5573.3,+8178.4]`），仍 0/64
  战胜 V76，判定 `REJECT_OPPONENT_IMPACT_PPO_UNSTABLE`。
- Stage 27：新增 32 维动作历史，恢复首商店承诺、上一回合/累计市场流及单位角色；
  Stage20 incumbent 扩展后的 `history32_stage20_incumbent_init` 在 4 局中与原 Actor
  闭环严格等价；旧 Stage17 历史初始化在强对手 smoke 连续 8 局金币为 0，已淘汰。
  V76-only BC 在 epoch1 后按用户要求中止，checkpoint 只作诊断，不得作为 challenger。
- 训练协议改为冻结混合联赛：Gold-Train/PPO History/Self-play/Exploiter/Anchor=
  40/30/15/10/5；64 fresh seed × 双座位首轮为 52/38/18/14/6 局，同 seed 双座位
  面对同一对手，并按层分别标准化 advantage。
- Gold 行为族按 60/20/20 拆成 Train/Dev/Blind；V76 总训练权重目标 9%，V54 只作 Dev，
  V66 在最终 Confirmation 前完全隔离。所有本地 agent/checkpoint 固定 SHA，失败 PPO
  仅作为训练对手或 Exploiter，不继承冠军身份。
- 首轮联赛已完成：64 fresh seed × 双座位=128 局，配额严格为 52/38/18/14/6，
  92,032 transitions，零异常；V76 占 9.375%，各层 advantage 独立标准化。
- `lr=1e-7/3e-7` 两个 shared-worker 候选在独立 16 seed × 双座位筛选中，score rate
  分别由 incumbent 的 31.25% 降至 25.00%/28.125%；配对 score gain 为
  `-6.25pp/-3.125pp`，两条 CI 均跨 0，全部 `REJECT_SCREEN`，未进入 Gold-Dev。
- `lr=3e-7` 虽有显著分差增益，但自身金币 CI 跨 0、得分率下降，改善主要来自压低对手
  金币，按预注册规则不得晋级。当前状态：`MIXED_LEAGUE_ITER1_REJECTED / INCUMBENT_UNCHANGED`；
  未打包、未提交 Kaggle。
- Stage 28 预注册：冻结全部既有行为参数，只训练 `own_global_dense/kernel` 新增 32 个历史
  输入行；参数差分烟测通过，原 60 行与其余参数逐字节一致。第 2 轮固定 seed
  11330000–11330063，候选学习率为 `1e-5/3e-5`，筛选集固定为 11331000–11331015，
  不得在看到筛选结果后追加学习率分支。
- Stage 28 第 2 轮联赛完成：64 fresh seed × 双座位=128 局、92,032 transitions、零异常，
  配额 52/38/18/14/6，V76 占 9.375%；两个分支均仅改变最后 32 个历史输入行。
- 16-seed screen：incumbent 7/0/25；`lr=1e-5` 8/0/24，自身金币增益 +1,567.8，
  CI `[+132.3,+3,377.5]`，进入 Gold-Dev；`lr=3e-5` 10/0/22，但灾难率由 12.5%
  升至 18.75%，`REJECT_SCREEN`。
- Gold-Dev V54：64 fresh seed × 双座位，基线与 `lr=1e-5` 均 0/0/128；候选自身金币
  配对增益 −410.6，CI `[-1,386.7,+622.0]`，分差增益 −340.8，CI
  `[-2,623.6,+1,911.3]`。最终 `REJECT_GOLD_DEV`；不登记专项 expert、不更新 incumbent、
  不启用 Gold-Blind，也未打包或提交 Kaggle。

### V113 Stage 29：现金安全市场 PPO expert（screen 否决）

- 不继承 Stage28；从 Stage20 等价的 history 初始化出发，将 market slot 2 克隆到独立
  slot 5，初始化 SHA256 `e49f084b1bc5e754006ed38901e2d83086da4c7488c2b5bb7b0f255bf2a9765c`。
- 4 fresh seed × 双座位克隆烟测共 8 局，slot 2/5 的金币、分差、胜负、动作计数完全一致。
- 只训练 market projection 的 slot 5；目标为相对企业价值、终局金币差和低于 3,000
  金币的灾难惩罚。训练 seed 11340000–11340063，screen seed 11341000–11341015，
  学习率预注册 `1e-5/3e-5`；Gold-Blind 继续隔离。
- 混合池训练完成：64 fresh seed × 双座位=128 局、92,032 transitions、零异常；配额
  52/38/18/14/6，V76 占 9.375%，各层 advantage 独立标准化。两个分支均只改变 market
  projection slot 5，其余参数逐位一致。
- 16-seed screen：基线 10/2/20、score rate 34.375%、灾难率 21.875%；`lr=1e-5`
  为 9/0/23、28.125%、灾难率 6.25%，自身金币增益 CI
  `[-950.6,+4,742.6]`；`lr=3e-5` 为 14/0/18、43.75%、灾难率 18.75%，自身金币
  增益 CI `[-2,341.3,+9,740.5]`、分差增益 CI `[-7,981.9,+9,583.8]`，且
  Gold-Train 平均分差退化 −2,616.7。
- 两条分支均未满足“灾难率严格下降 + 自身金币或分差 CI 下界大于 0”，最终
  `REJECT_SCREEN`；不进入 Gold-Dev/Gold-Blind，不登记专项 expert、不更新 incumbent，
  未打包、未提交 Kaggle。
- 下一步不对 Stage29 打补丁；新建独立的共享市场冲击响应 expert，使用新的预注册奖励、
  fresh seed 与相同混合联赛门控。两个独立职责 expert 均通过后，才训练 option Router。

### V113 Stage 30：共享市场冲击 PPO expert（预注册并启动）

- 不继承 Stage29；从 Stage20 等价 history 初始化将 market slot 2 克隆到独立 slot 4，
  SHA256 `0c34871fbe5bf3e6a560d5bd6eaa299b28beb23b79d980089449bfbee16a234d`。
- seed 11349000–11349003、双座位共 8 局克隆烟测中，slot 2/4 的金币、分差、胜负、状态
  和动作计数完全一致；只允许 market projection slot 4 更新。
- 独立职责：市场库存低于基准时，提高可变现商品库存和现金缓冲的信用，同时优化相对
  企业价值和终局金币差；不是 Stage29 的现金阈值奖励调参。
- 训练固定 11350000–11350063，screen 固定 11351000–11351015，预注册学习率
  `1e-5/2e-5`；通过 screen 前不访问 Gold-Dev，Gold-Blind 继续隔离，禁止提交 Kaggle。
- 混合池训练完成：128 局、92,032 transitions、零异常，配额 52/38/18/14/6，V76
  占 9.375%；两个分支均仅更新 market slot 4。
- screen 基线 11/0/21、34.375%、灾难率 25%；`lr=1e-5` 10/0/22、31.25%，自身金币
  增益 +2,267.3，CI `[+125.9,+5,002.5]`，灾难率 6.25%，但 pooled score 退化；
  `lr=2e-5` 13/0/19、40.625%，灾难率升至 31.25%，自身金币/分差 CI 均跨 0。
- 两条分支均 `REJECT_SCREEN`；不访问 Gold-Dev/Blind、不登记 expert、不更新 incumbent、
  未打包、未提交 Kaggle。
- 根因边界：现有 history 只记录己方动作，没有上一时点逐商品市场库存/价格，因此模型
  无法识别库存变化速度。下一条独立谱系先增加市场状态记忆，再训练冲击响应 expert；
  禁止继续调 Stage30 奖励权重。

### V113 Stage 31：市场状态记忆 PPO expert（预注册并启动）

- 从 Stage20 等价 history checkpoint 独立分叉，新增上一库存/库存变化/上一价格/价格变化
  共 36 维状态；专用 `market_memory_dense` 只接入市场分支，单位分支结构隔离。
- 初始化 SHA256 `8de3b486c5442478db0206a1bcf746b74773912966f31c62c660ef4c9353bc99`；
  4 fresh seed × 双座位的 8 局闭环与旧 market slot 2 逐项一致。
- 为单独检验状态记忆，不调整 Stage30 奖励或学习率：训练固定 11360000–11360063，
  `lr=1e-5/2e-5`，只训练 memory encoder + market slot 4；screen 固定
  11361000–11361015，Gold-Dev/Blind 尚未开放，禁止提交 Kaggle。
- screen：基线 8/0/24、25%、灾难率 15.625%；`lr=1e-5` 12/0/20、37.5%，自身金币
  增益 +6,667，CI `[+1,234,+12,478]`，灾难率 6.25%，通过；`lr=2e-5` 淘汰。
- V54 Gold-Dev：64 fresh seed × 双座位，基线/候选均 0/0/128；候选自身金币增益
  +763.0，CI `[-918.6,+2,419.4]`，分差增益 +916.8，CI
  `[-2,950.2,+4,692.2]`，灾难率 27.34%→25%。最终 `REJECT_GOLD_DEV`，不登记 expert、
  不更新 incumbent、不访问 Gold-Blind、未提交 Kaggle。
- 下一独立谱系改为 unit+market 同 slot 联合更新的“终局兑现协调”完整动作 PPO expert；
  市场记忆保留但不再调权重，V54 仍只作 Dev，禁止训练成 V54 专项策略。

### V113 Stage 32：终局兑现协调完整动作 PPO expert（预注册并启动）

- 从 Stage20 等价 history checkpoint 独立分叉，把旧 unit3/market2 克隆到新 slot 5，
  再添加零初始化 36 维市场记忆；SHA256
  `e9f90be063c5998c310c78177c557d3da0a94ad7814daf5d073e2fd25d9cf1c7`。
- 4 fresh seed × 双座位共 8 局闭环完全等价；只训练 memory encoder 与 unit/market
  projection slot 5，共享网络及其他专家冻结。
- 奖励不变，只检验完整动作协同；训练 11370000–11370063，预注册 `lr=5e-6/1e-5`，
  screen 11371000–11371015，V54 只作 Gold-Dev，Gold-Blind 隔离。
- screen 基线 9/0/23、28.125%、灾难率 9.375%；`lr=5e-6` 7/0/25，自身金币
  −3,124.7、分差 CI `[-19,165.5,-1,645.0]`；`lr=1e-5` 8/0/24，自身金币
  −3,347.1、灾难率 21.875%。全部 `REJECT_SCREEN`，未访问 Dev/Blind。
- 根因：720 步整场回报对单位动作的信用分配过于噪声化。下一独立谱系改为最后 48 步
  的终局 option，并把最终兑现目标直接加入 phase 回报；禁止继续调 Stage32 学习率。

### V113 Stage 33：终局 48 步完整动作 PPO option（预注册并启动）

- 独立从 Stage20 等价 checkpoint 初始化 unit3/market2 到 slot 5，并加入零初始化 36 维
  市场记忆；SHA256 `e9f90be063c5998c310c78177c557d3da0a94ad7814daf5d073e2fd25d9cf1c7`。
- 11379000–11379003、双座位 8 局闭环等价检查通过；Stage33 与 Stage32 只有初始化相同，
  训练时间范围和目标函数不同，不继承 Stage32 更新。
- mixed league iteration 7 固定 11380000–11380063，只学习步骤 672–719；终局回报直接加入
  phase，含平滑金币差、自身兑现和低现金灾难惩罚。训练范围限 memory + unit/market
  slot 5，分支预注册为 2 epoch、`lr=1e-5/3e-5`。
- screen 固定 11381000–11381015；通过后才访问 11382000 起的 V54 Gold-Dev，Blind 隔离，
  未经用户授权不得提交 Kaggle。
- 原 screen 使用全局强制 slot 5，实际不是终局 option：`lr=1e-5` 为 12/0/20、37.5%，
  自身金币 +3,545.7、灾难率 21.875%→9.375%，但金币/分差 CI 下界均为负且金牌 0 胜；
  `lr=3e-5` 为 7/0/25。两分支按该错误部署合同均否决，不访问 Dev/Blind。

### V113 Stage 34：终局 option 生效区间修正（预注册并启动）

- 不改训练参数或 checkpoint；仅把部署改为前 671 次动作使用 incumbent unit3/market2，
  最后 48 次动作使用训练后的 unit5/market5，即引擎 schedule `0:3,671:5` 与
  `0:2,671:5`。
- 为避免用已见 screen 做选择，重新固定 11383000–11383015；初始化与两分支使用完全
  相同的 seed/seat/对手 schedule。通过后才访问 11384000 起的 V54 Dev，Blind 隔离。
- 调度审计通过：每局 unit3/5 与 market2/5 分别使用 671/48 次。基线 8/0/24；
  `lr=1e-5` 7/0/25，自身金币 −313.6；`lr=3e-5` 9/0/23，自身金币 +330.9、CI
  `[-1,151.1,+1,934.2]`，分差 CI `[-3,738.1,+3,614.3]`。两者 Gold-Train 均
  0/0/12，正向经济 CI 门失败，最终 `REJECT_SCREEN`，不访问 Dev/Blind。
- 研究结论：终局 option 不是金牌缺口的主因。下一主线改为 Gold-Train 行为去重多教师
  动作 BC 初始化 + 混合联赛 PPO；教师仅生成监督标签，不进入在线 Router。

### V113 Stage 35：行为家族均衡多教师完整动作 BC（预注册并启动）

- 从零初始化 timed autoregressive full-action HMoE，不继承 V76 单教师 BC 或 Stage20；
  Gold-Train 按三个 behavior family 等权，V19/V21共享生产路线家族配额，Dev/Blind隔离。
- 教师完整闭环真实执行，训练标签为状态条件化 canonical 动作；禁止在候选轨迹上调用带
  内部状态的教师作为 DAgger oracle。正式数据固定 11391000 起、每家族 8 seed group、
  双座位，共48局、预期34,512行。
- Router 标签来自可观测职责而非教师ID：unit为作物/动物/物流/规划/终局，market为
  出售/采购/终局。先做三折 leave-one-family-out，再按同参数训练全家族 BC；只有通过
  fresh-seed闭环与混合screen后才接入固定混合池PPO。
- 正式数据为 48 局、34,512 行，三家族严格等权；数据 SHA256
  `501a0d60bf37953a8087d8fe841f9c2be75d469170fccac4c46e67a5b2eccbe3`。4,314 个官方
  transition 的 raw/canonical 状态 hash 全部一致。
- 修正逐步标签与 24 步 Router 缓存错配后，对 Starter 从 0/0/16 恢复为 16/0/0；单
  专家消融只有 8/0/8，证明 MoE 有效，但经济能力仍明显低于教师。
- mixed screen 中 candidate/incumbent 均 8/0/24；candidate 自身金币配对增益
  −23,629.8，CI `[-54,489.3,-1,061.5]`，灾难率 31.25%，Gold-Train 0/0/12，最终
  `REJECT_SCREEN`。不进入 PPO/Dev/Blind，不更新 incumbent。
- on-policy 审计显示 joint action 一致率在 step 72 后由 53.66% 跌至 3.47%，216 后为
  0。Stage36 预注册为行为家族均衡 candidate-state DAgger：11397000 起每家族 8 seed
  group，教师只标注不执行；与原数据等权合并后只训练一个 4-epoch、`lr=1e-4` 分支，
  新 screen 固定 11398000–11398015。
- Stage36 正式 DAgger 为 48 局、34,512 行、零 unknown token；合并训练 checkpoint
  SHA256 `fa2373d069dd19a45553f7b8fbd2be0e07df90a15a3fbe8e0fdbfc9c86fcf206`。但 Starter
  从 Stage35 的 16/0/0 退化到 11/0/5，加入严格终局职责 mask 后进一步为 9/0/7，故
  `REJECT_BASIC_GATE`，不运行 mixed screen。
- Stage37 预注册回到 Stage35 作为训练初始化：冻结 Router/trunk/decoder，只用混合联赛
  PPO 更新实际路由到的全部 expert projections。训练固定 11399000–11399063、配额
  52/38/18/14/6、单分支 `lr=3e-6`/1 epoch；screen 固定 11401000–11401015。
- Stage37 正式 rollout 已完成 128 局、92,032 transitions、零运行异常，配额仍为
  52/38/18/14/6，V76 占 9.375%；但采样策略只有 4胜6平118负，平均金币 26.40，
  128/128 局全部低于 3,000 金币灾难线。唯一 PPO 更新 checkpoint SHA256 为
  `18b17040ee73e2e06ab95fa0a7f7f31b527265ffb4ecef7a74ed3d69ab2fc665`，参数审计确认只改
  unit/market expert projections 的 4 个参数叶。
- 用户于 2026-08-30 要求停止目标及全部后台任务。Starter 诊断在 6/8 seed block 后中断，
  无最终产物、不计正式证据；11401000 mixed screen 未运行，Dev/Blind 未访问，incumbent
  未更新，未提交 Kaggle。状态：`STOPPED_BY_USER / NOT_GOLD`；复盘见
  `v113_simulator_hmoe_ppo/OVERNIGHT_TRAINING_SUMMARY_20260830.md`。

### V113 PPO v4：三时间尺度重构方案（仅设计）

- 基于 Stage17–37 的失败证据，停止逐 turn 联合随机探索，改为“日级/事件级 SMDP
  Manager + 稳定低层专家 + 有界 Residual PPO”；完整方案见
  `v113_simulator_hmoe_ppo/PPO_V4_PLAN.md`。
- 高层正常每 24 turn 决策一次，事件只触发带防抖、最短持续时间和冷却期的提前终止；
  低层先用真实闭环 BC 与 AWR/IQL 建立稳定经济路线，Residual 每天最多修正 4 个动作。
- 对手联赛从生存期 `15/35/10/5/35` 动态提升到最终 `40/30/15/10/5`；V76 不超过
  10%，Gold-Dev/Blind 继续隔离。critic 资格门、随机策略生存门、职责 expert 门、
  Manager 对最佳固定 expert 的 BEU 门和一次性 Blind 门均已预注册。
- 当前仅完成设计：未创建 v4 训练进程，未消费新 seed/Replay，未访问 Dev/Blind，未改变
  Stage20 incumbent，未授权或提交 Kaggle。

### V114：Day-SMDP Hierarchical MoE PPO（V4-0 启动）

- 用户于 2026-08-30 授权把 PPO v4 独立为 V114 并开始执行；`strategy_parent=null`，
  V113 仅作为失败证据和底层引擎/编码接口来源，不继承 Stage37 checkpoint。
- 方案迁移至 `v114_day_smdp_hmoe_ppo/PPO_V4_PLAN.md`；模型源码统一进入同目录，训练数据
  与证据统一进入 `model_data/v114_day_smdp_hmoe_ppo/`。
- 当前阶段为 V4-0 基础设施与资格门。Gold-Dev/Blind 仍隔离，Kaggle 提交未获授权。

### V114 V4-1/V4-2：原创低层专家闭环资格迭代（进行中）

- V4-0 已通过：42 项初始合同测试、100 局官方引擎 parity、72,000 状态零差异；后续完整
  回归扩展到 90 项。状态 critic 只能做预训练，same-state option 排序准确率最高 53.64%，
  未达到 65%，因此未启动 Manager/PPO。
- 依次否决三类一层结构：V113 phase slot 不是完整赛季策略；责任 BC 把多教师平均为一个
  动作头；lineage-only BC 又丢失功能阶段。Nested option×global-role V3 首次形成闭环，
  但正式 32 局的最好 option 仅 23/0/9、P10 2,941，未过 Gate A。
- Per-slot V4 暴露 teacher-role 标签泄漏：`STOP/买入/出售` 由当前动作反推 role，训练又把
  真值 role 喂入动作头；三个 option 在无安全 24 局中全败。扩充至 384 个教师执行对局、
  276,096 状态的 V5 虽把最好 option 提升到 6/0/2，但 P10 仅 521、仍有 2 个灾难局，证明
  数据不足不是唯一根因。
- V6 改为 causal latent-role：动作解码只使用模型预测 role，unit/market Router 均读取已
  执行前缀；首个 STOP 后提供吸收式尾部监督。数据 SHA256
  `c7b996dc5b5801faa19a0c7e709ccf5ee28ffa3830fdd8a923ab89b45f9d18c8`，checkpoint SHA256
  `ddc942b3d41177804a6163a3bde71d106daee9e6e8d0b7ca9d066df663e14dd2`。
- V6 无安全筛选三个 option 均 6/0/2，10-slot rate 已降至 0.56%–0.85%，但重复雇工导致
  灾难率 25%。只约束已确认失败动作（worker cap 4、reserve 0、step 671 后禁买）后，
  option1/2 均 7/0/1，P10 分别 2,372/2,845，仍低于 3,000 Gate A，不晋级、不启动 PPO。
- 下一唯一分支为冻结 V6 的 candidate-state DAgger：环境执行候选，Gold-Train 教师只在候选
  到达状态上标注不执行；目标是消除少数灾难轨迹。Gold-Dev/Blind 未访问，未提交 Kaggle。
- V7 DAgger 采集 64 局、46,016 个候选状态；V6 在该较大样本上仅 38/0/26，options1/2
  各 19/0/13、灾难率均 31.25%。合并后从零训练 V7，checkpoint SHA256
  `61fa2b774f0dc9ba37fa01a2a99e8f749004681b1c36e44c2eb0fbacaabc741e`；全新筛选两个
  option 均 0/0/8、灾难率 100%，`REJECT_COUNTERFACTUAL_TEACHER_STATE_MISMATCH`。
- 根因是 stateful 教师在自己未执行的候选历史上提供了不一致反事实标签。下一分支改用候选
  实际执行动作与真实终局回报做 KL 约束 AWR/IQL，自模仿高回报闭环；不再使用教师动作标签。
- V8 已从冻结 V6 在 20 个 fresh seed、两个 option、双座位、五层混合对手池采集 80 局
  真实候选动作，共 57,520 行；基线为 24/0/56、平均自身金币 3,848、灾难率 43.75%。
  训练前发现胜负回报会奖励低金币侥胜，故预注册复合效用：自身金币项 0.25、灾难惩罚 2.0，
  并把灾难轨迹 AWR 权重硬限制在 0.5；advantage 按 `option × opponent layer` 标准化。
- V8 使用 2 epoch、学习率 `1e-5`、KL 0.1 从冻结 V6 做实际动作 AWR；checkpoint SHA256
  `43e0115efcdadd2d5a30f9b9b59eb455cb43e689ec348d8172f295f913b435ce`，冻结参数最大变化 0，
  但当前仅为 `TRAINING_ARTIFACT_NOT_QUALIFIED`，必须先在相同 fresh seed/seat/opponent 上配对
  对比 V6，再决定是否进入 Gate A；Gold-Dev/Blind 未访问，未提交 Kaggle。
- V8 在 4 个全新 seed 上与冻结 V6 做同 option/seed/seat/Starter 配对筛选，32 场零错误。
  option1 为 5/0/3、P10 2,982、相对 V6 得分增益 0；option2 为 5/0/3、P10 3,142、
  相对 V6 得分 +25pp、自身金币 +2,328、灾难局 4→0。尽管 option2 的经济改善明确，
  两个 option 的绝对得分率都只有 62.5%，低于预注册 75% 生存线，故
  `REJECT_PAIRED_SCREEN`，不追加 16-seed 确认、不登记 expert。
- 结构性结论：真实动作 AWR 可以降低尾部风险，但以 V6 为初始化的小步更新仍是同一参数谱系，
  无法提供两个独立稳定专家。下一轮转向不继承 V6 参数的事件/日级宏动作 PPO：PPO 只选择
  生产路线、现金/雇工预算、出售风格和终局模式，确定性路线专家与状态安全执行器负责逐步落地。
- V9 正式登记为 `strategy_parent=null` 的 Event-Program PPO 独立谱系，执行计划见
  `v114_day_smdp_hmoe_ppo/V9_EVENT_PROGRAM_PPO_PLAN.md`。五头 Manager 从随机参数初始化；
  Production Program 与 Market Program 分开编译作物任务和市场订单；V6/V8 及历史金牌只作
  对手，禁止提供在线动作。当前处于 V9-0 合同实现，尚未训练、尚未资格认证。
- V9-0 已完成：事件现金读取、step 671 终局边界、五头 JAX Manager、masked joint log-prob、
  duration-aware GAE、确定性作物任务图和市场预算编译器均通过；V114 全量 156/156 测试通过。
  同 seed 两次完整赛季均执行 719 个动作、零违规、动作轨迹 SHA 一致、终局金币 4,343。
- V9-1 使用 8 个全新 seed、双座位、五个固定作物程序对 Starter 共 80 局。MELON、TOMATO、
  WHEAT、STRAWBERRY 均 16/0/0、零灾难；P10 分别 28,052、5,932、5,261、4,782。
  CARROT 仅 10/0/6、P10 2,933、4 个灾难局，单独淘汰。固定程序门要求至少两条生产线，
  实际 4 条通过，因此进入 V9-2 随机 masked Manager 生存门；这仍不是 PPO 或金牌认证。
- V9-2 随机五头 Manager 首轮在 8 个 fresh seed、双座位共 16 局中 0/0/16，平均金币
  417、灾难率 100%，但零运行错误/合同违规、五头覆盖率均 100%。审计发现空地错误地让
  生产线在已有跨日作物时仍可切换；只修复该通用状态机约束后，用另一组 8 seed 复验仍为
  0/0/16，平均金币升至 915，但灾难率仍 100%。
- 结论不是“网络不能训练”，而是五个高层职责同时均匀随机会先破坏完整经济闭环，无法提供
  有效 PPO 正反馈。按预注册失败分支停止继续针对已见 reward 打补丁，转入 V9-3：仅用 V9-1
  通过的 WHEAT/TOMATO/STRAWBERRY/MELON 四条独立程序采集日级状态，随机初始化 Manager
  做多程序 BC 预热，再以 fresh-seed on-policy SMDP PPO 更新；CARROT 保留网络输出维度但
  在 PPO 合格专家 mask 中禁用。Gold-Dev/Blind 未访问，未提交 Kaggle。
- V9-3a 用 64 局四程序数据训练随机初始化 Manager BC，1,792 条日级样本按 seed block
  隔离，验证联合准确率 97.32%。全新 8 seed 双座位 Starter 生存为 16/0/0，平均金币
  16,787、P10 5,828、零灾难；该 checkpoint 仅为安全 warm-start，不是 PPO/金牌。
- V9-3 PPO Iteration 1 使用 64 fresh seed × 双座位共 128 局、3,584 个 SMDP transition；
  easy 40/0/0，learnable 混合层 24/0/52，hard Gold 0/0/12，全部零灾难。首次 trainer
  审计发现无灾难时 constraint critic 随机残差仍推动 actor，原 checkpoint 作废；同数据、
  同参数仅修复该语义后重训，corrected checkpoint SHA256
  `be8be93368b562021b4e3d25ff8346666b0c2b5445916dcaba154ee7251ceb2c`，exact KL 3.15e-5。
- corrected PPO 与 BC 在 Starter/Stage17/Stage20 各 8 fresh seed、双座位配对。48 对胜负
  全不变、零灾难；Stage17 自身金币 +1,366.9，Stage20 自身金币 +1,182，但 Stage20
  金币差 −5,859.4、CI `[-13,865.3,0]`，因为对手增益更大。Iteration 1 只通过最小生存门，
  不晋升 incumbent。
- 根因：`tanh(margin/10000)` 对大额负分差饱和，且 joint PPO 把一次生产线选择与每日预算
  head 混在同一 ratio，关键初始决策被 28 个日级 transition 稀释。Iteration 2 改为相对财富
  份额终局奖励 + 仅对有两个以上合法选择的 head 做独立 clipped PPO；继续从 BC incumbent
  用全新 on-policy seed 采集，不复用 Iteration 1 数据。Dev/Blind 未访问，未提交 Kaggle。
- Iteration 2 完成 64 fresh seed × 双座位共 128 局、3,584 个日级 transition，easy
  40/0/0、learnable 24/0/52、hard Gold 0/0/12，零错误、零灾难。head-wise PPO checkpoint
  SHA256 `da097d3c05d18fd64a91ef86c8e21c5c064a60f0193444e0d24649feedc4f4f0`；生产线头
  128 个有效决策、exact KL 0.000475，其余头 KL 均低于 3.2e-6。
- 与 BC incumbent 在 Starter、Stage17、Stage20、V32 Gold 各 8 fresh seed × 双座位严格
  配对，共 64 局/模型。所有逐局动作、胜负、自身金币和金币差完全相同，故按预注册的“必须
  产生正向行为或结果变化”门槛 `REJECT_NO_OBSERVABLE_POLICY_CHANGE`；不更新 incumbent，
  不访问 Gold-Dev/Blind，不提交 Kaggle。
- 根因不是 reward 再次错误，而是固定 4 epoch 在允许 KL 0.01 的情况下仅走到 0.000475，
  没有跨过任何实际高层决策边界。Iteration 3 改为按有效 head 自适应信赖域：生产线头必须
  达到预注册的最小行为 KL，同时所有 head 不得越过最大 KL，超限自动回滚；训练停止条件由
  可观测策略变化决定，不再由机械 epoch 数决定。
- 独立审查发现 critic 仍可能经共享 trunk 污染其他 actor head，因此首个 Iteration 3 尝试在
  checkpoint 写出前中止，不计证据。修复后仅允许 `production_line_head` 与两个 critic head
  更新，trunk 和其余四个 actor head 按位冻结；每个 minibatch 检查全量 KL 并可恢复完整
  TrainState。22 项定向回归通过。
- 修复版 Iteration 3 在第 11 epoch、第 145 minibatch 达到生产头 KL 0.002001 后停止，
  checkpoint SHA256 `17a55bfa6e23c2f46041f452d3fac62c4d3dd66fe5c3b3c339dc4a884eb186d8`；
  冻结根最大变化均为 0，训练状态固定随机数下 8/128 个路线选择发生变化。
- fresh 配对门控中 Starter、Stage17、V32 Gold 共 48 局完全不变；Stage20 的 16 局仍
  0/0/16，候选自身金币 +574.4，但金币差 −1,210.8、CI `[-3,804.0,+171.6]`，表明对手
  增益更大。按困难分差不得退化的预注册门槛 `REJECT_HARD_MARGIN_REGRESSION`，BC 继续作为
  incumbent，不访问 Dev/Blind，不提交 Kaggle。
- 两轮证据已排除“只是 KL 太小”：根因是每个 seed 只采样一条路线，终局回报无法回答同一
  初始状态下其他三条路线的相对价值。Iteration 4 改为同 seed/seat/opponent 强制执行四条
  完整生产路线，形成 route-level counterfactual Q，再以路线相对 advantage 更新生产 Router；
  不再继续提高 KL 或对父代模型打补丁。
- Iteration 4 用 64 fresh seed × 双座位 × 四路线完成 512 场反事实比赛，零错误；128/128
  context 均有优于旧 Router 期望值的路线，平均 oracle utility gain `+0.1687`。utility 最优
  路线为 STRAWBERRY 36 次、MELON 92 次，旧 Router 四条路线仍近似各 25%。
- full-information clipped PPO 只更新生产头，在 KL 0.002036 停止；checkpoint SHA256
  `3237dcbe68df9b5b0d2186ffff033dea714952061a9403a901ab6da3633adb39`。stochastic screen
  仅 Stage20 一个 seed block 改变，金币差 −2,166.6，否决。
- 为区分训练探索与服务语义，在不改权重的前提下新增 masked-argmax serving。确定性 Router
  从 BC 的全 WHEAT 变为全 STRAWBERRY：Starter 与 Stage17 的 16/16 配对全部正向，V32
  自身金币 16/16 提高、平均分差 +25,451；但 Stage20 虽新增 2 胜、自身金币 +5,997，
  分差却 −27,968、CI `[-56,170,-2,296]`，明确退化，仍不晋级。
- 信息边界结论：step 0 的初始状态无法识别隐藏的对手行为家族，故线性生产 Router 只能塌缩
  为全局单一路线。Iteration 5 新建“24-step 安全侦察 expert → day-1 对手/市场路径特征 →
  route PPO”的延迟决策结构；先过侦察生存与信息增益门，再采集四路线反事实，不直接调权重。
- Iteration 5 的 24-step PASS 侦察在 Starter/Stage20 共 64 局中保持 719/719 调用、零违规、
  综合 P10 6,038；同 opponent/seed/seat 的四路线 day-1 特征逐位一致。首批两个 Random
  对手因内部 RNG 未绑定环境 seed 导致 32 个反事实上下文全部污染，原始 128 局只保留审计，
  另用 Stage21 与 V78 的 128 局 fresh 数据替换，未复用 seed、未绕过门控。
- 干净数据含 128 个 day-1 context、512 场四路线结果，平均 oracle utility gain 0.200；效用
  最优路线为 WHEAT 25、STRAWBERRY 18、MELON 85。只更新 production head 的层归一化
  full-information PPO 在 exact KL 0.001015 停止，checkpoint SHA256
  `aa40d756d2ae147f0d063a18edd78e4c5f4f044cac9726095c3f3c9f1478c670`。
- 训练后 BC 的 128/128 WHEAT 变为 127/128 STRAWBERRY、1/128 MELON，仍是全局换路线而
  非对手条件 Router。32 fresh seed、双座位配对中 pooled score +1.5625pp、自身金币 +5,318；
  V32 分差 +29,920、CI `[+10,713,+48,427]`，但仍 0/0/16。
- 决定性否决来自 Stage20：候选虽新增 1 胜、自身金币 +841，分差却 −40,307，CI
  `[−59,302,−22,002]`，15/16 配对为负。故 `REJECT_HARD_STAGE20_MARGIN_REGRESSION`，
  不晋级、不访问 Gold-Dev/Blind、不提交 Kaggle。
- 第一性原理结论：延迟观测可行，但冻结 trunk 的线性生产头学不到条件路由；更关键的是四条
  单作物专家对 V32/V76 的 oracle 仍全败，继续在弱专家间调 Router 不可能成为金牌。
  Iteration 6 转向独立的共享市场干预/商品级出售控制专家，先要求至少一个低层 expert 在
  强对手 fresh-seed 门控中产生真实胜局或非负分差，再允许新的 Router PPO。
- Iteration 6 完成独立 Town Demand Phase Trader 的机制门：Stage20 与 V32 各 4 个 fresh
  seed、双座位、WHEAT/STRAWBERRY × 三种出售时机，共 96 局，零错误、零违规。相对逐步
  立即出售，需求结算后出售在四个“商品 × 对手”组合中均逐局提高分差：Stage20 的 WHEAT
  `+1,889.8`、STRAWBERRY `+388.5`，V32 分别 `+122.6`、`+304.1`；seed-block bootstrap
  95% CI 下界均大于零，自身金币不退化、胜局不减少，故按已登记的宽松门槛
  `PASS_MECHANISM_GATE_NOT_GOLD`。但每个“对手 × 商品”只有 4 个独立 seed block，4/4
  同向的单侧精确符号检验 `p=0.0625`；因此它只是待独立复验的方向性信号，不是已验证机制。
- 日末集中倾销跨商品不稳定：WHEAT 按宽松预注册门通过，但 STRAWBERRY 对 Stage20 分差
  `−6,858.8` 且胜局 2→1，对 V32 分差 `−4,520.5`，说明共享市场冲击可能向对手转移经济
  利益。尽管 POST_DEMAND 市场时机值得复验，V32 的 48 局
  仍全败、绝对分差仍深负；下一轮只扩展数量比例和队列位置反事实，并训练有边界的 Market
  Residual PPO；探索集不能用于宣布成功，之后必须用独立 16-seed、多谱系对手确认，且不能
  登记 Router 或金牌。Gold-Dev/Blind 未访问，未提交 Kaggle。
- Iteration 7 用 Stage20/V32 各 8 个 fresh seed、双座位，对 WHEAT/STRAWBERRY 的
  `POST_DEMAND × {25%,50%,100%} × {FRONT,BACK}` 共完成 384 局，零错误、零违规。
  没有任何非基线变体同时改善两个对手：最接近的 STRAWBERRY 50% FRONT 对 Stage20
  分差 `+98.8`，但对 V32 `−7.9`，pooled seed-block bootstrap CI
  `[−214.6,+328.6]`，故 `REJECT_ORACLE_GATE_NO_PPO_TRAINING`。
- 动作等价性被实证确认：STRAWBERRY 100% BACK 与 FRONT 的 32/32 局收益逐局完全一致；
  WHEAT 的 pooled 改善仅 `+1.2`，CI `[−0.4,+2.5]`。全部 V32 192 局仍为失败，说明市场
  执行微调无法弥补生产规模、多商品组合和资金周转差距。按预注册失败分支，不训练会拟合噪声的
  Market Residual PPO，下一轮构造 `strategy_parent=null` 的独立多商品企业生产专家。
  Gold-Dev/Blind 未访问，未提交 Kaggle。
- Iteration 9 新建 `strategy_parent=null` 的市场暴露自适应禽业：6 禽舍、公开库存净流量估计、
  动态现金作物、饲料储备与分阶段雇工。Starter 16 局全胜，均值/P10 `40,887/39,339`；
  每局放置 6 鹅、卖出 276 鸡蛋和至少 4 类商品，零灾难。
- 对 Stage20 实现首个决定性专项突破：16/0/0，均值 `39,335`；相对 DAIRY/WOOL/MELON/
  STRAWBERRY 四控制逐 context 包络，16/16 配对改善，分差 `+67,745`、自身 `+19,338`、
  对手 `−48,406`。登记为 `stage20_exposure_adaptive_poultry` 专项专家/训练对手，但不是金牌。
- 对 V32 仍 0/0/16。候选自身相对包络 `+14,843`，但对手 `+32,997`，净分差
  `−18,154`，仅 5/16 配对改善。已消耗 seed 的逐动作诊断显示候选买入 137 小麦，而 V32
  买入 1,690、卖出 1,877；推断市场饲料购买可能把价格路径价值转给 V32，尚待因果验证。
  因此总体 `REJECT_GENERAL_STAGE_B_REGISTER_STAGE20_SPECIALIST_ONLY`，不训练 Router；下一轮
  构造自给饲料、肥料内部循环的独立禽业专家。Gold-Dev/Blind 未访问，未提交 Kaggle。
- Iteration 8 从官方 crop/animal/market 语义重新构造独立企业任务图，不继承历史 agent 动作。
  Starter Stage A 共 48 局：DAIRY_BERRY 与 WOOL_MELON 都 16/0/0、零灾难，每局出售四类
  商品，均值/P10 分别 `22,527/17,455` 与 `27,270/26,260`；GRAIN_MELON 因均值
  `15,740 < 18,000` 淘汰。首次证明 V114 新谱系能完整执行作物、牲畜、饲料、肥料、土地、
  雇工和终局兑现闭环。
- Stage B 在 Stage20/V32 各 8 fresh seed、双座位，对同 context 的 MELON/STRAWBERRY
  单作物包络比较，共 128 局。DAIRY 对 Stage20 分差 `+1,480` 但仅 8/16 改善；对 V32
  自身金币 `−4,546`、分差 `−5,829` 且有 4 个灾难局。WOOL 对 Stage20 分差
  `+19,707`，但仅 8/16 改善且胜局 2→1；对 V32 自身 `−2,044`、分差 `−26,916`，
  14/16 配对退化。零候选通过，故 `REJECT_ROUTER_PPO_GATE`，不训练只有弱专家的 Router。
- 第一性原理结论：多商品闭环解决了吞吐问题，但固定商品暴露并不等于稳健；强共享市场对手可
  让同一扩张计划损害自身经济或把价格路径价值转给对手。下一轮新建独立的“市场竞争暴露自适应
  企业”谱系，基于公开需求、库存/价格压力和可观测净流量先分配产能，再承诺土地与牲畜。
  Gold-Dev/Blind 未访问，未提交 Kaggle。

### V114 V4-2：L0/L1/L2 三级基础专家门控迁移与首次正式结果

- 2026-08-30 起基础专家改用三级门控：L0 Starter 生存、L1 行为去重 V1–V10 基础能力均为
  硬门；Stage20/V32/V37 降为 L2 影子诊断。Iteration 8/9 的强对手结果完整保留，但不再追溯
  否决基础专家。协议迁移见 `model_data/v114_day_smdp_hmoe_ppo/manifests/protocol_migration_001.json`。
- L1 对手在任何 fresh 结果前按归档 SHA、成员 SHA、谱系和已暴露 seed 行为去重并冻结：
  V2 生存闭环、V5-rule 动物/多商品、V5-PPO-topdays 商品级出售、V8 Kawa 五路线；四者各
  占 8/32 seed block。V1/V2、V3/V5-PPO/V6、V4/V5/V7、V8/V9 近克隆不得重复加权；V10
  是组合 Router 而非独立 agent，不进入 L1。
- 修正 Manager 审计口径：旧程序把终局 48 个 turn 全部计为重路由，得到 76 次/局；现在
  只计 28 个正常日界与一次吸收式终局 option，共 29 次，48 个终局执行 turn 单列。修正不改
  动作语义，相关定向测试全部通过。
- 三个原创规则基础程序各补 8 个 fresh Starter seed，与原 8 个合并后均达到 16 seed、双座位
  32 局：DAIRY、WOOL、POULTRY 都 32/0/0、零灾难，P10 分别 17,455、26,676、39,191，
  正式通过 L0。
- 固定 L1 使用另一组 32 fresh seed，三个候选各 64 局、合计 192 局，零运行错误。三者均
  0/0/64，未登记 `FOUNDATION_EXPERT_CANDIDATE`：DAIRY 均值/P10 15,571/4,584，WOOL
  4,767/2,110 且 19 个灾难局，POULTRY 17,408/14,043；对手均值约 14.8万–15.2万。
  Poultry 的 EGG 职责量 CI `[274,274]` 为正但仍无胜局，证明职责产出不等于完整经济能力。
- 第一性原理裁决：差距来自基础生产、劳动吞吐、库存周转和商店条件路线效率缺失，不可能靠
  每日最多四次的 bounded Residual 补齐。暂停未消耗 fresh seed 的 Supply Flood Iteration 10；
  下一分支训练两个互相独立的谱系基础专家：Adaptive 与 Kawa 分开做 phase-conditioned 完整
  闭环 BC，再以自身低熵 rollout 做 outcome-weighted AWR。历史 agent 只离线生成教师闭环，
  禁止在线动作回退；通过新的 fresh L0/L1 后才冻结并进入 Residual PPO。Gold-Dev/Blind
  未访问，未提交 Kaggle。
### V114 V4-2：V10 单谱系完整闭环 BC（2026-08-30）

- 预注册：两条参数独立、从零初始化的 history32 timed autoregressive HMoE；V10A 只用
  `demand-timing-preemption` 离线闭环轨迹，V10B 只用 `procurement-slot-ordering`，每条
  92,032 step、64 seed block、128 局。教师只提供离线监督，线上无历史 Agent fallback。
- 训练：各 12 epoch。V10A/V10B 最佳验证 loss 分别为 `0.34198/0.29505`；该指标只作工程
  诊断，不用于资格判断。checkpoint SHA 分别为 `414df6e7...14df9`、`448cea81...e3486`。
- 已暴露 seed 闭环 Screen：两条均 `15/0/1`，V10A P10=`10,194`，V10B P10=`5,829`；
  仅允许进入 fresh L0，不视为新证据。
- 正式 L0：V10A `28/0/4`、P10=`2,755`、灾难 `4/32`，淘汰；V10B `30/0/2`、
  P10=`3,757`、灾难 `1/32`，通过但尚未成为 foundation expert。
- 正式 L1：V10B 对冻结的 V2/V5-rule/V5-PPO/V8 四个代表共 64 局为 `0/0/64`；自身均值
  `7,945.69`、P10=`1,452`，对手均值 `142,647.53`，灾难 `11/64`，淘汰，不登记
  `FOUNDATION_EXPERT_CANDIDATE`，不得进入 Residual PPO。
- 第一性原理结论：单谱系 BC 已能复制完整闭环，但复制到的是约 8k–40k 的低吞吐分布，仍比
  本地基础模型低一个数量级。下一轮不调阈值、不修 V10 参数，切换到 V2/V8 官方 Replay 的
  真实高吞吐轨迹，分别构建独立 foundation 数据集。

### V114 V4-2：V11 V2/V8 真实 Replay 单谱系 BC（2026-08-30）

- 数据严格只取提交 Agent 的真实座位，observation `t` 对齐 action `t+1`，每局 719 行；V2
  91 局/65,429 行，V8 104 局/74,776 行。两个数据集不混合，checkpoint 从零训练，Replay
  文件束、同步清单、教师代码和数据集均固定 SHA，线上无历史 Agent fallback。
- 两条 12-epoch BC 的最佳验证 loss 为 `0.47961/0.60025`，单位动作准确率
  `94.25%/91.89%`、市场 token 准确率 `98.88%/98.56%`；这些只属 teacher-forced 工程指标。
- 首次已暴露 seed Screen 发现 train/deploy phase mismatch：serving Router 没按 step 480
  从采购切到出售。保留失败结果后，只做一次不改参数的预注册 phase schedule 语义修复，并在
  完全相同 seed 复核；未消耗 V11 fresh L0/L1。
- 修复后 V11A 为 `0/0/16`，均值/P10 `246/0`、16 个灾难局；V11B 为 `8/0/8`，均值/P10
  `3,475/1,059`、4 个灾难局。两者均完整运行、无引擎错误，但每局仍产生约 60–89 次出售与
  205–242 次采购/扩张。
- 裁决：`REJECT_STEPWISE_MARKET_ACTION_COMPOUNDING`。即使 market token 单槽准确率约 98.5%，
  719 个 turn 上反复生成完整订单序列仍会把低概率错误复利成现金和库存崩溃；固定 phase 也无法
  修复错误动作抽象。V11 不进入 fresh L0/L1，不登记 foundation candidate，不启动 Residual。
  下一轮改为事件触发的稀疏市场 option：PPO 只在商店/成熟/库存/现金/终局事件上决定一次订单
  意图与预算，执行器持有并终止 option；非事件 turn 强制无市场动作。
- 数据复核：V2/V8 原始 Replay 平均每局约 `968/959` 条市场指令、`277/277` 次 HIRE 和
  `496/493` 次 SELL，说明教师用大量重复 primitive 表达少量经营意图；V11 不应把它们当成
  独立决策。另修正 evaluator 的采购统计：旧口径只计 `BUY/HIRE/BUY_LAND`，漏掉
  `BUY_SEED/BUY_PRODUCT/BUY_ANIMAL`；历史 JSON 保持原样，新报告使用完整采购口径。

### V114 V4-2：V12 Event-Ledger HMoE（2026-08-30，进行中）

- 新谱系预注册 SHA=`ff0e6def...d222b6`，`strategy_parent=null`，不继承 V11/历史 checkpoint，
  线上历史 Agent fallback 禁止。市场动作从逐 turn queue 改为事件级绝对目标和交易账本；单位层
  改为跨 step task/target/完成状态，Residual 移到 Manager 之后。
- G0 静态门已通过：100 次相同事件输入仅 1 次 commit；23 个非事件 turn 市场订单为 0；
  终局采购订单为 0；season budget 上限 600 的压力测试最终支出恰为 600；源码历史动作源命中 0。
  报告 SHA=`831e3e04...19bfb`，10 个定向测试全部通过。
- 当前证据只说明防重复和跨 turn 预算账本成立，状态仍为
  `G0_ONLY_NOT_UNIT_SKILL_NOT_EVENT_MARKET_NOT_FOUNDATION_NOT_GOLD`。下一步 G1 从 Replay
  提取可持有的单位任务，先短 horizon BC，再在 market 强制为空的任务环境做 on-policy PPO。

### V114 数据硬边界二次收紧（2026-08-30，立即生效）

- 全局实际对局日期下限仍为 `2026-08-20`，但官方主数据进一步收紧为只允许
  `model_data/kaggriculture_episodes_index/date>=2026-08-25`；8/20–8/24 官方分区只可审计，禁止
  进入特征、训练、Dev、Blind、门控和晋级证据。
- 我方线上数据仍按实际对局日期 `>=2026-08-20`，只允许 Kaggle CLI 枚举和下载；每局必须登记
  submission/version/episode/date/seat、Replay SHA、agent/package SHA、agent-log SHA。字段缺失时
  fail closed，不进入训练或晋级证据。
- 全局去重键继续固定为 `episode_id + replay_sha256`；官方合格分区按日期切分，最新完整日期为
  Blind、次新日期为 Dev、其余 8/25+ 日期为 Train。Blind 最终确认前禁止读取内容。
- 旧 V2/V8 Replay、旧 V12 unit/event-market checkpoint 与所有旧口径评测继续保持
  `STALE_RULE_DISTRIBUTION_NOT_PROMOTABLE`。先输出样本量、日期/版本覆盖、重复/冲突/失败数与 SHA，
  registry 合格后才能从随机初始化重建 unit/market/opponent features 和 checkpoint。
- 当前未发现旧训练进程；禁止重启 V8 AWR 或旧 checkpoint 大评测。未经用户另行授权不得提交 Kaggle。

#### 严格口径数据盘点与注册结果

- 官方 `date>=2026-08-25` 注册表已 `QUALIFIED`：共 3,414 局，Train/Dev/Blind=
  `2,071/676/667`，重复 0、episode 异 SHA 冲突 0、失败 0；注册表 SHA=
  `36292a7051c1941fb3f7fba2ff8d4410eb4cac4fc2786db70ecd60c673ef28b4`。
- Kaggle CLI 枚举到实际对局日期 `>=2026-08-20` 的 33 个我方提交版本、2,293 个唯一 episode；
  806 行具备唯一 seat、Replay SHA、agent/package SHA 和 agent-log SHA，可进入合格子集。35 局 seat
  歧义、218 行缺精确 agent/package SHA、1,451 行缺 agent-log SHA，合计 1,486 行按 fail-closed
  隔离；CLI 源注册表状态为 `PARTIAL_FAIL_CLOSED`，SHA=
  `a6b7903fd916b0192d144a69880e8f9be8a9404ba24a8b45392035a315eef918`。
- 两源按 `episode_id + replay_sha256` 合并后合格 4,220 局：Train/Dev/Blind=
  `2,499/911/810`，官方 3,414、我方 806，跨源重复 0、episode 异 SHA 冲突 0。8/29 起冻结为
  Blind，8/30 新增局只进 Blind，不允许向 Dev/Train 回迁；合并注册表 SHA=
  `3fecb575e1db61a48014346b7aa0fc6d4eeab472f535a85f53110cedac94c1d5`。
- 数据注册门已通过，后续仅允许从合并注册表的 Train/Dev 条目从零重建特征和 checkpoint；Blind
  内容尚未读取。旧 checkpoint 和旧门控结论继续保持
  `STALE_RULE_DISTRIBUTION_NOT_PROMOTABLE`，不得因本次注册完成而恢复资格。

### Replay 两级置信度最终口径与终止记录（2026-08-30）

- 用户最终指定 Replay 只有两类准入，统一要求实际对局日期 `>=2026-08-20` 且与当前线上规则配置
  一致。此前“官方 index 仅限 8/25+”的表述由本节覆盖：8/20+ 官方按日 Replay 可以进入次级确认
  面板，但必须先完成当前规则配置校验。
- 高置信度主面板为本账号已提交模型产生的线上 Replay，包括 CLI 增量下载和本地已保存的历史提交
  对局；身份与 SHA 完整后保留使用。正式评测、门控和晋级首先看该面板。
- 次高置信度面板为官方 8/20+ 按日 Replay，仅用于扩大商店组合、需求轨迹和对手覆盖，并作独立
  确认。两面板必须分开统计和报告；官方数据不能靠更多局数、合并指标或训练权重覆盖主面板失败。
- 两源继续按 `episode_id + replay_sha256` 全局去重，并在各自面板内部按日期切 Train/Dev/Blind。
- 用户随后明确要求终止执行：所有训练、评测、下载和数据重建已停止，未启动 market 正式训练，
  未提交 Kaggle。unit BC 正式运行在 epoch 1 后被中止，已落盘 checkpoint SHA=
  `120a75ce57f9bc8f536528fcdbb0e0059e29e662edfcdce7c0dc30df24928d9c`，状态固定为
  `ABORTED_BY_USER_NOT_PROMOTABLE`，不得作为 Foundation、incumbent、门控或晋级证据。
- 没有新的用户明确重启命令前，不得自行启动任何后台研究任务。

### V120 活动金牌池门控（2026-09-02）

- 用户明确重启本轮评测，并指定 V120 为新的金牌级策略门控；没有重启训练、Replay 下载或研究搜索。
- 清单为旧总览的 19 个行为去重金牌，加上已通过 `GOAL_COMPLETE` 审计但尚未写回旧总览的 V123；
  V21/V29 只计一次。统一使用 32 个 fresh seed、双席位，共 64 场/候选、1,280 场总计。
- 门槛为纯胜率 `<50%` 淘汰，平局与错误均不计胜。1,280/1,280 场完成、错误 0、全部 719 次调用；
  V123 `64/0/0`、平均分差 `+8,433.11`，唯一保留。其余 19 个候选为 0% 或 3.125%，全部退出
  活动 V120 门控金牌池；历史金牌证据不删除、不改写。
- 决策：活动门控集合为 `V120 + V123`。该结论只覆盖本地 kagsim 1.32.7 相对门；线上 Rating、
  账号线上 Replay 主面板和官方按日确认面板继续独立。完整证据见
  `model_data/gates/v120_gold_pool_64_20260902/REPORT.md`。

### V123 对 V21/V29、V76 抗过拟合复核（2026-09-02）

- 使用上一轮实际测试的冻结 V123 release candidate（SHA `825e63b1...18652`），避开评测期间发生
  并发更新的工作区 V123 入口；没有覆盖或混用未冻结新包。
- 两组共用 32 个全新 seed，每组双席位 64 场。V123 对 V21/V29 为 `28/0/36`，对 V76 也是
  `28/0/36`；纯胜率均为 `43.75%`，seat 0/1 均为 14/32，错误 0。
- 对相同 64 个 seed-seat 任务，两组胜负结果完全一致，平均分差只差 `0.8125`，说明 V21/V29 与
  V76 在该面板上是近等价旧谱系，不能冒充两个独立压力源。
- 结论：`CROSS_OPPONENT_ROBUSTNESS_NOT_ESTABLISHED`。每组 Wilson 95% 区间
  `[32.29%,55.91%]` 仍覆盖 50%，因此这是明确的过拟合警报而非总体胜率低于 50% 的统计定论；
  本轮未预设新淘汰线，不自动改变活动金牌池。完整证据见
  `model_data/gates/v123_anti_overfit_v21_v76_64_20260902/REPORT.md`。

### 在线调度器执行密度墙：15 连败终局归档（2026-09-05/06）

- 目标：一个模型打全段位（用户明令不许分段接力），调度器+规则浅树同时拿下 tape 带碾压与金牌区稳态。
- 15 个已证伪方向（勿重试）：dist_pow、保底任务、区域聚簇、premium_zone 分区、全员救火、单工人救火、
  种植波次、固定巡回、错峰回避、显式拦截卖单、入库频率×2、商店条件闸门、到访批处理、顺路浇水、
  带状巡回目标层（V37）。共同死因：对战中盘 MOVE 占 56% 动作槽，调度器产出只有母带的 61-85%。
- V34（需求对齐+速率匹配卖出）价位分布已反超（高位成交 50% vs 对手 32%）但 margin 仍 -27.6k；
  duel_search 坐标下降全参数无正向（见 v34_demand_align/duel_search.log）。
- V36（全天排程重写）停在 20-27k 新生儿瘫痪态（动物 d2-4 饿死链，饲料现金闭环断）。
- 路线重解读（已向用户摊牌）：Crop Dusta 的"调度器+规则浅树"很可能运行在开发机上，线上跑的是
  离线优化后的准 tape；其适应是提交级（每日生成反制带上传），不是局内级。
- 当前主攻改为「每日母带再生成管线」：从当日 top 池/自家对局 replay 提取最强带 → 叠武器层
  （V17 护栏+扰动+fill+择时 nudge）→ 门控 → 换血上线。V26 换血流程 2 小时已验证。

### 重大勘误：V26/V32 换血从未生效，线上一直在跑 OceanMix 老带（2026-09-06）

- 铁证：`sub:` 口径测 V32 实际行为指纹（STRAW 254/WOOL 181/WHEAT 554/zero 29）与
  `tape_OceanMix_104547425.json` 完全一致，与 fam_F（256/180/564/11）不符。
- 根因：V120 执行核 `_v120_distilled_expert` 每次调用执行
  `global _ACTIONS; _ACTIONS = _V120_DISTILLED_ROUTE`——V26 build 在文件尾静态覆盖
  `_ACTIONS = _F_ACTIONS` 会被每步运行时重置冲掉。换带必须同时覆盖 `_V120_DISTILLED_ROUTE`。
- 二次发现：即使修复重置源，异源带过 V120 核仍崩/损耗（cand_2 过核 52k、fam_F 过核 192.0k
  vs OceanMix 过核 197.9k）——核与 OceanMix 带深度耦合，「换血」在该核上是伪命题。
- 含义修正：线上 V26-a30(1971)/a53(1882)/V32 的全部成绩 = OceanMix(裸 196.9k)+武器层；
  扰动军备曲线、门控胜率等结论仍有效（测的就是真实行为），但「fam_F 已上线」为假，
  fam_F/cand_2 的对轰特性从未被线上验证。
- 出路 V39（纯 tape 骨架+武器层，绕开 V120 核）：cand_2 异构带（198.1k，自带扰动开局，
  零卖出空窗=1）+护栏/fill/MM。两个适配点：①带自带扰动 → 关武器层叠加扰动
  （否则双买双卖+market[:10] 截断挤掉甜瓜种子单，崩至 41.7k）；②cand_2 依赖 t1
  「先卖48麦回笼→再买」严格顺序 → 关护栏 t≤1 市场单重排（否则现金链断，90-105k）。
  修复后单人产出 197.4-198.2k 与裸带一致，武器层保留。

### V41 玻璃刀：fam_F 纯骨架 + LEAD 先手卖单（2026-09-06）

- V41 = 纯 tape 骨架(fam_F 原带 13/8) + V17 动物护栏(关插单扰动/关排序) + LEAD + fill + MM。
- 扰动量弱行扫描(fam_F/pert_1/Andrey/Jesse, 32 局)：13/8=19/32 ≫ 30/25=14/32 ≫ 53/48=6/32。
  当前 meta 扰动型互杀，无叠加扰动收渔翁利；43/38 对无扰动海洋是屠刀(fam_B 打到 0)但对
  扰动型自爆——两头不可兼得，选 13/8。
- LEAD 层(提前一步抢挂 next-step 卖单)曾因骨架里 `_selected_route` 是字符串而
  `_selected_route(obs)` 抛异常被 except 吞掉，从未生效（又一例静默失效）。修复后：
  **fam_F 镜像局 4/8 → 8/8**（先手卖单抢占价格窗口，镜像局决定性优势），其余行无回归，
  单人产出仅 -0.2k。
- 门控（4 seed 双席位 96 局）：V32 基准 75/96=78.1% → v41 无 LEAD 77/96=80.2% →
  **v41-LEAD 81/96=84.4%**。keiz 8/8(+25.5k)、pert_1 6/8、镜像 8/8；
  余弱行 Jesse 6/8、Andrey 3/8、fam_A 6/8、fam_E 4/8（margin<5k 细刃局）。
- 提交：UTC 09-05 日限额满(5/5)，submit_when_quota.sh 守护每 30min 重试，包已升级 LEAD 版。

### 微变体轮换弹药库 + 翻译器离线证据（2026-09-06 凌晨）

- make_variant.py（v41_famF_glass/）：对 fam_F 带做保产出微扰（卖单拆分/小单延迟/开局买量±1），
  合格线 tape: 口径 3 seed min>=197k。26 次尝试出 3 个合格变体（famF_var_382c261c39 /
  5af1d02af0 / 621efa65ad，产出 198,157-198,160 与原带持平）。合格率仅 12%——带自洽性强，
  多数微扰掉产出 3k-100k，验证门槛必要。pack_variant.py 一键打包变体为待提交包（终验通过：
  变体 621e 过骨架 sub: 口径 197,965 满产指纹）。防识别轮换弹药就绪。
- 翻译器离线证据（v43_translator/EVIDENCE.md）：本游戏农场独立，对手只能通过市场影响我方，
  "死走位"真实来源是开局资源被抢后的级联失效（动物侧已由 V17 护栏修复）。V41 在 8 seed
  矩阵的全部败局（fam_E 10 败/pert_1 8 败/cand_0 5 败）中产出指纹均为满产
  （STRAW 255-256/WOOL 180）——**没有一场败局源于执行失效**，输在产出结构 vs 当局市场的
  错配（带选择问题，属开发机侧调度器职责）。翻译器对 V41 离线预期收益≈0，
  待 14:00 线上复盘确认后定级。
- 定时任务：08:05 提交 V41（crontab 8:02/8:32/9:02 三重冗余+幂等防重），14:00 六小时对局
  复盘+翻译器线上证据补充。

### 每日母带再生成管线固化（daily_loop/rebirth.py，2026-09-06 凌晨）

- 一条命令完成：增量拉在役 slot replay → 提取 bank>95k 强对手带 → tape: 口径 3 seed
  单人产出验证(>=197k) → 与带库 300 步重合率家族比对(<60% 判新家族) → 候选清单+
  推荐动作(推荐换血评估/入库备用/淘汰)，报告追加 rebirth_report.md。
- 不自动提交、不自动换血，决策留给主会话。与 make_variant.py/pack_variant.py 组成
  完整换代链：新带发现 → 门控 → 打包 → (人工确认)提交。

### 管线首跑捕获下一代母带候选 rb_7925cb146f（2026-09-06 凌晨）

- rebirth.py 首跑（V32 slot 35 局新 replay）：7 候选，6 淘汰，1 推荐——rb_7925cb146f
  （Ronnie Atuhaire，单人 197,777，与全库带重合 ≤33% 新家族）。
- 结构：开局与 fam_F 完全同款（免疫开局扰动），中盘重构为少草莓多羊毛（STRAW 233/WOOL 192），
  疑似反 fam_F 特化带——v41 对它仅 2/8（满产但结构性输），是「结构级反制」的实锤样本，
  微变体轮换防不了这类反制，已纳入永久门控池。
- 以彼之带还彼之身：rb_7925 装入 v41 骨架后单人 **198,463**（全场最高完整包，空窗多故
  武器层增益大）。8 seed 全矩阵 **162/192=84.4%**（v41 82.8%），行剖面互补：
  rb 版修复 v41 三弱行（fam_E 6→10/16、pert_1 8→10/16、fam_D 14→16/16），
  v41 独占 fam_F 镜像 16/16（rb 版 10/16）；头对头 8/16 纯平。
- 决策：8:05 仍提交 v41（验证链更长+镜像行契合海洋主流）；rb7925 版
  （v41_famF_glass/variant_7925cb146f/submission.tar.gz）为第二发弹药，v41 上线表现
  确认后可提交占双 slot——v41 打 fam_F 海洋、rb 版打结构流，互补覆盖。

- rb7925 版验证链补齐（与 v41 同等完备）：现役带 18/24（cand_0 硬币局 2/8+224、
  cand_1 8/8、cand_2 8/8 打到 32k）；对 V32 现役头对头 11/16。
  最终双弹药档案：v41（8seed 82.8%、现役 19/24、vs V32 14/16、镜像 16/16）先发；
  rb7925 版（8seed 84.4%、现役 18/24、vs V32 11/16、修复三弱行）二发。
  幂等提交守护已重挂（15min/次），与 crontab 8:02/8:32/9:02、定时任务 8:05 三机制
  并行，防重靠脚本内"列表已有 v41 即跳过"。

### 双弹药上线（2026-09-06 10:10 本地 / UTC 02:10）

- **56044730 = v41**（fam_F 纯骨架+护栏/LEAD/fill/MM）、**56044732 = v41-rb7925**（反 fam_F
  母带+同款武器层）双双提交成功。三 slot 在役：V32(最后见 1949 仍在涨)/v41/rb7925。
- 提交时间线复盘：限额确于 UTC 午夜(本地 08:00)重置，但夜间四重机制全部脱靶——守护 07:17
  用完 20 次重试退出（差 43 分钟）、macOS cron 疑被权限拦截未执行、8:05 定时任务未见执行痕迹；
  最终 10:09 手动提交成功。教训：守护重试次数要按"距重置时刻+冗余"计算，不要拍固定次数；
  macOS crontab 需要 Full Disk Access，不可作为可靠通道。
- 16:15 定时任务已更新（对齐"上线后 6 小时"）：双包复盘+败局产出指纹归因+翻译器定级+
  slot 管理建议。今日提交名额已用 2/5。

### 上线验收 + 弹药纵深（2026-09-06 上午）

- 部署验收（防"静态对、运行错"重演）：拉双包首批线上对局验行为指纹——v41 正式局 3/3 胜
  （120.9k/134.5k/84.1k）、rb7925 正式局 3/3 胜（117.2k/98.3k/89.2k），合计 6/6；两包各自
  三局挂单几乎逐单一致（甜瓜 72 满产全卖），线上执行与本地一致，部署正常。验证局为自家
  对打例行局不计。待观察：rb7925 重复挂单量偏大（约 v41 的 8-30 倍，无成本，复盘时确认）。
- make_variant.py 升级通用版（任意母带输入），给 rb7925 产出 2 个合格变体
  （rb_var_4581c03056 / rb_var_8830803d1a，产出 197,777-197,785 与母带持平）。
  变体库现状：fam_F 系 3 个 + rb 系 2 个，防"动作级反制"弹药纵深就绪。
- 16:20 数据兜底独立进程已挂（8:05 定时任务未执行的教训）：无论 16:15 复盘任务是否运行，
  双包对局数据都会自动拉好。

### 执行层全面证伪日 + Crop 结构解剖（2026-09-06 下午）

一日七实验，统一定律浮出：**本市场先手压倒一切，任何"让出当下"的改动皆负资产。**
- V44 配额卖出（等均价/避倾销两版）：单人可保满产但对战崩镜像（8/8→0/8）——等待让出先手；
  附带破案：货仓 100 容量是采收链咽喉；d2~d10 卖出回款是扩张生命线（二分定位，d11 前卖单不可动）。
- V45 深先手（LEAD 提前 2~4 步）：与提前 1 步持平——先手窗口仅一步深。
- V47 细流卖出（大单拆三连小单）：单人 +257 金（平滑不砸自价，机制成立）但对战 24/56 全面退化——拆单同样让出先手。
- 三流派带筛选：fam_E 包被 Andrey 打崩、Jesse 包全弱；cand_0 包与 v41 逐行同构（37/56），收编为
  "同性能异指纹"防反制替身（variant_ec979ad28d 已打包）。
- 施肥审计（正知识）：删 5 步施肥实验实锤边际 = +276 金/步 = 卖肥的 2.8 倍；fam_F 系带 d12~13
  草莓结果日无肥是全家族共同缺陷。零/微改造空间仅 10 窗口（~2000 金），V46（fill 加施肥分支，
  库存映射 inventories[0]=农夫）实收 +192 金，已可白拿。
- **Crop/keiz 带解剖（认知反转）**：Crop 单人仅 181k、keiz 148k（我们 198k），却线上 2800+——
  对战实力与单人产出解耦。共同指纹：施肥 168/114 步（我们 75）、零卖出空窗（生产端匀产匀卖，
  羊毛 216/212 vs 我们 180）、keiz 草莓仅 139。top 流派=牺牲单人产出换取生产-卖出全程连续性
  （全程占据价格窗=先手的连续版）。此结构无法靠改卖单模仿（V47 已证），需带级生产结构换代。
- 通往 90% 碾压度的结论性路径：等双包线上对局捕获新一代带（管线就绪）+ 官方面板 top 新带；
  执行层已无油水。

### 🏆 金牌线认证达成（2026-09-06 11:19，上线 69 分钟）

- 爬升轨迹：10:10 上线（起始 600）→ 10:34 1109.8 → 11:11 1850.3 → 11:13 1943.0 →
  11:16 1979.2 → **11:19 2019.2（排 824），破 2000 金牌线**。
- 斜率为 Crop 级（Crop 6 小时到 2500；我们 69 分钟到 2000+，同量级爬升曲线）。
- 线上 33 局系统复盘：28 胜 5 负（85%），与本地门控（82.8%/84.4%）精确吻合，
  5 败全为 3k 内细刃惜败、零崩局——本地 kagsim 仿真保真度获线上验证。
- 达成组合：v41（fam_F 纯骨架+护栏/LEAD/fill/MM）+ rb7925（反 fam_F 母带+同武器层）
  双 slot 互补。用户目标"2 天内 Crop Dusta 级金牌策略"的金牌线部分正式达成
  （目标发起约 1.5 天内）；后续观察能否向 Crop 分数段（2800+）继续爬升。


## 2026-09-09 合并的 Claude 研究记录

以下保留 Claude 分支原始历史口径；当前候选资格以 golden_model.md 为准。

# Kaggriculture 实验记录

## 记录原则

- 每个可提交方案建立独立子目录，代码与提交包放在同一目录。
- 每次实验固定随机种子，并记录对手、对局数、胜率、最终金币与运行错误。
- 本地评测至少覆盖 `random`、`starter`、自身镜像以及历史版本。
- 排行榜评级会随匹配池变化，本地结果与线上评级分开记录。

## 方案路线

| 版本 | 状态 | 目标 |
| --- | --- | --- |
| `v0_api_smoke` | 本地验收通过 | 跑通观察、动作、720 回合和提交格式 |
| `v1_adaptive_market` | 本地验收通过 | 接入公开双路线强基线并适配 1.32.7 市场规则 |
| `v2_survival_guard` | 已提交并通过线上验证 | 用公开败局回放修复非终局牲畜死亡，并安全裁剪非小麦种子 |
| `v1_baseline_scheduler` | 本地验收通过，未提交 | 另起一条**原创（非 replay 复刻）**线：确定性任务调度器，作为可归因、可调参的起跑线 |
| `v4_demand_race` | M0–M6 完成，未提交 | 原创线完整实现（账本×3 + Router + 分层执行器 + CEM）；M6 对 V76/V20 0/128，结构性差距如实记录 |
| `v4h_demand_race_hybrid` | M6 完成，未提交 | V4 市场层嫁接强底盘；M6 对 V76/V20 各 43/128（33.6%），margin −4.4k，与 benchmark 同量级 |
| `v1_wheat_loop` | 已由 v0 覆盖 | 完成小麦种植、浇水、收获、出售闭环 |
| `v2_daily_scheduler` | 待开始 | 加入寻路、每日任务队列与临时工分配 |
| `v3_roi_planner` | 待开始 | 按剩余天数计算作物、动物和扩地回报 |
| `v4_market_adaptive` | 待开始 | 根据市场库存、城镇需求和对手供给调整生产与出售 |

## 实验表

| 日期 | 版本 | 环境/对手 | 局数 | 胜/平/负 | 胜率 | 平均最终金币 | 错误率 | 线上评级 | 结论 |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| 2026-08-17 | `v0_api_smoke` | Py3.12 / KE 1.32.2；`pass`、`random`、`starter` 双席位 + 自博弈 | 7 | 6/1/0 | 85.7% | 5545.7 | 0% | 482.4（首场公开局后） | 线上运行通过；策略强度需升级 |
| 2026-08-17 | `v1_adaptive_market` | Py3.12 / KE 1.32.7；v0、`random`、`starter` 双席位 | 6 | 6/0/0 | 100% | 150871.3 | 0% | 600.0（完成验证后） | 完整双路线基线稳定运行；远强于 v0，hinge 修正收益很小但方向正确 |
| 2026-08-17 | `v2_survival_guard` | Py3.12 / KE 1.32.7；v0、`random`、`starter` 双席位；11 场公开轨迹配对 | 17 | 17/0/0 | 100% | 153523.3（6 场 smoke） | 0% | 600.0（完成验证后） | 公开轨迹 10 场持平、1 场 +6,585；激进 WHEAT 裁剪因 -9.5k 消融被否决 |
| 2026-09-01 | `v1_baseline_scheduler` | Py3.12 / KE 1.32.7；`starter`/`random`/`pass` 双席位（seed 601–604） | 24 | 24/0/0 | 100% | 76666.3 | 0% | 未提交 | 原创规则基线跑通；但对 `v1_adaptive_market` 8 战全负、平均 margin −78,549，定位为起跑线而非上榜候选 |

## 单次实验模板

### `<version>`

- 代码目录：`model/<version>/`
- Git 提交：
- 环境版本：
- 随机种子：
- 对手及局数：
- 核心策略：
- 相比上一版的变化：
- 本地结果：
- Kaggle 结果：
- 已知失败模式：
- 下一步：

### `v0_api_smoke`

- 代码目录：`model/v0_api_smoke/`
- Git 提交：未提交
- 环境版本：Python 3.12.13；`kaggle-environments==1.32.2`；Kaggriculture spec `0.1.0`
- 随机种子：短局 100–105；完整局 200–205；自博弈 300；文件加载 401；高杂草压力 501；干净归档 601。内置 `random` 自建未播种 RNG，因此该对手的结果会随重跑波动
- 对手及局数：48 回合短局 6 局；720 回合完整局 6 局；720 回合自博弈 1 局
- 核心策略：初始解锁区 3 块近仓小麦；买种、种植、每日浇水、成熟收获、入仓、出售；终局按可变现时间过滤任务
- 相比上一版的变化：首个版本
- 本地结果：所有完整局均为 `DONE/DONE`，每个 Agent 719 次调用，动作合法性审计零失败。首次完整矩阵最终金币：`pass` 5646/5545，`random` 5756/5371（重跑会波动），`starter` 5481/5349，自博弈 5672/5672；`weedSpawnChance=0.2` 压力局 5654；从干净目录解压归档后对 `starter` 为 5572/3491
- Kaggle 结果：提交 `55574764`，状态 `COMPLETE`。Validation Episode `93864357` 自博弈 5430/5430，双方 `DONE`；首场公开 Episode `93864896` 对 `Ornaat`，5888/51097 落败，双方 `DONE`。2026-08-17 08:56 UTC 排行榜快照为 482.4 分、第 3614/4878 名；Simulation 评级会随持续匹配变化
- 已知失败模式：策略仅覆盖小麦与单农民，不使用临时工、动物、扩地和价格自适应；本地 PyPI 环境与比赛最新说明在部分高级规则上存在版本差异
- 下一步：提交 v0 验证线上加载，再实现 `v1_wheat_loop` 的收益与调度改进

### `v1_adaptive_market`

- 代码目录：`model/v1_adaptive_market/`
- Git 提交：未提交
- 环境版本：Python 3.12.13；`kaggle-environments==1.32.7`；Kaggriculture spec `0.1.0`
- 随机种子：正式验收 v0 8100–8101、`random` 8200–8201、`starter` 8300–8301、自博弈 8400、干净归档 8500；定价消融 75101–75120，全部交换双席位
- 公开基线来源：Tetsutani 的 `Adaptive Farming Strategy for Kaggriculture`。采用其两条完整 720 回合路线、168 回合城镇需求选择器和局部执行保护；来源与官方平衡说明已写入版本 README
- 核心策略：共享开局后根据已解锁商店在平衡路线和羊毛友好路线之间选择；路线内协调土地、临时工、作物、牛羊、物流和市场；运行时修复杂草、喂养、仓容、出售排序、种子冗余与终局清仓
- 相比上一版的变化：从单农民三块小麦升级为完整多工人、多地块、作物与畜牧协同；CARROT、TOMATO、EGG 的内部估价更新为 1.32.7 `hinge` 曲线，`HINGE_GAIN=8.0`，并逐点对齐官方 `market_price`
- 基线筛选结果：原始 Adaptive 在 KE 1.32.7 下对 E283 为 19/0/1、平均金币差 +2819.4；对公开“2883 score”为 17/0/3、平均金币差 +8068.1。该结果用于选择起点，不等同于线上评级
- 本地验收结果：对 v0 双席位最终金币 146422/148983，平均优势 +142109；对 `random` 为 175062/158649；对 `starter` 为 190921/85191；所有外部对局 6/0/0。自博弈 143171/145246；从干净目录解压归档后对 `starter` 为 164174/3600。全部 720 回合 `DONE/DONE`，无超时或运行错误
- 1.32.7 定价消融：修正版对未修改公开基线 40 场为 20/10/10，平均金币 87088.88 对 87084.98，平均差 +3.9，范围 -2338 至 +2342。说明修正改变了部分同类商品的市场抢先次序，但不是主要强度来源
- 提交包：归档根目录仅 `main.py`；32,869 bytes；SHA256 `918509335c5bd09c6e816c22a42275d81b3bb2c686666963237dc9c63d93eacf`
- Kaggle 结果：提交 `55575950`，描述 `v1 adaptive market routes + KE 1.32.7 hinge pricing`，状态 `COMPLETE`；完成验证后的公开评分为 600.0，2026-08-17 20:56（台北）查询已随持续匹配升至 2617.3。同一查询时刻 v0 为 304.9；Simulation 评分会随之后的匹配继续变化
- 已知失败模式：主体仍是 replay-derived 开环路线；新 hinge 机制下没有专门的 TOMATO/EGG 生产路线，CARROT 产能也很少；公开同源对手会造成高度镜像的市场竞争；本地金币不代表 Kaggle 评级
- 下一步：建立独立 challenger，不直接扰动主路线。优先测试城镇出现 PET_CAFE/重复 FARMERS_MARKET 时的胡萝卜整季路线，再测试 PIZZA_SHOP 的番茄路线；只有在多种历史对手、双席位 holdout 上提升才合并

### `v2_survival_guard`

- 代码目录：`model/v2_survival_guard/`
- Git 提交：未提交
- 环境版本：Python 3.12.13；`kaggle-environments==1.32.7`；Kaggriculture spec `0.1.0`
- 随机种子：正式 smoke 沿用 v1 的 v0 8100–8101、`random` 8200–8201、`starter` 8300–8301、自博弈 8400、干净归档 8500；公开轨迹使用各 episode 原始 seed 与席位
- 核心策略：保留 v1 两条生产路线；18 点后只在最后安全时刻派遣携带小麦的最近工人救援连续未进食动物，第 672 步后保留原路线终局减产；对 CARROT、TOMATO、STRAWBERRY、MELON 做未来种植前缀裁剪，WHEAT 仅保留终局安全裁剪
- 相比上一版的变化：关键线上败局 Episode `93891282` 暴露 5 头牛在终局前逃走；保护器在固定轨迹回放中把损失降到 2 头。曾测试把同一裁剪推广到 WHEAT，但 Episode `93902833` 回撤约 9.5k，因此未纳入
- 本地结果：对 v0 双席位 146422/148983；对 `random` 170867/178756；对 `starter` 190921/85191，6/0/0，平均 153523.3。自博弈 143171/145246；干净解包后对 `starter` 164174/3600。11 场公开对手轨迹配对中 10 场与 v1 完全一致，Episode `93891282` 为 114762→121347（+6585），总金币差 +6585、总 margin 差 +6577
- 提交包：归档根目录仅 `main.py`；32,910 bytes；源码 SHA256 `dadc0b09eb16a0528553fbf00dd826fff8efbc826d3ef5864b1cbf6dea5d2a70`；归档 SHA256 `dc7dbd150dbebbad88686d75242f377e87f020eba67b9a3f5163059e82bd655e`
- Kaggle 结果：提交 `55578745`，描述 `v2 survival guard + safe seed pruning`，状态 `COMPLETE`，完成验证后的公开评分 600.0。Validation Episode `93918092` 为 720 回合自博弈，双方 `DONE`、零错误，奖励 53251/54369；Simulation 评分会随后续匹配变化
- 已知失败模式：固定轨迹回放不会随我方新动作自适应，因此只用于局部回归；关键回放仍有 2 头牛因可用携粮工人距离不足而逃走；主体仍是 replay-derived 开环路线
- 下一步：等待线上验证和公开匹配；若评级无改善，优先增加带路径与未来任务成本的全局喂养匹配，不再扩大 WHEAT 裁剪


### `v1_baseline_scheduler`

- 代码目录：`model/v1_baseline_scheduler/`
- Git 提交：本次分支 `claude/kaggriculture-research-baseline-a01467`
- 环境版本：Python 3.12.13；`kaggle-environments==1.32.7`
- 随机种子：开发筛选 101–106；参数确认 holdout 201–208；最终验收 601–604（双席位）；
  自博弈 400；干净归档解包 901；对 `v1_adaptive_market` 校准 501–504（双席位）
- 核心策略：静态地块角色规划（ANIMAL 10 / WHEAT 4 / MELON 18 / STRAWBERRY 0，按到 shed 距离由近及远）
  + 每回合任务优先级表 + 贪心分配（任务未完成不换目标）+ SELL 先于 BUY 的市场层 + 第 690 步起终局清算
- 相比上一版的变化：**不继承 v0–v3 的任何代码**。这是与 `v1_adaptive_market` 并行的第二条线：
  前者是 Tetsutani 公开 replay 路线的开环动作带，后者是全部由 observation 现算的确定性调度器
- 本地结果：seed 601–604 双席位对 `starter`/`random`/`pass` 24/0/0，平均终局金币 76,666.3，
  平均 margin +74,487.7，全部 `DONE/DONE`，零运行错误。干净解包后 seed 901 对 `starter` 88,730/3,550。
  自博弈 seed 400 为 59,886/63,462。运行时 719 次调用均值 0.125 ms、最大 21.7 ms
- 参数消融（对 `starter`，开发 101–106 / holdout 201–208 均值）：
  初版 herd 4S+8C/12 畜栏/melon14/straw6 = 62,886 / 72,774；
  herd 4S+6C/10 畜栏 = 82,790 / 81,668；**采用的 herd 4S+6C/10 畜栏/melon18/straw0 = 83,082 / 84,272**。
  否决：畜群 16（72,616）、纯牛群（54,644，方差极大）、小麦地块 8（67,854）、临时工 6（61,325）。
  临时工提到 12 无效果——`HIRE` 也占市场订单槽，每回合上限 10 单
- 提交包：归档根目录仅 `main.py`；25,000 bytes，
  源码 SHA256 `d8776c41f706c0f83b55de35b10131a0884f92b0668b8e80dc6de521a1392e7c`；
  归档 7,723 bytes，SHA256 `7515489f64f35ea9fb9591163db4e4fbcb9b7fcf901ea00f47cd916aa3ea4d25`
- Kaggle 结果：**未提交**。对既有 `v1_adaptive_market` 8 战全负（平均 30,227 对 108,776，
  平均 margin −78,549），上榜没有意义；本版的价值是可归因、可扫参的起跑线
- 已知失败模式：共享市场完全没建模（不读 `town.unlocked_shops`、不看对手供给），
  对手先吃掉甜瓜/牛奶的城镇需求坑后我方只能卖在 glut 分支；移动占约 2/3 的单位回合
  （社区基准 55%，紧凑布局地板 33%）；放弃草莓；不施肥；终局一把梭清算
- 下一步：按 README「已知缺口」顺序做单点消融，先加 `town.unlocked_shops` 驱动的产品选择
  与"对手同产品抢跑一回合"层；评测改用社区固定天梯
  `raykkretzschmar/kaggriculture-reference-agents` + Bradley-Terry，而不是对 `starter` 的金币

### 本轮社区调研的行动项（来源：`competition_description/public_solutions_survey.md`）

1. **优化目标要改。** 评级只看 W/L/T，最终排名是截止后两周内**双方都仍活跃**的对局做 Bradley-Terry
   重拟合。本地要按"对每个强对手的双席位胜率"判断，而不是平均金币；50 分以内的线上差异是噪声。
2. **提交策略。** 只有最近 2 个提交在跑；重复提交同一 bot 换运气对最终排名零收益。
   截止日只需要两个最强且无错误的提交，第二个 slot 用于对冲 meta 漂移。
3. **本地对照的陷阱。** 杂草与商店共用一条 RNG 流，改动只要动了地块占用数就会重掷商店：
   实测"少雇一个 hand"在 16 个 seed 上 0/16 保持同一城镇。要么本地把两条流拆开，要么钉住商店解锁序列。
4. **RL/BC 暂缓。** 社区多组独立实验的天花板是自博弈 80k 金币，而规则型公开方案是 140k–190k；
   截至 2026-09-01 无任何自报 Top 名次的方案是端到端 RL/BC。若要做学习型，
   共识的可行架构是"模型只选高层 Option + 确定性执行层"，且必须能验证模型真的改变了行为。
5. **可直接落地的引擎级修正**（若现有版本尚未包含）：不读 `obs["step"]`；动作只排到 step 718；
   市场列表 SELL 先于 BUY；肥料即收即卖；CARE 每天做（把动物日产从 1 提到 2）。


### `v4_demand_race` / `v4h_demand_race_hybrid`（2026-09-01）

- 设计：`model/v4_demand_race/DESIGN.md`（含 §11 实施结果）；代码单文件自包含。
- 基建：kagsim（1.32.7 bit-exact C++，5 万局/s）+ 钉商店 scenario 引擎 + 双席位配对
  arena + 64 个真实 episode 场景固化（`harness/scenarios_64.json`）。
- 关键 bug 修复链（每个都被 probe 证据驱动）：种子断供（reserve 卡采购）→ 喂食
  供应链（动物饿死）→ 动物 PICKUP 死锁（7 头牛困 shed）→ 收获优先级（melon 烂田）
  → 线性加权指派（5 步距离翻转优先级 → 严格分层）。
- CEM：26 维 × 40 代 × 24 个体（kagsim 9 进程并行），vs v1am margin −119k → −101k
  （固定 seed 复核），最优参数已固化进 POLICY。
- **M6（用户指定验收）**：64 真实场景 × 双席位 × {V76, V20}：
  V4 原创线 0/128 ×2（margin −145k/−146k）；V4H 43/128 ×2（33.6%，Wilson LB 26%，
  margin −4.6k/−4.2k）。对照裸底盘（随机 seed）margin −7.1k/−6.6k。
- QA：双引擎逐分一致（seed 911/912）；打包干净解包官方引擎 76,145/3,721 双 DONE，
  0.18ms/调用；归档根目录仅 main.py（44,967 bytes）。
- 结论：贪心+分层调度对整体规划 tape 有 ~30% 动作利用率的结构差距；市场层
  （账本/race/终局）作为嫁接层是有效路径。下一步：日级静态规划，或 tape 内省
  提高 race 触发率；V4H 提交前需合并单文件。

### `v4h_tape_ledger_hybrid`（蒸馏轨道 A）与 `v4h2_tick_defer`

- 日期：2026-09-02
- 环境：kagsim 1.32.7（bit-exact C++），M6 协议 = 64 真实 episode 场景 × 双席位、商店序列钉住
- 素材：OceanMix（榜第 2）纯开环 tape，82 场跨 seed/对手/席位逐步一致（episode `102549659`）
- 结果（vs V76 / vs V20）：
  - RAW tape 母体：18.0% / —，margin −20.2k
  - tape + 账本层（V16-RC5 式一回合前移 + weed 修复 + 终局兜底）：**25.0% / 23.4%**，margin −15.5k/−17.4k
  - 对照 V4H（v1am 底盘）：33.6% / 33.6%，margin −4.6k/−4.2k
  - V4H2（+V20 式 tick-defer）：33.6% / 33.6%，配对差中位 **+52.5 金币**（零翻盘，负结果归档）
- **轨道 A 的 40% 可证伪预测未达成**，按纪律关闭。层的净贡献 +7.0pp 干净可移植
- 两条通用教训：①卖单不要做 obs-shed 预检（引擎按 field 后新 shed 结算并自动截断；
  预检会错杀"同回合入库→卖出→购地"资金链，曾致 NE 购地静默失败、生产腰斩）；
  ②agent 内的 DIG 会改变空地数→重掷商店抽签，随机 seed 上 ±5k 的"机制效果"多为商店噪声
- 消融实录：race 跟跑（滞后信号追砸盘）−9k、现金流阀（多余贱卖）−15k、价格挂起小负——
  自创机制全军覆没，公开验证过的配方（V16-RC5 前移）是唯一存活者
- 下一步（按证据强度）：tape 内省式 lead（v1am 未来卖单可从路线表读出 + 对手 tiles 收获预报，
  做真正的"抢先"）；yarn=1 场景带专项（40 场 × 28% 是最大弱点）；多 tape 路由蒸馏降级

### `v5_tape_tree_hmoe`（分层蒸馏；loop 目标达成）

- 日期：2026-09-02
- 环境：kagsim 1.32.7；M6 = 64 真实场景 × 双席位、商店钉住；另 40 全新随机 seed × 双席位
- 数据：8/25–8/31 Daily Top Episodes，六支金牌队 1,056 场（提取脚本 `scan_teams.py` / `extract_library.py`）
- **决定性修复**：replay `steps[i].action` 是第 i−1 回合的动作；此前全部 tape 错位一回合。
  修正后精确回放 6/6 bit-exact（此前 6/6 DIVERGE）。方案 A 与可行性报告的 tape 数字全部失效并已加注
- 结果（OceanMix 树，= 修正后的 OceanMix tape + 守卫）：
  - M6 vs V76 **108/20 = 84.4%**（LB 77.1%，+13.7k）；vs V20 **112/16 = 87.5%**（LB 80.7%，+14.1k）
  - 全新 40 seed vs V76 / V20 各 **76/4 = 95.0%**（LB 87.8%）
  - M6 vs v1am / V4H 各 128/0
  - 消融：裸修正 tape 与树版 W/L 完全一致 → 路由/守卫层贡献 ≈ +100 金币，增益 100% 来自对齐修复
- 六队树对比：OceanMix 84%；yukino 48%；Driz Lo 48%；tetsuya 35%；MtN 29%；Crop Dusta 12%——
  自适应队伍的分叉依赖商店外信号，按商店路由的续盘失配；越自适应越不可蒸馏
- 提交包：`submission.tar.gz` 1,392,595 bytes（`main.py` 8,305 + `lib/OceanMix.json.gz` 1,611,115）；
  干净解包后官方引擎 vs kagsim 同 seed 逐分一致（84013/69281）。**未提交 Kaggle**
- 下一步：对更强对手池（其他金牌队 tape）评测；tape 日更管线；自适应队伍的保守路由
- **V120 门控对比**（2026-09-02，双席位）：V5 vs V120 在 M6 60/68 = 46.9%（−621，镜像级噪声）、
  新 40 seed 27/53 = 33.8%（−2.6k）；V120 vs V76/V20 在 M6 各 95/33 = 74.2%（低于 V5 的 84.4%/87.5%）、
  新 40 seed 各 77/3 = 96.3%（≈ V5 的 95%）。结论：不构成支配；V5 在真实场景更稳，V120 市场层
  在随机 seed 镜像局更强；下一步可把 V120 市场层嫁接到 V5 骨架，或把 episode 104547425 并入 V5 库

### V120 对抗 loop（2026-09-02）与评测环境勘误

- **勘误**：钉商店 arena 的 `force_shops` 被一次性传入全部 8 家 → 商店从第 0 步全部可见，需求与银行约翻倍。
  本日此前所有 "M6" 数字作废；修复后重跑见 `model/eval_m6_fixed/README.md`。随机 seed 数字（已与官方引擎对拍）有效
- 修复后核心矩阵：V5 vs V76/V20 **87.5%/87.5%**；V120 vs V76/V20 90.6%/90.6%；V5 vs V120 43.8%；
  V8（羊毛对冲）vs V120 **64/36/28**；tetsuya 103951199 vs V120 23.4%（失真环境曾 94.5%）；V4H 20–22%
- 对 V120 的杠杆逐个证伪：镜像=平局不动点；时序偏移全负；PASS 填充 ε=0；执行器互换无差；OceanMix 家族与其他五队
  ~500 条轨迹均 ≤ V5 档。唯一正向杠杆是羊毛赌注对冲（V8）
- 结论：胜负由赛季是否出现 YARN_STORE 决定（P=66%），提前承诺的 tape 被该分布锁死；80% 在"replay 蒸馏 + 参数搜索"
  范式内不可达，需要生成式的条件化动作链改写。详见 `model/v5_tape_tree_hmoe/V120_LOOP_REPORT.md`

### `v10_rule_distill`（规则蒸馏；对 V120 ≥80% 达成）

- 日期：2026-09-02。方法：把 tetsuya / Crop Dusta / MtN（8/25–8/30，529 场）的 replay 当作策略采样，
  对每个生产决策找可观测量上的最佳单分裂（只采信跨队一致者）；规则只用商店揭示与天数，不含 episode/seed
- 挖出的核心规则：羊数 ← 是否见 yarn（方差削减 0.53–0.79）；牛数 ← 奶类商店数（0.45–0.59）；草莓 ← 草莓商店数（弱且执行有害）
- 落地：V120 精确执行链 + "在不利城镇跳过该批购买"（R1 羊第 10 天逐批、R2 牛第 9 天奶店≤1）
- 门控（选阈值后的从未接触集合，100 seed × 双席位）：**vs V120 171/23/6 = 85.5%（LB 79.95%）**，vs V76 87.5%，vs V20 89.0%；
  M6：78.9% / 92.2% / 92.2%。对照 V120 本体 vs V76/V20 90.6%，V5 vs V120 43.8%，镜像 0%
- 网格教训：决策越晚越好但不能晚过 tape 购买时刻；牛规则只跳最后 1 头最优；草莓规则 −9k~−14k；提前到第 6–7 天跳牛反而差
- 提交包改为单文件 main.py（176,373 B；Kaggle 加载器无 `__file__`、取最后一个可调用），官方引擎路径式自博弈 DONE/DONE，与模块版逐分一致；
  **已提交 Kaggle：`55965430`**（2026-09-02 16:57 UTC），状态 COMPLETE，验证通过，初始公开评分 600.0
- 下一步："多买"方向（yarn 早现加羊、奶店多加牛）需要可重排执行器，是 85%→更高与追平 top 队的杠杆

### `v11_annex`（"多买"方向；负结果，2026-09-02）

- 目标：对 V10/V120/V76/V20 各 ≥75%。对后三者 V10 已 ≥85%；瓶颈是对 V10 本身（同源镜像 = 平局）
- 可行性：tape 用满 75 格、第 0–10 天现金≈0、shed 第 12/24/28 天顶到 100；加地加人 ROI 负；只剩纯小麦轮作地块的作物替换
- 实验（镜像 vs V10，5 seed）：小麦→甜瓜 −6.5k（镜像对手已把甜瓜市场砸到地板）；→胡萝卜 −8k（连续卖出≈base，还多付种子）；
  →草莓 ≈0~−1.6k（饱和）；胡萝卜版对 V76 也比 V10 差 4–7k
- 结论：镜像对手打饱和了 tape 能产的一切产品；唯一未饱和的蛋/胡萝卜深坑需要专属劳动与仓储重排，超出 tape 覆盖层能力。
  详见 `model/v11_annex/README.md`

## 2026-09-03 V12–V15："唯一剩下的路"（可重排执行器）执行记录

用户批准继续执行"更强计划 + 可重排执行器"。本日依次排除/推进：

| 版本 | 内容 | 对 V10（M6 fixed 64×2） | 结论 |
| --- | --- | --- | --- |
| V12 `v12_crop_dusta` | Crop Dusta 5 个 regime 的固定轨迹（修好 C92 守卫僵尸苗、雇佣/购买现金守卫后重跑） | 0–3.1%，bank 46–62k vs 87–110k | 顶队实时 agent 的轨迹在非原场景现金链断裂，回放路线正式判死 |
| V13 `v13_route_library` | Tetsutani 8/30 公开 notebook 的 5 条完整路线（10C4S/8C6S/6C8S/6C12S×2）装进 V120 守卫栈 | 3 场景冒烟每局 −20k ~ −35k | 公开路线比 V120 蒸馏路线（Top5 episode 104547425）弱，捷径排除 |
| V14 `v14_rule_search` | V10 底盘零额外劳动的计划级变异：晚期胡萝卜替换、牛奶/草莓价格节流、肥料即卖、末日雇工上限、末期种子剪枝 | 全部 ≤0（−0.2k ~ −25k）；只有 0 为无效 | V120 路线+守卫栈在其劳动预算下是紧局部最优；V10 镜像 56/64 场景精确平局、4/64 因杂草级联 ±32–46k |
| V15 `v15_closed_loop` | 原创闭环调度器（牧场环布局、角色+分区巡回、到块即做完、槽位预算市场、计划表对齐 V120 路线） | 全闭环 2/126=1.6%，bank 54.2k vs 105.9k；混合（前 20 天 V10 tape）4/124=3.1%，69.9k vs 82.4k（−12.5k） | 动物侧已持平（肥料 339/378、羊毛 175/196、照料 335/372），田间侧落后 15–25%（小麦 351/567、草莓 103/260）；毛线首店城镇尾段可 +21k~+39k |

关键工具：`harness/exact_rev.py`（官方引擎打桩的逐单位精确收入归因，支持钉商店与逐日）、
`harness/revenue.py`（城镇吸纳量计算）、`v15_closed_loop/prod_diag.py`（产量归因）。
关键机制发现见 `v15_closed_loop/README.md`（照料奖励累积、作物窗口浇水、草莓施肥翻倍、甜瓜第 10 天达产、先手卖出）。

现状判断：四门（V10/V120/V76/V20）≥75% 的目标在本日结束时仍未达成；执行器路线的剩余差距集中在田间产量与早期现金复利，
再投入的收益不确定，交由用户决定是否继续。

## 2026-09-03 `v11_distill_top20`：top20 × 08-20 以来全部 replay 的蒸馏研究（负结果 + 规则确认）

- 样本：13 天 Daily Top Episodes 头部扫描，8 支队伍建库（OceanMix / tetsuya / Crop Dusta / Milan Leonard / yukino / Driz Lo / MtN / Naru041104），
  含记录对手 24/72/144/216 步签名的 `_ctx` 版本（首版错位一步已修复，ALIGN_CHECK 720/720）
- 结构结论（RESEARCH.md §2）：只有 OceanMix 是纯 tape；其余为"固定骨架 + 商店条件规则（羊×yarn、牛×奶店、莓×莓店）+ 第 1 天对手识别 + 在线调度"；
  留一法整局保真度 0–7%（OceanMix 42%）→ 轨迹级蒸馏原理上不可行
- 树路由门控（修复环境 M6 64×2）：OceanMix 87.5/87.5/54.7（V76/V20/V120）；自适应教师 Jaccard 键 25–50% / 8–16%；
  商店序列精确键与 Jaccard 逐场相同；再加对手签名键：Milan 40.6/16.4（不变）、Crop Dusta 26.6/13.3（−6pp/不变）、tetsuya **57.0**/7.8（+7pp，margin 转正）
- §2.7 开发路线证据：Crop Dusta 对 OceanMix 家族 69%、对 4 羊家族 93%（meta 最优响应）；Milan 对 OceanMix 家族 95%；tetsuya 对 OceanMix 家族 30%（榜首靠打弱队）；
  Crop Dusta PASS 5%（用满劳动力的调度器）、6 天同时跑 2–4 个开局版本
- 结论：序列/树路由蒸馏对自适应教师收束；金牌差距定位在"能执行条件计划的调度器"；规则层已由 V10 落地（vs V120 85.5%）
- 工具：`scan.py` / `extract.py` / `extract_ctx.py` / `mine_policy.py` / `agree_ctx.py`，V5 `main.py` 新增 `route_key=shop_seq`、`oppsig_filter`

## 2026-09-03 `v16_online_fidelity` + `v17_market_guard`：线上 700 名根因 + 市场护栏

- 起因：V120（55971529，rating 1926 / rank 794）与 V10（55971546，51.3%）线上远低于本地门控预期
- 方法：拉取三次提交 341 局公开 replay，逐局产出/资金归因 + 对手按 300 步动作哈希聚类 + kagsim 保真度复现
- **根因 1（门控口径）**：线上 43% 对局的对手是公开 tape 家族复制品，头部家族产出（草莓 250-266/羊毛 138-261）与我方同级或更强；V76/V20 门控远弱于线上中位对手
- **根因 2（开局扰动，关键）**：两个家族（16 局 1W15L）与 OceanMix 家族带逐字相同，仅多一手 t0 买 53 小麦/t1 卖 48 的抬价扰动；
  我方 tape 第 1 步清单（动物在尾部）超预算被截断 → 少 2 只羊 → 羊毛 181→110、草莓 254→142、-25k；对方清单动物在前天然免疫
- 验证：单人任意 seed/商店序列产出恒定（排除商店失配）；trace 确认 t=1 少花 476（=截断的羊）
- **V17 防御**（开局清单重排[动物,雇,种,品] + 第 1-2 天牛羊补买守卫）：fam_B 0/8→8/8、fam_C 0/8→6/8，其余家族无退化，产出恢复 250/181
- **V17a 进攻**（+自打同款扰动，day0 全天重排）：8 seed 矩阵 A 14/16、D/E/W/X 16/16（margin +20k~+40k）、B 12/16、C 4/16（对轰近平）；
  M6: vs V120 96.9% (+18.7k)、vs V76/V20 90.6% 无退化
- 教训：重排范围是行为敏感参数（day0 全天 vs 仅开局两步在进攻分支下 B 从 12/16 变 0/8 量级翻转），经验定版、开关分离
- 提交包：`main_submission(_attack).py` 177KB 单文件，尾部追加守卫、入口 `kaggriculture_agent`（新键名，避开 dict 保序陷阱）；
  官方引擎 DONE/DONE，与模块版逐分 MATCH。详见 `v16_online_fidelity/REPORT.md`

### V17 提交记录（2026-09-03）

- **55981569** `submission_attack.tar.gz`（92,687 B；main.py sha256 f590b1b3…）：V17a 进攻版（防御护栏 + 开局扰动，day0 全天重排）
- **55981574** `submission_defense.tar.gz`（92,686 B；main.py sha256 eda4af01…）：V17 防御版（护栏 only，仅开局两步重排）
- 打包：tar 内单文件 main.py，入口 `kaggriculture_agent`（最后可调用）；官方引擎 DONE/DONE；与模块版逐分 MATCH

## 2026-09-04 线上首日复盘 + V19a（V10 底盘换装）

- 首日战绩（各 200+ 局）：V17a attack 2036.9（58.8%）、V17 defense 1774.0（52.7%）
- **两个假设均验证**：防御护栏线上对扰动型 82.4%（V120 时期 6%）；进攻扰动对无扰动对手 77.0%（+17.2k/局）
- **meta 剧变**：扰动型对手占 attack 版对局 42%（三天前采样仅 5%），且 rating 越高密度越大；对轰局 33.7% 是 2036 分天花板
- 对轰失血定位：yarn 早现局 56% vs **无 yarn 局 20%**（35 局）——羊毛无处高卖是主因；另发现新必输家族 ff71bda897（8W26L）、b55af2d9c3
- **V19a = V10 规则蒸馏底盘（R1 无yarn跳羊/R2 奶店跳牛）+ V17 护栏 + 扰动**：
  家族矩阵 G 16/16（线上 0/4 翻转）、A 14/16、E 16/16、B 12/16、F 8/16、C 4/16；
  M6 vs **V17a 78.9% (+438)**、vs V120 96.9%、vs V76/V20 92.2%；官方引擎 DONE/DONE、镜像完全对称（146859/146859）
- 证伪并止损：提前跳羊日（V120 带第 8 天前无羊单）、扰动持仓卖 53（压价反伤）——无 yarn 对轰 margin −140 暂接受
- **提交 56014863**（2026-09-04，`submission.tar.gz`，main.py sha256 2ad563f7…）替换 defense slot；在役=V17a 2036.9 + V19a

## 2026-09-04 V21 crop 调度器 M0 攻坚（G0 141.1k→159.6k=81%）+ 对战两座山

- 解剖 CornHub 满产出带：布局蓝图（17 牧场居中/33 草莓两翼/小麦外圈/甜瓜 d0-10）、稳态日程（h2-8 动物流程、h9-17 浇种施、PASS 只在日末）、
  草莓机制（不施肥不结果；肥效 3 天 vs 产出间隔 2 天 → 无缝续肥翻倍）、PLACE 第二语义=定量入库（DROP 会吞随身物资）
- 修复与负结果详见 `v21_crop_scheduler/README.md`；关键跳变 animals_per_ranch=3（+12k）
- 对战口径 G1 全败：产出 81% 在供给竞争下不够 + 实现价格差 ~17k（卖出层是与产出同量级的第二战场）
- 对轰研究（V19 支线）：无 yarn 对轰 margin 仅 −140/局但 R1 提前跳羊（V120 带 d8 前无羊单）、卖 53 均证伪

## 2026-09-05 V22 全局排序内核 + 对轰归因 + V19a 首日复盘

- V19a 线上 118 局 81.4%（对无扰动 87.9% +21.7k/局、对扰动 47.4%、新强 G 5W0L 预测兑现）；分数爬分中 1873
- 对轰归因（无 yarn 双扰动局）：可归因收入我方 +17k 领先但均价系统性低（straw 92 vs 114、wool 18.6 vs 33.5）= 先手差；
  卖单前移一步证伪——tape 卖出时刻本就是入库后最早时刻，无货可提前（B/C 两版逐分近似）
- **V22 内核**（v22_global_scheduler）：全场任务 value/(1+dist) 全局贪心替换 V15 分区最近优先；
  G0 159.6k→**169.0k（85.6%）**一天突破 V15 平台；MILK 264/MELON 72/FERT 370 达到或超过 CornHub；
  估值价陷阱（瞬时价被砸带偏产出决策→0.8×BASE 下限）；对战仍 0/8（变现率缺口，等 G0 95% 再攻）
- 快循环 daily_loop/daily.py 落地

## 2026-09-05（下午）V22 进化方案 EVOLUTION.md 制定 + E1 第 1 轮
- 方案：E1 满产出 95% → E2 变现 80% → E3 家族最优响应 → E4 自博弈快循环；每阶段止损 2 天
- E1 审计三病灶（MOVE +577/死亡 ×2/PLANT −87）；排序层三假设证伪（dist_pow/保底/聚簇）
- 收敛结论：169.0k 平台=排序层天花板，下一杠杆是布局蓝图（功能分区+固定巡回）

## 2026-09-05（冲刺日2）V24/V25：杂交层与做市武器；V25 上线 56030093

- 夜间搜索：V23 收敛 142.9k（+14.5k；sell_batch 12/hands 11/straw_last_plant 14）
- daily：V19a 175 局 69.7%（扰动占比升至 27%、对其 41.7% 是主失血）
- V24 原地填充/第13工人：证伪（净0/纯亏）——但逼出做市思路
- **V25 做市层**：对手 tape 不看市场→低吸其砸价货（0.8×BASE）等城镇推价回升（0.93×BASE）卖出；
  无yarn对轰 1/12→12/12；家族 A/E/G/W 全胜 margin 翻倍；M6 vs V120 97.7%；全门控绿，提交 56030093
- dict 保序陷阱第三次出现（_V24_PREV_AGENT 成最后可调用）：包装函数必须新名字置尾，已入 checklist

## 2026-09-05（冲刺日2下）V26 母带换血，提交 56030342

- 归因链：pert_1 有 yarn 局双席位恒定差 1-6.6k → 单人对比确认线上母带已升级（195.5k/198.2k vs 我们 185-190k）
- V26 = V120 执行核 + fam_F 带内嵌 + 护栏 + 扰动30 + fill + 做市；单人 197,884 保真
- 扰动量军备权衡：53 收割无防带但对同行弱；0 反之；30 两头 8/8 全局最优
- 家族剖面 47/56=84%（W/A/G/C 全胜、G +51k、F 6/8 首次稳赢）；M6 97.7/89.1/90.6；镜像对称
- 在役=V25（扰动池特化）+V26-a30（全能）双 slot 分工

## 2026-09-05（深夜）top4 解剖 + 金牌门控 + 扰动军备完整地图

- 双 slot 中程（63/58 局）：V25 61.9%（对扰动 53%）、V26 65.5%（对扰动 64.3% +9.7k、对无扰动 66.7%）；
  分数 1900-2000 带震荡爬升；共同弱点 F 型（合计 1W4L）
- **高段位真相**（9-04 面板 631 局含 top60）：顶级池是均衡互搏场——keiz(3011) 64%、Giulio(4th) 49.5%；
  keiz/Andrey/Giulio 100% 扰动（量 43/30/20）、Jesse(2nd) 0% 扰动 t0 直接买牛；
  金牌不需要 85%，需要在均衡池保持 60%+ 并靠对手加权 rating 爬升
- top4 带提取：keiz 带单人仅 147.7k（强在 18 变体条件切换）、Jesse 181k、Giulio 188k、Andrey 187k
- **金牌门控首跑：V26-a30 对 top4 最大变体 22/32=69%**（keiz 变体 8/8 +44.8k、Jesse 6/8、Giulio/Andrey 4/8 细刃）
  ——强度已入金牌池均衡带
- 扰动军备完整地图：量 0/20/30/43/53 全测。43=keiz 点位，对旧代（C53/W无防）收割最狠（+17.8k/+32.9k）
  但对新代 20 型（Giulio/pert_1）崩（2/8、0/8）。**量是相对博弈，混合 meta 下 30 全局最优，在役不动**
- 明日主攻：V28 条件路由（keiz 架构=共同前缀+条件后缀，V120 route 机制现成）

### keiz 架构侦察（当夜补充）
- 136 局两两公共前缀 min4/med21——主分叉早于商店揭示，非纯商店路由（轻调度器或对手条件分支）
- 确有 yarn 早现专用变体（21 局 yarn@1-2，羊重配置）与 V120 route 同构；但我方 yarn 早现局本就 80-95%，
  偷该分支边际小；keiz 带单人仅 147.7k，不宜做母带——其强度=条件化×执行×43 扰动的组合
- 剩余短板定型：F/Giulio/Andrey/pert_1 代高产带的五五细刃局（margin ±1k）+ Jesse 型（赢小输大）
- 次日路线：晨间 daily 定位线上真实细刃构成 → 细刃通用增量（终局优化/做市贴线）或双 slot 轮换实验

### V29 适应层撤销（负知识）：R1 跨底盘迁移与 R3 就地转产均证伪——F 带 7 只 d8-11 羊是产出主干、
换品打乱收割/浇水时刻表。tape 生产结构适应必须等真执行器。seed83 型（胡萝卜大赛季）暴雷接受为已知损失。

## 2026-09-06（凌晨）slot 组合优化：a53 收割变体上线 56033998

- 零收卖单归因：空转单无实际损失（引擎按 shed 截断），总差 276/局——不修
- 期望算术：在役 V25（旧 V10 底盘，对扰动 64/无扰动 71）换 V26-a53（新母带+满扰动收割，
  对无扰动池 +39.5k 碾压）——双 slot 变为扰动量 A/B（a30 全能 + a53 收割），组合期望更高
- a53 门控此前已全绿（M6 97.7/89.1/90.6、家族 47/56、官方镜像对称），零新增验证成本
- 在役：56030342 V26-a30 + 56033998 V26-a53（V25 做市版 56030093 退役，做市层在 a30/a53 内仍在）
- 夜间自动循环运转中（每 2h 复盘+快照）

## 2026-09-06（上午）用户 bug 报告核实 + V22 变现层攻坚第一轮

- **Bug1 成立（重大机制修正）**：引擎 BUY_PRODUCT 仅收 WHEAT/FERTILIZER——V25/V26 做市层的高价品买单全是废单；
  对轰 12/12 增益（实测为真）的真实机制=假持仓记账歪打正着触发的"价格回升时追加卖单"——
  零破坏纯增量 nudge，非低吸套利。羊毛崩盘吸筹的构想整体作废（不能买羊毛）。
- **Bug2 不成立**：V26 换表实际生效（V120 核对 tape 规范化深拷贝导致对象身份/参数补全差异；
  产出细节差异来自守卫层拉扯，总体保真 197.9k vs 198.2k）。
- V31 显式择时（拦截 base 低价卖单）全面崩盘（4/40）：**tape 卖单不可拦截**（时序级联），
  意外机制的精髓=不拦 base、只追加。V30 错峰回避亦证伪（对手高频卖出下回避=绝食）。
- V32 = a30 移除废单挂出（保留状态机触发器）：同 seed 行为逐分等价，存档为下次上线基线；
  按复利纪律不替换在役。
- V22 变现率之谜仍开放：意图卖出 1045 单位全成交、实现仅 32/单位 vs 对手 110——
  错峰/拦截双证伪后，剩余候选=混合步支出归因/卖出时刻分布，待下一轮。
- 入库频率 A/B（dep3/dep2）亦负——V22 变现差不在入库时刻。

### V22 变现层攻坚终局（六连败归档，2026-09-06）
- 价位分布铁证：V22 47% 货砸 <0.4×基准地板（W 带仅 29%，且 40% 卖在 ≥1.1 高位 61.8k vs 我们 33.1k）
- 六假设全灭：错峰回避/显式拦截/入库频率×2/无差别闸门（旧）/商店条件闸门
- **终局结论：tape 的高变现率=教师局双 tape 共同进化的价格生态位均衡，无法单方面复制**；
  调度器在 tape 海洋里供给节奏必然撞车。该问题在"调度器 vs 调度器"的金牌池内自然消失——
  V22 复活推迟到进入金牌池后（届时对手也是自适应体，生态位重新协商）
- 分段引擎方案修正：爬升段继续用 a53 收割（tape 生态位内作战）+ a30 均衡；产出=V32 等价清洁版（存档基线）

## 2026-09-06（下午）V33 对手条件路由：五层耦合债后止损（负知识重仓归档）

- 素材验证曾极佳：keiz 带裸放碾老代扰动（108k vs 15.5k、8/8）、t1 小麦缺口可精确分类对手、两带开局同源
- 五层 tape 耦合债逐一现形：(1) obs["step"] 本地不可靠（老坑）；(2) V120 main.py 本身 2262 行 9 个 def agent
  的层叠总装，路由层被短路；(3) 守卫栈按 F 节奏调教，套 K 带稀释碾压力（+93k→+1.4k）；
  (4) 判定在 t1 但 K 开局在 t0——异源开局差几百金即断链（2/8）；(5) 反转默认线后 hands 截断+
  V120 链状态初始化混乱全面崩盘（straw 77、pert 局 708 金）
- **终局结论：异源 tape 不可拼接。Crop 的变体切换可行因为变体=同一调度器的参数化输出。
  条件路由的完整形态只能由调度器承载（金牌池内 V22 复活时）**
- 当前最优保持：在役 a53+V32 复利爬升、夜循环威胁监控、V32 基线待真增量

## 2026-09-06（傍晚）V34 需求对齐调度器：Crop 机制的第一性重构与概念验证

- **第一性重解**（用户推动）：Crop 的规则浅树（羊×yarn/牛×奶店/莓×莓店）不是条件微调，
  是把产出结构对齐到本局需求结构——对齐的货城镇吃掉、价格不砸穿、变现率 90%。
  一个模型通吃全段位的根基=每局对齐（tape 固定产出撞大运）。规则树管产什么、调度器管执行与速率。
- V34 = V22 + 需求对齐生产（动物/草莓/胡萝卜配额=f(已解锁商店)）+ 速率匹配卖出（每步≤城镇吸收）
  + 牧场预留动态化（砍动物后地块回流田间）
- **概念验证成立**：卖出价位分布彻底翻转——地板 47%→26%、高位 24%→50%（超 tape 对手的 39%）；
  对战 bank 55-66k→66-70k（margin −45k→−30k）
- 剩余缺口 30k = 执行密度（V22 的 G0 85% 老大难：对齐释放的资源转化率、浇水/收获/补种吞吐）
  ——纯工程打磨量，非机制问题。V34 认定为调度器复活的正确路线图。

## 2026-09-06（夜）V34 全段位模型攻坚第二轮：执行密度墙确认

- 对战口径参数搜索（新工具 duel_search.py）：对齐方向全部确认（羊 2/牛 3 最优、rate 1.5），
  参数面平坦于 margin −27.6k——缺口是结构性的
- 产出账本：对齐"只砍不转"——总物理产出 1163 vs 对手 1894 单位（61%）；砍掉的劳力沉没在移动
- 显微镜（d12-13 对战中盘）：**MOVE 占 56% 动作槽、HARVEST 仅 2%**——反应式调度的布朗运动实锤
- 到访批处理（执行层新机制，十连败清单外）：小麦轮次终于解锁（380-488）但对战 margin 反降
  （58-60k）——批处理与动物侧/对战节奏的新互杀；抬种植价值在新形态下仍不翻案
- **战役状态**：需求对齐概念 ✓（价位分布翻转）、参数面 ✓、执行内核 ✗（MOVE 56% 的墙在
  V22 系载体上 13 连败）。V34 完整形态需要 V23 式内核重写（蓝图/待办/班表）+对齐的合体，数天级工程
- 线上：a53 45 局 77.8%（对无扰动 87.1%）爬升中、V32 起步 4 连胜

## 2026-09-06（深夜）V35 全段位内核战役 Day1

- V23 底盘证伪：待办制 MOVE 确实低（49% vs 55%）但对战地板 33k（死计划+卖出更原始）→ 回 V34 干线
- V35 对齐自愈：判定时点滞后揭示窗（羊 d8+/牛 d6+）+ 配额上调自动补差批次（早砍误伤晚买自愈）
- 到访批处理：单人小麦解锁（380-488 历史突破）但对战净负（无限时 −8k、限时 4 步 −4k）→ 默认关、留参数
- **价位结构已全面反超**（高位 45% vs 对手 32%、地板 32% vs 36%）——变现问题终结；
  剩余缺口=量：对齐砍动物 −10k 收入 +5k 现金、劳力转化≈0 → 当前净 −5k，一切压执行密度
- 明日序列：a) 批处理时段化（仅 h18-23 扫尾启用）b) 省钱→第 3 块地提前（+25 块麦田）c) daily 驱动
- 线上：a53 1882（77.8%）、V32 1048 爬升

### V36 全天排程调度器（深夜开工，骨架已立）
- M1 三候选一小时内全灭（时段化批处理 −2k、三地现金够不到、顺路浇水 −8k 时间成本非零）——执行密度 14 连败
- 判定：单点爬山正式死亡，开工 V36 全天排程（日初带状分区+蛇形巡回+任务序列，执行不重选=CornHub 日程的生成式）
- 首版 962 金新生儿瘫痪（放动物链 __GOTO__/巡回索引疑点）；明日调试主攻，参照 V23 调试轨迹（30k→133k 一晚）
- V34 干线冻结在：对齐+速率+自愈，对战 −27.6k（价位结构已反超，缺口=劳力转化）

### V49/V50 路由日:A 阶段落地 + B 阶段地基(2026-09-07)

背景:巡视发现社区前沿收敛为「块级 public-state 路由」(survey 二.27-34);包级证据
v41/rb7925 行互补(v41 镜像收割 100%,rb 修弱行)但 shop 特征看不见对手。

- **嫁接定律**:fam_F 与 rb7925 前 72 步唯一差异是 rb 让 1 号帮工闲置;t=72 双向嫁接
  零损耗(±33 金)。cand_0↔fam_F 在 144/288/432/576 全边界互通(≤79 金)——cand_0
  是 fam_F 的市场变体。块转移图:{F,C} 全通;{F,C}→R 可在 72/144/288;R→{F,C} 仅 288。
- **纯带 shop 矩阵**(20 对手 × 64 seed 双席位):rb 0.854 > cand_0 0.811 > fam_F 0.748;
  Crop_Dusta 带纯带内战仅 0.055——顶队的强不在带里,照搬无用。三带 shop 路由仅 +1.6pt。
- **包级门控推翻纯带排序**:v41 包 0.819 ≈ rb 包 0.812(纯带差 10.6pt!)——武器层×带
  交互决定包级强弱,门控必须在包级做。v49(纯 shop 路由)0.812 与现役平,不提交。
- **对手可观测性**:农场瓦片指纹 t≤144 全场同质(MELO12/PAST6/WHEA7)——「顶部不读
  对手」的真因是农场端读不出来;**市场端 t≤32 可分族**:dWHEAT(t0,t1) 分出 13/8 同款
  (-27/+16)、pert_1(-34)、Andrey(-44)、keiz(-57)、海洋无扰动(-14/+3),OceanMix 另有
  t28 卖 3 麦特征。窗口教训:检测窗不能覆盖我方前缀自身的 t30-32 买麦(首版误判全海洋)。
- **V50(已提交,56xxxxxx)**:fam_F 前缀 + t=72 两级闩锁(市场指纹优先:13/8 同款→F 尾
  LEAD 镜像收割、dw0≤-31 大扰动→rb 尾、Ocean t28→F;shop 表兜底 BRUNCH/ICE→c0 余 rb)
  + v41 武器层原封。holdout(2000-2015)0.834;全新 seeds(3000-3015)0.853;
  头对头 vs v41 4/8、vs rb 6/8、vs V32 4/8。行剖面:镜像/Ocean/G 100% 保留,A 69/D 84/E 56
  部分吃到 rb 修复。三 slot 变为 v41(1999)/rb7925(2046)/v50,顶掉 V32(1962)。
- 工具沉淀(v49_shop_router/):world_matrix.py(带×对手×seed 分桶矩阵)、gate.py
  (包级 holdout 门控)、graft/block_graft(边界拼接验证)、market_fp/fingerprint(对手
  指纹侦察)、build_v49/v50(路由包构建)。
- B 阶段(块级 CART 路由)缺口:graftable 家族内只有 F/C(同构)与 R 两种尾部结构,
  块候选多样性不足;明天用 rebirth 管线拉线上新带扩充块池,按转移图组装 30+ 全季路径。

### B 阶段首日:块池证伪 + 新带路由 v51b 上线(2026-09-07 下午)

- **v50 部署验收(6/6 全胜)**:上线 1 小时拉首批 6 局公开局,重建路由决策逐局比对——
  F/rb/c0 三条尾部全部真实触发且市场单逐单一致(c0 局 220/220);rating 爬升中(1110@6局)。
- **块池全量扫描(v51_block_router/block_pool.py)**:带库 30 带 × 5 边界嫁接:
  全边界可接=cand_0/变体系/rb 系/OceanMix/v47;t=288 是万能接口(cand_2/fam_B/D/E 仅 288+ 可接);
  pert 系/top 系/Crop_Dusta 布局异构不可接。
- **块候选对战全军覆没**:13 个新块组合(含 rb 前段+E 尾单人 +3.7k 的组合)对战全部劣于
  rb/c0/F 三尾(最好 0.760 < rb 0.865)——**本地带库块多样性已榨干;
  单人产出≠对战力再证(rbh288_fam_E +3.7k 金却 0.602)**。
- **rebirth 当日捕获**:新家族母带 rb_fed85a15a6(Skibidi Six Seven,197.9k,重合仅 46%)
  + 5 条备用。纯带行剖面:fed85a 是海洋族克星(fam_A 96/E 100/D 100);rb_837669b4a0 是
  cand_0/pert_1 双 100% 克星但单人 seed 依赖崩(70k@seed11)。
- **v51(13/8→837669)门控 0.797 失败**:837669 纯带对 fam_F 100% → 包级 56%——
  市场依赖型带与武器层(LEAD/MM 动市场单)冲突,包级教训第三次应验。
- **v51b(已提交)**:v50 全规则保留 + 单分支「无扰动海洋 + 对手 t2 卖麦 +2(fam_E/G 特征)
  → fe 尾(fed85a)」。holdout 0.847 / fresh seeds 0.863(v50 同批 0.834/0.853);
  fam_E 行 56→100;fam_G 94→75(E/G 需 t148 才可分,留给未来 t=288 第二决策点);
  头对头 vs v50 4/8、vs rb7925 6/8。
- **线上指纹分布(online_fp_stats.py)**:粗口径(混老数据)61% 对局对手是 13/8 同款开局
  ——线上被 fam_F 系变体统治;干净样本尚少,待 v50/v51b 累积对局后精算各分支线上胜率。
- 明日方向:①v50/v51b 线上对局复盘,校准分支触发率×胜率;②t=288 第二决策点
  (E/G 的 t148 特征改判、F↔fe/rb 的 288 互切已验证);③rebirth 持续挖新家族喂块池。

### V52:细刃局 margin 工程首刀——V46 施肥分支并入路由包(2026-09-07 傍晚)

- 背景:v51b 线上 21 局 19-2(90.5%,分支校准 13/8 6/6、fe 1/1),v50 35 局 27-8;
  10 场败局全为细刃局(差 234~6000 金,零崩局)——败在 margin 不在执行。
- v52 = v51b + V46 草莓施肥分支(fill 层 4 行:PASS 工人脚下草莓未施肥且身上有肥、
  day≤27 → FERTILIZE)。单人 +31/+142/+154 金。
- 门控:holdout 0.847 / fresh 0.863,与 v51b 完全持平(本地池细刃局少,+150 金不改胜负);
  **头对头 8/8 全胜、平均 margin +116**——镜像/细刃局的胜负手实锤。
- 已提交(第 3 发/日)。slot 阵型:rb7925(2043)+ v51b(2024↑)+ v52,顶掉 v50(1770)。

### 金牌区 replay 全景分析(episodes index 09-05 全量 664 局,2026-09-07 晚)

数据:kaggriculture_episodes_index date=2026-09-05(20GB,收录 top≈3027/median≈2877 的金牌区对局),
gold_extract.py 压成逐局生产指纹(v51_block_router/gold_0905.jsonl)。

**核心发现:施肥策略是金牌区顶部与主流的分水岭。**
- 高胜率三家全是「早肥多肥」流:kwa 67%(128 肥/首肥 t256)、keiz 66%(106 肥/t329,183 局样本)、
  Crop Dusta 61%(150 肥/t155,场均 95.5k 全场最高)。keiz 施肥段分布 d12-30 每 3 天 9-25 步,
  Crop 从 d6 起步、d18-30 段 25-32 步。
- 金牌区主流是 ~50% 胜率大团(MtN/Jesse/Andrey/CemBas/OceanMix 等):统一指纹
  肥 61-68/首肥 t342-347/harvest 456-470/plant 239-251——**与我们同谱系**。
  我们的带(自带肥 ~75,d12 后)就是这个大团的成员:进金牌区后将是镜像海,
  LEAD 先手层是既有优势,但施肥缺口(-30~-80 步,且晚)是结构性劣势。
- 异类:巨量幻影卖单流(薄和叶 WHE2228/MEL2071 每局、Scott Willis FER 百万级挂单),
  胜率 46%/26%——市场占位/操纵流存在但不赢,不学。
- 供给侧:我们带 d9-30 有 ~384 个 PASS 槽,装下 30-80 步施肥没问题;瓶颈是
  「工人恰好站在可肥作物上且手上有肥」的巧合率。

**v53-lite 证伪(未过门控第一关,不上线)**:V46 从草莓扩展到全作物 → 单人 -197/-659/-638
(肥料浪费在低价值作物+FERTILIZE 挤占浇水);草莓+番茄档=零变化(我们谱系不种番茄)。
**结论:fill 层「脚下机会主义施肥」的果实已被 V46 摘完;keiz/kwa 级的 100+ 施肥
必须走离线带编排(fert weaver),不是运行时规则能凑出来的。**

**下一版主项目 v54 = 离线施肥编排器(fert weaver)**:
1. kagsim 重放我们的带(单人),逐 turn 记录每工人位置、田块施肥状态、随身肥料;
2. 在 d9-27 窗口改写动作:PASS→FERTILIZE(就地)与「顺路」MOVE 微调(多步窗口,离线可做);
3. 肥料预算重排:自产 384 中自用 98+30 → 提到 130-150,相应减后段卖肥单
   (施肥边际 +276/步 vs 卖肥 ~100/单,净边际 +176);
4. 预期毛收益 +8-11k/局,净 +5-7k;
5. 门控全链(单人 → holdout → fresh → 头对头)全过才上线,任何一关不过即弃。

### v54 施肥深化:快速路径全线证伪,收敛到离线规划器(2026-09-07 深夜)

**新霸主解剖(09-06 数据)**:「我都先道歉」(77%/105k/174 肥)与「沒有道歉」是**真·在线
SCHEDULER**——同队两局动作重合仅 1.4-9.4%、t=1 即分歧、每局轨迹全不同;开局 7 连 HIRE+
全员牵牛。带与全库重合 0-3%(全新家族),单人产出强 seed 依赖(103k~214k),
**完全不可嫁接**(@72/144/288 全 LOSSY -78k~-207k)。金牌区顶部已代际跃迁:tape/路由流
(Crop 45%、Mengfei 42%)正被 SCHEDULER 流淘汰。
配方差异 top4:d18-30 施肥密度差 ~90 步、番茄产业缺失(8 株→93 卖量)、尾盘胡萝卜
(70 vs 14)、开局多雇 13 人。

**施肥移植三连证伪**(负知识,勿重试):
1. weaver 诊断:我们带的 straw_shedfert 池 48 个/局(站草莓上、棚有肥手无肥),
   pass_not_on_crop 239(需 MOVE 编排);
2. 离线改写(插 PICKUP+FERTILIZE):13 对中 12 对被引擎静默 noop(插入时刻棚恰无肥);
   唯一生效的 1 对导致**草莓 -16 产量**(PICKUP 占携带位挤掉收获)且单人口径混沌放大
   (-7k/+35k/-24k,配套加卖单零影响——市场是混沌放大器,单人口径对改写失真);
3. 对战口径终审:fw 带 0.566 vs 原带 0.744(-17.8pt),镜像 8/16→0、Ocean 16→4。
   **结论:精调带上的增产改写 = 混沌系统局部手术,双口径皆负;
   高施肥优势只能通过从头生成的生产结构获得。**

**明日主项 v55 = 离线带生成器(规划器跑在开发机,线上仍是带+路由)**:
- 按新霸主配方(174 肥/番茄/尾盘胡萝卜/开局 13 雇)+ 我们的先手卖出纪律,
  在 kagsim 里对每个常见 shop world 从头生成一条带(贪心/搜索,容量-物流-施肥一体规划);
- 传送线:生成带 → 单人 sanity → 对战矩阵(口径以对战为准)→ 嫁接不需要
  (自生带可原生共享前缀)→ 装入 v51b 路由 → 包级门控全链 → 提交;
- 已有资产:kagsim 0.3s/局、apo/noapo 四条参照带、gold_0905/0906 全量配方数据。

### v53e/v53d 双发收官:包级数据驱动的表修订 + a8 镜像分支(2026-09-08 凌晨,UTC 09-07 第 4/5 发)

- slot 机制实锤:活跃位=最新 2 个提交(v52 上线后 rb7925 12:48 停配,其 2043 为冻结分)。
- 包级审计(v51b/v52 门控 2560 局):SMOOTHIE 桶 68.5% 全场最弱(pert_2 0%、fam_A 33%)、
  FARMERS 81%(Jesse 0/8)、13/8 分支 75% 最弱分支(cand_0 拖累)。
- **v53a 表修订**(SMOOTHIE/FARMERS→c0):holdout 0.856/fresh 0.883,FARMERS 桶 81→100%,
  头对头 vs v52 4/8 纯平——无害。
- **肥料 LEAD**(v53b):对外 0.855、cand_0 62→78,但**内战 2/8 -236**(双方抢卖肥自伤)。
- **a8 分支**(13/8-clone → rb_84a8a63442 尾):cand_0 行 62→100%、镜像 100% 保持。
  b8 的包级失败不是"克星带都不兼容"——84a8 与 F 同源故与武器层兼容,教训细化:
  **市场结构异质的带(b8)与层冲突,同源微变体(a8)可安全换装**。
- **v53e = 表修订 + a8**:holdout 0.875 / fresh 0.914 / 头对头 vs v52 8/8 +2383(四关全过,
  内战 8/8 = a8 打对方 F 尾的镜像碾压兑现)。
- **v53d = v53e + 肥料 LEAD**:0.872/0.895/8/8 +1812,行为差异化对冲位。
- 双双提交(UTC 09-07 额度 5/5 用完)。活跃 slot:v53e + v53d。
- 本地门控演进史:v41 0.819 → v50 0.834/0.853 → v51b 0.847/0.863 → v52(+margin)
  → v53e 0.875/0.914。

### v54c/v54d:门控池换血 + chocolat 新代尾(2026-09-08 上午,UTC 09-08 第 1-2 发)

- **线上复盘暴露门控池失效**:v53e 线上 78.3%(69 局)、v53d 55.2%(105 局),远低于门控
  0.875-0.914;a8 分支线上 33-54%(门控 100%),且 v53d 对局 62% 触发 13/8;败局 margin
  -10k~-38k,对手 bank 95-128k——**线上 1600-2100 段已被新代高产 13/8 变体占领,
  8 月末 20 带旧池与现实脱节,门控分数是对旧世界的**。
- **对手即弹药(当日闭环第三次兑现)**:从今日 174 局提取 82 条强对手带,10 条前缀兼容
  ≥90% 全部嫁接零损。新池(top24)纯带矩阵:**ch(chocolat 尾,86% 兼容)0.815 全场最强**,
  打穿旧无解行(GamesJadley/Q1du/Joyal/8fcc/EnricRovira 全 100%);gj 0.758;旧王 a8 0.654;
  旧默认 rb 垫底 0.510。oracle 0.755→0.891。同族相克链:F→a8→ch 逐代克制。
- 证伪:v54(纯带数据全 a8 表)包级 0.632<v53e 0.644——第 4 次踩「纯带排序≠包级」;
  vineet/YinLi 高产带(solo 超 fam_F 7-16k)对战 0.44-0.47——SCHEDULER 单局输出不可当尾;
  SHALWIN 行 0/10 尾全灭,真无解,留给离线生成器。
- **v54c(已提交)**:v53e + ch 尾(13/8 分支 + shop 表默认位,BRUNCH 保 c0)。
  新池包级 0.726(v53e 0.644)、**旧池 0.909**、头对头 vs v53e 8/8 +2872。
- **v54d(已提交)**:v54c + 肥料 LEAD,新池 0.763(对新代对手最强),差异化对冲位。
- **门控流程升级**:自此双池门控(newpool 当日 top24 + 旧池回归)+ 头对头;newpool
  每日从自家对局重建(newpool_matrix.py + 提取脚本),对手池的保鲜期按天计。

### V55 生成器第一日:执行框架建成,复利链通,变现链待修(2026-09-08 下午)

- 架构落定:fam_F 前缀(t<72)+ 调度器接管;机制实测表见 v55_generator/README。
- 四个结构 bug 依次定位修复:①坐标系(farmer=[x,y] vs tiles[y][x],曾致全员堵角落);
  ②空地=None(补种任务从未生成);③BUY_LAND 缺失(全场只 25 格 vs fam_F 75 格);
  ④起步变现死锁(t72 只剩 27 金,卖麦阈值挡住第一个雇工)。
- 进度:17k → 32.7k(参数搜索)→ 结构修复后生产链全通(PLANT 119/WATER 742/HARV 152)
  但 bank 仍 32k——**变现链断裂**(疑自砸市场:premium 供给 60-80 单位即崩价)。
- 搜索管线就绪(search.py,14 参数 × 3 seed 并行);今日提交额度已用 2/5(v54c/v54d)。


### V55 生成器持续迭代:对战口径 8k→51k(2026-09-08)

- 用户设定上线门控:必须本地打赢最近六次提交的线上包(v51b/v52/v53e/v53d/v54c/v54d);
  未过前沿「自创策略+浅规则树」继续研究。门控预演:0/24,均差 -59k(我 45k vs 六包 104k)。
- 架构级收益链:固定预算发单(拆现金守卫,对战 8→27k)→ 作物窗口优先(37k)→
  本格任务优先一行 +40% → 动物静态划区+栏舍集中(49k)→ 爬山(51k, solo 71k)。
- 六项证伪:价格感知停售/象限3/晚牛/大畜牧/动态编制/蛇形巡回(详见 v55_generator/README)。
- 差距解剖:对战产出 51k vs 需求 104k;审计残余缺口=鹅链(77% 未喂)、浇水覆盖(50%+ 未浇)、
  施肥 54% 覆盖;根本瓶颈是农场吞吐动线与 fam_F 离线精调动线的差距。

### V55 三线并行(A修链爬山/B浪费审计/C混合)结果(2026-09-08 续)

- A:鹅饥饿提权+爬山 → 8 局对战均 51.3k,单局峰 72k(vs ch);EMA 卖出择时中性入参。
- B:浪费审计器(waste_audit.py)证明执行效率已 89%(PASS 8.6%、各动作无效率 2-7%)
  ——执行浪费不是瓶颈,认知转向动作价值密度。
- C:hybrid(带农场+实时市场)与纯带打平(+0~4k);实况调度器每 turn 3-6ms,
  线上 1s 预算余量巨大 → **调度器可直接上线,录带失配问题消解**。
- own_opening(自主开局)44k < prefix 51.3k,搁置留档(scheduler 支持 own_opening=1)。
- **对手收入表解剖(决定性)**:ch 基价收入 177k vs 我们 76k;其 2/3 来自动物经济
  (奶 41k+毛 39k+肥 37k,17 头牛羊);番茄/蛋/胡萝卜是伪产业(<8k)。
- **大畜牧三连败**(参数版 11.8k/日程版 30.1k):第 7+ 头动物在我们的动线下边际为负。
  根因=MOVE 占 60% 吃掉运营预算;ch 离线动线省出的移动步=多养 9 头的本钱。
  **最后硬骨头 = MOVE 压缩**(布局分区条播/工人日程闭环/作物-栏舍空间协同设计)。

### V55 MOVE 压缩专项:七连证伪,浅规则架构天花板确认(2026-09-08 续)

诊断:MOVE 4289/7106=60%,长途段(≥3 步)3011 步;分工种:farm 1772(任务跳跃)、
animal 966(栏舍两片+取料)、fert 217;PICKUP 181 次往返 ~1400 步。

七项试验全部证伪/中性(基线 51,311 可精确复现):
1. 批量取货(qty 8/6):暴跌 20.5k——随身占位挤掉收获物;qty=4 即甜点(2:43.6k/3:50.2k/4:60.9k);
2. 分层评分(优先级弱化换动线连续):单调劣化——优先级纪律(浇水时效)> 动线连续;
3. 惯性折扣(同方向任务优先):单调劣化(附带 bug:折扣把 dist=1 变 0 误判本格,已修);
4. 栏舍连片选址:中性(与环带逻辑等效);
5. 同心圆种植(高频内圈):四值一字不差——贪心"最近优先"已隐式优化空间结构;
6. 加人(hire 14/16):-21k/-42k——HIRE 实测前 10 人仅 143 金(基价 1 的 fib),但多余人无任务
   且 HIRE 单挤占 10 槽市场单;12 人=任务结构饱和点;
7. 日排程链(hour2 全天浇水最近邻链):-2.4k——排他链延迟收获/补种。
   (附带机制:hour0 雇工未到岗,build 链须 hour>=1。)

**架构级定论:反应式贪心调度器(浅规则)在本游戏对战口径的天花板 ≈ 51k。**
ch 的 104k 中约一半来自离线全局排程的动线红利(MOVE 60%→~45% 省出的动作预算
= 多养 9 头动物的 117k 动物经济),这超出"运行时浅规则"的表达能力——
需要离线搜索/排程生成(而生成后即是带,回到带的世界)。

### V55 A/B 续:重排证伪关闭 + 重大机制发现「商店解锁是内生的」(2026-09-08 深夜)

- **A 线(离线事件重排)证伪关闭**:四版递进(411→5k→40k→40k),单组差分证明重排本身
  无害(前 5 组 Δ+0)、二分定位 6 个崩塌组、修"新种格浇水不早于原时刻"后仍 4 seed
  全负(均 -11.7k)——**"日内时刻等效"假设被引擎证伪 + 市场混沌放大(第 5 次)**;
  事件级重排在此引擎不可行,内嵌全状态模拟=重写规划器,关闭。
  周边产出:日志无损性验证、组级差分工具、逐格 diff 工具。
- **B 线爬山**:51.3k→57.9k(share_straw 30 主推),seed11 单局 vs ch 打出 105k
  (触门控级)→ 方差主因=shop 世界。
- **商店消耗谱(实证,钉商店 PASS 局)**:YARN→WOOL310;PET_CAFE→CARROT274;
  SMOOTHIE/ICE/BRUNCH→STRAWBERRY119+奶/蛋155;PIZZA→TOMATO+WHEAT119+MILK155;
  BAKERY→WHEAT119+EGG155;FARMERS→四作物各119;城镇基础消耗 WHEAT655/MILK558/STRA414…
- shop 适应两版(份额偏移/窗口开闭)皆负:58k 配置已是跨世界稳健解,单向偏移伤基本盘。
- **重大机制发现:首店(商店解锁序列)= seed × 双方前 72 步行为共同决定(内生)**!
  PASS 口径 seed→首店表对实局无效(seed32 PASS 局 PET_CAFE、实局 BRUNCH);同前缀
  同对手下确定。这解释了世界爬山 holdout 全崩(世界标签错)与社区只读"实局首店"的原因。
  已重建实局口径表(real_shop_table.json,238 对局),世界爬山 v2(训练 4 对+holdout 4 对
  验收制)8 世界后台运行中。

### 「自创策略+浅规则树」路线实验封顶(2026-09-09)

最后一批方向全部证伪,天花板由实验划定:
- 市场单序重排三试全负(SELL 前置 -10k、HIRE>SELL>BUY -12k)——单序是与调度器共同
  演化的自然平衡,任何重排截断关键单(第 6 次印证"未共同演化的层是负资产");
- MM 买入侧被规则禁止(BUY_PRODUCT 仅麦/肥),premium 低吸不存在;
- 门控口径爬山(对手=v53e/v54c 包):训练 53.3→60.6k,但门控预演 margin 无改善
  (0/8, -95.8k)——训练增益是 8 局评价噪声;
- 右尾收割证伪:seed11 105k 顺风局录带跨 seed 36-60k(-50%),且顺风局本身也输
  (对手 112.9k)——右尾是当局价格轨迹运气,不可移植。

**路线结论**:浅规则运行时贪心在本引擎的对战产出上限 ≈55-60k(20+ 轮结构迭代、
运行时/离线双向探索);门控六包(离线精调带+武器层)对打产出 ~150k,差 2.5 倍。
两条独立证据链(社区调度器 15 连败 + 本线全图)指向同一结论:**运行时浅规则无法
达到离线精调带的执行密度;过门控需要路线定义之外的要素**。
产出资产:调度器全家(58k 稳态,可复现)、实局首店表、商店消耗谱、seed→世界机制、
8 项负知识、爬山/审计/录制/重排全套工具。
