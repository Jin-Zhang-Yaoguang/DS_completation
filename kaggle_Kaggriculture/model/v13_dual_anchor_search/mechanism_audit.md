# V13 双锚点进一步改进：机制审计与预注册建议

## 结论先行

A2 的提升是真实且跨面板的：在 frozen_v5 的 100 个新 source、双席位直接对 r002 中，A2 为 159/2/39，得分率 80.0%，source-cluster bootstrap 95% CI 为 74.5%–85.5%；对 7 个共同对手的配对净得分提升为 +5.786pp，95% CI 为 +4.536pp–+7.036pp，最差单对手为 0pp。[VERIFY: kaggle_Kaggriculture/model/v12_validation/runs_v5/formal/audit.json:175-324]

下一步不应再大幅重写 Router，而应继续做低维、可证伪的市场残差。审计得到 8 个互不重复的方向，但只有一个证据足以作为 confirmatory 候选，另一个只能低成本探索：

1. **C1（主候选）：`A2 + no-WOOL`**——保留 A2 的 no-shop、分支、小额出售、同回合入库和仓位守卫，仅让 WOOL 恢复父策略原销量；EGG/MILK 仍按 A2 规则处理。
2. **C2（探索性 screen）：`A2 + terminal-716`**——A2 全部逻辑不变，只把空闲市场槽补清仓的起点由 step 718 提前到 step 716；当前线上败局没有残货证据，不能称为 confirmatory 修复。

不硬凑第三个候选。`V8-only throttle` 看似保守，实际会删除 V5 分支上已经确认有效的 r002/A2 增益；价格门槛、订单价值排序和长期扣货已有灾难性反例；基于 shop 的逐商品 gate 已被 A2 直接证伪。

> 证据边界：本文使用 V11 Round 1–3、V12 v3/v4 screen、已经打开的 frozen_v5 formal、机制消融和社区研究；这些 source 从现在起全部视为开发暴露。没有读取 sealed/final test。C1/C2 的收益必须由全新且双锚点的 panel 证明。

## 1. 当前真实执行路径

### r002

r002 先运行 step-72 的完整专家 Router，然后仅在 day 10/17/24 把父策略已有的 EGG/MILK/WOOL SELL 数量乘 0.5；数量四舍五入为 0 的订单删除，但不直接改 farmer、hands、路线、购买或非动物品订单。[VERIFY: kaggle_Kaggriculture/model/v12_incumbent_r002/main.py:1-7] [VERIFY: kaggle_Kaggriculture/model/v12_incumbent_r002/main.py:41-95]

它在 V11 Round 3 的全新 100-source 双席位全矩阵中排第 1：3,000 局 2318/117/565，平均金币差 +3,832.07；对直接父 `learned_router` 为 128/0/72。[VERIFY: kaggle_Kaggriculture/model/v11_iterative_league/runs/round_003/report.md:7-22] [VERIFY: kaggle_Kaggriculture/model/v11_iterative_league/runs/round_003/report.md:43-45]

### A2

A2 并没有另写一个新策略；它实例化 V12A `BranchGuardAgent`，唯一显式配置是 `require_unlocked_shop_demand=False`。[VERIFY: kaggle_Kaggriculture/model/v12a2_no_shop_gate/main.py:14-31]

因此 A2 的实际残差是：

- 只在 day 10/17/24 生效；
- 只在 Router 选择 V5/V8 时生效；
- 不再根据已解锁 shop 逐商品过滤；
- 同回合存在 DROP/PLACE 时跳过；
- 动物品计划卖出总量小于 4 时跳过；
- 节流后的保守 shed 估计超过 90 时跳过；
- 通过后仍按 0.5 处理动物品订单。

上述判断顺序和阈值均来自真实服务代码。[VERIFY: kaggle_Kaggriculture/model/v12a_terminal_branch_guard/main.py:59-67] [VERIFY: kaggle_Kaggriculture/model/v12a_terminal_branch_guard/main.py:303-330] [VERIFY: kaggle_Kaggriculture/model/v12a_terminal_branch_guard/main.py:332-379]

A2 的成功说明的不是“所有 guard 都有效”，而是**删除错误的 shop-product gate 后，分支/容量保护下的稀疏节流有效**。原 V12A 的关键 W→L 来自同一 top day 内 WOOL 有时节流、有时不节流，导致库存与市场反馈路径不一致；删除 shop gate 可精确恢复该失败源。[VERIFY: kaggle_Kaggriculture/model/v12a_terminal_branch_guard/MECHANISM_DIAGNOSIS.md:5-14] [VERIFY: kaggle_Kaggriculture/model/v12a_terminal_branch_guard/MECHANISM_DIAGNOSIS.md:28-31]

## 2. 八个进一步改进方向

| # | 方向 | 因果假设 | 预计作用面 | 已知反例 / 泄漏风险 | 审计决策 |
|---:|---|---|---|---|---|
| 1 | **A2 去除 WOOL 节流** | WOOL 的市场容量和价格反馈不同于 MILK；已观察到的主要 W→L 首分歧正是 WOOL。让 WOOL 恢复父销量，可保留 A2 对 MILK 的季中供给平滑，同时减少 WOOL 的路径翻转。 | 仅 top days、V5/V8 分支、A2 guard 通过的 WOOL SELL；worker 完全不变。 | 既有 no-WOOL 数字是在看到商品级失败后选择，存在选择偏差；而且旧实现仍保留 shop gate，不能直接当作本候选。 | **预注册 C1** |
| 2 | **终局补卖提前到 step 716** | step 718 补卖在开发轨迹中零触发，可能因为父策略已在最后一步覆盖库存；step 716 可在最后 3 个可行动回合利用空槽，降低少量未售库存，并减少最后一步同回合冲击。 | 只新增最后 3 步 shed 剩余库存的 SELL，按当前价值排序，不改变已有订单。 | 现有 step718 零触发只证明死代码，不证明提前后有收益；最新线上抽样的 10 局 A2 全部终局 shed=0，提前卖还可能压低后两步价格。 | **仅探索性 screen** |
| 3 | 只在 V8 分支节流 | 原始 Router 对 Top-days 的弱点主要集中在 V8，减少 V5 上干预或许更稳。 | 删除 A2 在 V5 分支的全部动物品残差。 | 强反证：r002 在 V5 分支对 raw learned 的直接优势为 76.47%；A2 在 V5 分支对 r002 仍为 58.82%。关闭 V5 会丢掉两层正增益。 | **暂缓，不进本轮** |
| 4 | 按 day 单独选择 10/17/24 | 三个日期的市场冲击强度可能不同，删除一个无效日期可降低干预剂量。 | 只改触发日期集合。 | 当前没有独立的逐日因果消融；从同一 formal 挑最佳日期属于 7 组合多重试验，极易过拟合。 | 先做诊断，不参赛 |
| 5 | 动态节流比例 / shed 风险分段 | 当 shed 紧张时由 0.5 放宽到 0.75/1.0，可避免现金和容量链式伤害；空仓时维持 0.5。 | 只改已批准动物品订单数量。 | 当前 `maximum_post_sale_shed=90` 在 v3/v4 没有触发；直接扫阈值/比例是参数寻优。长期扣货曾造成仓满、动物归零和巨额亏损。[VERIFY: kaggle_Kaggriculture/model/v11_iterative_league/runs/round_002/strategy/independent_review.md:23-45] | 需要先校准触发率 |
| 6 | 不确定性感知的对手供给 gate | 对手潜在供给高且估计置信时才节流，低置信时 fail-open，可把固定日期规则升级为闭环市场响应。 | 动物品 SELL 的低频 gate，不改生产。 | 社区证据明确指出 MILK/WOOL 恰是最难识别的商品，价格地板、DROP/overflow 会破坏可识别性；没有本地 MAE 校准前不能上线。[VERIFY: kaggle_Kaggriculture/model/community_research/2026-08-23/INDEX.md:25-30] | 中期研究，不进本轮 |
| 7 | 第二决策点的完整专家 Router | step72 之后继续 shadow V5/V8，到市场或对手结构可识别时做一次完整专家切换，可解决共同固定开局导致的早期不可辨识。 | 完整专家选择，不拼接单个 worker 动作。 | 当前 Router 在 step72 后只推进已选专家；晚切需要继续维护多专家状态并证明状态兼容，工程风险明显高于市场残差。[VERIFY: kaggle_Kaggriculture/model/v10_replay_lolo_router/router.py:260-356] | 架构型 V14 方向 |
| 8 | 对局池上的混合/随机化专家 | 循环克制意味着单一最优专家可能不存在；按 payoff matrix 求 maximin 混合可降低被针对。 | 每局选择完整专家，局内不切 worker。 | 社区的六策略循环是作者自报且无法证明当前 meta；本地 Round 1–3 也显示强专家仍有特定弱对手。混合策略可能降低对当前 r002/A2 的直接胜率。[VERIFY: kaggle_Kaggriculture/model/community_research/2026-08-23/INDEX.md:28-33] | 作为联赛鲁棒性研究 |

## 3. 为什么 C1 是主候选、C2 仅探索

### C1：A2 + no-WOOL

**独立证据链：**

1. V12A 的确定性主要 W→L 首分歧是 WOOL，且删除 WOOL 节流在 v3/v4 的共同对手净得分分别为 +7.54pp/+9.13pp、最差单对手均为 0pp。[VERIFY: kaggle_Kaggriculture/model/v12a_terminal_branch_guard/MECHANISM_DIAGNOSIS.md:19-31]
2. 删除 MILK 的旧消融在 v3/v4 直接亲子仅 27.78%/30.56%，所以不能把所有动物品节流都删掉。[VERIFY: kaggle_Kaggriculture/model/v12a2_no_wool_throttle/README.md:5-10]
3. A2 的 formal 提升证明 no-shop 版本是当前正确底座，而不是旧 V12A。[VERIFY: kaggle_Kaggriculture/model/v12_validation/runs_v5/formal/audit.json:175-324]

**实现约束：**新候选必须同时满足 `require_unlocked_shop_demand=False` 和 `products=ANIMAL_PRODUCTS-{"WOOL"}`。现有目录 `v12a2_no_wool_throttle` 不能直接复用：它继承 V12A 默认配置，覆写只删除 WOOL，并没有关闭默认值为 true 的 shop gate。[VERIFY: kaggle_Kaggriculture/model/v12a2_no_wool_throttle/main.py:23-35] [VERIFY: kaggle_Kaggriculture/model/v12a_terminal_branch_guard/main.py:59-67]

**可证伪条件：**在全新 source 上，只要对 A2 的得分率不高于 50%，或任何日期/席位出现大幅负向集中，就否定“WOOL 是剩余主要负贡献”的假设。

### C2：A2 + terminal-716

V11 已有的 `terminal_clearance_fill` 设计起点本来就是 step716：只用空闲市场槽、扣除父策略已卖数量、按当前总价值排序补 SELL。[VERIFY: kaggle_Kaggriculture/model/v11_iterative_league/mutation_catalog.py:167-198]

V12A/A2 把起点改为 718；函数只在阈值后运行，仍不覆盖已有订单且最多 10 条。[VERIFY: kaggle_Kaggriculture/model/v12a_terminal_branch_guard/main.py:189-219] [VERIFY: kaggle_Kaggriculture/model/v12a_terminal_branch_guard/main.py:363-376]

开发 screen 中 step718 fill 为零触发，Round 2 代表性轨迹却记录到 2 个 terminal-unsold 事件，说明“最后库存风险存在，但 718 safety net 太晚或被父策略覆盖”值得用极窄窗口验证；这不是收益证据。[VERIFY: kaggle_Kaggriculture/model/v12a_terminal_branch_guard/MECHANISM_DIAGNOSIS.md:28-29] [VERIFY: kaggle_Kaggriculture/model/v11_iterative_league/runs/round_002/strategy/diagnosis.md:63-79]

**可证伪条件：**候选必须真实触发且终局剩余库存下降；若对 A2 得分率不高于 50%，或提前卖出造成平均金币差明显下降，即否定。

## 4. 最新公开 Replay 的机制核对

本节通过 Kaggle CLI 只读获取 `55713355`（A2）和 `55713359`（r002）各自最新 10 场公开 Replay；它们只用于发现机制，已列入 V13 fresh panel 永久排除。复核时把 replay 中 seat0 的 shared observation 与各自席位的 private observation 合并，再逐步重放本地 agent；20/20 局均 719 次动作完全一致，排除了“本地审计的不是线上策略”。

CLI 快照显示 A2/r002 分别有 63/68 条 episode 元数据（含各自 validation），提交 Rating 分别为 2424.6/2030.9。抽样不是同对手、也不是随机样本，因此不能比较两个版本的胜率。

A2 最近 10 局为 6/0/4。四场败局如下：

| Episode | 席位 | 对手 | 金币差 | Router 分支 | A2 节流 | terminal / 终局 shed |
|---:|---:|---|---:|---|---|---|
| 97689936 | 0 | NCK | -1,007 | V8 | 5 step；MILK 3、WOOL 3 | 0 / 0 |
| 97699112 | 0 | brightest66 | -391 | V8 | 5 step；MILK 2、WOOL 3 | 0 / 0 |
| 97703736 | 0 | Ryo | -726 | V8 | 5 step；MILK 3、WOOL 3 | 0 / 0 |
| 97706034 | 1 | Emmanuel Lo | -1,088 | V8 | 5 step；MILK 3、WOOL 3 | 0 / 0 |

这四局支持“剩余弱点仍集中在 V8/动物品市场时序”，但**不证明 WOOL 是败因**：A2 的多场胜局也有完全相同的 5-step、MILK+WOOL 触发签名。C1 仍需闭环新 panel，而不能把这四局当作反事实胜局。

这批线上证据反而削弱 C2：10 局 A2 均 `terminal_fill_steps=0` 且终局 shed=0；r002 最近 10 局也只有一场胜局剩余 1 只 SHEEP，其余为 0。因此 C2 只能检验“提前两步是否改变成交时序”，不能再宣称修复已观察到的终局残货。

复现命令：

```bash
kaggle competitions submissions kaggriculture --csv
kaggle competitions episodes 55713355 --format csv
kaggle competitions episodes 55713359 --format csv
kaggle competitions replay <episode_id> --path <temporary_directory> --quiet
```

## 5. 明确暂缓的方向

### V8-only throttle

第 2 轮确实显示 raw `learned_router` 对 `v8_topdays` 的弱点集中在 V8 分支，V5 分支反而强。[VERIFY: kaggle_Kaggriculture/model/v11_iterative_league/runs/round_002/strategy/independent_review.md:7-14]

但这不足以推出“A2 应删除 V5 节流”。同一条 V5 分支上，r002 已显著优于 raw learned，A2 又继续优于 r002。关闭它相当于一次删掉两层已验证收益，风险大于潜在简化收益。因此本轮不把它放入候选池。

### 价格门槛、价值排序与长期扣货

`premium_floor_guard` 在新面板对直接父只有 8/0/192，长期撤单造成仓库占满、动物归零和现金链断裂；`value_slot_priority` 的历史直接亲子得分率也只有 4.5%。这两类不是“参数略错”，而是机制级反证。[VERIFY: kaggle_Kaggriculture/model/v11_iterative_league/runs/round_002/strategy/independent_review.md:23-47]

### 重新引入 shop-product gate

社区的 shop demand 研究值得用于路线专家或特征，但 V12A 已证明把“是否有已解锁 shop”直接当作动物品节流开关会制造同一日不一致路径。A2 的核心成功恰恰是删除它，所以本轮不得换个阈值重新引入。[VERIFY: kaggle_Kaggriculture/model/community_research/2026-08-23/INDEX.md:29-31] [VERIFY: kaggle_Kaggriculture/model/v12a_terminal_branch_guard/MECHANISM_DIAGNOSIS.md:3-14]

## 6. 双锚点验证要求

每个新候选必须同时对 `v12_incumbent_r002` 和 `v12a2_no_shop_gate`，且两组使用完全相同的 source 列表和双席位；不得把两个锚点各自的可用日期取交集后伪装成同周期。

建议固定如下两阶段设计：

1. **Screen panel**：在冻结候选代码之后选一批全新 source；C1、C2 分别对 r002/A2，所有 source 双席位。按 `min(score_vs_r002, score_vs_A2)` 排序，任一锚点低于 50% 即淘汰；C2 还必须真实触发且相对 A2 非等价。只选最多 1 个进入 confirmatory。
2. **Confirmatory panel**：再换一批完全未暴露 source；只评 screen 冠军对两个锚点。报告 W/T/L、纯胜率、得分率、平均金币差、日期、席位、Router 分支、触发次数，并用按日期分层的 source-cluster bootstrap 给 95% CI。
3. **晋级门槛**：对 A2 的得分率点估计 >50%，95% CI 下界 >50%；对 r002 的得分率同样要求下界 >50%；全部对局 `DONE/DONE`、零 stderr、零 fallback。没有同时过两个锚点，就不能称为 A2 的进一步改进。
4. **暴露隔离**：永久排除 Router-fit、V11 Round1–3、V12 v3/v4 screen、frozen_v5 formal、全部 QA/smoke/机制消融 source；sealed/final test 保持 0 次读取。

得分率必须定义为 `(胜 + 0.5×平) / 总局数`，并与“纯胜率”分列，避免把两者混称。

## 7. 社区研究如何影响本轮

- 社区建议的正确部分是“真实败局 → 单机制 challenger → 多对手、双席位、新 episode 验证”；这与 A2 的因果修复路径一致。[VERIFY: kaggle_Kaggriculture/model/community_research/2026-08-23/INDEX.md:30-33]
- 共享市场意味着只看最终金币或自博弈不够，必须检查不同供给风格、双席位、胜率和金币差。[VERIFY: kaggle_Kaggriculture/model/community_research/2026-08-23/INDEX.md:32-33]
- 对手库存估计和多专家混合值得做，但目前都缺少针对 MILK/WOOL 的本地可识别性校准或当前 meta 的独立复核，所以只能列为中期研究，不能挤占本轮两个低风险残差的验证资源。[VERIFY: kaggle_Kaggriculture/model/community_research/2026-08-23/INDEX.md:25-30]
- 端到端低层 PPO、继续堆同质 BC 数据已有负面社区证据；本轮坚持完整专家 + 稀疏市场残差，不重启原子动作 PPO。[VERIFY: kaggle_Kaggriculture/model/community_research/2026-08-23/INDEX.md:35-43]

## 8. 验证清单

- r002 节流范围：`v12_incumbent_r002/main.py:1-7,41-95`
- A2 唯一显式配置：`v12a2_no_shop_gate/main.py:14-31`
- A2 guard 判断：`v12a_terminal_branch_guard/main.py:59-67,303-330`
- A2 执行和 fail-open：`v12a_terminal_branch_guard/main.py:332-379`
- A2 formal 结果：`v12_validation/runs_v5/formal/audit.json:175-324`
- no-WOOL 旧消融与选择偏差：`v12a_terminal_branch_guard/MECHANISM_DIAGNOSIS.md:19-31`
- 旧 no-WOOL 并非 no-shop 子代：`v12a2_no_wool_throttle/main.py:23-35`
- step716 terminal 原型：`v11_iterative_league/mutation_catalog.py:167-198`
- Router 单次 step72 完整专家选择：`v10_replay_lolo_router/router.py:260-356`
- 社区证据边界：`community_research/2026-08-23/INDEX.md:25-43`
