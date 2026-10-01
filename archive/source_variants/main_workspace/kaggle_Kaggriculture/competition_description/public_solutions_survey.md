# 公开高分方案调研 — Kaggriculture

> 首次调研时间：2026-08-20。方法：Kaggle API 按 scoreDescending / voteCount / dateCreated 三种排序各取 top 20 合并去重，精读 10 份高票/高分 notebook 源码与说明，提取策略结构、关键机制、自报成绩与来源归属。目的：建立本比赛公开 meta 的方法论综述，供后续方案选型与每日巡视 diff 使用。

## 更新日志

| 日期 | 内容 | 结论 |
| --- | --- | --- |
| 2026-08-20 | 首次全量调研，精读 10 份 | 榜首 meta 已收敛为「公开 Replay 路线重建」军备竞赛；市场时机 wrapper 是当前唯一持续产生增量的创新点；公开 top 方案中几乎无 RL/ML 路线 |
| 2026-08-20（巡视） | diff 出 6 个新 ref，精读 4 份（nekkon 元分析、tetsutani 新作、boatlee V13-R3、andrewsokolovsky V16 slot sniper） | 镜像战军备竞赛继续细化（同日队列槽位抢占）；nekkon 量化证实「对 starter 调参几乎不迁移」；boatlee V13-R3 的 one-turn shift 控制器参数与本项目 v7 的 preempt 子系统完全一致（clone≤6 / 120–680 步 / 批量≤30 / 四商品 / append+合并），构成独立交叉验证 |
| 2026-08-22（增量） | 用 Kaggle 官方 CLI 按最新运行时间与票数刷新；下载并精读 7 份新 notebook，另核对 3 篇讨论和公开 GitHub 工程 | 前沿已从「一条固定路线」转向「完整路线组合 + 公共状态路由 + 极小市场残差」；Kaito v38 和 boatlee V21 是最值得复现的规则 Router；社区 RL 证据支持高层选专家，不支持端到端控制工人 |
| 2026-08-22（Rating 策略） | 精读当前榜首 Ryo Hasegawa 的提交与评分经验帖（discussion 736219），连同评论区异议 | 官方/赛页层面需遵守「仅最新两份活跃、终局重新评估」；作者经验表明前 60–100 局 Rating 噪声很大，应按相同局数比较，以真实胜负率而非金币或短期 Rating 决策；一个槽位保护强基线，另一槽位只放真实增量或异质 hedge |
| 2026-09-07（巡视） | 两周未巡视后大批新方案；精读 7 份（yhay81 Six-Day/Three-Day、Tschinkel 74.5%→93.8% Router、Kaito v48、Goose Portfolio 2615、destbreso 97% predictable、tetsutani Shape the Shop）+ 4 篇讨论（评分机制 739534、BT 终局 739410/731587、replay 合规 738837、739179 榜首解剖） | 前沿完全收敛为「强 anchor tape + 块边界 public-state 路由」；修复层被大规模消融证伪（Tschinkel v5 删光修复层反升到 93.8%）；官方确认 replay tape 合规、终局为两周后单次 Bradley-Terry 锦标赛、第二槽位是无损 hedge；同码双提交分差 ~800 证明 LB 单次得分噪声极大 |

## 一、公开榜格局

**总体判断**：比赛仍由「公开 Replay 路线重建 + 市场时机微调」主导；排行榜前列大量方案是从 top 队伍公开 Replay 蒸馏出的确定性动作序列。2026-08-22 的新增变化是：社区开始把多条完整路线组织成**公共状态 Router/portfolio**，并用谱系化 live-agent 面板验收。仍没有证据表明强化学习或机器学习模型类方案已进入 top 梯队。

分数段 × 方案类型：

| 分数段（自报/标题） | 方案类型 | 代表 |
| --- | --- | --- |
| 3000+ Rating | 多代 replay 重建 + 市场 impact 排序 + 终局修正 | Rayk findings 系 C45/C71/C72（3085.4）、salemali7「3094 score」 |
| 2800–3000 | replay 重建核心 + premium market lead / midgame reset | boatlee V16-RC5（181 票）、Kaito v27（163 票） |
| 2500–2800 | 完整路线 notebook（双路线/混合策略） | tetsutani Adaptive（123 票）、indarkarhana Top10（68 票） |
| <2500 或无分数 | 经济学规划器、教学、EDA、工具 | pilkwang 经济政策（95 票）、bovard Getting Started（691 票） |

**meta 收敛证据**（Rayk findings 4.7）：8 月 9 日下载 top 20 队伍各 10 场计分提交 Replay（200 份），**单一 field hash 出现在 40 个队伍的 144 场中**；rank 3–20 大多 field 动作 99–100% 相同。成熟农场收敛到约 **8 牛 / 5–6 羊 / 12 临时工 / 3 象限 / 23 草莓 + 31 小麦**。

**ladder 动态**（busyaprime 对每日 Replay 的统计）：每日中位分已**见顶回落**（斜率显著为负），top 与中位的差距多次压缩——场上策略已收敛，「复制当前 meta」的边际收益在下降，剩余优势需来自场上没人做的方向。

## 二、逐个方案分析

### ⭐ 1. Rayk Kretzschmar — Kaggriculture: Findings from Zero to Top Meta（91 票）

**本次调研信息量最大的一份**：完整的「replay hunting」工作日记，记录了从 c14 到 C94 的 20+ 次迭代。

- **方法**：下载当前榜首队伍的公开 Replay → 找「跨多个对手重复出现的稳定 field/market 日程」→ 蒸馏为本地可执行 agent → 双席位配对验证 → 上线。
- **replay 筛选三准则**：① 同一 field 日程是否出现在多个对手的对局中；② market 日程是否稳定（还是随对局反应）；③ 蒸馏出的 tape 能否双席位击败上一版 agent。
- **关键迭代**：
  - c14：senkin13 的 720 回合完整日程在 5 场中完全一致（8 牛/6 羊/7 草莓），加终局 8 回合清仓后 standalone 2182.2；
  - c15：移植 Hamburger 的 clone-aware 提前出售 wrapper，对母版 14-2；
  - c16/c18：top 5 → top 10 刷新，发现五支队伍用同一 8 牛/5 羊/12 工/3 象限计划，队伍间只差 2–5 个 field 回合；
  - c27：终局时机修正——**step 718 是最后一个可执行动作，index 719 不会执行**；终局控制器从 712 延后到 717 多保留 5 回合强 tape；
  - C45：把合格 premium 出售提前 2 回合（记账保证原时点减量），3085.4、rank 9；
  - C70 诊断：**83-5、平均 margin +14,196 却卡在 3000 以下**——Rating 只奖胜不奖分差，刚性路线赢不了少数关键接近局；
  - C71：换 GiovanniCR 的 market 时机 + 按自致价格冲击排序 premium SELL（MELON/STRAWBERRY/MILK/WOOL 可抢在对手 dump 前；WHEAT/FERTILIZER 保持保守时机因对手会买）；
  - C72：日内资本化——仅当工人携带 ≥2000 金币价值的 premium 货且距 shed ≤1 步时才改道入库；阈值 500/1000 或两步改道全部 0-8 败退；
  - C93：第四象限（SE）扩张实验为**负结果**；C94：开局饲料封锁 + 一回合肥料抢占。
- **Rating 机制重要观察**：完全相同的 `main.py`（SHA-256 一致）两次上传得到完全不同的 Rating 轨迹（2182.2 vs 1210.1→1865.6）——早期对手、seed、席位决定爬坡路径；只有最新两个提交持续获得对局。
- **下载方法论纠错**：必须按 `publicScore` 匹配队伍展示分数再选 episode，否则会采到该队伍评分更低的另一个活跃提交。

### ⭐ 2. boatlee — V16-RC5 | High-Score 8C/4S Premium Market Lead（181 票，分数榜第 1）

- **方法**：从 Nikita Lugovoy 高分提交 `55440039` 的 3 场公开 Replay（92165990/92185587/92223213）重建路线：逐决策步取三条 trace 的多数动作。field 日程三场完全一致，market 日程 99.91% 一致。
- **路线内容**：扩 3 象限；快速 4 羊、step 192 达 8 牛；WHEAT+STRAWBERRY+MELON 混作；每日 HIRE/FEED/CARE/收获/收肥协调；premium 商品分波出售。
- **原创增量**（两点）：① 状态漂移恢复——按当前临时工数对齐动作表、WEED 阻塞计划时修复；② **一回合 premium market lead**：检查下一回合计划出售的 4 种 premium 商品，若当前回合无对应城镇需求且 shed 库存足够，把部分出售提前一回合；两回合总量不变，只改执行时间。
- **自报**：本地对重建核心 30 seed 双席位 60/60 全胜。
- **同族版本**：V16-RC2（near-mirror market relay）、V17-R1-RC2（10C/4S）、V20-Adaptive-R1（multi-route）、84/84 V14 Clone Preemption——boatlee 是迭代最勤的 replay 重建者之一。

### ⭐ 3. Kaito Fukami — 25/27 Strict-Future | v27 Midgame Meta Reset（163 票）

- **核心论点**：「主导开局没有失败，失败的是它过时的续着」。保留低熵 HIRE4 开局，**替换 step 161 以后的全部续着**，合成一条双席位一致的 719 步路线 + actor-local WEED 修复 + 已有 SELL 槽内的价格冲击排序。
- **路线来源**：Ezzzzzekki 提交 `55390428`、episode `91493566`、seat 0 的公开动作（附动作 SHA-256 归属声明）。
- **自报**：冻结评测对当前 inner 28/30、development outer 29/30、策略冻结后实盘 25/27，并把 v26 的 3 场真实败局全部反事实翻回（3/3）。注意 25/27 是本地 strict-future 反事实（对手重放公开动作、不会反应），非官方 LB。
- **方法论亮点**：把「rating warm-up」与「策略性衰退」分开归因；对每场真实败局做动作级审计；拒绝了一个 inner 分更高但输掉 2/3 真实败局的 seat router。
- **同族版本线**：v18 Closed Loop（40/53 Top-10）→ v19（41/49）→ v20 WEED-Slip Recovery（159/160）→ v21.1 Conditional Memory（177/180 Top-30）→ v25 Meta Reset（15/16）→ v27。

### 4. Roman Tamrazov — Kaggriculture | Hamburger 🍔（127 票）

- **定位**：被多方引用的市场时机思想源头。最佳分支 `Clone Quad H1`：检查双方公开农场是否近乎镜像，连续两个接近检查点后，**向前看一回合自己的日程，在预期的共享市场 dump 之前卖掉一条可用的 premium 线**（melon/strawberry/milk/wool）。
- **自报**：对锚点 6-0、平均 margin +1,865.7。小 wrapper、大镜像战效果。
- **V27 版关键修正**：官方解释器执行 step 718 后即 DONE，**index 719 的动作不会执行**；终局 routing/清仓集中在 716–718。终局 inventory relay：只覆盖无法入库的终局 PASS/PLACE/DROP，把可达搬运工移向 shed 邻接格并在最后可执行步 DROP。
- **候选分支管理**：精确锚点 / 关现金流排序 / 静态或碰撞感知 SELL 槽内重排 / 碰撞感知 SELL 前置 / 716 或 717 起终局 relay / 组合——只有严格提升 broad mean money 且不降胜场和 robust minimum 才打包，否则提交原基线。

### 5. tetsutani — 🌾 Adaptive Farming Strategy for Kaggriculture（123 票）

- 早期广泛传播的完整双路线基线（平衡路线 + 羊毛友好路线，按城镇商店选择），多工人/多地块/作物畜牧协同，含杂草修复、仓容保护、市场槽排序、终局清仓。
- 当前版本自述为「Adaptive Premium Queue Farming」：保持整季路线一致性，把 premium 出售时机作为一等决策——宽需求期可把计划 premium 出售**提前两回合**，yarn/bakery 开局保持一回合时机。
- 历史地位：多个后续方案的共同祖先之一（Rayk 的引用表也列有它）。

### 6. pilkwang — Kaggriculture: Structured Economic Policy（95 票）

- **唯一的「第一性原理」经济学规划器**：以终局银行为所有决策的统一单位，建立现金转化链 B₀→K_t（承诺资本）→Y_t（产出）→Z_t（可变现库存）→B_T。
- 三条不变式：① 不可逆损失优先于可选增长；② field 承诺先于 market 承诺；③ 每个承诺必须终局可行（成熟、收获、返程、出售都在 T=720 前完成）。
- 作物价值 V_c(t) 含服务完成概率、折现预期价、种子成本、劳动力/土地影子价格 λ_W/λ_L；牲畜同框架按生产回合求和。market 规划用 0.85 折现预期收入来约束后续购买。
- 代表「不抄 replay、从经济机制推导」的路线；票数高但无 top 分数声称。

### ⭐ 7. cjlcjlcjl — What the Top Farms Do — a Live Meta（74 票）

每日在官方 replay 数据集（kaggriculture-episodes-index，按 agent rating 排序、每日 20GiB 上限）上重跑的 meta 追踪器 + 引擎经济学教学。**引擎数值要点**（内嵌 1.32.x 市场模型计算，注意草莓价格悬崖在 1.32.x 是 62 单位、某些新 build 是 ~247，版本差异会静默污染分析）：

- **每格每天利润**是种植决策基础：melon 纸面最高（$250 基础价）但一次性且价格悬崖陡；tomato 低价但持续产出；strawberry 持续高产——**是 top meta 的主作物**；wheat 薄利但双重隐藏价值（饲料 + 价格几乎不崩，3000 单位才到底）。
- **肥料**：一次性作物奖励窗口内浇水 +1 产量/天，肥料翻倍 +2/天；wheat 光浇水到不了 6 单位上限、**必须施肥**；melon 浇水即可到顶、施肥浪费；动物每天产 1 份肥料（不收集即消失）——「养动物卖肥料」是免费钱循环，top 对局卖数千单位。
- **价格悬崖**：wool/strawberry/milk 超供 ~60–80 单位即从万元基线崩到 $1 底（最脆弱）；melon ~158；tomato/carrot ~500–850；wheat/egg ~3000（压舱物）。**应对：小批量计量出售（每单 4–8 单位）**，一次倾倒=前几单位高价、其余 $1。

### 8. indarkarhana — 🌾 (Rank Top10) Read the Market, Choose the Farm（68 票）

- **完整策略混合（mixture of complete strategies）**：两条路线共享同一开局，在共享开局期观察 `town.unlocked_shops`，**step 168 做一次性不可逆决策**：出现 YARN_STORE 则走羊毛友好路线，否则走默认路线；此后整季一致执行。
- 思想：最强农场不是单个盈利动作的集合，而是作物/动物/土地/劳力/仓储/市场时机支持同一个经济计划；最优计划随城镇需求变化。

### 9. salemali7 — 3094 score | Kaggriculture（60 票）

- HarvestForge-X：8 牛 / 4 羊、快速牲畜扩张 + melon/strawberry/wool premium 优先。
- 来源与 boatlee V16-RC5 **完全相同的三场 Replay**（92165990/92185587/92223213，Nikita Lugovoy 提交），逐阶段取最频繁动作重建确定性基线。说明同一公开源被多人独立重建并各自上分。
- 另有前作「Kaggriculture +3000 socre」（46 票）。

### 10. busyaprime — What actually wins on the Kaggriculture ladder（24 票）

- 从原始 episode replay 重算 meta 的分析框架（每日 fork 重跑，所有数字现场解析）：按 agent 名聚合胜率（Wilson 区间）、胜/负方动作计数对比、主作物胜率、动作指纹热图、利润分布。
- **关键结论**：① 胜方并不做更多动作——plant/sell/hire/harvest/fert 计数与负方几乎相等，胜方甚至种得略少；差距在「种什么、执行效率」；② ladder 已停止爬升：每日中位分见顶回落（给出斜率、p 值、CI），top-中位差距压缩数倍——**复制当前 meta 的价值大不如前，剩余优势要来自场上没人在看的地方**。

### ⭐ 11. nekkon — The top agent is a 720-turn replay, not a strategy（1 票，2026-08-20 巡视新发现）

诚实的测量型笔记，给出两个便宜可验证、但改变构建方向的结论：

- **对 `starter` 调参几乎不迁移**：同一 agent 对 starter 赚 $68,052、对真实榜首 agent 只赚 $29,444——starter 不碰市场，城镇吃掉的价格坑整季敞开，所有农场看起来都富；**agent 间差异在 starter 面前被压缩到看不见**。他的重建对真实 agent 是 +167% 胜率，对 starter 只有 +15% 金币。
- **最强公开 agent 不是策略而是离线序列**：V16-RC5 的 `main.py` 是「压缩 JSON 里 720 条每回合完整动作 + 小型反应层（修杂草、重排收获）」。榜首在做的是 offline sequence optimisation，不是更聪明的启发式。
- **V16-RC5 路线的解剖数字**：8 牛 / 4 羊 / 无鹅；264 次 HIRE（第 10 个工人 $55，整条板凳 $143，对 $100k 赛季不算什么）；$4,000 象限从不购买（第 6、10 天各扩一次即止）。作者自己的按「每格收益」分配器想要 27 头牲畜——错在约束是**动作**而非格子：一头动物每天要吃掉 4 个单位回合（喂/照料/收获/收肥）。
- 附带发布：从 notebook 提取对手 `main.py` 的四种形态（`%%writefile` / `%%agentfile` / base64 / zlib-blob）；macOS `ProcessPoolExecutor` spawn 陷阱（模块级全局不进 worker，必须把路径放进 job tuple）。
- 作者自报：对 top 5 公开 agent 胜率从 3.0% → 8.0%（仍是输，选择公开诚实数字与方法）。

### 12. tetsutani — 🌾 Read the Town, Build the Farm（1 票，2026-08-20 巡视新发现）

- tetsutani（Adaptive Farming 作者）的新作，主题从「premium 队列时机」转向**需求阅读 + 资本纪律 + 终局现金**。
- 把整季组织为三个问题：① 哪些需求会持续（读城镇解锁）；② 选能服务该需求的生产系统（路线承诺）；③ 足够早地停止扩张，让库存/产能/市场价值在第 720 步前都能变成银行余额（资本下限 + 计量清仓）。
- 属于「经济学规划器」路线的延续（与 pilkwang 同类），强调终局可变现性而非纸面产量。

### 13. boatlee — V13-R3 | Top-Meta Order-Safe Premium Control（14 票，2026-08-20 巡视新发现）

- 声称 clean-room 独立实现（不 fork 公开源码），生产日程与市场先验从公开 replay 观察重建。
- **核心是镜像战的 one-turn premium shift**：当双方都计划在 t+1 卖同一 premium 商品时，把有界的一部分提前到 t 回合，两回合总量守恒（t 卖 s，t+1 卖 q−s）。
- **激活门与参数**：near-mirror gate（公开作物/动物/结构/工人数/象限的 clone 距离 ≤ 6）；仅覆盖 STRAWBERRY/MELON/MILK/WOOL；仅 `120 ≤ step < 680`；单商品上限 30 且不超过下一基础 SELL、投影仓库与 replay 先验中位数；带偿还。
- **order-safe 细节**：早期原型用 `market.insert(0, ...)` 插队首，会推迟自己同回合更高价值的基础出售（尤其草莓）反而受损；R3 改用 `market.append(...)`，若队列已有同商品 SELL 则合并数量。
- 注：以上门控参数与本项目 v7 的 preempt 子系统（clone≤6 / 120–680 / 批量≤30 / 四商品 / append+合并）完全一致，构成独立交叉验证。

### 14. andrewsokolovsky — Kaggriculture V16：Same-Turn Slot Sniper（13 票，2026-08-20 巡视新发现）

- 在 V14 生产策略（公开）基础上测试更窄的反镜像机制：**不动数量、只动队列位置**。
- V14 抢占的是镜像对手的**下一回合**出售；V16 攻击的是**本回合**已排定但排在队列后面的 premium 出售——把同商品 SELL 从 slot 4 移到 slot 0，让自己的单位先到达共享市场，吃到价格曲线的高位。
- 用 V14 公开的 clone-distance 信号门控，硬回滚：候选只有在对称对局中击败精确的 V14 父代并通过回归面板时才提交，否则提交原 V14。
- 与 V13-R3 一起说明：镜像战军备竞赛已从「跨回合提前」细化到「同回合槽位排序」。

### ⭐ 15. Kaito Fukami — 180/208 Public-Notebook Blind | v38 Lineage Guard（38 票，2026-08-21）

- **核心升级**：不再把 Top-30 当作唯一对手分布，而是恢复并实时执行 26 份公开 notebook agent，覆盖 21 个不同谱系；每局重新加载模块，保留对手自身的状态反应。
- **路由方法**：v36 与 v37 共用前 116 个 actor/market 动作；在 step 96 用当前公开状态匹配 416 个训练原型的 5 个最近邻，估计两条兼容续着的价值。陌生状态回退 LB-wide v37；只有 v36 估计优势至少 $10,000 才切换。
- **输入边界**：只用双方公开农场、公开现金、市场、商店和自己的合法私有状态；不使用作者名、hash、episode、seed 或对手私有库存，属于「按状态识别谱系后果」，不是身份查表。
- **自报证据**：最终盲测 4 seed × 26 live agent × 双席位 = 208 局，v38 为 **180/208、平均 +$18,725**；另过 current Top-30（40/64）、多代（147/172）、近期 hosted（62/78）三层反回归面板，0 runtime failure。作者明确说明这些是本地盲测，不是 Public LB。
- **研究价值**：这是目前最完整的规则型 MoE/Router 公开实现。它直接支持我们 PPO v3 的方向：先保证专家续着兼容，再让模型学习选择；并说明「一个总体平均分」不足以选 checkpoint，必须分谱系验收。

来源：[Kaito v38 Lineage Guard](https://www.kaggle.com/code/kaitofukami/180-208-public-notebook-blind-v38-lineage-guard)

### ⭐ 16. boatlee — V21-R1 Public-State Route Portfolio（2026-08-21）

- 保留多条完整生产日程，只根据当前公开农场、公开现金、共享市场和商店解锁序列选路；不使用用户名、seed、episode 或未来观察。
- 本地三面板合计 **272 局 235/0/37**；配对结果合计 **120/0/16**，所有对局均为 720 frame、双方 `DONE`。证据强于只对 starter 或只给平均金币的方案，但仍没有可归因的线上 Rating。
- 对本项目很重要：V8 的 Kawa 五路线本就来自 V20 同代公开谱系，现有综述把 V20 标为 skip 是错误的研究优先级。应把 V20→V21 的路线差异、状态门控和完整 719 步轨迹 hash 固化为可执行专家族。

来源：[boatlee V21-R1 Public-State Route Portfolio](https://www.kaggle.com/code/boatlee/v21-r1-public-state-route-portfolio)

### ⭐ 17. Lynxx — Kaggriculture Adaptive Portfolio V21（6 票，2026-08-21）

- **五条完整路线**：按 YARN_STORE 和奶制品商店的出现顺序，选择 6C/12S/4Q、6C/8S/3Q、10C/4S/3Q 或默认 8C/6S/3Q，而不是把不同路线的单步动作随意拼接。
- **三项引擎修正**：step 0 先执行路线已有的小麦买单；同回合 `SELL` 早于农场 `DROP`，所以不能拿工人携带库存为当前卖单融资；终局追加卖单必须扣除已有计划量，不能重复计量。
- **研究价值**：它没有给出可靠的配对胜率，因此不是已证高分方案；但它是 V8/V9 动作编译器、仓容保护和 716–718 清仓逻辑的高价值审计清单。

来源：[Farming Score V2 / Adaptive Portfolio V21](https://www.kaggle.com/code/lynnsakurai/farming-score-v2-a-better-approach)

### ⭐ 18. dzjiann — RL of Meta Agent：960 Matchups and a PPO Plateau（2026-08-20）

- 不是让 PPO 直接控制工人，而是在 6 个公开强策略之间学习选择/切换；16 seed、双席位，合计 960 场。
- 最关键发现是**非传递循环**：B85 对 Andrews 30:2，Andrews 对 Kaito 21:11，Kaito 又对 B85 24:8。不存在一条对所有对手都最优的固定路线。
- **研究价值**：支持用 pairwise payoff、条件 Router 和多专家联赛训练；反对只按单一平均胜率挑一个“全局最佳专家”。这与 Kaito v38 的分谱系路由形成独立交叉验证。

来源：[RL of Meta Agent: 960 Matchups and a PPO Plateau](https://www.kaggle.com/competitions/kaggriculture/discussion/736439)

### 19. Steven Lee Hans — X567：单变量牛奶时序残差（21 票，2026-08-21）

- 保持 X562 的完整路线不动；仅在公开预测的 X036 牛奶产量低于阈值且对手不是近镜像时，把 step 264 的 `SELL MILK 6` 延迟到 265。
- 两阶段配对：预探 30 组为 13/17/0、平均 +$7.37；不相交确认 50 组为 20/30/0、平均 +$4.72，双席位和库存/动物/杂草等 guardrail 无回归。
- **研究价值**：绝对收益很小，具体阈值不宜照抄；值得学习的是「预注册一个动作、两阶段确认、只在非镜像局激活」的因果实验方法，以及从公开产能预测市场时点。

来源：[Kaggriculture X544（正文当前为 X567）](https://www.kaggle.com/code/stevenleehans/kaggriculture-x544-nah-i-d-win)

### 20. 开源 RL 基础设施 — diffmap/kaggicultureRL（2026-08-20）

- 提供 Rust 批量环境、结构化特征、动作 mask、循环策略、BC、PPO、单/双席位训练和测试，是目前社区里工程最完整的端到端 RL 框架之一。
- 但仓库没有发布可复现 checkpoint，也没有统一协议下的强对手胜率或线上成绩；现阶段只能证明训练连接器和评测器可运行，不能视为高分 baseline。
- **可借鉴部分**：并行环境、张量契约、动作合法性 mask、recurrent state 和评测隔离；不应直接采用其模型结论。
- 另一份 [phucthaiv02/kaggriculture](https://github.com/phucthaiv02/kaggriculture)（Apache-2.0）设计了 Top-10 Replay→BC→随机恢复/AWR→league PPO，并用冻结 BC anchor 的 KL、胜率/金币/P10 三重晋级门；但同样没有公开训练数据、checkpoint、曲线或强对手验证，且配置偏 H100，只能作为架构参考。

来源：[RL model release 讨论](https://www.kaggle.com/competitions/kaggriculture/discussion/736407)、[GitHub 仓库](https://github.com/diffmap/kaggicultureRL)

### 21. 负结果与弱证据方案

- **End-to-End RL Is Harder Than It Looks**：作者从排行榜 Replay 做 BC 再训低层动作 PPO，一周后仍失败；BC 轨迹高度同质、动作空间巨大、长周期信用分配困难，奖励塑形还会错误惩罚买地，使第二/第三块地成功收获率仅约 20%–40%。这是支持「高层 Router + 冻结执行器」的关键负证据。来源：[讨论](https://www.kaggle.com/competitions/kaggriculture/discussion/736567)。
- **X594 Ryo-live closed-loop planner**：基于 Ryo 完整 Replay 做公开状态闭环重写，但作者报告对 X578 的本地配对 gate 为负；说明“复制榜一 opening + 大范围闭环规划”不会自动优于固定路线。来源：[X578 slug / 正文 X594](https://www.kaggle.com/code/stevenleehans/kaggriculture-x578-i-m-the-strongest)。
- **Premium-First Market Agent**：自报仅对 starter 将终局资金从 $145,580 提到 $175,725，缺少强对手配对和完整输出，且与现有 slot/lead 思路高度重叠；只列观察。来源：[notebook](https://www.kaggle.com/code/ameythakur20/kaggriculture-premium-first-market-agent)。
- **EcoBot v2**：14–16 头动物、10–14 格小麦自给、42 格草莓和末季小麦推进，可作为高密度 OOD 生产专家候选；目前主要是 starter/sanity 证据，不进入主候选。来源：[notebook](https://www.kaggle.com/code/premaananda108/economics-driven-rule-agent-ecobot-v2)。
- **amerob 市场负实验**：30 场配对中，自适应储备出售约 −$149k、出售 MELON+肥料约 −$18.4k；提前卖掉肥料还会令随后 `FERTILIZE` 因库存为空全部 no-op。它提示任何市场残差都必须检查是否破坏 FEED/FERTILIZE/PLANT 的生产依赖。来源：[amerob/kaggriculture](https://github.com/amerob/kaggriculture)（无明确许可证，仅引用结论）。

### ⭐ 22. PJarbas/kaggriculture — FastEnv + CMA-ES 规则专家生成

- 用官方 `interpreter()` 驱动精简 FastEnv，而不是重写规则；仓库自报与完整环境 240 步状态逐字节一致，约 **13,500 turns/s**。
- 把混合牲畜、工人、土地、售价等约 16–25 个宏参数交给 CMA-ES 联合搜索；每个 seed 双席位配对，用 Wilcoxon、下行风险和多对手池做晋级，所有 episode 写入 SQLite，再用 Bradley–Terry 汇总族群强度。
- 当前 `ScaledFarmPolicy` 的 H29 参数在三块独立真实引擎 seed 上对 H9 合计 **69/70**；但这是项目内部父子代比较，没有可靠的当前线上 Rating，也不能直接把参数迁移到 Kawa 路线。
- **研究价值**：它最适合用来自动生成路线/生产结构不同的规则专家，为 PPO v3 扩充有效多样性；也能显著降低反事实和 league 的 CPU 成本。必须先锁定 Kaggle 实际引擎版本后复验。

来源：[PJarbas/kaggriculture](https://github.com/PJarbas/kaggriculture)（MIT）

### ⭐ 23. GzmCR/Kaggriculture — 路线 × 市场层 cross-graft

- 不是单纯再训一个 PPO，而是固定生产路线，收集单事件 advance/delay 反事实，再用岭回归/上下文 bandit 为市场残差做 LCB 门控。
- 公开结果显示，H1/H2/H3 全量提前卖在其路线族上均为负：有效样本平均约 **−$568**；更小数量抢跑也约 **−$74 至 −$130**，最终保守门控会回退 control。双向 advance/delay 的窄动作有过约 +$35 至 +$125 的小幅 holdout 改进。
- **研究价值**：这不直接推翻 V8/V9，因为底层路线和对手池不同；但它证明「提前 2/3 回合」高度依赖路线，必须做 `Kawa 路线 × market overlay` 交叉移植，不能把 wrapper 当成普适增益。

来源：[GzmCR/Kaggriculture](https://github.com/GzmCR/Kaggriculture)（无明确许可证，仅研究方法，不复制代码）

### 24. Seyamalam/Kaggriculture — late-game capital latch

- 在既有生产/市场策略上加一个一次性资金状态门：后期若公开对手已落后至少 $5,000，关闭新增 sweep/市场干预，避免领先局继续承担攻击风险。
- 100 个配对 seed 对父代 V18 为 **2 胜 / 97 平 / 1 负，平均 +$6.98**；效应很小，但实验是父子代直接配对，适合当低成本消融。
- **研究价值**：与 V9「镜像时更激进」互补，可测试 `领先时降档、落后时升级` 的风险控制；阈值必须在冻结 holdout 重选，不能照搬旧路线的 $5,000。

来源：[Seyamalam/Kaggriculture](https://github.com/Seyamalam/Kaggriculture)（MIT）

### 25. iZackk26 — 参数化规则专家与 winner's curse 记录

- 约 240 个实验脚本、99 条结论，用 CMA-ES-with-Margin 搜索约 50 个混合参数；13 个策略、3,744 场对局用于族群比较。
- 600 场冻结 holdout 为 **68.0%**，Wilson 区间 `[64.2%, 71.6%]`；作者同时记录开发期 87.5% 掉到 holdout 68%，是社区少见的 winner's curse 实证。
- **研究价值**：不是直接替代 V8/V9，而是提供生成异质规则专家、严格冻结 holdout 的参考。仓库无标准开源许可证，只能吸收实验设计。

来源：[iZackk26/Kaggriculture---AI-Agent](https://github.com/iZackk26/Kaggriculture---AI-Agent)

### ⭐ 26. Ryo Hasegawa — 1st Place Currently: Submission Strategy for Beginners

这不是游戏内生产路线，而是一套**线上提交、Rating 解读与双槽位管理方法**。帖子发布于 2026-08-19；抓取快照中作者位列第 1，正文约 29 净赞。以下严格区分赛制信息与作者的经验拟合。

| 层级 | 帖子要点 | 证据边界 |
| --- | --- | --- |
| 赛制/页面信息 | 只有最新两份提交继续活跃；截止后继续生成约两周对局，最终榜用 Bradley–Terry 基于该阶段对局重算 | 作者引用比赛 Evaluation 页面；最终看真实胜负，不继承 live Rating 历史 |
| 作者经验 | 新提交从 600 起步；前约 5 小时可完成约 60 局并接近收敛值的 90%；之后增长近似对数型 | 来自作者自己的提交和 Elo 风格模拟，并非 Kaggle 公布的内部参数 |
| 作者经验 | Rating 更新看胜/平/负，不看金币差；早期匹配密集，之后降到约每小时 1–2 局 | 用于解释「金币很多仍输」和不同提交的 Rating 轨迹差异 |
| 作者经验 | 约 60 局前不应下结论；即使 200 局后，几十点差距仍可能是噪声；应在相同对局数比较版本 | 作者给出的经验噪声带约为 ±25–50 Rating，早期更大 |
| 作者经验 | 原样重传同一 bot 只是重新抽一次 live 轨迹并挤掉旧槽位，不能改善最终榜表现 | 对最终评测无结构性收益，只会制造新的短期随机路径 |

作者给出的收敛速查：20 局约到最终 live Rating 的 60%，60 局约 87%–90%，96 局约 92%，200 局约 97%，300 局约 99%。这些百分比应当视为**量级参考**，不能当成官方保证。其拟合还给出近似的 `K ≈ 200 × exp(-n/26)` 加小幅下限，但评论区有人观察到更像「前期平台后快速衰减」，因此 K 的函数形式尚未被独立确认。

**可直接采纳的操作规则**：

1. 一个在线槽位长期保留当前已证实的强基线，提供稳定参照；第二个槽位只用于有实质差异的 challenger，或行为明显不同的 hedge。
2. 不为“重抽一个好 Rating”而原样重传；上线前先做同 seed、双席位、强对手分层的胜负配对。
3. 线上比较必须对齐对局数，并优先看胜/平/负、对手谱系和配对结果；平均金币与短期 Rating 只作诊断。
4. 我们现行 80 局口径仍可作为最低监控窗口（前 40 爬坡、后 40 稳定），但不足以只凭 Rating 宣称优越；100 局以上、同局数比较更稳妥。
5. 截止前最终两槽应放两份最强且零错误的 agent；若两者强度接近，保留路线或市场行为不同的组合可降低 meta 风险。

**评论区仍未解决的问题**：K 值究竟平滑衰减还是分段下降；最终 Bradley–Terry 如何处理平局；双方席位偏差有多大；hedge 需要多大行为差异；以及如何构造不会被固定对手误导的离线 sparring pool。另有参赛者报告新提交约 60 局已达到其当前 Rating 的 98%、首阶段约每小时 16–17 局，方向上支持“早期快速爬坡”，但仍只是个案。

来源：[Ryo Hasegawa 的原帖与评论](https://www.kaggle.com/competitions/kaggriculture/discussion/736219)

### ⭐ 27. yhay81 — Six-Day Public-State Fieldbook（129 票，2026-09-07 巡视）

- **架构**：6 天块（144 turn）× 5 块的块级路由。块边界用小决策树（4 棵树共 16 个二元测试、20 叶）在候选 6 天计划间选择，路线组合 `1×2×1×3×5` = 30 条全季路径，仅存 8 条 tape（复用）。特征只用观测内信息：解锁商店、市场价格/库存、公开农场状态、自家 shed/hand；明确不读对手身份/seed/终局。
- **路线来源**：top-200 公共 replay 按 SHA-256 去重（363 条完整历史），rank 3/8 的全部公开局按 6 天块切成 swap 候选；候选块在**同一边界、fresh seed、双席位**对测后入选。
- **budget guard**：块开始前核算块内计划采购成本，现金不足只卖多余产品（保护块所需库存，高价优先）。
- **自报成绩**：冻结面板 188 对手 × 64 seed × 双席位 = 24,064 局，点率 **0.9485**（95% CI [0.9371, 0.9565]）；常规 164 对手子集 0.9948，**硬 24 对手子集仅 0.6322**（作者自认主要短板）。C++ 实现（policy.cpp → agent.so），tape 存外置 Dataset。

### 28. yhay81 — Three-Day Shop Router（121 票，2026-09-07 巡视）

- 标题名不符实：**不是更细粒度全季路由，而是收缩为「anchor tape + 单决策点」**。719 turn 中仅 turn 360–431（恰 3 天）存在两条分支，唯一决策点 t=360，两条手写阈值规则：首店 BAKERY 且化肥库存 ≤10232.5、或首店 PET_CAFE 且对手种植格 ≤64.5 → 换入替换段。替换段是同一生产计划下的市场操作变体（多卖 WOOL/MILK、少买化肥），t=432 后与 anchor 逐字节相同——**离线对齐拼接、运行时零状态校正**。
- 全文无任何验证数字；budget guard 完整代码在此件中公开（72-turn 边界核算、保护性库存、价格降序补卖、sales-first 重排）。信号：该作者体系已收敛到「强 anchor + 极少数高价值分叉点」。

### ⭐ 29. Thomas Tschinkel — Public State Router v3.1（74.5%）→ v5（93.8%）（2026-09-07 巡视）

- **v3.1**：4 条 tape（MAIN/YARN/YARN_CARROT/MILK_GLUT，差分存储），3 个手工切换点：t=226 看 YARN_STORE 解锁、t=360 看胡萝卜价 ≥42、t=433 看牛奶市场库存 ≥10067；运行时 `_switch_ok` 逐 turn 前缀一致才许切换。三个每-turn 修复层（weed_dig/dead_stock/clamp_sells）合计 +19/−0。验证：968 局（真实 ladder 录像席位重放），SEARCH/SCREEN/HOLD 三段切分，HOLD 74.5%。
- **v5**：升级为 **6 天块决策树路由**——5 条完整块对齐 tape，5 棵离线拟合 CART 树（每块一棵），t=0/144/288/432/576 五个边界重路由；特征 100 维（双方金钱与农场全量普查、9 商品价格/库存偏差、商店解锁与需求映射、自家 shed/种子）。**修复层全部删除**：2,048 局消融显示清仓/除草/预算清算等手工层增益 0 或为负（预算清算 −440 局），「Simplicity won」。验证：689 对手 tape × 32 seed × 双席位 = 44,096 局 **93.76%**，独立 256-seed 面板 93.85%，对旧版 live 16–0。
- **关键教训（destbreso 独立证实）**：作者上传的实际参赛 agent 与公开 notebook 不同（t=0 即分歧、719 中 697 turn 不同）——高手普遍「净化版公开发布」。

### ⭐ 30. Kaito Fukami — v48 Fast Routes（131 票，2026-09-07 巡视）

- **从 v38 的 21 谱系 5-NN 路由大幅收缩**：6 条完整 719-step tape（default/yarn_fast/farm_fast/yarn_second/yarn_third/bakery_capital），路由器为纯规则事件检测 + 一次性闩锁（切出不回切）。事件全部锚定**商店解锁**：首店 YARN_STORE（t≥88，共享前缀到 87）、首店 FARMERS_MARKET（t≥120）、二店/三店 YARN 变体、以及 t=160 单点的 BAKERY 资本恢复分支（附对手公开农场条件）。
- **v47 惨案**：每回合并行评估 4 个子策略 → 托管超时 → 前 11 局全 PASS、0/11。v48 核心不变量：**每回合恰好调用 1 个子策略**。托管 1 秒动作预算下多子策略并行评估不可行。
- 消融：最强单路线在 Top-10 留出面板仅 29/46，v44 底盘 35/46，稀疏混合 **39/46**；早期地板面板 40/40。防泄漏：每队最新 2 个 episode 留 holdout、队内时间序切分（谱系共享导致按队分折泄漏）。
- **meta 观察**：Top-30 至少 4 队（Crop Dusta、junseok lee、taiseiu、Kaileh57）是 20/20 开局的快爬流；开局分歧点=首店解锁（YARN≈t88、FARMERS≈t120）；克隆检测（公开农场签名 L1 距离 ≤2.0 连续 24 turn）+ 卖出抢占仍保留但被状态否决约束。

### 31. dmitriigluzdov — Goose Portfolio（自报历史 LB 2615，2026-09-07 巡视）

- 2615 的主体是继承的 prvsiyan《Moon Counts Melons》V29 固定 tape（压缩 blob）；作者增量是 t=150 的**畜牧资产组合单点决策**（2 牛/1 牛 1 鹅/2 鹅），估值函数含 30 天营收预测与价格挤压（cannibalization）模型，双门槛（+600/+2000）。本地面板 38 胜 4 负 6 平；且加不加第二道门槛动作完全相同（增量未证明）。
- **最重要事实**：**同一字节相同的代码两次提交，得分 2615.0 与 1833.3**——LB 单次得分噪声约 800 分，历史高分不构成复现证据。

### ⭐ 32. destbreso — 97% predictable: Extracting decision trees（2026-09-07 巡视）

- 方法：对 BRANCHER 型 agent 从公开 replay 提取行为决策树。三步：动作前缀等价类找分叉 turn → 官方引擎重放重建分叉时观测、决策树桩搜索解释 → 置换检验 + leave-one-out 验证。**LOO 分支级预测命中 123/126 = 97.6%**（并入 Tschinkel 案后 187/195 = 95.9%）。
- **top 15 形态普查**（2026-09-04）：BRANCHER 1（恰是 rank 1 keiz 3054.1）、MIXED 6、SCHEDULER 6、纯 SCRIPT 2。
- **顶部共同骨架**：①第一级分叉全部落在**商店解锁 turn**（t=72–80、t=144–155），分离特征是某商品价格（商店抽签编码在价格里）；②第二级读**自家现金**；③**没有一个显著分叉以对手状态为最佳解释**——「顶部 BRANCHER 基本不读对手」。MtN（rank 5, 2896）被完整读出两级树：t=80 WOOL 价 → t=144 WHEAT 价 → t=150 EGG 价 → t=155+ 现金微分叉。
- 工具本身即对手建模器（`read_tree(SUBMISSION_ID)` 可读任意对手），但作者明确「读出树 ≠ 打败它」，且对 SCHEDULER（6/15）无效、深树需 20–40 局公开局。
- 另:739179 帖 x-ray 记录了一个真正的每-turn 自适应 mutant 曾以 40–0、中位 margin +13,065、rating 2977 登顶后被队伍主动撤下（防复制）。

### 33. tetsutani — Shape the Shop, Work the Pasture（118 票，2026-09-07 巡视）

- 与 Tschinkel v3.1 **同源同构**（同样 4 条 tape MAIN/YARN/YARN_CARROT/MILK_GLUT、同样 3 个切换点 226/360/433、同阈值 42/10067、同修复层）——该 tape+router 家族在社区多作者间传播，被 indarkarhana fork 成 "TOP 10" 版（94 票）。本作唯一增量：收盘 shed 目标从 100 改 99（留 1 格缓冲）。
- 生产结构参考值（MAIN 带）：种植 WHEAT 164/STRAWBERRY 33/CARROT 31/MELON 12；9 牛 5 羊 3 鹅、14 牧场 4 鸡舍；FEED 361/CARE 381/收肥 384；**肥料外销 351 单位、100 笔订单，是订单数最多的商品**；施肥 98 次且全部在 t≥342（后半季）；胡萝卜全压 t≥673 尾盘卖。

### 34. 关键讨论（2026-09-07 巡视）

- **738837（官方 bovard 答复）**：「用公共 replay 训练/构建/参考你的提交是允许且被鼓励的」——tape 路线合规性官方定调。
- **731587 + 739410（官方）**：终局评估 = 截止后继续跑两周 episode，然后对**届时仍活跃的 agent 做单次 Bradley-Terry 锦标赛**定名次；队伍取两个提交中较好者（**第二槽位是无损 hedge**）；平局各记半胜。
- **739534（评分机制实测）**：2300 前每胜约 +100；2300 后降至约 +60 并递减到 <10；**一场败会使收敛提前约 500 分**；前 80 局每 ~4 分钟配 1–2 局，之后 10–15 分钟一批；约 5 小时可爬到真实 rating 附近。评论区：top 10 匹配池很窄、会反复遇到同几个对手；有人 peak 第 6 后 4 天掉到 700 名——**挂榜 agent 会被新 meta 持续打压，分数非静态**。
- **739179**：#1 一日易主十余次；纯自适应 mutant 登顶即撤（社区惯例：最强 agent 不留在榜上，防被 x-ray/克隆）。

## 三、社区共识配方

**交叉验证过的结论**：

1. **top meta 是 replay 重建军备竞赛**：多个独立作者（Rayk、boatlee、salemali7、Kaito、Navaz）都从 top 队伍公开 Replay 蒸馏路线；同一源（如 Nikita Lugovoy `55440039`、Tran `89674601`、Ezzzzzekki `55390428`）被多方重建，SHA-256 可证同源。收敛终态约 8 牛 / 5–6 羊 / 12 工 / 3 象限 / 草莓+小麦为主。
2. **同一路线谱系的镜像局主要由市场时机分胜负，跨代对局仍可能由生产路线决定**：clone-aware 提前出售（Hamburger→c15 对母版 14-2）、提前 2 回合 premium 出售（C45 → 3085.4）、价格冲击排序（C71）、一回合 premium lead（V16-RC5 60/60）都是「同路线上的窄域 wrapper」；但本项目 V7→V8 的实验已显示 Kawa 五路线带来明显生产代差。2026-08-20 后市场战线又细化到同回合 slot 排序；GzmCR 的负结果进一步说明 lead/preempt 不能脱离底层路线独立评价。
3. **终局机制**：step 718 是最后可执行动作（719 不执行）；终局控制器接管时点（712→717）值一局胜负；终局清仓/inventory relay 是标配。
4. **premium 商品必须计量出售**：wool/strawberry/milk ~60–80 单位即崩到 $1；每单 4–8 单位小批量；wheat/egg 是压舱物（~3000 单位才崩）。
5. **Rating 机制决定策略选型**：只奖胜不奖分差 → 83-5 仍可卡在 3000 下（C70）；接近局转化能力比碾压弱队重要；相同代码重传会有不同 Rating 轨迹；只有最新两个提交持续获得对局。
6. **下载 top replay 要按 publicScore 匹配计分提交**，否则采到同队伍的低分活跃提交。
7. **镜像战是主要对局形态**：双方路线高度同源时，一回合出售先手即可决定胜负（Hamburger 6-0、V16-RC5 60/60）。
8. **对 `starter` 的本地金币几乎不具迁移性**（nekkon，2026-08-20）：starter 不参与市场，价格坑整季敞开，同一 agent 对 starter 赚 $68k、对真实榜首 agent 只赚 $29k；agent 间差异在 starter 面前被压缩。本地验收应以**可执行对手族的配对胜率**为准，starter 只能当冒烟测试。
9. **约束是动作而非格子**（nekkon 解剖 V16-RC5）：top 路线只有 8 牛/4 羊/无鹅、264 次 HIRE、不买 $4k 象限；按「每格收益」贪心会想要 27 头牲畜，但每头动物每天消耗 4 个单位回合（喂/照料/收获/收肥），动作才是稀缺资源。
10. **对手分布应按可执行谱系管理，而不是只看榜单名次**：Kaito v38 在 21 个公开谱系上训练/盲测，并同时守住 Top-30、历史代和近期 hosted 三个面板。公开代码族本身已成为当前 meta 的重要组成部分。
11. **专家间存在非传递性**：960 场 meta-agent 实验出现 A 胜 B、B 胜 C、C 又胜 A 的循环。训练 Router 时应保留 pairwise payoff 和最差谱系门槛，不能只优化等权平均胜率。
12. **完整路线兼容性优先于自由切换**：Kaito 只在两条路线共同的前缀期选一次续着；boatlee/Lynxx 也选择完整季节方案。这说明 Route/MoE 动作必须带可达状态和兼容前缀约束。
13. **市场结算早于农场动作**：同回合工人 `DROP` 的货不能用于当前 `SELL`；终局和仓容逻辑只能按动作前 shed 库存下单。这是新公开实现反复修正的引擎级陷阱。
14. **前沿架构已收敛为「块级 public-state 路由」**（2026-09-07 修订）：yhay81（6 天块 × 决策树，0.9485 点率）、Tschinkel v5（6 天块 × CART，93.8%）、Kaito v48（商店事件闩锁 × 6 tape）三个独立体系同构。共同点：块边界=商店解锁节奏；tape 离线对齐、运行时零状态校正；路由特征以商店解锁/商品价格为主、自家现金为辅、**不读对手**。
15. **修复层大势已去**（2026-09-07 新增）：Tschinkel v5 消融证明 weed_dig/清仓/预算清算等每-turn 修补在强 tape 上增益 0 或为负（预算清算 −440 局）并整体删除；Kaito v47 因每回合并行评估多子策略而托管超时全 PASS（0/11）。执行层结论：**每回合恰好一次查表 + 极少修饰**是安全上限。
16. **LB 单次得分噪声约 ±400**（2026-09-07 新增）：同码双提交 2615.0 vs 1833.3；#1 一日易主十余次；peak 第 6 名的提交 4 天滑落到 700 名。单次 LB 分数不可作为方案 A/B 证据，本地大面板（万局级）+ 相同局数比较才可信。
17. **评分动力学**（739534 实测）：2300 前每胜 +100、之后 +60 递减；一败提前收敛 ~500 分；前 80 局高频匹配（4 分钟一批）。**快速爬分的全部秘密 = 前 80 局零败**；顶部匹配池窄，rating 上限由「对反复相遇的同几个 top 对手的胜率」决定。

**避坑清单（社区已证伪的方向）**：

- 第四象限（SE，$4000）扩张：负结果（C93）；top 几乎只买 NE+SW。
- 日内资本化的宽阈值：500/1000 金币阈值、两步改道全部 0-8 败退；只有「≥2000 价值 + 一步距离」存活（C72）。
- 长 horizon 搜索的聚合胜场陷阱：horizon 25 赢了长 horizon 入围门，却对新 seed 上的父代 C45 0-6——对弱历史 agent 的聚合胜场会掩盖对直系父代的回归。
- 激进持续清仓：远劣于保守路线（C72 对照）。
- melon 施肥：浇水即可到顶，肥料应留给 wheat。
- 引擎版本差异：1.32.x 与新 build 价格悬崖参数不同，分析/训练前必须锁定版本。

**仍缺可靠公开证据的方向**（busyaprime 的收敛结论 + 2026-08-22 增量观察）：

- 从相邻回合市场库存变化中扣除城镇消费和我方订单，反推出**对手实际 SELL/BUY、lead horizon 与批量风格**；V9 当前主要按农场结构判镜像，尚未真正识别对手市场行为；
- 能在陌生状态下稳定工作的经济规划/OOD 专家。Kaito v38 已用公共状态最近邻迈出一步，但仍有公开谱系硬例；
- 进入 top 梯队且有公开 checkpoint、强对手配对和线上证据的强化学习 agent。目前社区 RL 主要是工程框架、负结果或高层 meta-agent 实验；
- 适合 Router 的高质量反事实数据。端到端 BC 已被多方观察到固定轨迹同质化，下一步应采集同状态、多专家、可执行完整续着的收益标签。

**本项目调研基础设施待修**：`v8_kawa_lead2_slot/extract_top_routes.py` 当前所谓 field hash 只覆盖稳定样本的最后一回合，而不是完整 719 步生产轨迹，可能把不同路线误判为同族。后续每日巡视应记录完整轨迹 hash、来源 episode、席位、计分提交 `publicScore` 和引擎版本。

## 附录：已调研清单

| ref | 标题/自报分数 | 状态 | 调研日期 | 备注 |
| --- | --- | --- | --- | --- |
| boatlee/v16-rc5-high-score-8c-4s-premium-market-lead | V16-RC5（181 票） | read | 2026-08-20 | 见二.2 |
| kaitofukami/25-27-strict-future-v27-midgame-meta-reset | v27（163 票） | read | 2026-08-20 | 见二.3 |
| romantamrazov/kaggriculture-hamburger | Hamburger（127 票） | read | 2026-08-20 | 见二.4 |
| tetsutani/adaptive-farming-strategy-for-kaggriculture | Adaptive Farming（123 票） | read | 2026-08-20 | 见二.5 |
| pilkwang/kaggriculture-structured-economic-policy | Structured Economic Policy（95 票） | read | 2026-08-20 | 见二.6 |
| raykkretzschmar/kaggriculture-findings-from-zero-to-top-meta | Findings from Zero to Top Meta（91 票） | read | 2026-08-20 | 见二.1 |
| cjlcjlcjl/kaggriculture-what-the-top-farms-do-a-live-meta | Live Meta（74 票） | read | 2026-08-20 | 见二.7 |
| indarkarhana/rank-top10-read-the-market-choose-the-farm | Top10 Read the Market（68 票） | read | 2026-08-20 | 见二.8 |
| salemali7/3094-score-kaggriculture | 3094 score（60 票） | read | 2026-08-20 | 见二.9 |
| busyaprime/what-actually-wins-on-the-kaggriculture-ladder | What actually wins（24 票） | read | 2026-08-20 | 见二.10 |
| nekkon/the-top-agent-is-a-720-turn-replay-not-a-strategy | Top agent is a replay（1 票） | read | 2026-08-20 | 见二.11；starter 不迁移 + top agent 解剖 |
| tetsutani/read-the-town-build-the-farm-kaggriculture | Read the Town（1 票） | read | 2026-08-20 | 见二.12；tetsutani 新作，需求阅读+资本纪律 |
| boatlee/v13-r3-top-meta-order-safe-premium-control | V13-R3（14 票） | read | 2026-08-20 | 见二.13；one-turn shift 门控参数与本项目 v7 preempt 一致 |
| andrewsokolovsky/kaggriculture | V16 Slot Sniper（13 票） | read | 2026-08-20 | 见二.14；同回合槽位抢占 |
| kaitofukami/180-208-public-notebook-blind-v38-lineage-guard | v38 Lineage Guard（38 票快照） | read / priority | 2026-08-22 | 见二.15；21 谱系、公共状态 5-NN Router、208 局盲测 |
| boatlee/v21-r1-public-state-route-portfolio | V21-R1 Route Portfolio（0 票快照） | read / priority | 2026-08-22 | 见二.16；完整路线组合、272 局 closed-loop screen |
| lynnsakurai/farming-score-v2-a-better-approach | Adaptive Portfolio V21（6 票快照） | read | 2026-08-22 | 见二.17；五路线 + 三项引擎修正，缺量化胜率 |
| kaggriculture/discussion/736439 | RL of Meta Agent（4 票快照） | read / priority | 2026-08-22 | 见二.18；960 场、专家非传递循环 |
| kaggriculture/discussion/736567 | End-to-End RL Is Harder Than It Looks（2 票快照） | read / negative | 2026-08-22 | 见二.21；低层 BC/PPO 失败复盘 |
| kaggriculture/discussion/736407 | RL model release（2 票快照） | read / infra | 2026-08-22 | 见二.20；对应 diffmap/kaggicultureRL，无 checkpoint/强对手成绩 |
| kaggriculture/discussion/736219 | 1st Place Currently - Submission Strategy for beginners（29 净赞快照） | read / methodology | 2026-08-22 | 见二.26；区分官方终局赛制与作者的 Rating 收敛经验，指导双槽位和等局数比较 |
| github/PJarbas/kaggriculture | FastEnv + CMA-ES | read / priority | 2026-08-22 | 见二.22；规则专家生成与统计晋级框架，MIT |
| github/GzmCR/Kaggriculture | Cross-graft market residuals | read / priority | 2026-08-22 | 见二.23；市场抢跑非普适增益，无明确许可证 |
| github/Seyamalam/Kaggriculture | V21 capital latch | read | 2026-08-22 | 见二.24；领先时收缩风险，MIT |
| github/iZackk26/Kaggriculture---AI-Agent | 参数化规则实验 | read | 2026-08-22 | 见二.25；600 场 holdout 与 winner's curse 记录，无标准许可证 |
| github/phucthaiv02/kaggriculture | BC/AWR/league PPO 架构 | read / infra | 2026-08-22 | 无数据、checkpoint 或强对手验证，Apache-2.0 |
| github/amerob/kaggriculture | 市场与生产依赖负实验 | read / negative | 2026-08-22 | 提前卖肥料会破坏后续生产动作，无明确许可证 |
| stevenleehans/kaggriculture-x578-i-m-the-strongest | slug X578 / 正文 X594（2 票快照） | read / negative | 2026-08-22 | Ryo-live 闭环 planner 配对 gate 为负 |
| ameythakur20/kaggriculture-premium-first-market-agent | Premium-First（1 票快照） | read / watch | 2026-08-22 | 仅 starter 增益，缺强对手配对 |
| premaananda108/kaggriculture-ecobot-v2 | EcoBot v2（8 票快照） | read / watch | 2026-08-22 | 高密度 14–16 动物路线，主要为 starter/sanity 证据 |
| ameythakur20/kaggriculture-deterministic-farm-planning-agent | Deterministic Planning（4 票） | skip | 2026-08-20 | 新发布低票 |
| koushikkumardinda/kaggriculture-starter | Starter（4 票） | skip | 2026-08-20 | starter 克隆，无新内容 |
| bovard/kaggriculture-getting-started | Getting Started（691 票） | skip | 2026-08-20 | 官方入门教程，无新策略内容 |
| kaitofukami/15-16-strict-future-v25-meta-reset | v25（97 票） | skip | 2026-08-20 | v27 的旧版本 |
| kaitofukami/177-180-fresh-top-30-v21-1-conditional-memory | v21.1（92 票） | skip | 2026-08-20 | v27 的旧版本 |
| kaitofukami/159-160-vs-frontier-v20-weed-slip-recovery | v20（74 票） | skip | 2026-08-20 | v27 的旧版本 |
| kaitofukami/40-53-top-10-future-holdout-v18-closed-loop | v18（36 票） | skip | 2026-08-20 | v27 的旧版本 |
| kaitofukami/41-49-future-unseen-v19-replication-to-control | v19（18 票） | skip | 2026-08-20 | v27 的旧版本 |
| ravi123a321at/177-180-fresh-top-30-v21-1-conditional-memory | v21.1 转载（1 票） | skip | 2026-08-20 | Kaito 的 fork |
| boatlee/v16-rc2-high-score-near-mirror-market-relay | V16-RC2（79 票） | skip | 2026-08-20 | V16-RC5 的旧版本 |
| boatlee/v16-rc5-r5a-high-score-8c-4s-recovery | V16-RC5-R5A（12 票） | skip | 2026-08-20 | RC5 变体 |
| boatlee/v17-r1-rc2-high-score-10c-4s-market-storage | V17（5 票） | skip | 2026-08-20 | RC5 旧变体 |
| boatlee/v20-adaptive-r1-multi-route-agent | V20（37 票） | read / priority | 2026-08-22 | 纠正旧分类：它是本项目 V8 Kawa 五路线来源与本地上界，不应按旧版跳过 |
| boatlee/84-84-base-public-holdout-v14-clone-preemption | V14（64 票） | skip | 2026-08-20 | boatlee 旧版 |
| prvsiyan/kaggriculture-frontier-the-soil-remembers-rain | Frontier 系列（79 票） | skip | 2026-08-20 | EDA/叙事系列，非可提交策略 |
| prvsiyan/kaggriculture-frontier-the-moon-counts-melons | Frontier 系列（75 票） | skip | 2026-08-20 | 同上 |
| prvsiyan/kaggle-frontier-lab-strategy-improvement | Frontier Lab（56 票） | skip | 2026-08-20 | 同上 |
| prvsiyan/kaggriculture-frontier-lab-high-score-visuals | Frontier Lab（55 票） | skip | 2026-08-20 | 同上 |
| georgymamarin/kaggriculture-visualized-what-every-crop-pays | Visualized（79 票） | skip | 2026-08-20 | 作物经济学 EDA，要点已被 Live Meta 覆盖 |
| georgymamarin/kaggriculture-daily-replays-the-live-meta-report | Daily Replays（23 票） | skip | 2026-08-20 | 每日 replay 报告，与 Live Meta 重叠 |
| flexonafft/kaggriculture-multi-route-farming-agent | Multi-Route（77 票） | skip | 2026-08-20 | 多路线规则基线，选路思想已被 indarkarhana 覆盖 |
| andrewsokolovsky/kaggriculture-breaking-the-tie | Breaking the Tie（64 票） | skip | 2026-08-20 | 平局分析，非策略方案 |
| romanrozen/strong-barnyard-economist | Barnyard Economist（59 票） | skip | 2026-08-20 | 早期基线（LB~950），melon 时机思想已入 findings 引用表 |
| jek1wantaufik/building-a-kaggriculture-ai-agent | Building an AI Agent（58 票） | skip | 2026-08-20 | 教程类 |
| navazshfathi/notebook198200c757 | （56 票） | skip | 2026-08-20 | Tran episode 89674601 重建，与 Hamburger 锚点同源（SHA-256 相同），已被 findings 日记覆盖 |
| salemali7/kaggriculture-3000-socre | +3000（46 票） | skip | 2026-08-20 | 3094 版的旧版本 |
| anasriaz/kaggriculture | （45 票） | skip | 2026-08-20 | 标题无信息，未入选 |
| bruceqdu/my-2026-08-04-high-score-pipeline | 08-04 Pipeline（44 票） | skip | 2026-08-20 | 早期 pipeline，已被后续 meta 取代 |
| degnonguidi/kaggriculture-agent-builder | Agent Builder（44 票） | skip | 2026-08-20 | 工具类 |
| lucifer19/kaggriculture-night-harvest | Night Harvest（40 票） | skip | 2026-08-20 | 未入选精读 |
| saitejabandaruin/kaggriculture-pure-architecture-2600-elo-v3 | Pure Architecture V3（27 票） | skip | 2026-08-20 | 自报 2600 Elo，未入选精读 |
| saitejabandaruin/kaggriculture-ultimate-mega-ensemble-3000 | Mega-Ensemble（22 票） | skip | 2026-08-20 | 公开 agent 集成器，无原创模型 |
| mpwolke/doomed-kaggleculture-harvest | （24 票） | skip | 2026-08-20 | 评论类 |
| alexandergremyakov/harvest-pulse-goose-dividend-v2 | Goose Dividend（24 票） | skip | 2026-08-20 | 鹅策略小票方案，未入选 |
| raykkretzschmar/kaggriculture-rank-your-agent | Rank Your Agent（84 票） | skip | 2026-08-20 | 评测工具，非策略 |
| denizeryilmaz/v111-8c4s-economic-core-premium-lead | V111（16 票） | skip | 2026-08-20 | 8C4S 衍生品，低票 |
| kunaldesale2408/kaggriculture-2026-v1 | （15 票） | skip | 2026-08-20 | 低票 |
| kunaldesale2408/kaggriculture-ttv1 | （9 票） | skip | 2026-08-20 | 低票 |
| reyhanksatria/best-market-agent-high-strategy | （5 票） | skip | 2026-08-20 | 低票 |
| web3cainiao/kaggriculture-v21-tactical-memory | （6 票） | skip | 2026-08-20 | 低票 |
| stevenleehans/kaggriculture-x544-nah-i-d-win | slug X544 / 正文 X567（21 票快照） | read | 2026-08-22 | 见二.19；非镜像牛奶时序的严格单变量消融 |
| zakariajoudar/rule-based-agent-with-dynamic-ma | （9 票） | skip | 2026-08-20 | 新发布低票 |
| mansiaggarwal88/why-our-kaggriculture-ai-failed-math-vs-reality | （9 票） | skip | 2026-08-20 | 失败复盘随笔 |
| maulikgajera/2153-7-kaggriculture-solutions | 2153.7（6 票） | skip | 2026-08-20 | 低分方案 |
| destbreso/a-dna-test-for-agents | （6 票） | skip | 2026-08-20 | 分析工具 |
| destbreso/dissecting-the-top-two | （5 票） | skip | 2026-08-20 | 分析类，低票 |
| destbreso/what-1-32-7-changed-and-what-it-did-not | （1 票） | skip | 2026-08-20 | 版本变更说明 |
| destbreso/kaggriculture-compare-two-agents | （1 票） | skip | 2026-08-20 | 工具 |
| destbreso/kaggriculture-measure-your-agent | （1 票） | skip | 2026-08-20 | 工具 |
| moushunchen/twelve-seeds-three-melons | （4 票） | skip | 2026-08-20 | 低票 |
| ahmed1harfoush/kaggriculture-notebook | （3 票） | skip | 2026-08-20 | 低票 |
| tuannm3812/hierarchical-task-coordinator-htdc-v12 | HTDC v12（1 票） | skip | 2026-08-20 | 低票，层级任务调度，巡视时若更新可复核 |
| lucashmateo/kaggriculture-replays-no-oom-3-dataframes | （0 票） | skip | 2026-08-20 | replay 解析工具 |
| keremelik/kaggriculture-paired-not-paper | （0 票） | skip | 2026-08-20 | 低票 |
| keremelik/kaggriculture-two-fail-cells | （0 票） | skip | 2026-08-20 | 低票 |
| keremelik/kaggriculture-cash-path-1327 | （0 票） | skip | 2026-08-20 | 低票 |
| nagatakengo/predict-future-melon-prices | （0 票） | skip | 2026-08-20 | melon 价格预测实验，新发布，巡视时可复核 |
| zaedradwan/notebookbbeb477a58 | （0 票） | skip | 2026-08-20 | 无信息 |
| holeneckles/notebooke394244546 | （0 票） | skip | 2026-08-20 | 无信息 |
| artemzapara/type-safety-with-pydantic-models | （0 票） | skip | 2026-08-20 | 工程实践，非策略 |
| yhay81/six-day-public-state-fieldbook | Six-Day Fieldbook（129 票） | read / priority | 2026-09-07 | 见二.27；6 天块路由，0.9485 点率 |
| yhay81/three-day-shop-router | Three-Day Shop Router（121 票） | read | 2026-09-07 | 见二.28；anchor+单决策点，budget guard 全码 |
| thomastschinkel/kaggriculture-public-state-router-74-5-win-rate | Router v3.1 74.5%（98 票） | read | 2026-09-07 | 见二.29 |
| thomastschinkel/kaggriculture-93-8-win-rate-public-state-router | Router v5 93.8%（2 票） | read / priority | 2026-09-07 | 见二.29；6 天块 CART，删修复层 |
| kaitofukami/40-40-early-floor-39-46-top-10-v48-fast-routes | v48 Fast Routes（131 票） | read / priority | 2026-09-07 | 见二.30；KNN→事件闩锁 |
| dmitriigluzdov/kaggriculture-goose-portfolio-historical-lb-2615 | Goose Portfolio 2615（8 票） | read | 2026-09-07 | 见二.31；同码双提交分差 800 |
| destbreso/97-predictable-extracting-decision-trees | 97% predictable（5 票） | read / priority | 2026-09-07 | 见二.32；对手树提取 |
| tetsutani/shape-the-shop-work-the-pasture-kaggriculture | Shape the Shop（118 票） | read | 2026-09-07 | 见二.33；与 Tschinkel v3.1 同源 |
| kaggriculture/discussion/738837 | replay tape 合规问询 | read | 2026-09-07 | 见二.34；官方允许并鼓励 |
| kaggriculture/discussion/739410 | BT 终局三问 | read | 2026-09-07 | 见二.34；取两提交较好者、平局半胜 |
| kaggriculture/discussion/739534 | 评分机制实测 | read | 2026-09-07 | 见二.34；2300 前 +100/胜、一败 −500 收敛 |
| kaggriculture/discussion/739179 | 榜首 x-ray：mutant 登顶即撤 | read | 2026-09-07 | 见二.34 |
| indarkarhana/shape-the-shop-work-the-pasture-top-10 | TOP 10 fork（94 票） | skip | 2026-09-07 | tetsutani 同名作 fork，母本已读（二.33） |
| lynnsakurai/farming-score-a-mathematical-approach | Mathematical Approach（47 票） | skip / watch | 2026-09-07 | lynnsakurai 新版，前作 v2 已读（二.17），巡视再核 |
| avioon/kaggriculture-apex-v7-god-emperor | Apex V7（50 票） | skip | 2026-09-07 | 标题浮夸无分数口径 |
| evgendvorkin/kaggriculture | （32 票） | skip | 2026-09-07 | 标题无信息 |
| flexonafft/kaggriculture-smart-farm-strategy-lab | Smart Farm Strategy Lab（26 票） | skip | 2026-09-07 | flexonafft 系列，前作已 skip |
| flexonafft/kaggriculture-adaptive-farm-intelligence | Adaptive Farm Intelligence（52 票） | skip | 2026-09-07 | 同上 |
| yamakawanin/king-v4e-rc4 | King-v4e RC4（2 票） | skip | 2026-09-07 | 低票 |
| yamakawanin/kaggriculture-2312-9-q30-v2a | 2312.9 Q30 v2a（3 票） | skip | 2026-09-07 | 低票自报 2312.9，巡视再核 |
| y3uanm/kaggriculture-market-impact-router-v4 | Market-Impact Router v4（1 票） | skip | 2026-09-07 | 低票 |
| destbreso/which-language-does-your-agent-speak | Which language（2 票） | skip | 2026-09-07 | 97% predictable 的前作分类学，要点已并入二.32 |
| busyaprime/kaggriculture-800-paired-games-and-the-map-wins | 800 paired games（0 票） | skip / watch | 2026-09-07 | busyaprime 统计系列，票起再读 |
| busyaprime/kaggriculture-five-days-of-the-ladder | Five days of the ladder（0 票） | skip | 2026-09-07 | 同上 |
| tokenjunkielabs/titan-kaggriculture-frontier-source | TITAN Frontier Source（0 票） | skip | 2026-09-07 | 低票 |
| tokenjunkielabs/tokenjunkielabs-farm-manager | Farm Manager（0 票） | skip | 2026-09-07 | 低票 |
| muelsyse111/kaggriculture-exp006-independent-baseline-audit | EXP006 Baseline Audit（0 票） | skip | 2026-09-07 | 低票 |
| muelsyse111/kaggriculture-crop-timing-and-labor-budget | Crop Timing and Labor Budget（0 票） | skip | 2026-09-07 | 低票 |
| az05192000gmailcom/kaggriculture-from-orders-to-actual-trades | From Orders to Actual Trades（1 票） | skip | 2026-09-07 | 低票 |
| hank0123/kaggriculture-is-your-agent-really-better | Is Your Agent Really Better（0 票） | skip | 2026-09-07 | 低票评测方法帖 |
| serariagomes/kaggriculture-rule-based-agent | Rule-based Agent（0 票） | skip | 2026-09-07 | 低票 |
| holeneckles/grandmaster | Grandmaster（0 票） | skip | 2026-09-07 | 无信息 |
| paiky1995/inside-the-kaggriculture-market-machine | Market Machine（1 票） | skip | 2026-09-07 | 低票 |

### 二.35-40(2026-09-09 全局调研增量,要点版)

- **35. zhincez「重放他人带=88%」(定量分水岭)**:96% 对手是 tape;重放只回收其主人分数的 88.4%(同带自打 100% 相似仍丢 15%——"当带主"值 12%,不可复制);最强带主 2914.5×0.88≈2576 < 金牌 2746 → **抄带全家封顶金牌线下**。另:商店抽取与杂草共用 RNG,同 seed 两跑可落不同商店(钉对手才能对照)。"Score in coins, not wins."
- **36. rogerrogerroger3r「最强玩家的带重放最差」**:16 条 2970-3074 带同底盘 4000 局对测,rank1 带 diff -22k~-25k,最优带来自第二弱 agent——强玩家的分在"带主另一半"。
- **37. starkhushi「6 引擎陷阱实测」**:①种植日即未浇日(当晚枯);②一次性作物 yield 仅在浇水窗口 [ceil(myd/2),myd] 内 +1/浇(施肥+2)——wheat 可达 4 非 6;③顶格收 +33%(age3 收麦 2 单位/茬);④过期悬崖(lifespan=种日+myd+1,过期每 2 步掉 1 单位);⑤肥仅浇水日生效(+67%);⑥shed 非 tile/LOCKED 可走不可作/FEED 耗执行者随身麦;雇佣 6 人 $20/8 人 $54/10 人 $143。
- **38. yhay81 Shop Router 0908(fork 实测 2715.6)**:4 带+2 决策点(step144 看 YARN 计数、step648 看 EGG 库存,深度 1 树);**工艺核心=马赛克拼接**:1326 局公开史→1313 唯一序列→抽强 1 天/3 天段在拂晓边界拼接→2100 万次候选-对局比较精修(最后只调尾盘卖量/序);75 维命名特征;降级协议(异常保持当前带)。作者自认 tape-对手模拟对自适应对手失真。
- **39. dmitrii 三部曲**:①Last-Mile Planner:710-718 步收尾搜索(unit_model.py=引擎逐字提取的精确单步模拟器,独立可复用;dominance 接受准则),对无漏损父策略仅 +4.9/+1.8 金;②What We Learned 16 条(账面羊修复 +6833、末小时孤牛 +4513、死单 -80/局、多产 2 羊毛亏 45 的机会成本、同码四提交 2183→1811);③Cow Placement 2531:BUILD→PLACE 两步事务摆位修复 + 尾盘 _AM_CONFIG 全参数(保留梯度/价格门 0.66/棚压 72/88/近镜像守卫);附 **Thomas 93.8% 完整 5 带族+树(Apache-2.0,tapes.json 598KB)**。
- **40. 论坛 RL 现状**:端到端 RL 最好公开成绩 80k 终端现金(JAX 10k SPS,数十亿步,PPO+自博弈联赛)仍距 top 甚远;340M 步 90k vs 静态带 122k 未追平;共识=混合架构(确定性执行器+宏决策)。「三层大脑」帖:执行层应为多日任务承诺链而非逐步贪心。BC 高帧精度但实战低一个量级(719 步复合漂移)。
