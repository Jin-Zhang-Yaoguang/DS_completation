# 公开方案与社区讨论调研 — Kaggriculture

> 首次全量调研时间：2026-09-01。方法：用 Kaggle API 拉取本赛题 Code 区全部 228 个公开 notebook 的元数据（按
> `scoreDescending` / `voteCount` / `dateCreated` / `hotness` 四种排序合并去重），拉取其中 60 份源码（11 份逐要素精读、49 份结构速览）；
> 同时用 `kaggle competitions topics/topic-messages` 拉取讨论区全部 139 个主题及其全部楼层（约 32 万字符）并通读。
> 目的：搞清楚"社区到底在用什么方案、什么被证伪了、评测口径要求我们优化什么"，为本项目的方案选型提供依据。
> 本文只写调研所得，不与本项目现状做对比；行动项另记在 `model/experiments.md`。

## 更新日志

| 日期 | 内容 | 一句话结论 |
| --- | --- | --- |
| 2026-09-01 | 首次全量：228 notebook 元数据 + 60 份源码（11 精读 / 49 速览）+ 139 个讨论主题全文 | 公开榜是"replay 复刻 + 市场时序微调"的单一生态；RL/BC 在社区被反复证伪；真正的竞争面已从"种什么"移到"什么时候卖" |

---

## 一、公开榜格局

### 1.1 排行榜快照（2026-09-01 台北时间中午）

| 名次 | 队伍 | 评分 |
| ---: | --- | ---: |
| 1 | tetsuya | 2940.0 |
| 2 | OceanMix | 2885.7 |
| 3 | Crop Dusta | 2878.6 |
| 4 | Driz Lo | 2840.8 |
| 5 | QQ Farming | 2839.4 |
| 10 | Mc10nys0n | 2775.2 |
| 20 | Saravanan Jaichandaran | 2717.1 |

**Top-20 挤在 2717–2940 的 220 分带内。** 多个讨论帖（`736219`、`734000`、`737955`）一致指出：
这个带宽小于评级噪声本身，名次日内变动大多不是强度变化。

### 1.2 方案类型 × 分数段

| 类型 | 代表 | 公开自报强度 | 在榜占比（社区实测） |
| --- | --- | --- | --- |
| 官方教程 melon_maxxer | `bovard/kaggriculture-getting-started`（895 票） | ~3.5k 金币，评级最低档 | 大量新手起点 |
| 手写启发式（原创、无 replay） | `romanrozen/strong-barnyard-economist`、`ektarr/diversified-scheduler-baseline` | 1.5k–2.2k 评级 | 少数 |
| **replay 复刻 + 执行保护（当前 meta）** | `boatlee/V16-RC5`（303 票）、`kaitofukami/v27`（181 票）、`tetsutani/adaptive-farming`（140 票）、`indarkarhana/shape-the-shop` | 本地 140k–190k 金币；公开榜 2600–3100 | **压倒性多数** |
| 市场时序微调层（叠加在复刻之上） | `romantamrazov/Hamburger`（129 票）、boatlee 的 premium market lead | 相对母体 +1.7k~+3.2k margin | 与上一类高度重叠 |
| 分析/工具类（不含强 agent） | `raykkretzschmar/rank-your-agent`、`georgymamarin/visualized`、`destbreso` 系列、`nikital7/4000x-speedup` | — | 提供评测基建 |
| RL / BC | `xishengfeng/rl-v9`、讨论区多帖 | 自博弈 20k–80k 金币，**未进入 Top** | 极少数 |

**关键事实：整个 Top-30 的开局已经收敛到同一个先验。** `kaitofukami/v27` 冻结时统计 Top-30 的 Day-0 签名：
26/30 队共用 `1 COW + 4 SHEEP + 5/5 seed + WHEAT 5` 核心，只在 `HIRE4`（14 队）与 `HIRE5`（12 队）上分叉。
更早期 `raykkretzschmar` 在 8 月 9 日下载 Top-20 各 10 场共 200 个 replay，**单个 field hash 出现在 40 支队伍的 144 场里**，
排名 3–20 的 field 动作 99–100% 相同。讨论帖 `732902` 有人实测 Top 的**第 1–51 回合在 13 个 player-instance、8 个不同 seed 下逐字节相同**。

---

## 二、逐个方案分析

### ⭐ 2.1 `raykkretzschmar/kaggriculture-findings-from-zero-to-top-meta`（157 票）— 全站信息量最高的一份

这是一份"replay 猎取日志"，从 c14 一路记到 C92，每一步都带消融证据。**它本身就是本赛题的方法论教科书。**

**流程（可直接复用）**：下载当前榜首 replay → 找出跨对手重复出现的动作序列 → 蒸馏成本地 agent →
双席位对打上一版 → 大部分候选被否决 → 冻结胜者 → 在更晚的 episode 上复测。

**三条采信 replay 的前置检查**（避免把噪声当策略）：
1. 同一套 field schedule 是否对多个不同对手都出现？
2. market schedule 是否也稳定，还是在对局中反应？
3. 蒸馏出的 tape 是否在**双席位**上打赢上一版？

**版本演进与每步的净收益**：

| 版本 | 改动 | 证据 |
| --- | --- | --- |
| c14 | 选一份跨对手重复的完整 schedule + 终局 8 回合清理 | 对 c11/c12/c13 各 27-3；独立 ladder 跑到 2182.2 |
| c15 | 加 Hamburger 的"克隆前抢一回合卖 premium" | 对无 wrapper 的同源 tape 14-2 |
| c16 | 十队 refresh 后换成收敛后的更强 base | 与另一份同 meta tape 对打 7-7-2（说明两者是同一策略） |
| c18 | **field 完全不动，只换 premium 清算的市场时序** | 对 c16 在 20 seed 双席位 35-5，均值 margin +3161；相对 c16 只改 20 个 field 回合但改了 112 个 market 回合 |
| c27 | 终局控制器接管点从 step 712 推迟到 717 | 全新 10 seed 双席位 90-10 |
| c45 | premium 卖出提前 2 回合并记账扣减后续量 | 上榜 3085.4，排名 9 |
| 否决 | 固定 horizon 25 | 内部 gate 赢，但对 C45 与未改动 V14 在新 seed 上 0-6 |
| c68 | 换 THUNDER field tape + **在线推断对手抢跑 horizon（1–6，默认 4）** | 最终 block 342-18 零错误 |
| c71 | 保留路线族，只换市场轨迹 + 按自身价格冲击排序 premium SELL | 对 C70 31-9；广义 holdout BT 1996 vs 1953 |
| c72 | 只在"携带 ≥2000 金币 premium 且距 shed ≤1 步"时打断物流去入库 | 109-11 / 29-11 / 27-13；阈值 500、1000 与两步版本全部 0-8 落败 |
| C90–C92 | 杂草修复三段式（见下） | C92 对 C91 100 局 22-6-72 |

**杂草修复的三级递进（这是很少被讲清的一段）**：
- **C90**：只有当某工人当天剩余动作全是 `PASS`、身上空手、且时间够走过去 `DIG` 时才去除草。→ 30 seed 双席位对 C89 16-14-30（+234）。
- **C91**：追加"未来确实会用到该地块"的守卫。→ 100 局与 C90 17-17-66，均值 −35.2，**经济上中性**，只改善因果纪律。
- **C92**：检测"工人已到位但 `BUILD_PASTURE`/`PLANT`/`PLACE` 因杂草失败"，替换成 `DIG`，只把该工人路线顺延一回合，
  用下一个 `PASS` 吸收延迟。→ 在 DePie 的固定 tape、seed `247063490` 上把 **−7,288 的败局变成 +3,455 的胜局**；
  关掉杂草时 C91/C92 完全打平（证明 overlay 是休眠的）。

**它列出的高频 bug 表**（对写 agent 极有价值）：

| bug | 症状 | 修复 |
| --- | --- | --- |
| CARE 优先级排在 melon WATER 之上 | 第 9 天只浇了部分地，产量 ~70 而非 ~96 | age 6–12 内 WATER 优先 |
| HARVEST 后不 DROP | 产物卡在单位随身库存，IPO 缺资金 | 携带 melon/milk 堆时回 shed DROP |
| 过早把 melon 地挖成 pasture | 毁掉未收的果实 | 保护到卖出为止 |
| Day 0 买一堆牛却没留饲料钱 | 第 2 天动物逃走 | 买动物前预留 wheat 现金 |
| 永远固定 10 头牛 | 镜像局双方银行一起塌到 ~40k | 加羊/草莓/对手路由 |
| 只优化对 starter 的平均金币 | 本地分高、Elo 平庸 | 双席位打强 bot |
| 两个几乎相同的活跃提交 | meta 一变两个一起死 | 第二个 slot 要分散 |

**本地评测协议（10 步）**：编译打包后的 exact `main.py` → 自博弈必须双 DONE → 在**不相交的 seed、双席位**上打
incumbent 和 unmodified parent → **输给任一方即一票否决**（哪怕总胜场好看）→ 加入几个真正不同的公开 field family →
报告逐对手战绩而非聚合 → 冻结全部参数后跑一个未用过的 seed block → 审计现金/喂食/动物存活/仓容/运行时 → 保留全部结果含败局 → 才打包。

---

### ⭐ 2.2 `kaitofukami` 系列（v21.1 / v27 / v43 / v48 / v58，99–181 票）— "同开局、换续盘"

**v27 的核心论点**：主导开局没有失效，失效的是它**过时的续盘**。v27 保留完全相同的 HIRE4 Day-0 队列，
第一处 market 差异出现在 **step 161**，第一处 farmer/hands 差异在 **step 170**，719 步总距离 634。
计划量的变化：买入 WHEAT 380→360，卖出 MILK 218→241，卖出 FERTILIZER 245→235，SELL 单数 171→168。

**两个可迁移的判断**：
1. **"当前评级低"≠"胜率低"**。v26 在自己的公开战绩里是 87/90（最近 20 场 20/20，均值 margin +18,415），
   但对**新的对手分布**冻结重测只有 14/27。历史战绩与当前反事实鲁棒性回答的是两个不同问题。
2. **席位路由器被否决**：内部分数更高的 "Nikita seat0 + Ezz seat1" 只修好 3 个真实败局中的 1 个，
   而固定 Ezz 路线 3/3 全修好且 outer margin 更高（+9,591 vs +9,212）。→ 删掉席位分支而不是再加一个专家。

v58 标题为 "Minimax Closed Loop"，v48 为 "Fast Routes"，同一作者持续用"冻结 → 反事实回放 → 只改一处"的方式迭代。

---

### ⭐ 2.3 `boatlee/V16-RC5`（303 票，Code 区第 2 高票）— 最干净的"复刻 + 一回合抢跑"模板

- **生产路线**：从 Nikita Lugovoy 提交 `55440039` 的 3 个公开 replay（episodes `92165990`/`92185587`/`92223213`）
  逐步取**多数动作**重建。三场的 field schedule 完全一致，market schedule 99.91% 一致。
- 路线内容：解锁 3 个象限；立即 4 `SHEEP`，到 step 192 达 8 `COW`；WHEAT + STRAWBERRY + MELON 混种；
  每日协调 HIRE/FEED/CARE/收获/肥料；产物以 premium 波次释放。
- **执行修复**：动作列表按当前 hand 数对齐；当 `WEED` 挡住计划中的 `PLANT` 或 `BUILD_PASTURE` 时就地修复。
- **premium market lead**：对 MELON/MILK/STRAWBERRY/WOOL，若本回合无对应城镇需求且 shed 存量足够，
  就把**下一回合**的部分卖单提前到本回合执行，并从原单中扣除等量。两回合总量不变，只改执行时间。
- 本地成绩：对重建核心 30 seed 双席位 **60/60**，30 组配对全为正。

后续 `V20-Adaptive-R1`、`V21-R1 Public-State Route Portfolio` 转向"用公开状态在多条路线间选路"。

---

### 2.4 `tetsutani/adaptive-farming-strategy`（140 票）— 用开局商店需求选整季路线

架构是**四层**：
1. **OPENING SIGNAL**：读最早解锁的 1–3 个商店；
2. **ROUTE SELECTOR**：在 yarn-first / yarn-second / yarn-third / milk-support / generalist **五条完整 720 回合路线**中选一条；
3. **RUNTIME GUARDS**：杂草修复、市场时序位移、仓容压力、窄口径反制；
4. **DEADLINE**：保护 shed 余量 + 终局清算。

明确写出的设计信条："**先读需求选定一个连贯的农场，然后保卫执行，而不是每回合重新规划。**"
它也提示了 1.32.6 之后的规则变化：Town Center 改成每日各买 1 个且不再有倍率；商店**有放回抽样**，
所以可能出现重复商店，必须读实时 `unlocked_shops` 而不是假设一个均衡的城镇。

### 2.5 `romantamrazov/Hamburger`（129 票）— 终局时序的两个硬事实

- **官方解释器处理 step 718 后就把 episode 标记 DONE，index 719 的动作不会执行。** V27 因此把终局路由与清算集中在 716–718。
- 候选分支被逐一消融：精确锚点 / 关闭现金流排序 / 仅在既有 SELL 槽内做静态或防撞重排 / 防撞 SELL 前置 /
  716 或 717 起的终局库存接力 / 组合。**终局接力只覆盖那些无法完成入库的终局 PASS/PLACE/DROP 动作。**
- 推广规则：若没有候选在不降低胜场与鲁棒下限的前提下严格提高广义平均金币，就打包**原样基线**。

### 2.6 `indarkarhana/shape-the-shop-work-the-pasture`（86 票，自报 Top 10）

在完整农场程序之上的**分层可见状态规则网络**，两个连接起来的生产决策：
1. 在不改变路线几何、动物数量、卖单槽的前提下，把守恒的 cow/sheep 牧场包**按可见的奶/毛需求重新贴标签**；
2. 在一个引擎校验过的检查点上，多买一头需求对齐的动物 + 一个 hand，用受保护的 pickup/NORTH/PLACE 序列放进已服务的空牧场。
   任何几何、库存、容量、现金不匹配都 **fail closed 回退到母体**。

它同时给了一份很规范的验证披露：`kaggle-environments==1.32.7`、双席位、预登记 seed block、
最新三档 gate 24-6/27-3/27-3、九族群审计最弱 seed 得分 .817、最差 10% CVaR −$8,854、
冻结后对当前 Top 十队 136-14（双席位均 .907）、平均策略运行时 **0.492 ms/次调用**。

### 2.7 `pilkwang/kaggriculture-structured-economic-policy`（97 票）— 唯一把因果账本写成数学的

- 目标写成 $\max_\pi E[B_T^{(p)} - B_T^{(1-p)}]$，三条不变式：**不可逆损失优先于可选增长；field 承诺优先于 market 承诺；
  每个承诺必须终局可行（成熟、收获、返回、卖出都要塞进 T 之前）。**
- **同回合因果**：一个回合内 field 先于 market 结算，即 $s^{post} = M(F(s,a^F), a^M)$。
  所以**同回合 DROP 的货可以同回合卖掉**；反过来**同回合的卖出所得不能给已经结算的种植/喂食/浇水买单**：$B_t^F = B_t$。
  市场规划里用 $B_t^M = B_t + 0.85\sum \hat R_t(s) - \sum \bar c_t(b)$（对预期收入打 0.85 折、对成本取上界）。
- 作物价值：$V_c(t) = \Pr(\text{服务完成}) \cdot y_c \hat p_c(t+g_c) - s_c - \lambda_W w_c - \lambda_L g_c$，
  其中 $\lambda_W$、$\lambda_L$ 是劳动与土地的影子价格；只有在 $t + 24 g_c + \tau^{harvest} + \tau^{return} < T$ 时才允许种。

### 2.8 `flexonafft/kaggriculture-multi-route-farming-agent`（86 票）

方法一句话：**用早期解锁商店顺序在 yarn-led / milk-supported / balanced 三条固定 replay 路线中自选一条**，
没有额外 gate、组合强制或事后 overlay。是"路线选择器"这一类最精简的公开实现。

### 2.9 `bovard/kaggriculture-getting-started`（895 票）— 官方基线与它的四个已知缺陷

`melon_maxxer`：缺种子就买 → 走到最近空地种 melon → 站在自己的 melon 上就浇水/成熟就收 → 价格 ≥200 才卖 → 收入滚回买种。
官方自己列出的问题：**从不雇人也不买地（一个农民一个象限）；只种 melon；从不施肥；卖出时一次性倾倒整个库存，
在成交过程中就把价格砸到阈值以下。** 这四条恰好定义了 baseline 应该修的第一批东西。

### 2.10 分析/工具类（不给 agent，但给了整套基建）

| notebook | 提供了什么 |
| --- | --- |
| `raykkretzschmar/kaggriculture-rank-your-agent`（104 票） | **十个有文档的参考 agent 组成的固定天梯**（tier 0–5 是从零手写、共用逐字节相同的调度器，只有顶部 `POLICY` dict 不同 —— 差异因此**只来自经济决策**），加上打赢这十个的 top-meta agent；席位交换的循环赛 + **Bradley-Terry** 排名（与官方最终口径一致）；直接产出可提交的 `submission.tar.gz`。数据集：`raykkretzschmar/kaggriculture-reference-agents`。**它还专门警告：`importlib.metadata.version()` 读的是新写入的包元数据，而 `import kaggle_environments` 可能仍解析到 `sys.path` 上更早的旧副本 —— 必须用"回放一场已知对局并断言银行数到分不差"的行为性 fixture 来验证引擎版本。** |
| `georgymamarin/kaggriculture-visualized-what-every-crop-pays`（87 票） | 每种作物/动物的付费曲线可视化；商店抽签分布；melon 的六格实测 |
| `busyaprime/what-actually-wins-on-the-kaggriculture-ladder`（26 票） | 从当日 replay 现算 meta：**赢家和输家的动作计数几乎一样**（赢家甚至种得更少），差别在种什么和跑得多有效率；并拟合出**天梯已经见顶回落**，复刻当前 meta 的收益在下降 |
| `nikital7/4000x-environment-speedup`（25 票） | 环境加速；讨论区另有人报 CUDA 版 1024 并行环境 5 万 transition/s、Rust 版单二进制回放 4000 场 |
| `destbreso` 系列（`X-ray your agent`、`A DNA Test for Agents`、`A Field Guide to Replay Agents`、`Rating convergence`、`The Farm Day as a Routing Problem`、`How much money is in this game?`） | 指纹识别 agent 血统；replay agent 判别；评级收敛的 episode 数而非小时数；把农场日建模成路由问题；全局金钱上限 |
| `nekkon/strawberry-pays-24x-what-the-price-table-says` | 价格表排序与真实价值相反的推导（见第三节） |
| `revanthtambisetty/two-private-bots-beating-kaggriculture-meta`（14 票） | 8 月 9 日 Top-5 中三队开局逐字节相同（公开参考 agent），把 ELO 带钉死在 3117–3131；上面两队不匹配任何已知 notebook |
| `xreina8/wins-not-money`（讨论中引用） | 论证目标函数应为 $\Pr[\text{win}] = \Phi(\mu/\sigma)$ 而非期望 margin，对公开 episode 拟合 MAE 0.068 |

### 2.11 原创（非 replay 复刻）的公开基线 —— 数量少但对我们最有参考价值

| notebook | 做法 |
| --- | --- |
| `ektarr/diversified-scheduler-baseline-kaggriculture`（18 票） | 无依赖的 `main.py`：**每天雇便宜临时工、给每个单位分配唯一的农场任务、保护作物不漏浇、把初始 5×5 分散种植**以降低对共享市场价格崩盘的暴露 |
| `premaananda108/economics-driven-rule-agent-ecobot-v7-arena`（36 票） | 完全反应式：每回合从 `obs` 用宏观经济公式和真正的路由求解器**现算**雇佣、交易、种植、派工；只有季节截止（生长窗口、清算日）和少量储备/阈值常数是固定的 |
| `pavloivanin/kaggriculture-baseline`（18 票） | 动态价格地板守卫（市场过剩时禁止倾销 melon/strawberry）、跟踪 `town.unlocked_shops` 调整卖出排期、按进度动态雇工 |
| `koushikkumardinda/kaggriculture-starter`（28 票） | 把 meta 的要点写成教学版：**对齐 4 回合商店需求窗卖货**、预算 Fibonacci 雇佣曲线并保证 $2,000 流动性缓冲 |
| `romanrozen/strong-barnyard-economist`（61 票） | melon 时机 + "job value"（任务价值）框架，被 `raykkretzschmar` 引为方法来源之一 |
| `yhay81/fieldbook-commit-for-three-days`（26 票） | 一句话哲学：**"计划保持三天，只在商店解锁时重新考虑"**——observe once → choose a chunk → ignore weak noise |

### 2.12 一个值得记住的失败案例

`kaitofukami/v48` 的开篇：**v47 的线上产物完全没有下棋 —— 11 场记录对局全部以恰好 3,000 结束，动作流里没有一个非 `PASS` 动作。**
本地看起来正常的 agent 在线上可能因为打包/执行路径问题彻底静默失效。
这也解释了为什么社区标准做法是：**打包后重新导入 exact `main.py` 做冒烟测试**，并检查动作流里非 PASS 的比例。

### 2.13 本地评测的算力现实

- 官方 Python 环境约 **1.2 episode/秒**（`nikital7`）。一次"几百 seed × 双席位 × 若干对手"的正经对比就是几千局。
- 因此社区出现了三条加速路线：C++ 重写（`nikital7`，自报 4000x）、CUDA 批量（讨论区自报 1024 并行环境、5 万 transition/s @ RTX 5090）、
  Rust 单二进制（有人把 4000 场天梯局跑通并验证与官方环境逐位一致）。
- `indarkarhana` 披露其策略平均运行时 **0.492 ms/次调用**，远低于 1 秒软预算 —— 说明当前 meta 完全不受时限约束，
  时限只在做在线搜索/神经网络推理时才成为问题。


---

## 三、社区共识配方

以下条目都经过至少两个独立来源交叉验证（讨论帖 + notebook，或两位作者互相复现）。

### 3.1 引擎事实（文档与引擎冲突时以引擎为准 —— 主办方已确认）

讨论帖 `732450` 列出的差异，主办方 `bovard` 逐条确认并改了文档：

| 项 | 引擎真实行为 |
| --- | --- |
| CARE 奖励 | `pending_care_bonus` 每天 **+1**（不是 +2），且只在"当天喂了且照料了"才累积，只在"喂了的产出日"兑现 |
| 卖化肥 | **可以卖**（`SELL FERTILIZER` 合法） |
| DIG | 只对**空**结构生效；有动物的地块 DIG 无效 |
| 种植日浇水 | 新种的作物 `consecutive_unwatered` 初始为 **1**，当天不浇当晚就变杂草 |
| Melon 奖励窗 | age 10 就到 6 上限，文档写的 12 天里最后两天是死回合 |
| Strawberry | **不是无限产**：在 age 10/12/14/16 各产 1，共 4 次后死亡 |
| Shed | 不是 tile，`tiles` 数组里搜不到；接入点严格是 4 个中心格 **(4,4)、(5,4)、(4,5)、(5,5)** |
| `obs["step"]` | seat 1 的**序列化** observation 里恒为 `None`（live `env.run()` 里是对的，见 `737545` 的更正与致歉）。**社区共识的家规：任何地方都不要读 `obs["step"]`，一律用 `day * turnsPerDay + hour`** —— 这样在 live 对局、replay 分析、`env.step()` 自建 harness 三种场景下同一份代码都正确 |
| 最后一个动作 | **step 718 会执行，index 719 不会**（Hamburger 发现，多方复现） |
| 市场订单 | 不需要站在 shed 接入格也能执行；**按列表 index 逐单位并发结算**，所以给同一次购买供资的卖单必须排在更低的 index |
| 同回合因果 | field 先于 market：同回合 DROP 的货能同回合卖；同回合卖的钱不能给已结算的 field 动作买单 |
| 回合时限 | `actTimeout = 1` 秒软预算 + 每 episode 60 秒 overage 池（首回合模型加载要从这里出）+ 整局硬上限 1200 秒 |
| 商店 | 1.32.6 起**有放回抽样**（可能 2 个 Donut、0 个 Yarn）；Town Center 改为每日各买 1 个、不再加倍 |
| 杂草 RNG | `_end_of_day` 用 `random.Random((seed*1_000_003) ^ day)`，**先给两名玩家喷杂草（每块空地消耗一次 `rng.random()`）再抽商店** —— 所以商店抽签受双方空地数影响 |

### 3.2 经济学共识

**价格表的排序与真实价值几乎相反**（`nekkon` 推导，`destbreso` 独立复现同样的九个数）。
产品有两个价值，取决于卖进"城镇挖出的坑"还是砸进未被消耗的市场：

| 产品 | base | 整季城镇吃掉 | 卖进坑里 | 平铺倾倒 |
| --- | ---: | ---: | ---: | ---: |
| STRAWBERRY | 120 | 426 | $100,445 | $4,173 |
| MILK | 160 | 327 | $86,662 | $6,432 |
| WOOL | 200 | 228 | $54,340 | $8,097 |
| WHEAT | 25 | 525 | $21,152 | $10,813 |
| TOMATO | 60 | 228 | $16,812 | $7,861 |
| CARROT | 35 | 327 | $13,246 | $6,904 |
| EGG | 50 | 228 | $12,972 | $9,658 |
| MELON | 250 | 30 | $8,184 | $7,416 |

- **草莓晚卖比早卖值 24 倍**，是全场最大的市场；**甜瓜是最贵的商品却是最小的市场**（8 个商店菜单里一个都不收 melon，
  整季只有城镇中心每天 1 个 = 30 个）。
- **动物按地块碾压作物**：按边际收入贪心分配地块，**前 15 格全是牛和羊**，melon 大约在第 16 格进入，
  strawberry 在 100 格里只值约 13 格。"草莓是最好的卖品，却是平庸的种植品。"
- **肥料被系统性低估约 3 倍**：`_daily_refresh_animals` 对每头存活动物**无论是否喂过**每天都置 `fertilizer_available = True`，
  且不累积。这条流一季约值 $2,900，而动物本身命名的产品（奶/蛋/毛）只值 $1,300–1,760。
  但肥料是**唯一城镇需求为 0** 的产品（没有坑可以卖），只能走 glut 分支约 $98/单位并缓慢衰减 —— 它是低方差收入，产品是高方差收入。
- **1.32.7 的 hinge 改动**（CARROT/TOMATO/EGG 的 scarcity 分支改为 `linear` 到拐点 T 后加 `8.0*(scarcity/T-1)^2`）：
  实测触发率 tomato 55.0% / carrot 28.3% / egg 25.8%（主办方声称 50/26/22）。但**中位数局几乎没变**：
  carrot 中位 1.35x、p90 2.00x、最深的一局才 9.56x；tomato 中位 1.00x（到分不差）、p90 1.98x；egg 中位/p75/p90 = 1.00/1.00/1.06x。
  原因是三者的拐点对比整季城镇需求：CARROT 拐点 450 vs 需求 327（**够不到**）、TOMATO 200 vs 228（**刚好越过**）、EGG 332 vs 228（**够不到**）。
  **真正让 carrot 涨价的不是 hinge，而是公告里没提的 `below_target` 0.20 → 1.00**（在拐点以下就抬高了整条曲线：
  scarcity 327 时 $41 → $65 靠的是 below_target，hinge 本身反而 −$1）。
- **场上的反应是"重新提交"而非"自适应"**：patch 后 carrot 种植率从 6.3% → 44.2% 的席位局，
  但 332 个跨两窗口的提交中**零个**翻转过是否种 carrot（冻结的代码就是冻结的）；新提交里 60% 种 carrot，旧的只有 12%。
  且**银行余额是诚实的零结果**：723 支跨窗口队伍的配对 delta 只有 +610 金币（373 升 350 降，p=0.41）。
- **动作才是真正的约束，不是土地也不是钱。** 每单位每回合一个动作，市场每回合最多 10 单 —— 买卖近乎免费，种/浇/收不是。
  按"每农民动作利润"排序：melon 142 > 羊毛(每日 CARE) 100 > 牛奶(每日 CARE) 79 > 牛奶(只喂) 35 > 羊毛(只喂) 32 >
  蛋(CARE) 28 > 草莓 27 > 蛋(只喂) 18 > 番茄 17 ≈ 胡萝卜 17 > 小麦 15。
  **每日 CARE 把羊从 32 抬到 100**，是全场最大的杠杆之一。
- **走路是最大的浪费**：某作者第一版 agent **83% 的单位回合花在移动**上（因为每回合重算每个 hand 的目标导致来回震荡）；
  改成"先做完脚下这块地再移动"（FEED/CARE/HARVEST/COLLECT_FERTILIZER 都在同一格完成）后降到 55%，**最终银行约翻三倍**。
  另一位在紧凑单农民六格布局下测得 32.8% 移动 + 16.3% PASS，认为 **1/3 是移动占比的地板**。
- **劳动力不是约束**：`HIRE` 成本 fib(n) 且每天早上重置，**10 个 hand 全天只要 $143** 换 230 个额外动作。
  欠雇通常比在便宜的 Fibonacci 区间内过雇更贵。
- **第 4 象限（SE，$4000）几乎没人买**：额外 hand 的 fib 成本、更长的通勤、更晚的投产使 ROI 不成立。
  Top 常见是 NE + SW 两块。`raykkretzschmar` 的第四象限实验是明确的负结果（C93）。
- **全 melon 开局会破产**：melon $80/格、day 10 前零回报，铺 25 格就吃掉 3000 本金的 2/3，
  然后雇不起人、一个农民浇不完 25 株，全田枯死 —— 实测终局 18 金币。
  **wheat 从 day 2 就付钱，是正确的引导资产**；同一份代码：全 melon 18 / 抄 replay 的畜牧优先 2,687 / wheat 引导→melon **15,394**（内置 starter ≈3,500）。
  但在只有六格的小规模下，melon 版比 carrot 版多赚 +11,665（8 seed 全胜）—— **"最小的市场"和"最差的作物"不是一回事**，取决于规模。
- **羊毛是唯一只有一个商店（YARN_STORE）收的产品**，而商店有放回抽 8 次 → **34% 的赛季完全没有羊毛买家**。
  用市场模型对 500 个采样城镇定价三种单一畜群：有 yarn store 时羊群季中位 ~$39k，没有时 ~$11k；牛群在 70% 的城镇里排第一。
- **全局金钱上限**：由城镇 drain 表可推出封闭形式的整季双方金钱上限，中位需求下约 **$703k**；
  32,570 场公开 episode 中无一超过，最好的一场只拿到 48%。**"市场的支付意愿"不是瓶颈，执行才是。**

### 3.3 评测口径共识（决定优化目标）

- **评级只看胜/负/平，不看金币差额。** 一个 140k 却输掉的对局照样掉分。
- **新提交从 600 起，约 60 局（前 4–5 小时，约 15 局/小时）后收敛到 ~90%**，之后转为 1–2 局/小时，
  分数只按 $\mu(n) \approx a + b\ln n$ 缓慢爬升（每 100 局约 +50–70），残差噪声 ±25–50。**50 分以内的差异是噪声。**
- **路径依赖极强**：有人提交两个**逐字节相同**的 agent，相差两小时，一个 ~1700、一个 >3000（差 1400 分）；
  另一位报差 300。早期一场败局（哪怕只是自己这边随机长了根杂草）会让后续爬升极慢。
- **重复提交同一个 bot 换运气**：在 96 局判读时期望约 +40 分，200 局 +25，收敛后 +10–15，**且完全不会进入最终排名**。
  代价是丢掉一条已收敛的轨迹。
- **最终排名是重新算的**：截止后继续跑约两周，用 **Bradley-Terry** 在这些 episode 上重拟合。
  主办方补充确认：**BT 用整个比赛期间"两个仍然活跃的 agent 之间"的全部 episode；
  与已停用 agent 打的那些不计入 —— 双方都必须仍然活跃。**
- 因此**截止日需要的只有两个最强、无错误的提交**，不要在最后一刻推未测过的代码（报错的 agent 一场都不打）。
- **离线评估要对齐这个口径**：按"对每个强对手的胜率"判断，而不是聚合平均；
  一个平均多赚 3k 但把对 #2 的两场胜局变成败局的改动，在天梯上是亏的。
- **同一 seed 不等于同一城镇**：改动只要动了地块占用数就会改变商店抽签。实测：只重排市场订单 → 16/16 seed 同城镇、配对 sd=1；
  少雇一个 hand → **0/16 seed 同城镇**、配对 sd=1,322，要检出 +342 的效应需要约 77 个 seed。
  规则窄化为：**当改动不可能改变地块占用时，固定 seed 才是真正的对照。**
  实践对策：本地把杂草与商店拆成两条 RNG 流，或强制钉住商店解锁序列。

### 3.4 关于 RL / BC —— 社区反复证伪的方向

这是讨论区体量最大的一条线（`734952` 28 楼、`736567` 29 楼、`738079` 15 楼、`736439`、`736917`、`737937`、`738619`、`738325`）。
**截至 2026-09-01，没有任何一个自报 Top 名次的方案是端到端 RL/BC；多位 Top 选手明说自己是纯启发式。**

已公开的量化结果：

| 作者/来源 | 方法 | 自博弈终局金币 |
| --- | --- | --- |
| 规则型公开 notebook | 启发式 | **140k–190k** |
| `738619` | 纯 PPO + JAX（10k SPS，全动作空间，warm-up 用启发式 trace 到 7% 动作一致） | **80k**（撞墙） |
| `736567` msg28 | BC + end2end RL | 75k |
| `738079` msg6 | BC | 80k |
| `734952` msg28 | JAX + TPU 完全自博弈 | 20–22k |
| `734952` msg4 / msg2 | PPO | 20k / <5k |
| `738325` | PPO（JAX 向量化） | 2–3k，mean return 近零 |
| `734952` msg5 | 双策略 RL（worker + trading） | $100–3,000 |

被反复独立复现的失败机理：
1. **模仿本身就已经失败，而模仿是简单版本**：在强 replay 的 held-out 帧上拿到很高的 next-action 准确率，
   实际下场却比被克隆的轨迹低一个数量级。**719 步的复合误差**：一步错就进入训练分布从未覆盖的状态。
   （有人做到近 100% 离线准确率，去掉 teacher forcing 后**整局 PASS**，最后发现是验证目标信息通过中间表示泄漏回预测。）
2. **动作空间是组合的、不是扁平的**：每回合一个 farmer 动词 + 十几个 hand 动词 + 至多 10 个市场单。
   拆成 per-unit heads 会破坏最关键的耦合 —— **市场单按 list index 结算，给购买供资的卖单必须排在更低的 index**；
   独立 head 无法保序，一旦破坏购买静默失败，后面每一步都在对一个与计划不符的农场执行。
3. **信用分配**：719 步 × 十几个单位，奖励只在最后到达。
4. **稀疏 reward → 局部最优**：多人独立得到"极其高效的 melon 农场"这一个吸引子。
5. **样本稀缺 + 多模态**：每日 replay 数据不够，且引擎频繁打补丁；replay 的**有效行为多样性远小于 replay 数量**
   （很多是同一份公开 tape 的克隆），模型在 OOD 状态上表现很差。
6. **非传递性**：实测六个公开策略、16 seed、双席位共 960 局，存在明确的克制环
   （Public B85 胜 Andrews2883 30-2，Andrews2883 胜 Kaito v35 21-11，Kaito v35 胜 Public B85 24-8）。
   Adaptive Farming 总胜 121/160 却仍被 Kaito v35 以 17-15 压制 —— **成对支付矩阵比平均胜率更有信息量**。
   PPO 在"开局必须先于识别对手做出"时会产生互相抵消的梯度，收敛到高熵混合策略；
   这可能是**合理的混合均衡而非训练失败**。（该作者的诊断：只知对手 56.5%、只知开局分支 56.5%、
   **同时知道对手与开局 67.5%**，多数基线 54.2%。）
7. **确定性反而是反对 RL 的论据**：引擎公开、价格函数公开、seed 可精确复现、模型可任意频次调用 ——
   **这是搜索与规划问题，不是从回报里学策略的问题**。

社区收敛出的**唯一被认为有希望的学习型架构**（`738079` 长文 + 多人附议）：
**模型只选高层 Option，确定性执行层把 Option 变成动作**。模型拥有权衡（现在值得追哪个目标、候选计划怎么排序、
投多少预算、承担多少风险、何时放弃当前计划），执行器保证正确性（合法性、任务依赖、路由物流、资源冲突、硬截止、安全失败）。
配套的三条硬约束：
- **执行层可以淘汰非法或明显不可行的计划，但绝不能偷偷决定哪个可行计划"更好"** —— 一旦规则改变了可行计划之间的偏好序，它就不再是执行约束，而是在做策略。
- **"扩张"这类 Option 必须是跨天的承诺包**（土地、融资、激活所需的工人、新地上的生产、最终变现属于同一个目标），
  持续到完成、明确失败或模型主动取消为止。作者实测：某轮 99.84% 的 Land 准确率完全由多数类（保持当前地块数）驱动，
  300 个真实日初分支里模型自己拒绝了 187 次购地、同步融资检查失败 100 次，最终只确认了 7 次扩张，均终局现金 2,671。
- **必须能验证模型真的起作用**：冻结执行器，把模型换成常数输出；如果行为和结果几乎不变，策略其实藏在规则里，模型只是装饰。

### 3.5 避坑清单

1. 不要读 `obs["step"]`，用 `day * turnsPerDay + hour`。
2. 不要把动作排到 index 719，最后可执行步是 **718**。
3. `SELL` 只看 shed；`HARVEST` 进的是单位随身库存，**不 DROP 就等于零**（且要赶在需要资金的那一回合之前）。
4. 市场列表里 **SELL 排在 BUY 之前**，否则同回合的购买拿不到卖出所得。
5. Shed 容量 100（不含种子），**超出部分在日终被丢弃**；买入的 wheat/化肥/动物也占容量。
6. 买动物前留出饲料现金；`FEED` 消耗的是**执行动作那个单位自己身上的 WHEAT**，不是 shed 里的。
7. 动物买入后进 shed，要 `PICKUP` → 走过去 → 在空的 `PASTURE`/`COOP` 上 `PLACE`。
8. `BUILD_PASTURE`/`BUILD_COOP` 免费，但只在 `tile is None` 时生效（有杂草就静默失败）。
9. 种下当天必须浇水；连续两天不浇变杂草；动物连续两天不喂**永久逃走**。
10. 不要只看对 `starter` 的平均金币，要对强 bot 双席位打，把"输给母体"当一票否决。
11. 不要用别人的 bot 做对照基准去比较自己的两个版本 —— 对方的下法会改变你的商店抽签。
12. 一个提交在 60 局之前不要下判断；两个提交要在**相同局数**下比较。
13. 别在最后一天推未测代码，报错的 agent 一场都不打。
14. Notebook 里只 `%%writefile main.py` 而不打包，"Submit to Competition" 可能不产出提交物。
15. 大额卖单会在成交过程中把价格砸穿自己的阈值 —— 分批卖。
16. 化肥只会贬值（5 场 replay 的终局价 20/9/1/18/4），**收到就卖**。
17. Premium（melon/milk/wool/strawberry）有 day 9–14 的窗口；崩了基本不会反弹（melon day16 触底 89，三天后才 96）。
18. 便宜货反而升值：wheat 到 day 21 差不多翻倍，carrot 和 egg 的终局价也高于起始价。

### 3.6 规则与生态

- 主办方与社区确认：**公开可得的东西都算 fair use**，包括原样提交公开 notebook 的 agent；
  被禁止的是团队之外**私下分享**的代码。但社区共识是"原样提交公开 agent 永远赢不了"。
- 有人提醒：**警惕冒充 Kaggle 管理员索要源码的诈骗邮件**（`737885`，29 票）。
- 生态观察：固定策略**在 24 小时内就会被克隆**（有人指纹追踪到自己 8 月 26 日的开局在一天内被 15 支队伍复制）。
  只有真正自适应的策略有机会不被立刻复制。
- 提交节奏建议（来自"前第一名"的长文，78 票）：**把最好的 bot 放一个 slot 让它变老**，
  第二个 slot 只用于真正相信更强的版本、或用于对冲 meta 漂移的刻意差异化版本。

---

## 附录：已调研清单

状态说明：`read` = 拉取源码并精读；`skim` = 拉取源码、只读结构与说明；`skip` = 未拉源码（附原因）。
原因缩写：`fork` = 同一 meta 家族的版本分叉/复刻，方法论已被同族代表覆盖；`generic` = 标题无信息量的通用/入门 notebook；
`dup-analysis` = 分析结论已由讨论帖或同作者代表作覆盖；`low-signal` = 无自报强度、无方法说明。

| ref | 标题 | 票 | 状态 | 说明 |
| --- | --- | ---: | --- | --- |

| `bovard/kaggriculture-getting-started` | Kaggriculture: Getting Started | 895 | read | 核心方案/工具，正文已逐要素分析 |
| `boatlee/v16-rc5-high-score-8c-4s-premium-market-lead` | V16-RC5 / High-Score 8C/4S Premium Market Lead | 303 | read | 核心方案/工具，正文已逐要素分析 |
| `kaitofukami/25-27-strict-future-v27-midgame-meta-reset` | 25/27 Strict-Future / v27 Midgame Meta Reset | 181 | read | 核心方案/工具，正文已逐要素分析 |
| `raykkretzschmar/kaggriculture-findings-from-zero-to-top-meta` | Kaggriculture: Findings from Zero to Top Meta | 157 | read | 核心方案/工具，正文已逐要素分析 |
| `tetsutani/adaptive-farming-strategy-for-kaggriculture` | 🌾Adaptive Farming Strategy for Kaggriculture | 140 | read | 核心方案/工具，正文已逐要素分析 |
| `romantamrazov/kaggriculture-hamburger` | Kaggriculture / Hamburger 🍔 | 129 | read | 核心方案/工具，正文已逐要素分析 |
| `kaitofukami/40-40-early-floor-39-46-top-10-v48-fast-routes` | 40/40 Early Floor / 39/46 Top-10 / v48 Fast Routes | 127 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `raykkretzschmar/kaggriculture-rank-your-agent` | Kaggriculture Rank Your Agent | 104 | read | 核心方案/工具，正文已逐要素分析 |
| `kaitofukami/177-180-fresh-top-30-v21-1-conditional-memory` | 177/180 Fresh Top-30 / v21.1 Conditional Memory | 99 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `pilkwang/kaggriculture-structured-economic-policy` | Kaggriculture: Structured Economic Policy | 97 | read | 核心方案/工具，正文已逐要素分析 |
| `prvsiyan/kaggriculture-frontier-the-soil-remembers-rain` | Kaggriculture Frontier / The Soil Remembers Rain | 96 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `georgymamarin/kaggriculture-visualized-what-every-crop-pays` | Kaggriculture, Visualized: What Every Crop Pays | 87 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `indarkarhana/shape-the-shop-work-the-pasture-top-10` | Shape the Shop Work the Pasture (TOP 10) | 86 | read | 核心方案/工具，正文已逐要素分析 |
| `flexonafft/kaggriculture-multi-route-farming-agent` | Kaggriculture / Multi-Route Farming Agent | 86 | read | 核心方案/工具，正文已逐要素分析 |
| `prvsiyan/kaggriculture-frontier-the-moon-counts-melons` | Kaggriculture Frontier / The Moon Counts Melons | 85 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `boatlee/v16-rc2-high-score-near-mirror-market-relay` | V16-RC2 / High-Score Near-Mirror Market Relay | 79 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `kaitofukami/159-160-vs-frontier-v20-weed-slip-recovery` | 159/160 vs Frontier / v20 WEED-Slip Recovery | 74 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `cjlcjlcjl/kaggriculture-what-the-top-farms-do-a-live-meta` | Kaggriculture: What the Top Farms Do — a Live Meta | 74 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `boatlee/84-84-base-public-holdout-v14-clone-preemption` | 84/84 Base+Public Holdout / V14 Clone Preemption | 73 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `kaitofukami/103-128-fresh-public-v43-sparse-shop-hybrid` | 103/128 Fresh Public / v43 Sparse Shop Hybrid | 72 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `andrewsokolovsky/kaggriculture-breaking-the-tie` | Kaggriculture: Breaking the Tie | 71 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `salemali7/kaggriculture-2900` | Kaggriculture / 2900+ | 71 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `indarkarhana/rank-top10-read-the-market-choose-the-farm` | 🌾 (Rank Top10)Read the Market, Choose the Farm 📈 | 69 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `jek1wantaufik/building-a-kaggriculture-ai-agent` | Building a Kaggriculture AI Agent | 69 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `salemali7/harvest-kaggriculture` | Harvest/ Kaggriculture | 68 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `denizeryilmaz/v111-8c4s-economic-core-premium-lead` | V111 / 8C4S Economic Core Premium Lead | 66 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `boatlee/v20-adaptive-r1-multi-route-agent` | V20-Adaptive-R1 / Multi-Route Agent | 63 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `romanrozen/strong-barnyard-economist` | [STRONG] Barnyard Economist | 61 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `tetsutani/shape-the-shop-work-the-pasture-kaggriculture` | 🌾 Shape the Shop Work the Pasture / Kaggriculture | 57 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `prvsiyan/kaggle-frontier-lab-strategy-improvement` | Kaggle Frontier Lab / Strategy Improvement | 57 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `navazshfathi/notebook198200c757` | notebook198200c757 | 57 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `prvsiyan/kaggriculture-frontier-lab-high-score-visuals` | Kaggriculture Frontier Lab / High-Score + Visuals | 55 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `boatlee/v21-r1-public-state-route-portfolio` | V21-R1 / Public-State Route Portfolio | 54 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `bruceqdu/my-2026-08-04-high-score-pipeline` | My 2026-08-04 High-Score Pipeline | 48 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `boatlee/v16-rc5-r5a-high-score-8c-4s-recovery` | V16-RC5-R5A / High-Score 8C/4S Recovery | 45 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `anasriaz/kaggriculture` | Kaggriculture | 45 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `degnonguidi/kaggriculture-agent-builder` | kaggriculture-agent-builder | 44 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `lucifer19/kaggriculture-night-harvest` | 🌾🚜Kaggriculture: Night Harvest | 42 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `premaananda108/economics-driven-rule-agent-ecobot-v7-arena` | Economics-Driven Rule Agent (EcoBot v7) + Arena | 36 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `kaitofukami/238-238-known-streams-v58-minimax-closed-loop` | 238/238 Known Streams / v58 Minimax Closed Loop | 35 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `reyhanksatria/kaggriculture-adaptive-shop-guard` | Kaggriculture: Adaptive Shop Guard | 35 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `lynnsakurai/farming-score-a-mathematical-approach` | Farming Score: A Mathematical Approach | 31 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `georgymamarin/kaggriculture-daily-replays-the-live-meta-report` | Kaggriculture Daily Replays: The Live Meta Report | 30 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `stevenleehans/kaggriculture-x544-nah-i-d-win` | Kaggriculture X544 - Nah, I'd Win. | 28 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `koushikkumardinda/kaggriculture-starter` | Kaggriculture Starter | 28 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `saitejabandaruin/kaggriculture-pure-architecture-2600-elo-v3` | Kaggriculture / Pure Architecture (2600+ Elo) V3 | 27 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `yhay81/fieldbook-commit-for-three-days` | Fieldbook: Commit for Three Days | 26 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `busyaprime/what-actually-wins-on-the-kaggriculture-ladder` | What actually wins on the Kaggriculture ladder | 26 | read | 核心方案/工具，正文已逐要素分析 |
| `nikital7/4000x-environment-speedup-kaggriculture` | 4000x environment speedup / Kaggriculture | 25 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `lynnsakurai/farming-score-v3-replay-revised` | Farming Score V3: Replay Revised | 24 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `mpwolke/doomed-kaggleculture-harvest` | Doomed KaGGLEculture Harvest | 24 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `alexandergremyakov/harvest-pulse-goose-dividend-v2` | Harvest Pulse / Goose Dividend / v2 | 24 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `yamakawanin/kaggriculture-adaptive-public-state-multi-route` | Kaggriculture — Adaptive Public-State Multi-Route | 22 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `kunaldesale2408/kaggriculture-2026-v1` | Kaggriculture 2026 V1 | 22 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `saitejabandaruin/kaggriculture-ultimate-mega-ensemble-3000` | Kaggriculture / Ultimate Mega-Ensemble 3000+ | 22 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `destbreso/a-dna-test-for-agents` | A DNA Test for Agents | 21 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `jocelyndumlao/kaggriculture-ai-agent` | 🌾Kaggriculture AI Agent | 19 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `rajan1673/kagriculture` | kagriculture | 18 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `pavloivanin/kaggriculture-baseline` | 🌾 Kaggriculture Baseline | 18 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `ektarr/diversified-scheduler-baseline-kaggriculture` | Diversified Scheduler Baseline / Kaggriculture | 18 | skim | 已拉源码，核对结构与自报数据；结论并入同族代表 |
| `ameythakur20/kaggriculture-premium-first-market-agent` | Kaggriculture: Premium-First Market Agent | 17 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `avikdas567/kaggriculture-microeconomic-dynamic-policy-engine` | Kaggriculture: Microeconomic Dynamic Policy Engine | 17 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `nagatakengo/kaggriculture-movements-top-xx` | Kaggriculture_Movements_top xx% | 16 | skip | low-signal：无自报强度、无方法说明 |
| `boatlee/v13-r3-top-meta-order-safe-premium-control` | V13-R3 / Top-Meta Order-Safe Premium Control | 15 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `pilkwang/kaggriculture-precomputed-schedule-policy` | Kaggriculture Precomputed Schedule Policy | 15 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `sidhaarthshree/the-complete-getting-started-guide` | The Complete Getting-Started Guide | 15 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `chaitanyajamble/kaggriculture` | Kaggriculture | 15 | skip | generic：标题无信息量，无自报强度或方法说明 |
| `dheerajkannaujiya/start-with-basic` | Start_with_Basic | 15 | skip | low-signal：无自报强度、无方法说明 |
| `revanthtambisetty/two-private-bots-beating-kaggriculture-meta` | Two Private Bots Beating Kaggriculture Meta | 14 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `andrewsokolovsky/kaggriculture` | Kaggriculture | 13 | skip | generic：标题无信息量，无自报强度或方法说明 |
| `nagatakengo/predict-future-melon-prices` | Predict_future_melon_prices | 13 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `mansiaggarwal88/why-our-kaggriculture-ai-failed-math-vs-reality` | 🚜 Why Our Kaggriculture AI Failed:Math vs Reality | 13 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `jeffmarcecadet/reverse-engineering-rank-5-thunder-thunder` | Reverse-Engineering Rank #5 (THUNDER THUNDER) | 13 | skip | low-signal：无自报强度、无方法说明 |
| `destbreso/a-week-four-x-ray-of-the-top-twelve` | A week-four X-ray of the top twelve | 12 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `stevenleehans/kaggriculture-x578-i-m-the-strongest` | Kaggriculture x578 - I'm the strongest | 12 | skip | low-signal：无自报强度、无方法说明 |
| `ameythakur20/kaggriculture-deterministic-farm-planning-agent` | Kaggriculture Deterministic Farm Planning Agent | 12 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `chaimaamatrag/kaggriculture-competition` | kaggriculture_competition | 12 | skip | low-signal：无自报强度、无方法说明 |
| `nagatakengo/kaggriculture` | Kaggriculture | 12 | skip | generic：标题无信息量，无自报强度或方法说明 |
| `ocean240812/kaggriculture-strategy-guide` | Kaggriculture Strategy Guide | 12 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `reyhanksatria/best-market-agent-high-strategy` | best market agent - high strategy | 11 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `prvsiyan/kaggriculture-baseline` | Kaggriculture Baseline | 11 | skip | generic：标题无信息量，无自报强度或方法说明 |
| `destbreso/from-1-to-24-000-episodes-a-second` | From 1 to 24,000 episodes a second | 11 | skip | low-signal：无自报强度、无方法说明 |
| `morinokuma3/adaptive-shop-guard-fork` | Adaptive Shop Guard Fork | 11 | skip | low-signal：无自报强度、无方法说明 |
| `destbreso/wins-not-money` | Wins, not money | 11 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `llccqq624/kaggriculture-replay-data-miner` | Kaggriculture Replay Data Miner | 11 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `kunaldesale2408/kaggriculture-ttv1` | Kaggriculture TTV1 | 10 | skip | low-signal：无自报强度、无方法说明 |
| `msama01/kaggriculture-evaluation-agent-performance-analys` | Kaggriculture Evaluation: Agent Performance Analys | 10 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `emanuellcs/kaggriculture-agent` | Kaggriculture Agent | 10 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `songoku2005/kaggriculture` | Kaggriculture | 10 | skip | generic：标题无信息量，无自报强度或方法说明 |
| `mansiaggarwal88/kaggriculture-local-agent-evaluation-harness` | 🚜 Kaggriculture: Local Agent Evaluation Harness | 10 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `llccqq624/kaggriculture-top-5-meta-ensemble` | Kaggriculture Top-5 Meta Ensemble | 9 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `koushikrudra/kaggriculture-preempt-h6` | Kaggriculture Preempt H6 | 9 | skip | low-signal：无自报强度、无方法说明 |
| `pengwang91/wide-sigma-cma-tuned-scenario-aware-submitted` | Wide-Sigma CMA Tuned Scenario-Aware (submitted) | 9 | skip | low-signal：无自报强度、无方法说明 |
| `rauffauzanrambe/kaggriculture-finding-conditional-fresh-vegetable` | Kaggriculture: Finding Conditional Fresh Vegetable | 9 | skip | low-signal：无自报强度、无方法说明 |
| `destbreso/island-ga-an-owned-schedule-is-a-moat` | Island GA / An owned schedule is a moat | 9 | skip | low-signal：无自报强度、无方法说明 |
| `destbreso/dissecting-the-top-two` | Dissecting the Top Two | 9 | skip | low-signal：无自报强度、无方法说明 |
| `zakariajoudar/rule-based-agent-with-dynamic-ma` | 🤖Rule-Based Agent with Dynamic Ma | 9 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `destbreso/kaggriculture-what-kind-of-optimisation-is-this` | Kaggriculture: what kind of optimisation is this? | 9 | skip | low-signal：无自报强度、无方法说明 |
| `lynnsakurai/farming-score-v2-a-better-approach` | Farming Score V2: A Better Approach | 9 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `stevenleehans/kaggriculture-rank-238-oh-you-re-approaching-me` | Kaggriculture Rank 238 - Oh You're approaching me? | 8 | skip | low-signal：无自报强度、无方法说明 |
| `sakhawathossen/kaggriculture-final-hybrid-champion` | Kaggriculture Final Hybrid Champion | 8 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `boatlee/v17-r1-rc2-high-score-10c-4s-market-storage` | V17-R1-RC2 / High-Score 10C/4S Market & Storage | 7 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `web3cainiao/kaggriculture-v21-tactical-memory` | Kaggriculture v21 Tactical Memory | 7 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `mugundhjb/v21-multi-route-agent-sell-divergence-guarder` | V21/Multi-Route Agent/Sell Divergence Guarder | 7 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `maulikgajera/2153-7-kaggriculture-solutions` | [2153.7]🌾 Kaggriculture: Solutions | 7 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `rahuljiwane/kaggriculture-rahul-jiwane` | Kaggriculture: Rahul Jiwane | 6 | skip | low-signal：无自报强度、无方法说明 |
| `dimong4/kaggriculture` | Kaggriculture | 6 | skip | generic：标题无信息量，无自报强度或方法说明 |
| `sidhaarthshree/kaggriculture-the-scarcity-rancher` | Kaggriculture: The Scarcity Rancher | 6 | skip | low-signal：无自报强度、无方法说明 |
| `sidhaarthshree/a-reactive-agent-with-optimal-task` | A Reactive Agent with Optimal Task | 6 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `akhileshgodugu/strong-statr-barnyard-economist` | [STRONG STATR] Barnyard Economist | 5 | skip | low-signal：无自报强度、无方法说明 |
| `llccqq624/kaggriculture-weedproof-clone-market` | Kaggriculture / Weedproof Clone Market | 5 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `navazshfathi/v16-rc5-high-score-8c-4s-premium-market-lead` | V16-RC5 / High-Score 8C/4S Premium Market Lead | 5 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `llccqq624/kaggriculture-premium-queue-split` | Kaggriculture / Premium Queue Split | 5 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `farhanabidtech786/kaggriculture-beginner-friendly` | kaggriculture-beginner-friendly | 5 | skip | low-signal：无自报强度、无方法说明 |
| `kaiwalyaatulraut/kaggriculture-solution` | Kaggriculture Solution | 5 | skip | low-signal：无自报强度、无方法说明 |
| `mtoshidesu/testkaggriculture-hamburger` | TestKaggriculture / Hamburger 🍔 | 5 | skip | low-signal：无自报强度、无方法说明 |
| `yhay81/public-match-history-router-rating-2929-aug-30` | Public Match History Router - Rating 2929 - Aug 30 | 5 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `destbreso/six-checks-before-you-waste-a-submission` | Six checks before you waste a submission | 5 | skip | low-signal：无自报强度、无方法说明 |
| `hboyang/kitex-v0` | KiteX v0 | 4 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `lynnsakurai/farming-score-v5-timing-optimized` | Farming Score V5: Timing Optimized | 4 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `lynnsakurai/farming-score-v4-a-better-shop` | Farming Score V4: A Better Shop | 4 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `navazshfathi/kaggriculture-best-score-farming-score` | Kaggriculture---best---score--Farming Score | 4 | skip | low-signal：无自报强度、无方法说明 |
| `llccqq624/kaggriculture-the-shops-remember-the-route` | Kaggriculture / The Shops Remember the Route | 4 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `navazshfathi/kaggriculture-best-score` | KAGGRICULTURE- BEST-SCORE | 4 | skip | low-signal：无自报强度、无方法说明 |
| `binasalama/kaggriculture-v31-early-livestock` | Kaggriculture V31 Early Livestock | 4 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `amaterasuuuuu/shabby-farm` | Shabby Farm | 4 | skip | low-signal：无自报强度、无方法说明 |
| `junaid512/kaggriculture-v01-drip` | Kaggriculture — v01 “Drip” | 4 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `yhay81/replay-public-episode-actions-across-seeds-in-c` | Replay Public Episode Actions Across Seeds in C++ | 4 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `skomuro/2000-baseline-silver-medal-route` | 2000+ Baseline: Silver Medal Route | 4 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `rafifariqrabbani/kaggriculture-greedy-optimizer-staged-frozen-rl` | Kaggriculture: Greedy Optimizer + Staged Frozen RL | 4 | skip | low-signal：无自报强度、无方法说明 |
| `mansiaggarwal88/550-lb-kaggriculture-reactive-agent` | 🌱 550 LB: Kaggriculture Reactive Agent | 4 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `busyaprime/the-best-thing-to-farm-has-a-market-of-59-units` | The best thing to farm has a market of 59 units | 4 | skip | low-signal：无自报强度、无方法说明 |
| `llccqq624/kaggriculture-adaptive-counterbook` | Kaggriculture / Adaptive Counterbook | 4 | skip | low-signal：无自报强度、无方法说明 |
| `vijaikm/kaggriculture-bc-policy-inference-starter` | Kaggriculture BC Policy Inference Starter | 4 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `vijaikm/kaggriculture-modular-agent-framework` | Kaggriculture Modular Agent Framework | 4 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `ashok205/top10-replay-dataset-archive` | top10-replay-dataset-archive | 4 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `ahmed1harfoush/kaggriculture-notebook` | Kaggriculture  Notebook | 4 | skip | low-signal：无自报强度、无方法说明 |
| `moushunchen/twelve-seeds-three-melons` | Twelve Seeds, Three Melons | 4 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `akashbabu17/kaggriculture-autonomous-multi-agent-farming` | 🌾 Kaggriculture: Autonomous Multi-Agent Farming | 4 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `navazshfathi/177-180-fresh-top-30-v21-1-conditional-memory` | 177/180 Fresh Top-30 / v21.1 Conditional Memory | 3 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `llccqq624/kaggriculture-dual-market-relay` | Kaggriculture / Dual Market Relay | 3 | skip | low-signal：无自报强度、无方法说明 |
| `foysalemonshanto/read-the-market-choose-the-farm` | ðŸŒ¾ Read the Market, Choose the Farm ðŸ“ˆ | 3 | skip | low-signal：无自报强度、无方法说明 |
| `djamilabenchikh/graph-reinforcement-learning` | Graph + Reinforcement Learning | 3 | skip | low-signal：无自报强度、无方法说明 |
| `harishyadav0506/v16-rc5-high-score-8c-4s-premium-market-lead` | V16-RC5 / High-Score 8C/4S Premium Market Lead | 3 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `sangitabannore/kaggriculture-sangita-jiwane-2` | Kaggriculture: Sangita Jiwane 2 | 3 | skip | low-signal：无自报强度、无方法说明 |
| `evgendvorkin/kaggriculture` | Kaggriculture | 3 | skip | generic：标题无信息量，无自报强度或方法说明 |
| `daniilkrasnovvv/farm-top-solution-in-lb` | [Farm] Top solution in LB! | 3 | skip | low-signal：无自报强度、无方法说明 |
| `stpeteishii/kaggriculture-match-replay-reproducer` | Kaggriculture Match Replay Reproducer | 3 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `mobeenfatimah/kaggriculture-agribot-heuristic-state-machine` | Kaggriculture(AgriBot): Heuristic State-Machine | 3 | skip | low-signal：无自报强度、无方法说明 |
| `binasalama/kaggriculture-v29-reactive` | Kaggriculture V29 Reactive | 3 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `destbreso/kagsim-the-engine-at-2000-episodes-per-second` | kagsim / The engine at 2000 episodes per second | 3 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `busyaprime/one-town-in-three-has-no-yarn-store-at-all` | One town in three has no yarn store at all | 3 | skip | low-signal：无自报强度、无方法说明 |
| `xishengfeng/rl-v9-market-off-tape-rulemirror-league` | RL v9 Market Off Tape RuleMirror League | 3 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `ravi123a321at/177-180-fresh-top-30-v21-1-conditional-memory` | 177/180 Fresh Top-30 / v21.1 Conditional Memory | 2 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `flexonafft/kaggriculture-adaptive-farm-intelligence` | Kaggriculture / Adaptive Farm Intelligence | 2 | skip | low-signal：无自报强度、无方法说明 |
| `stevenleehans/kaggriculture-strongest-farmer-of-today` | Kaggriculture - Strongest Farmer of Today? | 2 | skip | low-signal：无自报强度、无方法说明 |
| `navazshfathi/84-84-base-public-holdout-v14-clone-preemption` | 84/84 Base+Public Holdout / V14 Clone Preemption | 2 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `harishyadav0506/v111-8c4s-economic-core-premium-lead` | V111 / 8C4S Economic Core Premium Lead | 2 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `daniilkrasnovvv/kaggriculture-easy-bronse-in-lb-2628-2` | [Kaggriculture] Easy bronse in LB (2628.2)! | 2 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `biohack44/kaggriculture` | Kaggriculture | 2 | skip | generic：标题无信息量，无自报强度或方法说明 |
| `shorooghahmadi/kaggriculture-v3-agent` | Kaggriculture v3 agent | 2 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `moncefelm/kaggriculture-getting-started` | Kaggriculture: Getting Started | 2 | skip | low-signal：无自报强度、无方法说明 |
| `navazshfathi/notebook76f6a59396` | notebook76f6a59396 | 2 | skip | generic：标题无信息量，无自报强度或方法说明 |
| `destbreso/x-ray-your-agent` | X-ray your agent | 2 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `evelyn3976/kaggriculture-kaito-v27-public-safety-v7` | Kaggriculture Kaito V27 Public Safety V7 | 2 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `binasalama/kaggriculture-v28-gate-fixed` | Kaggriculture V28 Gate Fixed | 2 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `xreina8/kaggriculture-a-b-two-agents-with-error-bars` | Kaggriculture: A/B two agents with error bars | 2 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `evelyn3976/kaggriculture-v21-public-market-v5` | Kaggriculture V21 Public Market V5 | 2 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `stpeteishii/kaggriculture-head-to-head-match-runner` | Kaggriculture Head-to-Head Match Runner | 2 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `mansiaggarwal88/when-smart-math-fails-in-adversarial-games` | When Smart Math Fails in Adversarial Games | 2 | skip | low-signal：无自报强度、无方法说明 |
| `kaptaan45/kaggriculture-championship-agent-simulation` | Kaggriculture: Championship Agent & Simulation | 2 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `bruceqdu/reinforcement-learning-and-mcts-a-tutorial` | Reinforcement Learning and MCTS: A Tutorial | 2 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `bssgirl/notebook317289f44a` | notebook317289f44a | 2 | skip | generic：标题无信息量，无自报强度或方法说明 |
| `rakhansyah/an-unintelligent-attempt-teaching-greedy-workers` | An Unintelligent Attempt: Teaching Greedy Workers | 2 | skip | low-signal：无自报强度、无方法说明 |
| `xreina8/what-decides-rating-once-money-stops-mattering` | What decides rating once money stops mattering? | 2 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `xreina8/kaggriculture-300-melons-return-36-of-face-value` | Kaggriculture: 300 melons return 36% of face value | 2 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `nekkon/the-top-agent-is-a-720-turn-replay-not-a-strategy` | The top agent is a 720-turn replay, not a strategy | 2 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `tuannm3812/hierarchical-task-coordinator-htdc-v12` | Hierarchical Task Coordinator (HTDC) v12 | 2 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `ryanmyers03/kaggriculture-agent-v1` | Kaggriculture Agent v1 | 1 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `kathimunishwar/kaggriculture-replay-agent` | Kaggriculture replay agent | 1 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `junaid512/02-adaptive-replay-agent` | 02 Adaptive Replay Agent | 1 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `merkiraz/counter-cyclical-orchard` | Counter-Cyclical Orchard | 1 | skip | low-signal：无自报强度、无方法说明 |
| `bnzn261029/visible-state-all-router-over-seven-public-syouya` | Visible-state all router over seven public Syouya | 1 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `kevin250304/kaggriculture-healthstone-route-20260810` | Kaggriculture HealthStone route 20260810 | 1 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `destbreso/an-instrument-for-agent-selection` | An instrument for agent selection | 1 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `theepanss/notebooke6e24888ed` | notebooke6e24888ed | 1 | skip | generic：标题无信息量，无自报强度或方法说明 |
| `binasalama/kaggriculture-v30-time-switch` | Kaggriculture V30 Time Switch | 1 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `evelyn3976/kaggriculture-frontier-v156-coherent-liquidity-v6` | Kaggriculture Frontier V156 Coherent Liquidity V6 | 1 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `dariushafshar/your-rating-fell-your-standing-rose` | Your Rating Fell. Your Standing Rose. | 1 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `destbreso/a-field-guide-to-replay-agents` | A Field Guide to Replay Agents | 1 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `destbreso/rating-convergence-episodes-not-hours` | Rating convergence / Episodes, not hours | 1 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `manderson240/cohezion-kaggriculture-multi-agent-policy-baseline` | Cohezion Kaggriculture Multi-Agent Policy Baseline | 1 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `vinceybb/kaggriculture-validate-before-you-submit` | Kaggriculture: Validate Before You Submit 🌾 | 1 | skip | low-signal：无自报强度、无方法说明 |
| `vijaikm/kaggriculture-match-replay-eda-starter` | Kaggriculture Match Replay EDA Starter | 1 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `vijaikm/kaggriculture-simulation-eda` | Kaggriculture Simulation EDA | 1 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `joymietalicuad/economics-driven-rule-agent-ecobot-v2` | Economics-Driven Rule Agent (EcoBot v2) | 1 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `maverickss26/kaggriculture-v1` | Kaggriculture v1 | 1 | skip | generic：标题无信息量，无自报强度或方法说明 |
| `dariushafshar/same-file-9-days-apart-1839-vs-1238` | Same File, 9 Days Apart: 1839 vs 1238 | 1 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `umutdorukztrk/kagricultre-baseline` | Kagricultre_baseline | 1 | skip | low-signal：无自报强度、无方法说明 |
| `destbreso/the-farm-day-as-a-routing-problem` | The Farm Day as a Routing Problem | 1 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `destbreso/the-trades-were-paying-for-the-farm` | The trades were paying for the farm | 1 | skip | low-signal：无自报强度、无方法说明 |
| `destbreso/what-1-32-7-changed-and-what-it-did-not` | What 1.32.7 changed, and what it did not | 1 | skip | low-signal：无自报强度、无方法说明 |
| `destbreso/what-is-fixed-what-emerged-and-how-you-can-tell` | What is fixed, what emerged, and how you can tell | 1 | skip | low-signal：无自报强度、无方法说明 |
| `destbreso/kaggriculture-how-much-money-is-in-this-game` | Kaggriculture: How much money is in this game? | 1 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `destbreso/how-many-opponents-is-a-pool-of-forty` | How many opponents is a pool of forty? | 1 | skip | low-signal：无自报强度、无方法说明 |
| `motemen/kaggriculture-meta-census-lineage-occupancy` | Kaggriculture Meta Census — Lineage Occupancy | 0 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `trnhquangminh140/kaggriculture-strategic-decision-making` | Kaggriculture - STRATEGIC DECISION-MAKING | 0 | skip | low-signal：无自报强度、无方法说明 |
| `leneen/kaggriculture` | Kaggriculture: | 0 | skip | generic：标题无信息量，无自报强度或方法说明 |
| `taylorclark637/kaggriculture` | Kaggriculture | 0 | skip | generic：标题无信息量，无自报强度或方法说明 |
| `evelyn3976/kaggriculture-v6-limited-dynamic-v8` | Kaggriculture V6 Limited Dynamic V8 | 0 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `earnestgomer/sifi-model-1` | SIFI MODEL 1 | 0 | skip | low-signal：无自报强度、无方法说明 |
| `justinmnic/kaggriculture` | kaggriculture | 0 | skip | generic：标题无信息量，无自报强度或方法说明 |
| `evelyn3976/kaggriculture-adaptive-market-scheduler-v1` | Kaggriculture Adaptive Market Scheduler v1 | 0 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `lixiuqixiaoke/v24-robustmarketlead` | V24-RobustMarketLead | 0 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `vijaikm/kaggriculture-score-convergence-2026` | Kaggriculture Score Convergence 2026 | 0 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `harishyadav0506/economics-driven-rule-agent-ecobot-v4` | Economics-Driven Rule Agent (EcoBot v4) | 0 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `hboyang/kaggriculture-adaptive-shop-guard` | Kaggriculture: Adaptive Shop Guard | 0 | skip | low-signal：无自报强度、无方法说明 |
| `ritzraha/cow-money-melon-mayhem-and-the-scoreboard` | Cow Money, Melon Mayhem, and the Scoreboard | 0 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `alejandrofonda/kaggriculture-state-p1-2-2` | Kaggriculture State P1.2.2 | 0 | skip | low-signal：无自报强度、无方法说明 |
| `dariushafshar/a-small-public-split-costs-13-shakeup-points` | A Small Public Split Costs 13 Shakeup Points | 0 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `dariushafshar/your-top-10-is-a-coinflip-past-2000-teams` | Your Top 10 Is A Coinflip Past 2000 Teams | 0 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `bssgirl/notebookb3d1e95bdc` | notebookb3d1e95bdc | 0 | skip | generic：标题无信息量，无自报强度或方法说明 |
| `bssgirl/notebook2775387d0f` | notebook2775387d0f | 0 | skip | generic：标题无信息量，无自报强度或方法说明 |
| `dariushafshar/a-perfect-5-point-correlation-debunked-at-n-1-009` | A Perfect 5-Point Correlation, Debunked at n=1,009 | 0 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `dariushafshar/kaggriculture-s-mean-vote-beats-biohub-s-by-52` | Kaggriculture's Mean Vote Beats Biohub's by 52% | 0 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |
| `xreina8/does-a-farming-game-get-supply-and-demand-right` | Does a farming game get supply and demand right? | 0 | skip | low-signal：无自报强度、无方法说明 |
| `antimocarlino/o-p-a-antimode-v1` | 🎖️ O.P.A. — ANTIMODE v1 | 0 | skip | fork：公开 meta 家族的版本分叉，方法论已被同族代表覆盖 |
| `lucashmateo/kaggriculture-replays-no-oom-3-dataframes` | Kaggriculture Replays: No OOM, 3 DataFrames | 0 | skip | dup-analysis：分析/工具类，结论已由讨论帖或同作者代表作覆盖 |

合计 **228** 个公开 notebook：`read` 11，`skim` 49，`skip` 168。
下次巡视时用本表做 diff 基线：只精读新出现的 ref，以及标题分数显著刷新的旧 ref。
