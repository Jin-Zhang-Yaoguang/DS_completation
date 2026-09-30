# Kaggriculture 社区现场调研（CLI）

- 抓取截止：2026-08-26T12:10:21Z（Asia/Taipei 20:10）
- 数据入口：Kaggle CLI 2.2.3；discussion 的 `topics list/show/topic-messages`，code 的 `kernels list/pull`
- 范围：公开社区；未使用浏览器、未改任何模型、未创建提交
- 互动量会继续变化；下文均为抓取时快照

## 结论先行

最高价值不是直接复制一个新高票 agent，而是组合四类能力：

1. **可验证的高速仿真**：把模型池、宽 seed、双席位和分簇留出真正跑足；`kaggriculture-cppsim` 是当前最值得接入的研究基础设施，但必须先过其 1.32.7 golden traces，再用官方环境抽检。
2. **拥有自己的基础时序**：Island GA 的“声明式 genome -> 从头编译融资/动作流 -> CRN screen -> 独立 confirm”值得复用；现成默认目标仍主要是 vs idle，不能直接作为梯子适应度。
3. **把城镇结构变成路线风险**：羊毛在约 34.4% 的城镇没有买家；不同商品相同平均需求不代表相同断供风险。适合把 `room_for(unlocked_shops)`、买家缺失概率和观察到的商店组成加入路线选择/限产。
4. **只做因果、局部的对手响应**：固定强时序作骨架，市场层只在“对手公开农场状态、当前库存/价格、基础 farmer/hands 动作仍一致”时干预；避免整条动作流拼接和从未来回放偷看。

## 2026-08-23 旧快照之后的新讨论

| ID | UTC 时间 | 作者 | 题目 | 评论 / 票 | 价值判断 |
|---:|---|---|---|---:|---|
| 737571 | 08-26 06:49 | SZU蓝心 | Which version got the final rating? | 2 / 0 | 社区回答声称最终活跃版本/约 3 天 100 局；没有官方确认，不能当规则事实 |
| 737570 | 08-26 06:10 | madmax0404 | Can game parameters change…? | 0 / 0 | 只有问题，无答案 |
| 737568 | 08-26 05:23 | Sandeep063 | Reached ~$15K average… | 1 / 0 | 回复给出大量经验阈值，但没有原始回放/代码，列为待验证假设 |
| 737545 | 08-26 03:41 | stpete_ishii | obs["step"] seat1 bug | 0 / 3 | 回放存储层缺字段属实；帖子对运行时 agent 的影响推断被本地反证，见下文 |
| 737492 | 08-25 19:10 | Rustam Bazarbayev | How many days need…? | 2 / 0 | 最有价值的是按 episode 而非小时比较 rating 漂移，并只比较同期活跃 agent |
| 737480 | 08-25 18:00 | renji_starfall | How do you perform behavioral cloning? | 2 / 2 | 给出可直接复用的 replay 动作抽取、逐美元回放校验与安全时钟写法 |
| 737459 | 08-25 16:48 | Omkar Kadam | Tips starting now | 8 / 2 | 引出 1.32.7 C++ 仿真仓库和“优先回放/仿真、慎用 RL”的社区意见 |
| 737457 | 08-25 16:03 | DILIP BAVISKAR | Reward Calculation | 2 / 0 | “只看最终现金”的说法没有组织者背书，不纳入事实 |
| 737431 | 08-25 13:32 | Rahul Balakrishnan Adhi | Regarding Deadline | 1 / 0 | 社区猜测，不纳入规则事实 |

讨论链接统一为：`https://www.kaggle.com/competitions/kaggriculture/discussion/<ID>`。

### 可直接复用：回放动作抽取

讨论 737480 的 `destbreso` 回复给出：

```python
actions = [replay["steps"][t + 1][seat]["action"]
           for t in range(len(replay["steps"]) - 1)]
```

- 720 个 replay state 只有 719 个 acting turn；turn `t` 的动作在 `steps[t+1]`。
- 以同 seed、同对手回放，最终双方 bank 必须逐美元相等，才能证明没有 off-by-one。
- 安全时钟写作 `t = obs["day"] * 24 + obs["hour"]`；B85 + zlib 只是单文件打包，不是克隆算法。
- 纯复制他人回放有原创性、许可/署名和元游戏失效风险；合理用途是固定对手、仪器校准、反事实和原创自适应层的骨架。

### `obs["step"]` 争议：帖子标题不能直接当结论

在本地项目 `.venv` 的 `kaggle-environments==1.32.7` 复现：

- `env.steps[i][1].observation.get("step")` 确实一直为 `None`，与帖子一致。
- 但两个 agent 的实际回调都连续收到 `step=0..8`，与帖子“seat1 agent 永远看到 0”的推断相反。
- 原因：`core.__get_shared_state()` 会按 schema 将 `shared=True` 的 `step` 从 seat0 注入每个 agent 的运行时 observation。
- 本地包证据：`core.py` SHA256 `0922c459...6d45d0e`；`kaggriculture.py` SHA256 `bc8a5487...ccee653e`。

所以目前能确认的是**存入 replay 的 seat1 observation 缺 step**，不能确认线上运行时 seat1 agent 缺 step。仍建议入口统一从 `day/hour` 派生时钟，并增加 raw-loader + 双席位 smoke；不要据此否定所有依赖 `step` 的社区方案。

### 待验证经验阈值（不能当已证实机制）

讨论 737568 的回复自称基于 214 episodes / 326 万 actions，提出：提前卖出是主要损失、动物在 elbow day 前约 2 天入场、CARE 在 6/12/18、开局支出约 2982、奶牛 day0-4、premium 分批不超过 20 等。正文未附原始数据、版本、对手池和统计区间；适合逐条 A/B，不适合整体照搬。

## 值得研究的公开代码 / notebook

### P0：高速仿真与验证纪律

- Kaggle：`destbreso/from-1-to-24-000-episodes-a-second`（08-26 10:53Z，抓取时 3 票）
- GitHub：<https://github.com/destbreso/kaggriculture-cppsim>
- 固定 commit：`812e50c58543e436828465f89e4cf808a388874f`，Apache-2.0
- 直接可用：`kagsim.Stream`、`run_episode`、`run_many`、L1 `Game.observe/step`、`tests/test_golden.py`、trace exporter。
- 作者 M4 测量：4,139 eps/s 单线程、24,442 eps/s 十核；这是作者机器结果，本次未编译复测。
- 仓库声称六条 1.32.7 golden trace 在两席位 719 步逐步一致，且原始 1.32.6 对照全部失败；接入前必须本地运行 golden，并用官方环境保留抽检/降级路径。

### P0：自己的 schedule 搜索器

- Kaggle：`destbreso/island-ga-an-owned-schedule-is-a-moat`（抓取时 7 票）
- GitHub：<https://github.com/destbreso/kaggriculture-island-ga>
- 固定 commit：`be23b55a63d6376057097cb2d07e92e0ddbeb2c3`，MIT
- 直接可用：12 参数 genome、compiler、reference executor、island GA、CRN screen、独立 confirm、checkpoint、pool、双席位 arena、单文件打包前检查。
- 关键设计：搜索“规格”而不是直接拼动作流；融资、购买和卖出顺序由 compiler 从头推导，避免时序被悄悄破坏。
- 局限：默认 screen 只有 3 seeds、confirm 5 seeds，且入池主要按 vs idle bank；README 明确提醒长搜索会记住小 seed panel。要改成模型池谱系等权、宽 seed、source-cluster 留出和 paired uplift，才适合当前目标。

### P1：城镇/商店条件化的路线风险

- Kaggle：`busyaprime/one-town-in-three-has-no-yarn-store-at-all`（08-24 15:00Z，抓取时 4 票）
- 公开枚举 6,435 种商店 multiset；结论称 wool 在 34.4% 城镇没有买家，carrot 与 milk 平均需求接近但无买家风险约 10% vs 2%。
- 可直接复用：notebook 内 `room_for(unlocked, worst_case=0.10)`，把观察到的商店组成换算为可被城镇消化的产能/地块上限。
- 值得验证：是否用商店缺失风险做前置路线选择；是否在 day12 之前看见足够商店信号；不同 agent 的除草 RNG 会改变后续商店抽取，不能仅凭 seed 预知城镇。
- 配套 notebook `the-best-thing-to-farm-has-a-market-of-59-units` 自我纠正了“卖到 floor 的数量就是容量”的错误：商店会持续消耗，静态 floor 计数不是全年可售容量。保留分散商品/分散卖出时点的方向，不采用标题数字作硬上限。

### P1：当前强者行为与市场稀缺区

- Kaggle：`destbreso/a-week-four-x-ray-of-the-top-twelve`（08-24 14:17Z，11 票）
- 数据窗口冻结于 08-23/24，144 个 top-12 episodes，每个 submission 12 场；不是 08-26 的实时 meta。
- 新线索：当时 top5 多为 day3 后仍会变的 live policy；#6/#7/#10/#11/#12 更接近完整路线组合；#8/#9 是固定 opening + live tail。
- 当时 top5 分化为多作物、蛋/鹅、wheat flood + carrot/tomato/egg 稀缺、第三块地/高现金、premium 等路线。
- tomato 在该周约 8%-15% turns/day 进入 scarcity knee，峰值价 786 vs base 60；这是值得在本地 replay/引擎重新统计的市场信号，不应直接固化阈值。
- 80 场内部对局没有足够证据证明稳定的石头剪刀布；某些分组 10-4 但 p=0.18，不能据小样本建立路由。

### P1：局部自适应层的可拆设计

以下整包代码都已拉到本地，适合拆模块和读策略，不代表可直接上榜：

- `yamakawanin/kaggriculture-adaptive-public-state-multi-route`（16 票）：首次分歧路由、只改市场 channel、无未来信息的 yarn repair、从公开对手农场做粗分类、farmer/hands 一致才允许干预。
- `reyhanksatria/kaggriculture-adaptive-shop-guard`（20 票）：terminal clearance、shed projection、精确价格下的 SELL 重排、weed repair、稀疏 market rollout、reserve-safe 一步 market maker、clone-distance / phase detector。
- `llccqq624/kaggriculture-premium-queue-split`（4 票）：把 premium 卖单前移一步、下一步等量“偿还”，并避开 pickup/既有卖单；这是小而可证伪的市场干预模板。
- `lixiuqixiaoke/v24-robustmarketlead`（0 票）：只把 premium front-run 数量封顶 4，增量很小，优先级低。

复用原则：逐模块移植、保留父策略动作一致性 gate、双席位/宽 seed/模型池做 paired 测试；不要把多个公开动作流直接拼接。票数只是关注度，不是线上得分或因果证据。

### P2：评测与 rating 观察工具

- `stpeteishii/kaggriculture-head-to-head-match-runner`：有 raw agent loader、`day*24+hour` 补时钟、双席位运行模板。不要要求换席后 bank 完全相同；席位/RNG 本就可能引入差异，正确做法是成对汇总。
- `destbreso/rating-convergence-episodes-not-hours`：仅在 episode_count 变化时采样，以 `delta rating / delta episodes` 看漂移；同一字节 agent 也可能随对手群变化。可用于解释线上分数，不替代本地胜率。
- `mansiaggarwal88/when-smart-math-fails-in-adversarial-games`：提出 Newsvendor/Real Options 因共享市场和复利时序失败，但展示的是硬编码分数数组/少量路径，证据较弱，只能作为负面假设。

## 建议的可验证实验

1. **商店条件化限产**：只改变 route risk / max tiles，不改基础时序；按城镇商店 cluster 分层，比较总体 score rate、无买家城镇尾部损失和 paired uplift。
2. **稀缺商品机会层**：对 carrot/tomato/egg 分别做只读价格/库存预测，再做受 reserve 与原动作一致性约束的 SELL 前移；逐商品消融，避免把收益误归因于整个 overlay。
3. **公开对手状态识别**：只用当前可见农场/市场构造 regime（例如早期畜牧、premium、wheat flood），先验证分类稳定性与未来市场状态的互信息，再决定是否路由；分类不稳时回退父策略。
4. **人口权重搜索**：复用 Island GA orchestration，但适应度改为谱系等权模型池；screen 使用 common seeds + 双席位，confirm 使用不相交 seed/source-cluster，报告 paired uplift CI，而非 vs idle bank。
5. **仿真一致性 gate**：任何高吞吐结果先过 golden；随机抽取候选/对手/seed 在官方 1.32.7 逐步比较 bank、inventory、market，漂移即 fail closed。

## 证据局限

- discussion 的回复不是官方规则；最终版本选择、参数是否变化、reward 定义和截止安排均需比赛规则/组织者确认。
- notebook 票数与作者自报分数不能证明线上有效；很多 artifact 共享公开回放或同一思路，不能当独立样本。
- top-12 X-ray 的 meta 已冻结数日；其结果适合提出假设，不适合硬编码对手类别。
- cppsim 与 Island GA 本次只完成源码/commit/许可审查，未在本机编译运行，因此性能和 bit-exact 仍是“作者可复现实验”，不是本地已验证结果。
- 本目录只新增调研材料和公开源码快照；没有修改模型、没有发起 Kaggle submission。

## 本地材料

- `kernels/`：12 个 Kaggle notebook/script 的原始 pull + metadata
- `external_repos/kaggriculture-cppsim/`：上述固定 commit 的公开仓库
- `external_repos/kaggriculture-island-ga/`：上述固定 commit 的公开仓库

