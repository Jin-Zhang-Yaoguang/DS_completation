# V116 启发式研究迭代记录

## 目标

构造一个不依赖父 agent、不含 Replay 动作或逐步位置蓝图、由规则/浅树模型驱动的
Hierarchical MoE。只有在冻结的金牌模型池上双座位纯胜率不低于 75%，且 Router 严格优于
最佳固定专家，才登记到 `golden_model.md`。

## R0：719 步目标状态执行器——淘汰

- 实现：从轨迹编码 719 个逐步目标，再由状态安全执行器尝试恢复动作。
- 结果：1 seed × 6 个金牌锚点 × 双座位，`0/12`；候选终局约 15k–23k。
- 原创性：失败。逐步位置虽未显式保存动作，但仍是等价开环蓝图，违反冻结协议。
- 机制根因：状态目标不能唯一确定融资顺序、物流承诺和市场槽位；首个状态漂移后，贪心
  分配器无法恢复原生产链。
- 决策：停止扩大样本，R0 永久淘汰，不进入实验注册。

## R1：日级聚合目标 + 在线任务图——淘汰

### 模型边界

- 每局最多 30 个日级目标；只含土地数、hands 上限、作物/建筑/动物数量、种子/棚库储备、
  商品产能等聚合值。
- 不保存 action、actor 位置、tile 坐标序列或任何长度为 719 的策略向量。
- 布局由候选自己的确定性 compiler 生成；每回合动作由当前状态与目标差异生成。

### 分层结构

1. 商店需求 Router：商店公开后，在 wool、dairy-fruit、balanced 三个生产专家间选择；
2. 生产专家：把日级聚合目标变成作物、畜牧、扩张任务；
3. 状态安全执行器：任务 deadline、携货、共享 shed 和原子资源约束下分配 actor；
4. 商品级出售控制器：根据 projected shed、饲料/种子储备和当前价格产生订单；
5. 对方路径预测：只作高置信 veto，基础模型过门前默认关闭。

### 递进门槛

1. **执行健康门**：未见 seed 对 idle 平均终局 bank `>=70k`，日目标兑现率 `>=90%`；
2. **锚点门**：8 seeds × 6 金牌 × 双座位，纯胜率 `>=75%`，零错误；
3. **Router 门**：FULL 严格优于最佳固定专家，有正胜负翻转，三个专家均真实激活；
4. **Development**：64 × 18 × 2；
5. **Confirmation**：128 × 18 × 2，模型/seed/对手/引擎哈希全部冻结。

执行健康门只是提前止损，不是金牌证据。任何门失败，都按逐局归因递增版本，不回头调已
暴露 confirmation seed。

### 实测结论

- 合规：30 个日目标，无 Replay 动作/逐步位置流；四个生产专家均真实触发；719 调用完整，
  0 schema violation、0 fallback。
- idle smoke：4/4 胜，但平均 bank 只有 `34,213`，低于 70k 健康门。
- 金牌锚点：8 seeds × 6 对手 × 双座位，`0/96`；候选均值 `16,747.99`，对手均值
  `129,927.84`，平均败差 `-113,179.85`。
- 机制证据：96 局累计 move 304,369 次、idle 188,914 次。日目标只描述“建什么”，没有
  恢复小时级的资本顺序、持久物流和市场融资链；继续调商店 Router 没有意义。
- 决策：R1 淘汰，不进入实验/金牌注册。

## R2：低移动拓扑 + 24 小时滚动任务拍卖

R2 保持 R1 的原创性边界，但替换最弱的执行层：

1. compiler 先最小化资产到 shed、同角色任务间的预期移动，不使用老师路线坐标；
2. 每个 actor 持有跨回合任务链，按 deadline、移动距离、携货匹配和切换惩罚竞拍；
3. 先完成 `HARVEST → 回仓 → SELL → 采购` 的现金闭环，再扩大土地和畜群；
4. 用 24 小时滚动窗口估计任务可兑现率，超过劳动容量的生产目标直接延后；
5. 对手预测和复杂需求延迟继续关闭，直到底盘通过 70k/90% 健康门。

### 实测结论

- 冻结 smoke：4 个未见 seed × 双座位，共 8 局；每局 719 次调用，零 schema 错误。
- 原创性审计通过：只含 30 条日级聚合目标，无 Replay、逐步位置、父 agent 或 `_ACTIONS`；
  合法现金状态扰动会改变市场动作。
- 对 idle 为 `8/0/0`，但平均 bank 只有 `67,603`，中位数 `70,423.5`，区间
  `[56,308,72,155]`，低于冻结的 `70,000` 均值门。
- 日级目标平均兑现率 `80.62%`，低于冻结的 `90%` 兑现门；两个健康门均失败。
- 机制测试单独确认商品控制器的逐单位动态价格、现金账本、仓容/储备、十订单上限和终局清仓；
  这只是部件正确性，不是完整模型强度。
- 决策：`FAILED_IDLE_STRENGTH_AND_TARGET_REALIZATION_GATE`。R2 淘汰，不进入金牌 arena，
  不注册 `golden_model.md`。

## R3：商店需求 Router + 四生产 genome + 公平补种（进行中）

R3 不改写 R2 失败产物，新增独立候选：

1. 首个可见商店/城镇需求只路由一次，在 balanced、wool、dairy、orchard 四个紧凑 genome
   中选择，禁止用对手身份或隐藏信息；
2. 补种从固定 WHEAT/MELON 优先级改为按目标缺口比例、公平年龄和当前库存共同排序，防止
   STRAWBERRY/CARROT 长期饿死；
3. 集成已通过机制测试的商品级动态价格、出售融资和储备控制，但完整候选必须自包含；
4. 保持 sticky role、全局任务拍卖、状态安全执行器和 30 条日级聚合上限；
5. 仍先执行相同 4 seed × 双座位健康门。只有平均 bank `>=70k` 且平均日目标兑现率
   `>=90%` 才能进入金牌锚点。

### 实测结论

- 同一冻结回归面板 4 seed × 双座位共 8 局；对 idle `8/0/0`，每局 719 calls，零 schema
  错误；静态原创性、首店路由和状态扰动审计通过。
- 四专家最终作物目标均为 59；末局绝对生产资产最低 63、最大观测 68，没有用缩目标提高
  兑现率。
- 平均 bank `69,882.125 < 70,000`；平均日目标兑现率
  `89.9222% < 90%`。两项均非常接近，但冻结口径不取整、不放宽。
- PET_CAFE 路由到 balanced_root 的两局均值只有 `56,640`；其余 6 局均值约 `74,296`。
  这说明主要剩余尾部来自公开需求与商品配置错配；阶段目标突增仍造成前中期兑现缺口。
- 决策：`FAILED_RC3_HEALTH_GATE_DO_NOT_RUN_GOLD_ARENA`。R3 淘汰，不进入金牌 arena。

## R4：24 小时阶段预备 + 通用商店需求投影（进行中）

为避免在 4 个已暴露 seed 上无边界调参，R4 只允许两个机制：

1. 仅在 day 4/day 8 对下一阶段做 24 小时真实预备：允许提前购买土地、种子、动物、hands、
   饲料并建设结构；种植、放置和日常维护仍服从当日目标，禁止多日 lookahead；
2. balanced_root 按首次公开商店商品，把第二、第三阶段的非需求作物确定性转移 3/5 格给需求
   作物；总作物目标仍为 59，并保留 WHEAT/MELON/STRAWBERRY 下限。PET_CAFE 的预注册终局
   投影为 `W24/M15/S9/C11`。

R4 先在 7100–7103 只作回归，再在不查看候选收益、仅按首次商店类别选出的 4 个新 PET seed
和 4 个新非 PET seed 上双座位确认。两面板各自必须同时通过 70k/90%、末局绝对生产资产
不低于 58、719 calls 和零错误；新面板的 PET/非 PET 分层均值还须各自不低于 65k。只有全部
通过，才允许进入金牌锚点。

### 回归结论

- 7100–7103 双座位 8 局平均 bank `74,030.625`，通过 70k；最低末局生产资产 58，通过
  绝对规模门；每局 719 calls、零 schema 错误。
- 平均日目标兑现率降至 `87.4618%`，低于 90%；因此按顺序门立即停止，未选择、未运行
  fresh PET/非 PET 面板，也未运行金牌 arena。
- 与 R3 相比，收益上升但兑现率下降，且 PET_CAFE 两局仍只有 `45,372/59,338`。两项新
  机制同时加入，当前不能把改进或退化归因给其中任一项。
- 决策：`FAILED_RC4_REGRESSION_GATE_STOP`。先在已暴露面板做 staging-only 与
  projection-only 的 2×2 因果消融，再构造 R5；消融只用于选机制，不作为晋级证据。

### 2×2 机制消融

| 模式 | 平均 bank | 平均兑现率 | 最低末局生产资产 |
| --- | ---: | ---: | ---: |
| R3：无新增机制 | 69,882.125 | 89.9222% | 63 |
| staging only | 77,475.000 | 87.4019% | 58 |
| projection only | 75,190.500 | 89.7677% | 57 |
| R4：两者同时 | 74,030.625 | 87.4618% | 58 |

- staging 单独使 bank `+7,592.875`，但兑现率 `−2.5203pp`、末局资产均值 `−2.875`；
  它用未来扩张挤压当前维护，淘汰。
- projection 单独使 bank `+5,308.375`，兑现率只下降 `0.1546pp`；作用仅出现在两局
  PET_CAFE，bank 分别 `+25,196/+17,271`，其余六局逐局不变。
- 两机制存在负收益交互 `−8,752.75`。R5 只保留 projection；消融面板已暴露，不能作为
  fresh 或金牌证据。

## R5：需求投影 + 收获绑定补种——淘汰

R5 从 projection-only 分支继续，禁止恢复 staging。新增机制必须直接修复有限周期作物在收获、
补种之间的空窗和最低末局资产 `57 < 58`，同时保持 projection-only 的收益；具体机制先经源码与
逐局任务审计冻结，再运行回归和全新分层健康面板。

### 回归结论

- 机制把每次真实执行的 non-ongoing HARVEST 绑定为最多两条补种 claim；仅为真实 claim
  预留种子，并把空地补种提高到 priority 1。
- 8 局平均 bank `76,164.875`，但平均兑现率只有 `89.8232%`，最低末局生产资产跌至 52；
  每局 719 calls、零错误，原创性审计通过。
- 8 局累计创建 1,119 条 claim。限制“每回合最多两条”仍会跨 720 回合累积，priority-1
  补种与持久占位反而挤占维护和普通目标，属于任务洪泛。
- 决策：`FAILED_RC5_REGRESSION_GATE_STOP`；未运行 fresh 或金牌 arena。

## R6：公开需求作物的有界补种 option——淘汰

R6 回到 projection-only 基线，不继承 R5 claim 状态。补种闭环只允许服务首店公开需求中的
non-ongoing 作物，并同时限制 live claim、每日新增和存活时长；目标是保留 PET_CAFE 投影收益，
消除 R5 的任务洪泛。边界冻结后仍先跑已暴露回归，再决定是否消费 fresh 面板。

### 回归结论

- live claim 最多 2、每日新增最多 2、TTL 6 步；只在两个 PET_CAFE/balanced 局触发，
  共 64 条 claim，scope 零违规。
- 8 局平均 bank `70,291.25`、最低末局生产资产 62、719 calls/零错均通过；平均兑现率
  `89.9565% < 90%`，差 `0.0435pp`，仍按失败处理。
- PET 两局兑现率从 projection-only 的 `89.1414%/89.2851%` 提高到
  `90.0165%/89.9208%`，但 bank 分别从 `74,855/80,892` 降到 `53,300/63,253`。
  有界补种修复了生产连续性，却以过高的收获机会成本换取目标占用。
- 决策：`FAILED_RC6_REGRESSION_GATE_STOP`；未运行 fresh 或金牌 arena。R7 必须同时恢复
  PET 收益并补足极小的全局兑现缺口，不能继续增加 claim 数量。

## R7：同轮收获后的种子预留——淘汰

- 回到 projection-only 劳工拍卖，删除坐标 claim 与 priority-1 补种；只对本轮实际执行的
  公开需求作物 HARVEST，在同轮市场按收获后库存预购替换种子。
- 8 局平均 bank `70,566` 通过；平均兑现率 `89.7796%`、最低末局生产资产 55 均失败；
  每局 719 calls、零错误，机制 probe `7/7`、scope 零违规。
- 两个 PET 局累计 139 次 eligible harvest。种子提前一轮到位，但普通 priority-3 PLANT
  仍受劳动执行延迟约束，未守住生产资产。
- 决策：`FAILED_RC7_REGRESSION_GATE_STOP`；未运行 fresh 或金牌 arena。

## R8：参数化启发式搜索（方案重构中）

R3–R7 已显示手工单点修补在 bank、目标占用和劳动路径间反复转移损失，且当前 70k–76k 的
idle 资金量级仍明显低于本地金牌对手约 130k 的水平。R8 停止逐版本手调一个补丁，改为：

1. 将紧凑生产 genome、任务拍卖权重、市场阈值和首店浅树 Router 参数化；
2. 用公共随机数、固定训练/开发/确认 seed 分割和多阶段早停做 derivative-free 搜索；
3. 第一目标直接包含对金牌锚点的纯胜/分差，idle 资金与兑现率只作灾难护栏，不再单独充当
   强度代理；
4. 搜索产物仍只允许聚合参数和规则，不得写入 Replay 动作、逐步坐标、父 agent 或等价路线；
5. 最终仍按 18 金牌、双座位、75% 纯胜、Router BEU 和 fresh confirmation 协议裁决。

### 首代全局控制器搜索结果

- sealed manifest 共 258 个互斥 seed，与 7 个历史 exposure 源和 7100–7103 的交集为 0；
  R1/R2/R3/R4、Router、Development、Confirmation 均预先分离。
- R1：128 组全局 auction/market 参数 × 8 seed × 双座位，共 2,048 局；全部 DONE、719
  calls、零 schema，留 32。头名平均 bank `80,517.5`、CVaR25 `75,680`。
- R2：32 × 24 fresh seed × 双座位，共 1,536 局；全部胜 idle、零错误，12 个候选均通过
  mean bank `>=70k` 与 CVaR25 `>=55k`。头名平均 `78,806.65`、CVaR25 `65,832`。
- R3：12 × 18 金牌 × 2 fresh seed × 双座位，共 864 局；零 ERROR/违规，但总计
  `0/0/864`。候选均值 `52,875.13`，对手均值 `154,089.43`，平均分差 `−101,214.31`。
  最佳配置仍为 0 胜、18/18 对手中位分差全负，中位分差 `−73,081`。
- 决策：`FUTILITY_ALL_CONFIGS_FAILED`；R4 未启动，dev/confirm 未访问。只调静态拍卖和市场
  阈值不能应对强对手引起的共享市场路径变化。

## R9：公开对手路径预测 + 反市场碰撞浅树——淘汰

R9 不再扩大静态阈值搜索。先对 R3 已暴露 seed 做同 seed/seat 的 idle 与金牌配对日级轨迹
诊断，定位强对手如何改变候选资金、商品库存和公开市场路径；再仅用路由时或当前已经公开的
对手作物、动物、土地、hands、价格/库存变化构造最大深度 2 的路径分类器。分类器只能调整聚合
生产目标和出售策略，禁止预测未来隐藏事件或调用对手 agent。任何分支必须先做 predictor-off
消融并产生正 margin 翻转，才允许重新进入 sealed 搜索。

### 配对诊断与固定专家反证

- 同一 p0064、2 个已暴露 R3 seed、双座位，分别对 idle/V21 共 8 局：全部 719 calls，候选
  零 schema 错误。idle 下候选均值 `80,887.25`、分差 `+77,887.25`；V21 下候选均值
  `49,107.50`、分差 `-79,936.25`。同 seed/seat 的 V21-minus-idle 使候选 bank
  `-31,779.75`、分差 `-157,823.50`。
- 强对手会改变共享 RNG 下实际出现的首店：两个 seed 分别从
  `ICE_CREAM_SHOP -> FARMERS_MARKET`、`PIZZA_SHOP -> BAKERY`，所以首店不是可从 seed
  manifest 预先标注的外生标签，Router 必须只使用运行时实际公开状态。
- V21 前中期净买 WHEAT、持续卖出 MILK/MELON，day 29 再广谱清仓。市场残差必须按
  `I[t+1]-I[t]-own_flow[t]+town_demand[t]` 计算，并使用上一 step 的商店；若我方同商品发过
  SELL/BUY_PRODUCT，因请求量不等于成交量，该样本标记 contaminated，不得触发不可逆生产。
- 为区分 Router 与底层执行器，另固定五个生产专家各跑 `72` 局（2 seed × 18 金牌 × 双座位）。
  五者均为 `0/0/72`、零错误：最佳平均自身 bank 是 dairy `52,449.25`；最佳平均分差是 root
  `-71,627.21`；最佳中位分差是 tomato `-69,247.50`。因此当前主要瓶颈是生产/劳动/现金闭环，
  不是首店 Router；RC9 overlay 即使通过机制测试，也必须用实际胜局证明价值，不能继续仅调
  路由阈值。

### Replay 评测口径修订

- 2026-08-30 起，synthetic seed 只保留为机制诊断。正式金牌证据改为两个独立 Replay 场景
  面板：本账号提交模型线上 Replay 为主面板，官方逐日 Replay 为独立确认。
- 两类数据都必须满足实际日期 `>=2026-08-20`、当前 `module_version` 和完整 configuration
  逐字段一致，并按 `episode_id + replay_sha256` 去重；任一字段缺失或不一致即排除。
- 只可提取商店解锁顺序/时点、环境配置和派生城镇需求；玩家动作、成交、奖励、私有状态及
  市场库存/价格轨迹全部禁止进入模型、调参和评测场景。
- Development 与冻结测试按 `episode_id/seed/scenario_sha256` 成组隔离。两个来源分别计算
  纯胜率，最终各自都必须 `>=75%`；不得合并分母，也不得用官方数量覆盖账号主面板失败。

### 2×2 + 固定叶消融结论

- p0064、2 个已暴露 R3 seed、18 金牌、双座位，BASE/TARGET_ONLY/MARKET_ONLY/FULL 加
  3 个固定叶共 `504/504` 局完成；每局 719 calls、候选零 schema 错误，ERROR 为 0。
- 7 个模式合计 `0/0/504`。BASE 自身均值 `49,102.40`、平均分差 `-79,597.26`；FULL
  自身均值 `47,916.65`、平均分差 `-81,541.36`。
- TARGET_ONLY 和 FULL 相对 BASE 的平均自身 bank 都为 `-1,185.75`、分差
  `-1,944.10`；MARKET_ONLY 的 bank、对手 bank、分差和逐局得分变化全部为 0，说明安全
  passthrough 使市场 overlay 行为惰性；2×2 协同项也全为 0。
- FULL 的 72 局终局全部落在 scarcity 叶；固定 liquidator 与 BASE 完全等价并严格优于 FULL。
  因而同时失败：无真实胜局、生产 overlay 退化、市场机制无行为、三路径未覆盖、Router 不优于
  最佳固定叶。
- 决策：`REJECT_NO_WIN_NEGATIVE_TARGET_OVERLAY_ROUTER_COLLAPSE`。不进入 Replay
  Development，不登记 `golden_model.md`，不提交 Kaggle。

## R10：程序化空间工作队列企业执行器（设计中）

R9 和五固定专家反证表明，约 8 万 idle / 5 万强对手 bank 的共同底座才是数量级瓶颈。R10
禁止再给 RC8 加 Router/市场小补丁，改成三个相互独立的完整生产企业专家；每个专家都必须拥有
自己的布局 compiler、资本采购账本、actor 分区、跨 step 持久任务链和商品出售闭环。

最低研究门先冻结为：程序化规则、不读取历史 action/坐标/Replay 玩家字段；对 idle 的未暴露
机制面板平均 bank 至少 100k、移动空转显著低于 RC8；至少一个完整专家在已暴露金牌 scout
产生真实胜局，才允许使用白名单 Replay Development 场景训练 Router。若底层专家仍全部 0 胜，
继续重构执行器，不消费 Replay frozen 面板。

### R10 实测结论：P2 淘汰

- 自包含 `main.py`、`strategy_parent=null`，四个 mode 可实例化；合成机制和 96-step
  smoke 通过。这只建立 P0 和部分 P1 证据。
- P2 使用 6 seed × 4 mode × 双座位，共 `48/48` 局；全部 719 calls，候选
  schema/ERROR 为 0。
- Router 平均 bank `682.67`、CVaR25 `237.67`；Root/Dairy/Fiber 平均 bank 仅
  `201.17/1,958.58/469.42`。末局生产资产最低 `0`，48 局仅 1 局胜 idle。
- 根因不是 Router：失效 daily WATER 票在作物变 WEED 后仍永久存活；布局/阶段切换
  不取消 orphan 票；step 72 直接跳入 day-3 绝对目标；过期/WAIT_RESOURCE 票误推动
  劳工与资本计划；作物死亡被误记为 completed harvest。
- 决策：`REJECT_P2_ECONOMIC_HEALTH`。不运行 P3，不打开 Replay steps，不登记
  `golden_model.md`。证据在 `r10_enterprise_queue_hmoe/evaluation/runs/r10_p2_exposed_001/`。

## R11：产能分批准入 + 可证明工单失效——淘汰

R11 不调 Router 阈值，只修复 R10 的状态安全执行器：

1. daily 票跨日强制结束；WATER 只对 PLANT，FEED/CARE 只对动物；
2. 专家、phase、layout lease 变化时取消 orphan 生产票，actor 每步重验 active ticket；
3. HARVEST 由随身库存增量和 DROP/隔夜入 shed 确认；资产消失记
   `FAILED_ASSET_LOSS`，不得充当 completion；
4. Router 只提交专家身份，产能按 commit-relative phase 和可服务劳工 tranche 逐批准入；
5. 采购只服务已准入可执行票，过期、orphan、WAIT_RESOURCE 不得推动 hire/capex。

先跑 seed 7100 单局 kill-fast：step 144 生产资产 `>=12`且漏水杂草为 0，终局 bank
`>=60k`、资产 `>=30`、invalid 动作/orphan/expired 为 0。失败则继续修执行器，不运行 P2/P3。

### Kill-fast 结论

- 12/12 状态安全机制测试通过；唯一 seed7100/router/seat0 对 idle 完整 719 calls，
  invalid WATER/FEED/PLACE、live orphan/expired 均为 0。
- step144 资产 5、终局 bank `14,288`、终局资产 12，分别低于 12/60k/30 门槛；
  漏水转 weed 23。
- 根因是晚间 PLANT 无法确保同日 WATER，`service_cap` 是规划容量而非已兑现维护量，
  且方向移动 3,013 次。决策：`NOT_GOLD_KILLFAST_REJECT`，未运行 P2/P3/Replay。

## R12：PLANT→WATER 原子 bundle + 扩产降档——淘汰

R12 只改执行闭环：成功 PLANT 必须产生同 owner、优先级 0 的 WATER 后继；未完成前不再
种植，hour>18 禁止新种植；扩产只在已实现资产、漏水和维护准时率同时达标时发生。

- 机制回归 16/16 通过；唯一 kill-fast 719 calls、零运行错误。
- 漏水 weed `23→0`、方向移动 `3,013→1,077`、nonprogress `31→6`，invalid
  WATER/FEED/PLACE 和 live orphan/expired 仍为 0。
- 但 step144 资产 5、终局资产 7、bank `13,994`，同时 PASS 627 次。全局只允许
  一个 bundle 使劳动长时间闲置；收获后的有限作物没有及时进入补种容量，tranche
  在 12/14/16 反复冻结、降档。
- 决策：`NOT_GOLD_KILLFAST_REJECT`；未运行 P2/P3/Replay。

## R13：RC8 安全吞吐 Hierarchical MoE（kill-fast 通过，P2 待测）

R13 的反证审计发现，单纯把 R12 改成并行 ticket 仍然会保留其强制逐次回仓、刚性角色和弱扩张
等根问题。因此本轮回到 RC8 已证明的“当前 observation 每步重算 + 全局劳工拍卖”
吞吐主干，保持自包含 `strategy_parent=null`，不运行时导入 RC8/R12/历史金牌，再加入状态安全层：

1. 五个完整专家保留共享健康 opening，首店浅树只修改后续聚合目标，不清空旧资产；
2. 每步根据未完成 WATER/FEED/CARE、目标距离、PLANT 和 WATER 执行成本重算安全工时，
   最多并行准入 3 个种植，hour>18 禁止新种植；
3. 只有 HARVEST 后下一 observation 确认库存增加，才登记最多 3 个补种 continuity credit；
   失败收获不登记，也不构造持久坐标 claim；
4. 收获物默认批量携带，仅现金紧张且载货达阈值或终局时回仓；typed guard 在发射前复核
   WATER/FEED/CARE/PLACE/PLANT/HARVEST/BUILD，采购只在下一 observation 记入 receipt。

### Kill-fast 结论

- 机制/静态 16/16 通过；唯一 seed7100/router/seat0/idle 跑满 719 calls。
- bank `95,060`、step144 生产资产 22、终局生产资产 67，全部高于 60k/12/58 门槛；
  runtime、schema、语义非法动作和漏水转 weed 均为 0。
- 生产吞吐恢复为 PLANT/HARVEST/WATER `237/302/1,335`；DROP 仅 21 次，并行种植最大值 3。
- 决策：`KILLFAST_PASS_NOT_GOLD`，只授权下一阶段 P2。尚未运行多 seed、固定专家、金牌对手或
  Replay 面板，不得登记 `golden_model.md`。

### P2 结论

- 六 mode × 6 个已暴露 seed × 双座位，共 `72/72` 局完成；全部 719 calls，零
  ERROR、零候选 schema 违规，最低终局生产资产 62。
- Router mean bank `76,393.33 < 100,000`，CVaR25 `55,153 < 80,000`。五个 fixed 均值为：
  wool `79,211`、dairy `84,604`、tomato `67,221`、root `64,781`、grain/egg `67,470`，
  都未达 90k。
- 虽然对 idle 为 `72/0/0`，但这只是弱对手健康证据；决策严格为
  `REJECT_P2_ECONOMIC_HEALTH`，未运行 P3、Replay 或金牌登记。
- 所有 mode 终局都有 14 hands；Router 平均方向移动约 4,782，unit PASS 约 1,572。在生产
  资产已稳定 62–68 的前提下，下一个最高确信损失是 14-hands plateau 的边际工时/日薪倒挂。

## R14：有证据的自适应劳工上限——机制门淘汰

R14 不改五专家、首店 Router、准入资产或 P2 门槛，只用当日 critical jobs、预计移动和安全
余量推导 hands 需求，且硬上限不高于 10。目标是删除边际日薪高于边际产出的工人，
同时保持终局生产资产 `>=58`、漏水为 0 和原有动作安全门。仍先只跑唯一 seed7100
kill-fast，必须 bank `>=100k` 才允许重跑已暴露 P2。

- 静态原创性/接口检查 8/8 通过，机制检查 13/14。
- 失败项为 `labor_target_tracks_workload_and_caps_at_ten`：预注册高负载夹具不能把
  目标推到 cap=10，因此劳工容量公式没有完成自身可验证合约。
- 决策：`NOT_GOLD_KILLFAST_REJECT`。按顺序门未运行 seed7100、P2、P3 或 Replay。

## R15：结算安全 + 硬 cap=10——淘汰

R15 不再使用 R14 未过门的工作量公式，hands 上限直接冻结为 10。同时只修复 R13 P2 可从
源码和 72 局证据直接确认的错误：

1. step `>=696` 停止 BUY_PRODUCT/SEED/ANIMAL/LAND/HIRE，禁止终局先卖 WHEAT 再买回；
2. WHEAT BUY_PRODUCT 按市场 inventory 变化逐单位计价，以累计真实成本决定可买量并扣款；
3. 实际调用已存在但 R13 漏用的 `_true_eligible_harvests()`，让有限作物同轮收获时真正
   预留补种种子；
4. 把 `market_withheld` 更名为 `purchase_withheld_budget`，不再将它误解为惜售。

机制全过后只跑唯一 seed7100/router kill-fast；bank 必须 `>=100k`、资产与安全门全过，
才允许 P2。

- 机制检查 24/24 通过；终局止买、逐单位 WHEAT 估值、同轮收获预留和诊断更名均已实现。
- 唯一 seed7100/router kill-fast：bank `96,287 < 100,000`，step144 资产 22，终局资产
  `52 < 58`；719 calls，runtime/schema/invalid/漏水均为 0。
- 决策：`NOT_GOLD_KILLFAST_REJECT`。硬 cap10 经济改善不足且损伤产能，未运行 P2/P3/Replay。

## R16：高价值骨架 + cap11 + 净收益 Router——淘汰

R13 P2 的 cap10 反事实上限仍无法使 Router/root/tomato/grain 过门，且每局已执行的非 PASS
动作超过 cap10 容量约 300–460 次。cap11 的理论容量高于 72 局最大非 PASS 动作，因此 R16
冻结 cap11，并保留 R15 结算修复。

路由不再简化为“需求品就是最优主生产”：已暴露 P2 中 PET→root 均值 54.5k、PIZZA→tomato
均值 58.8k，而同局 dairy/wool 明显更强。R16 将两条分支改为 dairy/wool，但仅视为已暴露
开发假设。五个 fixed 必须保留 focus crop/animal 最低配额和不同聚合目标，只共享高价值
MELON + SHEEP/COW 骨架，否则 Router 会退化为假 MoE。

- 机制/静态检查 27/27 通过；五个 fixed 的终局目标与市场动作均不同。
- 唯一 seed7100/router kill-fast：bank `97,030 < 105,000`，step144 资产 22，终局资产
  63，719 calls，runtime/schema/invalid/漏水均为 0。
- 决策：`NOT_GOLD_KILLFAST_REJECT`。cap11 恢复了 R15 损失的资产，但收益仅比 R15 增加 743，
  证明继续微调劳工数或首店映射不足以达到 P2/金牌数量级。未运行 P2/P3/Replay。

## R17：局部巡回计划 + 可审计商品账本（修订后研究方案）

R17 停止劳工上限与 Router 映射的单点调参，直接处理 R13 P2 每局 4,558–4,844 次方向移动和
每小时重做全局贪心匹配导致的折返：

1. 布局 compiler 按 WATER/FEED/CARE/HARVEST 频率把高频资产放在 shed 附近，同商品资产连成
   局部巡回；
2. 每个 actor 按 day/zone 领取最长 24-step 短任务束，WATER/FEED 可抢占，其余任务不再每回合
   全局换目标；
3. cap11 保持不变；入门门槛新增方向移动 `<=3,600`，同时仍要求 bank `>=105k`、
   step144/终局资产 `>=12/58`和零安全错误；
4. evaluator 新增分商品 produced/requested sold/实际库存变化、终局 shed/carried、discarded 和
   实际成功 HIRE 账本；在账本建立前，不再对 root/tomato/grain 的产品组合做归因性改动。

R17 若通过 kill-fast，仍必须重跑已暴露 P2；五 fixed 均值、Router mean/CVaR25 全部过门才
允许 P3。P3 过后才能精确准入 Replay Development，最终仍需 A/B 两个冻结面板各自纯胜率
`>=75%`。

### R17 实测：收益过门，资产与移动淘汰

- 候选静态/机制 `40/40` 通过，`main.py` SHA256 为
  `7d6504512aac7bb39fdf49718022e3ae6c61353ffe0589efd3ce2fd5e333d908`。
- 唯一预注册 seed7100/router/seat0/idle 跑满 719 calls；bank
  `106,891 >= 105,000`，runtime/schema/invalid/漏水均为 0。
- 但方向移动 `3,949 > 3,600`，终局资产 `42 < 58`，因此严格为
  `NOT_GOLD_KILLFAST_REJECT`，不运行 P2/P3/Replay。
- 相对 R16，PLANT `207→146`、HARVEST `256→209`，而 CARE+COLLECT
  `366→456`。R17 的 zone continuation 允许本区 CARE/肥料压住外区 PLANT/HARVEST，且
  `_jobs()` 在只生成、未执行 PLANT 时就推进 `crop_cursor`，造成 exact target 抖动。
- evaluator-only `kagsim_accounting` 与原 1.32.7 引擎 observation/reward 等价测试 `6/6`
  通过。精确账本显示 R17 相对 R16：真实 sell revenue `118,034→126,172`、spend
  `24,004→22,281`，但实际 planted seeds `207→146`；收益提升来自高价值动物产品兑现与
  少支出，资产下降来自补种吞吐，不是终局集中收割。该真值 API 不进入 observation，候选侧
  仍只保留 requested/方向差分，不能读取 evaluator accounting。

## R18：语义目标锁 + 同格任务束 + 有预算资产恢复（构造中）

R18 保留 R17 已验证的收益机制、cap11、五专家目标、Router、出售器和布局，只修改执行调度：

1. `_jobs()` 改为纯函数；规划不修改 `crop_cursor`，只在 typed-safe PLANT 真正发出时推进；
2. `semantic_target=(x,y,op,args)` 不含 priority；原目标仍存在时不换目标。普通 WATER 留在
   本 zone，只有 priority0 或 hour>=18 的 WATER、以及 FEED，允许跨区安全抢占；
3. 同一坐标每步最多一个 owner，并保持动物
   `FEED→HARVEST→CARE→COLLECT_FERTILIZER` 与有限作物
   `HARVEST→确认空地→同 crop PLANT→确认存在→WATER` 的同格后继；
4. zone continuation 只有在本地任务 priority 不劣于全局最佳任务时成立，禁止 CARE6/肥料5
   压住 PLANT/HARVEST2；
5. 从 day27/step648 开始，有限作物 HARVEST 使用
   `max(0, productive_assets-58)` 严格逐 job 扣减预算；低于 58 时每步最多一个 growth lane
   用现有种子恢复资产，优先级低于 WATER/FEED、高于 CARE/肥料/DIG，step696 禁购不变。

R18 仍只允许一次 seed7100 kill-fast。门槛保持 bank `>=105,000`、移动 `<=3,600`、终局资产
`>=58`、719 calls 和零安全错误；任一失败继续淘汰，不消费 P2 或 Replay。

### R18 实测：删除式任务束造成吞吐退化

- 静态/机制 `22/22` 通过，但唯一 kill-fast 只有 bank `91,959`、移动 `3,981`、终局资产
  `40`；719 calls、runtime/schema/invalid/漏水检查为 0，终局仍有 5 个 weed。决策
  `NOT_GOLD_KILLFAST_REJECT`，未运行 P2/P3/Replay。
- 相对 R17，PLANT 只增加 `4` 次，而 HARVEST/FEED/CARE/FERT 分别减少
  `20/22/38/31` 次；精确产销账本的 sell revenue 从 `126,172` 降至 `111,021`。
- 根因是 `_bundle_jobs` 在 actor 可执行性判断前每格只保留一个 op；FEED 不可执行时，同格
  HARVEST/CARE/FERT 已被删除。普通 WATER 局部化还会删除未匹配 WATER；单条 hard chain 与
  restoration cap1 又把补种重复串行化。

## R19：增长债务与吞吐恢复（构造中）

R19 回到 R17 完整 jobs 和全局 WATER/FEED 安全抢占，只保留 R18 已验证的 pure planning cursor
与 priority-free semantic key。day8 起计算
`growth_debt=max(0,min(58,planned_assets)-observed_assets)`；总并行种植仍为 3，仅一个最近 PLANT
升为 priority1。任务按生产资本/低价值维护分层，PLACE/BUILD 与 PLANT/HARVEST 同属生产层，
避免修复作物时再次饿死奶牛。R19 不继承 R18 的 hard chain、删除式 bundle 或普通 WATER 丢弃。

### R19 kill-fast 冻结合约（运行前）

仍只允许 seed7100/router/seat0/idle 一次。原门槛保持不变：bank `>=105,000`、step144/终局
生产资产 `>=12/58`、方向移动 `<=3,600`、719 calls、零 runtime/schema/invalid/漏水损失。
为直接验证本轮“day8 增长债务 + 动物产能恢复”的机制目标，运行前额外冻结：day9/day12
生产资产 `>=30/50`、终局 weed 为 0、终局 COW `>=6`，且 CARE+COLLECT_FERTILIZER
`>=430`。任一门失败即淘汰，不进入 P2/P3/Replay。

### R19 实测：可行边死锁，淘汰

- 机制测试 `18/18`，候选 SHA256=
  `45e48f244123334329e9f35dd01d461ffc2919eac0ffaff4ce7d471cdb802ed7`；唯一 kill-fast
  719 calls、零 runtime/schema/invalid，day9 资产 34 通过。
- bank `77,471`、day12/终局资产 `45/45`、方向移动 `3,739`、终局 weed `2`，均未过门；
  CARE+COLLECT_FERTILIZER 仅 `236`，决策 `NOT_GOLD_KILLFAST_REJECT`。
- day9--12 每日仍生成 144--168 个 CARE/FERT job，但实际连续四天发出 0，同时每日 PASS
  `65/108/109/68`。根因是调度器先按 remaining 中“存在 primary”选层，再找 finite edge；
  primary 只剩不可执行 PLACE 时直接 break，不会回退到可执行 CARE/FERT。持续存在的
  PLANT/HARVEST 也会硬饿死 secondary。
- 预注册的 `terminal_cows_ge_6` 暗含 dairy 路由假设，但本局实际首店路由为 wool；该门作为
  评测合约错误废止；复算改为实际 wool 目标 `SHEEP=6/COW=4`，终局为 `6/3`，仍失败。
  bank、资产、移动、day12、终局 weed 和维护吞吐这些路由无关门也均已失败，淘汰结论不变。
- evaluator-only 精确账本 6/6 完整、5/5 测试与商品/种子/现金守恒均通过，候选看不到
  accounting。R17/R18/R19 双座位均值 sell revenue 为 `118,769/109,936.5/95,580`；
  R19 相对 R17 只少花 `556`，却少收入 `23,189`，FERTILIZER/MILK 产量分别少
  `114.5/84.5`，同时 PLANT/WATER 多 `27.5/146`、CARE/FERT 动作少 `93.5/114.5`。
  该账本只作单 seed 根因诊断；三版本 Router 实际分支可能不同，不能宣称纯调度因果 A/B。

## R20：状态化可行坐标任务束（预注册，构造前）

R20 只允许修复 R19 的调度死锁，不改 Router、五专家目标、市场参数、day8 growth debt、
并行 PLANT=3 或任何强度门槛：

1. jobs 按坐标形成持久 `TileWork(coord, owner, ready_ops, phase, ready_since)`；同一观察仍一格
   一个 actor，但未执行的同格 op 不得删除；
2. 动物按 `FEED→CARE→HARVEST→FERT`，持续作物按 `WATER→HARVEST`，有限作物按
   `HARVEST→原格同品种 PLANT→WATER`，普通扩张按 `PLANT→WATER`；每个 phase 只由下一
   observation 的真实状态确认推进；
3. 派工只看 finite feasible edge：先 WATER/FEED，再原 owner 的可行同格后继，再按
   `ready_since→原始 priority→distance` 派全部剩余 head；某类无可行边只跳过该类，禁止
   break 整个 scheduler；owner 不可用时最近 actor 接管；
4. kill-fast 维持 R19 的路由无关门，并以实际选中专家 day29 的逐动物目标完全兑现替代固定
   COW 数。只有全门通过才允许 P2。

新增机制测试必须覆盖：不可执行 PLACE 回退 CARE/FERT、持续 primary 不饿死动物 bundle、
动物同格单次到达续作、有限作物原格补种浇水、三路扩张并行、跨观察保留未执行 op、普通 WATER
不丢弃、最后一次 transition 的 weed，以及 R19/R20 Router/目标/阈值/params hash 完全一致。

### R20 实测：状态链成立，但远距 owner 与陈旧 head 反向增程

- 机制 `14/14`，候选 SHA256=
  `29a40d9bb751710c50baf5c698d54413928b3227723889ac98203f6138484838`；唯一 kill-fast
  719 calls、零 runtime/schema/invalid，day9/day12 资产 `38/50`，实际 wool 动物目标
  `SHEEP=6/COW=4` 完全兑现，PASS 从 R19 的 `1,572` 降至 `831`。
- 但 bank `74,903`、终局资产 `42`、方向移动 `4,413`、终局 weed `1`、CARE+FERT
  `261`，仍为 `NOT_GOLD_KILLFAST_REJECT`；未运行 P2/P3/Replay。
- 状态账本记录 owner assignments `2,280`、takeover `689`。owner 即使被 WATER/FEED 带离
  原格仍保留租约，随后跨区返程；全局按 `ready_since` 先陈旧任务，使刚确认的 replacement
  PLANT/WATER 反而排在后面。资产 day18--21 曾到 `57`，day25 因服务债务和 6 weeds 跌至
  `42`，说明问题是后半程队列调度，不是开局目标或动物采购。

## R21：链龄继承软租约（预注册，构造前）

R21 只修改 R20 的一套租约排序语义，Router、专家、市场、阈值、任务生成和状态确认链全部不变：

1. `ready_since` 定义为 bundle 创建时间；动物 `FEED→CARE→HARVEST→FERT` 与有限作物
   `HARVEST→PLANT→WATER` 的 phase/head 变化不得重置链龄；
2. 删除永久 owner-first pass；每次先选最老的可行 bundle，再为它选最近可行 actor；旧 owner
   只能在距离并列时作为 tie-break，不能召回远端 actor；
3. 每个 actor 最多拥有一个活动 lease；接管新 bundle 时必须清除该 actor 在其他坐标的 owner；
   owner 不可用或不再最近时自然 handoff。

机制测试必须新增：available-but-far owner 让位最近 actor、单 actor 不能多坐标持租、replacement
与动物全链龄继承、旧链压过较新的 ordinary head、owner 映射一对一、合成路径无返程。仍只允许
一次相同 kill-fast；全门通过才允许 P2。

### R21 实测：软租约有效，但未发射意图错误持久化

- 机制 `15/15`，候选 SHA256=
  `19804af6270c00f40122be668c78d4fad71d96f2ec980e54a70d3aa2cd95b98f`；唯一 kill-fast
  bank `86,130`、CARE+FERT `323`、移动 `4,233`，相对 R20 分别
  `+11,227/+62/-180`，owner takeover `692→379`，证明软租约方向有效。
- 但 day12/终局资产 `48/48`、终局 weed `3`，实际 wool 动物目标只完成
  `SHEEP=6/COW=3<4`，仍为 `NOT_GOLD_KILLFAST_REJECT`，未运行 P2/P3/Replay。
- 新根因是 R20 遗留的“结构仍可执行就保留”规则：普通 BUILD/PLANT/PLACE 尚未发射，也会在
  planner 已不再提议该坐标后持久。pasture 在 day9--10 从 6 增到 13、终局 14，超过目标 10；
  终局仍有 ready_since=216 的旧 PLACE。过期意图占用链龄、地块和移动，并非观察确认链本身。

## R22：观察有效前沿（预注册，构造前）

R22 只收紧 TileWork 的状态边界：已经发射后处于 `await_*` 的动物/作物/补种后继可以跨观察
持久；尚未发射的 ordinary PLANT、BUILD、PLACE、DIG 必须在当前 `_jobs()` 的同坐标同语义
提议中仍存在，否则立即删除并释放 owner。其余 R21 代码和全部门槛不变。

机制测试必须覆盖：目标已满足后旧 BUILD 全部失效、planner 换坐标时旧 ordinary PLANT/PLACE
失效、已发射 HARVEST→PLANT→WATER 不因 planner 暂时无 job 而丢失、单观察并行 BUILD 数不超过
当前结构 deficit。机制全过后仍只跑一次相同 kill-fast。

### R22 实测：超建和移动修复，但精确坐标有效性造成种植抖动

- 机制 `14/14`，候选 SHA256=
  `0abdbf4f97749c603a65312936974dab930b54cb56e2a12954b564ec5a8868a6`；唯一 kill-fast
  pasture 精确 10、wool 动物目标完全兑现、终局 weed 0、移动 `3,566<=3,600`，首次同时
  通过这些执行门。bank 提升到 `94,861`，CARE+FERT 为 `429`。
- 但 day12/终局资产只有 `35/42`、PLANT `140`、PASS `1,869`，bank/资产/维护吞吐仍失败；
  决策 `NOT_GOLD_KILLFAST_REJECT`，未运行 P2/P3/Replay。
- 精确坐标仍在 planner 才允许保留 ordinary PLANT；其他 actor 完成种植导致 fair planner 重排
  坐标时，在途意图被取消。R22 共过期 193 个意图，虽然避免超建，却把 R21 的 PLANT
  `189→140`。问题是租约应由“当前缺口配额”担保，而不是由同一坐标重复提议担保。

## R23：缺口担保意图账本（预注册，构造前）

R23 保留 R22 的软租约和 observation 确认链，只替换未发射意图的准入：按当前 `_jobs()` 中
同语义任务数量形成 quota（PLANT 按 crop，PLACE 按 animal，BUILD/DIG 按 op）；每类先保留
最老且目标状态仍合法的现有 lease，最多 quota 个，planner 新坐标只填剩余额度；quota 归零或
超额的 lease 立即取消。这样坐标可稳定，但永远不能超过当前结构/动物/种植准入缺口。

测试必须覆盖：3 个 PLANT quota 在 planner 换坐标后仍保留 3 个而不扩成 6 个、BUILD deficit4
最多四 lease 且目标完成后归零、不同 crop/animal quota 隔离、最老合法 lease 优先、await 链不计
未发射 quota 且不被取消。其余代码和 kill-fast 门槛全部不变。

### R23 实测：缺口账本无效，停止意图保留微调

- 机制 `18/18`，候选 SHA256=
  `5936491ce7ea99239afbaba67de0da0b8a718f5ff60f19fc376aa66ea0412b2f`；唯一 kill-fast
  PLANT `149`，只比 R22 多 9。
- bank `92,336`、day12/终局资产 `39/39`、移动 `3,810`、CARE+FERT `394`；动物目标和
  终局 weed 通过，但收益、资产、移动和维护吞吐均失败。决策 `NOT_GOLD_KILLFAST_REJECT`，
  未运行 P2/P3/Replay。
- ledger 保留旧坐标后，移动和 owner 转移回升；又只恢复很少 PLANT。R22/R23 已分别代表
  “精确坐标立即失效”和“语义 quota 保留旧坐标”，二者都未恢复增长，故停止继续微调租约规则。

## R24：专家确定性地块契约（预注册方向）

下一轮重构空间规划：选中专家后，从其 day29 最终结构/动物/作物目标编译不重叠的固定槽位；
各 stage 只激活该最终契约的确定性子集，普通 PLANT/BUILD/PLACE 坐标不再由每步 fair planner
临时重排。沿用 R22 的 observation-valid frontier、soft nearest lease、状态安全链和市场控制，
删除 R23 deficit ledger；Router、专家目标、市场参数和强度门槛不变。

构造前必须证明：route commit 前公共 opening 不会与 commit 后槽位冲突；day8→day12 只追加槽位
不重映射；结构/动物/crop 槽互斥；3 路 PLANT 坐标在任一未完成 observation 中稳定；有限作物
仍原格补种；现有异类 tile 不被破坏或强制收割。

### R24 实测：槽位稳定成立，但全局 oldest-first 调度仍损失吞吐

- R24 直接从 R22 派生，机制/parity/static `19/19` 通过；候选 SHA256=
  `6969291a22ce8212cc169ad7c877f98fb231bef3a96220dfe9d2de510e3da16b`。
- 唯一 killfast 的 bank `95,263`、终局资产 `41`、移动 `3,935`、day12 资产 `44`、
  CARE+FERT `401`，五项均未过冻结门；安全门、终局 weed 与 wool 动物目标通过。
- 相对 R22，固定槽位把 PLANT `140→159`、day12 资产 `35→44`，但移动 `3,566→3,935`，
  维护 `429→401`；说明空间目标稳定只修复了 planner 抖动，没有修复“最老 bundle 先于
  距离/收益”的全局派工机会成本。
- 决策 `NOT_GOLD_KILLFAST_REJECT`；未运行 P2/P3，未读取 Replay，未登记金牌。

## R25：可运营容量分区泳道契约（预注册）

R25 保留 R24 的 Router、五专家 genome、30 天目标、确定性 slot、商品级市场控制和全部冻结
门槛，只替换生产容量准入与派工。主假设是：固定坐标还不够，每个 slot 必须同时拥有
`service_zone/lane/circuit_ordinal`，每个 lane 绑定日内角色；新增 slot 只有在其完整维护路线仍能在
剩余 unit-actions 内闭合时才准入。维护负载只允许缩短固定 slot 前缀，不能换坐标。

调度按 `安全风险→deadline slack→原格续作→可达 owner→同 zone→距离→稳定 key` 对全部
actor-task 边做确定性匹配；日切清除 hand owner，只有旧 owner 无法赶 deadline 时才允许接管。
普通 observation 任务不再继承永久 `ready_since`；只有已发射的有限作物
`HARVEST→确认空格→PLANT→确认→WATER` 链持久。WHEAT feeder、seed、终局收割资产 floor
都使用同轮资源预留，最终 typed action validator 对未知动作 fail closed。

构造门必须证明：容量过载拒绝、卸载后按同序接纳；lane/slot 唯一且路线连续；正常负载零跨区
接管；日切 lease 失效；FEED/seed 不重复预留；有限作物原格闭环；终局并发收割不能把生产资产
打穿；Router/targets/market 与 R24 parity。机制门通过并冻结 SHA 后只跑一次原 killfast，任一
`105k/58/3600/50/430` 门失败即淘汰，不运行 P2/P3/Replay。

### R25 实测：完整生命周期容量证明过度保守，否决

- static/parity/mechanism `32/32` 与全部反例通过；多项式 min-cost max-flow 在 69 tasks、
  759 edges、11 actors 压力样例约 `0.0042s`，候选 SHA256=
  `573b24a8169e9dcb0446c27c80e365c07f1018e4ba5bc71574b12f28ff84b71f`。
- 唯一 killfast 虽把移动 `3,935→2,518`，却把 PASS `1,328→3,506`、PLANT
  `159→79`；bank `49,166`、step144/day12/终局资产 `11/17/26`、CARE+FERT `339`，
  并留下 2 个终局 weed。容量证明把未来全生命周期工时反复计入当前准入，形成安全但不工作的
  生产刹车。
- 决策 `NOT_GOLD_KILLFAST_REJECT`；不运行 P2/P3/Replay。R26 不调容量阈值，必须把
  “扩张准入证明”和“当前任务 work-conserving 派工”解耦。

## R26：持久可行 Option 图（预注册）

R26 删除 R25 对每个新增 slot 预收完整 `shed→lane→shed + 未来维护` 工时的容量门，也删除会让
一个 weed/缺 seed 阻断全局的 ordinal prefix；不修改 R24 的专家目标、Router、市场参数和
killfast 门槛。当前 observation 中的安全任务前沿必须 work-conserving，容量只约束当前 option
head 和不可分割的后继资源，不预收未来 FEED/CARE 或返仓工时。

有限作物改为跨观察 `PersistentOption`：`HARVEST_ISSUED→EMPTY_CONFIRMED→REPLANT_READY
→PLANT_ISSUED→WATER_READY→DONE`。owner 移动或被 delivery/pickup 覆盖时 option 与 seed
reservation 继续存在，普通种植不得占用；只在成功确认或真实冲突时释放。引擎允许单位进入
LOCKED 地块、只拒绝越界，因此 MCMF、移动生成和最终 validator 必须共享同一“网格内可行”
语义，禁止匹配后才把合法 LOCKED 移动转 PASS。作物扩张按 lane 独立
固定顺序，lane A 冲突不得阻断 lane B，也不得重映射 A；weed 是被阻 slot 的高风险前置依赖。
动物 BUILD 同时要求对应物种 deficit，FEED 只用 deadline 可达的携粮量抵扣。

冻结前必须新增：两格三 tick replacement、owner unavailable、seed 跨 tick 独占、同步幂等、四向
进入 LOCKED 合法/越界拒绝、跨 lane 独立、weed 依赖、off-contract SHEEP/COW 结构耦合、hour22
可达 feeder、临近 `max_lifespan_step` 不被 terminal floor 扣住，以及当前 frontier
work-conserving 反例。机制通过后仍只跑一次原 router killfast；失败不进 P2/P3/Replay。

### R26 实测：持久补种恢复，但补给与本地性失控

- static/parity/mechanism `36/36`，候选 SHA256=
  `b3d38f2235ef2cdc35bbec951e36a6da336435f96349743fd8811bfa104e8fc0`。
- 唯一 killfast 的 bank `79,264`、终局资产 `34`、移动 `4,397`、CARE+FERT `340`、
  day12 资产 `37`；PICKUP 达 `246`，并有 5 次漏水成 weed。相对 R25，任务供给恢复、PASS
  下降，但 deadline feeder 反复派人取粮且没有批量 carrier option，MCMF 又缺少稳定 zone owner，
  导致补给往返和维护抢占。
- 决策 `NOT_GOLD_KILLFAST_REJECT`；不运行 P2/P3/Replay。R27 必须把 FEED 补给变成持久批量
  supply option，并把 WATER 设为不可被补给抢占的硬 deadline；不得调低门槛。

## R27：持久 Supply-Lane 与硬截止 Service Circuit（预注册）

R26 每个 observation 按动物缺口派 `PICKUP WHEAT 1`，而引擎单位携带无数量上限、每次 FEED
只耗 1。R27 将未喂动物编译为最少数量的持久 `SupplyTrip`：一次批量 PICKUP q，沿固定动物
circuit 逐只 FEED；trip 完成前 actor 不得被旧 owner 或 residual MCMF 拉走。WATER 同样从
逐点任务升级为连续 `WaterArc`，精确日末条件为 `hour + distance <= 23`，允许 hour23 原地动作和
hour22 距离1的移动后浇水；所有 urgent/new-plant WATER 必须有完整覆盖证书后才准软任务。

普通扩张改成 `PlantOption: PLANT→观察确认→WATER→确认关闭`；当日没有闭环空间则不启动。
每个 Role 在 shed/途中仍保持 zone/lane 身份；AnimalServiceArc 连续处理 CARE/HARVEST/FERT；
residual MCMF 只能消费未被 SupplyTrip、WaterArc、finite/plant option 或 AnimalServiceArc 保留的
坐标。seed ledger 要逐事务闭合，任何 work 删除前必须显式释放 reservation。

冻结前必须证明：10 动物只有一次 `PICKUP WHEAT 10` 并连续 FEED；旧 owner 不打断配送；hour23
原地 WATER 与 hour22 距1 WATER 可执行；高负载日切漏水 weed=0；每个 PlantOption 都有 WATER
确认；新增 PLANT 用滚动服务可行性而非固定阈值；hard-owned 坐标不进 MCMF；Role 在 shed/途中
不丢身份；seed live/reserved/released 守恒。机制通过后仍只允许一次原 killfast。

## 失败驱动的下一步

- bank <70k 或兑现率 <90%：只修改劳工任务分配、持久物流和融资闭环，不调 Router；
- 固定专家过门而 Router 退化：修改专家差异或淘汰 Router，不搜索切换阈值；
- 锚点胜率不足但 bank 合格：优化商品组合、需求时点和共享市场订单；
- 预测层无正消融：永久关闭对方路径预测；
- 满足 75% 但 Router 无严格增益：只能记录为强启发式单专家，不得称 Hierarchical MoE。

## 2026-08-31：用户停止研究

- 状态：`STOPPED_BY_USER / NOT_GOLD / R27_UNFROZEN_DRAFT`。
- R24–R26 均在 killfast 淘汰，未运行 P2/P3 或正式双 Replay 面板；正式胜率为 `NOT_RUN`。
- R27 只有未冻结的 `main.py/test_r27.py` 草稿，未运行测试、未生成 manifest、未跑 killfast。
- 不注册 `golden_model.md`，不提交 Kaggle，不安排后台续跑或自动恢复。
- 完整停止总结见 `STOP_SUMMARY_2026-08-31.md`。
