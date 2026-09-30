# V14 社区前沿与第一性原理机制审计

> 调研时点：2026-08-24 00:42（Asia/Taipei，2026-08-23 16:42 UTC）  
> 范围：只读复核社区材料、当前 V13C/A2 结果与 Kaggriculture 1.32.7 引擎；未改候选代码、未运行新正式验证、未提交。  
> 获取方式：Kaggle CLI 2.2.3 / 官方 API；没有使用浏览器，也没有保存或输出凭据。

## 结论先行

V13C 的下一次跃迁不应来自另一个全局出售倍率，也不应来自端到端 PPO。当前最大的结构性缺口是：**我方 Router 在 step 72 选择的是“给定 shop 与 seat 的平均最优完整专家”，并没有估计对手会走哪个生产分支，更没有优化专家之间的条件对局收益。**

本地核验 `learned_router_weights.npz`：61 个输入特征只有 9 个拥有非零系数，即 `seat` 和 8 个 shop；18 个市场特征、双方全部公开农场特征的系数都为零。服务代码确实只在 step 72 选择一次完整专家，之后整季不再重选。[VERIFY: `model/v10_replay_lolo_router/router.py:28-50,94-127,238-254,260-356`]

这不是小问题。V13C 对 A2 的既有 200 场确认结果按双方最终分支重分组后为：

| V13C 分支 | A2 分支 | W/T/L | 纯胜率 | 得分率 |
|---|---|---:|---:|---:|
| V5 | V5 | 3/20/3 | 11.5% | 50.0% |
| V5 | V8 | 6/0/11 | 35.3% | 35.3% |
| V8 | V5 | 11/0/6 | 64.7% | 64.7% |
| V8 | V8 | 75/35/30 | 53.6% | 66.1% |

这些是对已经打开的 V13 confirmatory 原始结果做的**诊断重分组**，不是新的留出验证。它说明三个事实：

1. 专家收益显著依赖“自己的分支 × 对手分支”，全局平均分会混掉这个交互；
2. V5 对 V8 是明确弱配对，V8 对 V5 则明显更强；
3. 55 场平局中，20 场来自 V5/V5，35 场来自 V8/V8。只优化 Kaggle 得分率而不处理同分支平局，不可能满足“对 A2 纯胜率 65%”目标。

因此第一优先级应是两层组合，而非一个大而全的新模型：

- **G1：分支对分支的完整专家 Best-Response Router**，先消灭 V5→V8 这类系统性错误配对；
- **G2：同分支下的对手供给解码 + product-aware counter-slot 市场编译器**，在不改出售总量的第一阶段优先转化 V5/V5、V8/V8 平局。

结构化市场预测、现金/仓位影子成本、晚季风险控制是第二阶段；故意制造供给冲击只能作为窄反事实实验。操纵 shop RNG 和用市场去攻击当前 step-72 Router 均不应立项：前者没有可观测 seed 时在期望上没有优势，后者被“市场系数全为零”直接否定。

## 1. 本次社区增量

### 1.1 最新 discussion 列表

以下命令检查了 `new` 前 3 页，并用 `topic-messages` 读取正文：

```bash
kaggle competitions topics list kaggriculture --sort-by new --page 1 --format json
kaggle competitions topics list kaggriculture --sort-by new --page 2 --format json
kaggle competitions topics list kaggriculture --sort-by new --page 3 --format json
kaggle competitions topic-messages kaggriculture 737128 --sort-by old --page-size -1 --format json
```

在 `2026-08-23T00:00:00Z` 之后只有一篇新主题：[737128 — Hello! It's nk.](https://www.kaggle.com/competitions/kaggriculture/discussion/737128)，发布时间 `2026-08-23 15:24:33 UTC`，当时 1 票、0 评论。到本次检查时没有 8 月 24 日新增主题。

旧主题在 8 月 23 日的策略性增量也很少：

- [736567](https://www.kaggle.com/competitions/kaggriculture/discussion/736567) 的最新实质性评论称，固定生产路线上的市场层能得到边际优化，但一旦替换作物或动物，整条耦合路径会崩掉、梯度失效。它支持“完整专家 + 稀疏残差”，不支持拼接局部生产动作。
- [736439](https://www.kaggle.com/competitions/kaggriculture/discussion/736439) 8 月 23 日的新评论仅讨论实验 dashboard，没有新策略证据。
- [736219](https://www.kaggle.com/competitions/kaggriculture/discussion/736219) 只有一条询问榜首目前使用 RL 还是规则的评论，没有作者回答。

结论：本轮社区增量中没有可直接复制的高分 baseline；唯一需要认真拆解的是 737128 的 MELON 价格预测。

### 1.2 737128 与三个公开 Notebook

作者报告了三条工作线：未来 MELON 价格决策树、Top 玩家行动范围分析、成本与价格分析，并发布了一个将浅树嵌入规则 Agent 的版本：

- [Predict future melon prices](https://www.kaggle.com/code/nagatakengo/predict-future-melon-prices)
- [Range of action](https://www.kaggle.com/code/nagatakengo/range-of-action)
- [Costs](https://www.kaggle.com/code/nagatakengo/costs)
- [Agent notebook](https://www.kaggle.com/code/nagatakengo/kaggriculture)

本次通过 `kaggle kernels pull ... -m` 下载并审阅。抓取到的 Notebook SHA256 分别为：

| Notebook | SHA256 |
|---|---|
| `predict-future-melon-prices.ipynb` | `a9f1b76d28a2aae893a21334c1fcc9aa770579dc535c0d224f7ea2afbb761c90` |
| `range-of-action.ipynb` | `d9100ec8e296e370b2b26e118013932bf01070daaaa4ddcdb3134c649977cce5` |
| `costs.ipynb` | `22f759b63d8b9b57ebb8cd2c72ca1c85ca1eb8dd500db2d189138323fd9c2360` |
| `kaggriculture.ipynb` | `3b8bd56503e2b665b46fa5597560d711ff30f2eb1edf93f0cdd1048999c22064` |

#### 论坛/Notebook 事实

- 数据说明为 298 场、214,560 行，按 `game_id` 做 80/20 拆分，而不是随机拆行；这个处理是正确的基本防泄漏动作。
- 目标是未来 12/24/48 回合 MELON 最高价。作者报告完全生长的 Decision Tree 的 MAE 为 0.048/0.108/0.109；用于提交的 `max_depth=3` 树，MAE 3.176、RMSE 5.129。
- 浅树最终实际只使用 `step/current_price/market_stock`，虽然接口还传入自己的 shed、过去价格、过去库存和过去出售量。
- 提交逻辑在 `current_price >= predicted_future_max` 时卖出，否则持有；step 710 后强制卖出。
- `range-of-action` 主要比较两个样本轨迹，观察到解锁时间与若干行为高度相同，并推测中上游玩家共享同源 Notebook。

#### 本地推断

这些结果不能被解释为“未来价格已被高精度预测”：市场价格本来就是当前 inventory 的确定函数，而未来最高价标签又是在原数据策略继续行动的条件下生成的。高度同源的路线、确定性需求钟和深树记忆会让观测预测很容易，但它没有回答反事实问题——**如果我现在不卖、分批卖或多卖，价格和对手随后行为会怎样改变。**

浅树没有 opponent、shop composition、未来确定性 demand 或预测不确定性，也没有强对手 head-to-head 结果。它适合作为“结构化预测值得做”的提示，不适合原样 graft 到 V13C。

#### 可证伪假设

将“预测未来绝对最高价”改为“比较有限动作集合的反事实 margin”可能有效：对同一个现态分别评估 `parent quantity / half / hold-one-tick / demand-sized clip`，使用引擎精确价格曲线、确定的下一次 town demand 与对手供给区间。若在新 panel 上不能提高纯胜率，或只提高金币而增加负局，则否定该机制。

## 2. 旧社区创意的重新解释

### 2.1 共享市场不是一个附加特征，而是唯一的交互通道

[732121](https://www.kaggle.com/competitions/kaggriculture/discussion/732121) 指出对手通过共享库存改变价格；[734412](https://www.kaggle.com/competitions/kaggriculture/discussion/734412) 进一步给出 shop demand hole、1.32.7 价格曲线修正和“最大金币不等于最大胜率”的讨论。本地 1.32.7 引擎确认：

- 价格是 inventory 的确定函数；[VERIFY: installed `kaggriculture.py:27-58,192-212`，文件 SHA256 `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`]
- town shop 每 4 回合、town center 每 24 回合消耗，当前已解锁 shop 的下一次需求完全可计算；[VERIFY: installed `kaggriculture.py:728-749`]
- 市场订单按 slot 处理；一个 slot 内的大额订单逐单位执行完，才进入下一个 slot；同 slot 双方每个单位使用同一个 commit 前报价。[VERIFY: installed `kaggriculture.py:544-628`]
- 除 WHEAT/FERTILIZER 外，商品不能从市场买回；价格为 1 时出售不会增加公开 market inventory。[VERIFY: installed `kaggriculture.py:596-605,652-671`]

由此推导出两个此前没有被充分利用的闭环量：

1. **对手逐回合净出售量**：对 premium 商品，在非价格地板区，`opp_sell = Δmarket_inventory + town_demand - own_sell`，可在下一观察步精确恢复；到地板后改为区间而不是点估计。
2. **订单槽位的博弈价值**：相同商品若我方排在对手更早的 slot，我方先吃掉高价段；若排在同一 slot，双方逐单位共享 commit 前报价。出售总量不变，仅改变商品顺序也可能改变最终 margin。

这比“看见价格跌了就少卖”更接近真正的对手建模。

### 2.2 对手库存估计应从点预测升级为可识别区间

[737027](https://www.kaggle.com/competitions/kaggriculture/discussion/737027) 报告 CARROT/TOMATO/EGG 可近乎恢复，MILK/WOOL 因价格地板、DROP 与 overflow 更不确定。该帖的关键不是一个神奇库存数字，而是“何时不可识别”。

正确用法应是：

- 对非地板 premium 商品逐回合精确解码 opponent sell；
- 用公开 tiles 中的 crop age、animal type/placed day/yield cadence 预测未来产能；
- hidden shed 只维护 `[lower, upper]`，不把中点伪装成事实；
- uncertainty 超阈值时保持 V13C，而不是强行切换市场动作。

这和失败的 V12B 不同：V12B 是粗粒度市场反馈/领先门，金币略增却更常输；这里先验证观测量的可识别性，再让它只控制订单排序或少量离散残差。

### 2.3 非传递专家池要求条件 payoff，而不是静态混合

[736439](https://www.kaggle.com/competitions/kaggriculture/discussion/736439) 自报六专家 960 局存在 `30-2 / 21-11 / 24-8` 循环，并给出 `opponent + opening` 的 outcome accuracy 67.5%，明显高于仅使用 opponent 或 opening 的 56.5%。这不证明 PPO 最优，但支持 payoff matrix 的交互项。

本地 `v12d_static_minimax_mixture` 已证明静态混合会退化为单一 incumbent；新方向必须是：

```text
公开 shop / seat
        │
        ├─ 预测已知对手的完整专家分支 e_opp
        │
        └─ 从兼容完整专家中选择 argmax_e Q(e_self, e_opp, context)
```

不是按平均收益选 `argmax_e V(e, context)`，也不是把多个专家逐动作拼接。

## 3. 四个维度的原创候选

下表中的“事实”来自论坛、引擎或既有实验；“推断”是由事实推出的设计；“假设”必须在新闭环 panel 上被证伪。

| ID | 维度 | 机制 | 与既有失败的区别 | 风险 | 优先级 |
|---|---|---|---|---|---|
| G1 | 自身优化 + 对手识别 | **Branch-pair Best-Response Router**：在 step72 用同一公开 selector、对手 seat 和共同 shop 精确预测 A2 分支，再以 `Q(own expert, opponent branch, shop, seat)` 选完整专家 | 不是静态 mixture，也不是晚期不兼容切线；四个专家前 72 步已逐动作验证同前缀 | 容易过拟合 A2 身份；必须设 unknown fallback 和谱系留出 | **P0** |
| G2 | 对手识别 | **Opponent Supply Decoder**：从市场差分扣除 own sale 与确定性 town demand，维护逐商品 opponent sell 流；公开农场推未来产能，floor 区只给上下界 | 不是 V12B 的粗价格 gate，也不把 MILK/WOOL 点估计当真 | DROP/overflow/floor 造成不可识别；需 coverage 与 MAE/interval coverage 门 | **P0** |
| G3 | 主动干扰 | **Product-aware Counter-Slot Compiler**：总出售量不变，按预测的对手商品/slot 和本地价格斜率重排现有 SELL | 不是旧 premium-first 的统一排序；它显式针对同商品对手 slot，第一版不扣货、不加量 | 预测错商品会让别的商品失去先手；必须保留订单依赖与资金顺序 | **P0** |
| G4 | 市场预测 | **Robust Market MPC**：结构化模拟未来 4/24 回合确定需求、own plan 与 opponent supply interval，只在有限残差集合中选最大 worst-case margin / win score | 不是 737128 的观测式绝对价格树，也不是 V9 固定延迟两回合 | 对手会响应；模型误差可把 hold 变成仓满/现金断裂 | P1 |
| G5 | 自身优化 | **Route-obligation Liquidity Guard**：若当前节流会导致下一日固定 BUY_LAND/ANIMAL/SEED/HIRE 无法成交，则取消节流；同时预测 end-of-day carried drop 和下一次 yield 后的 shed 占用 | 不是 V13D 的“公开金币领先就取消”，而是自己路线的真实现金义务和容量约束 | 需要可靠识别路线义务；阈值扫描易过拟合 | P1 |
| G6 | 自身优化 | **Compatible-continuation second decision**：新造共享更长前缀的完整专家，在 day7/10 依据已暴露 shop 与对手产能再选一次 | 与“现有 V1/V2/V5/V8 在 step72 后硬切”不同；后者状态不兼容已被否定 | 工程量大，专家多样性不足会退化 | P1-架构 |
| G7 | 风险控制 | **Liquidation-adjusted lead policy**：只在晚季使用 `bank + 可变现库存区间 - 未来义务` 的领先概率，领先降方差、落后选择高方差 sale schedule | 不是 V13D 的早中期公开 bank 单点 gate | 胜率模型校准困难；必须只做晚季窄动作 | P1/P2 |
| G8 | 自身优化 | **Safe work-conserving repair**：仅当父专家 PASS/无效移动且脚下存在确定合法高价值动作时执行，记录对后续路线是否产生 divergence | 不是重写 worker policy；论坛 walking 结果只提供机制动机 | 顶级路线很可能已无覆盖；状态分歧可能破坏后续计划 | P2 |
| G9 | 主动干扰 | **Asymmetric supply attack**：仅在估计对手即将出售量显著大于我方时，提前小额 dump，使对手价格损失大于自己机会成本 | 不是长期扣货/统一价格门槛；每次用精确曲线算外部性 | 容易双输，当前市场 overlay 负例很多 | P2-仅反事实 |
| G10 | 干扰/引擎 | **改变空地数量以移动 shop RNG** | 引擎先按空地消耗 RNG，再抽 shop，机制真实[VERIFY: installed `kaggriculture.py:860-891`] | 看不到 seed 时替代 shop 仍近似均匀，且改地块有生产成本；策略脆弱 | **拒绝** |

## 4. 建议首先实现的 G1 + G2/G3

### 4.1 G1：A2 分支可在 step72 被确定性预测

当前 learned selector 的非零输入只有共同 shop 与 seat。对战 A2 时，我们知道：

- A2 使用同一组 Router weights；
- town shops 对双方完全相同；
- opponent seat 是 `1 - own seat`；
- selector 不读 private，且当前 farm/market 权重均为零。

因此无需猜对手 hidden inventory，便可在 step72 计算 A2 将选 V5 还是 V8。新 Router 的最小实现为：

1. 所有 V1/V2/V5/V8 继续 shadow 0–71，保留现有 prefix gate；
2. 用 opponent-perspective public vector 得到 `predicted_opponent_branch`；
3. 从训练 panel 估计 `Q(e_self, e_opp, shop_signature, seat)`；
4. 只在 cross-fit 支持数与置信下界达标时用 best response，否则回退 V13C 的原选择；
5. 选择后仍由一个完整专家执行整季，V13C 市场残差作为 branch-conditioned wrapper。

应优先测试最小可证伪版本：**当 A2 预测为 V5 时，我方强制 V8；其余保持 V13C。**既有诊断中 `V8 vs V5=11/0/6`，而 `V5 vs V5=3/20/3`，有明确事前方向；但 17/26 场样本很小，只能作为候选依据，不能作为通过证据。

### 4.2 G2/G3：先解码行为，再动订单；第一版不改数量

状态维护建议：

```text
每回合 observation(t)
    ├─ market Δinventory
    ├─ 上回合 own SELL
    ├─ 已解锁 shops + t%4/t%24 → 精确 town demand
    ├─ public opponent crops/animals → future supply capacity
    └─ floor/drop/overflow flags → uncertainty interval
                         │
                         ▼
             opponent sale signature / confidence
                         │
                         ▼
 parent market queue ─ product-aware slot permutation ─ final queue
```

排序目标不能只是“贵的在前面”，建议以：

`priority(product) = expected_opponent_same_turn_volume × local_price_slope × confidence`

为主，并施加硬约束：

- 不改变任何 SELL 数量；
- 不删除 BUY/HIRE/BUY_LAND；
- 不超过 10 个 orders；
- 如果重排会让父策略的资金依赖不成立，整回合回退；
- floor risk 或 classifier confidence 不足时保持父顺序。

第一阶段只做顺序，可以把因果范围压到最小；若连同量排序都无法转化平局，才进入 G4/G9 的数量干预。

## 5. 明确不应重复的方向

| 方向 | 不再做的原因 |
|---|---|
| 再训练端到端原子动作 PPO | 社区 736567/736917 与本地 V3 都显示同质 BC、累积误差、长信用分配和 OOD 失败；当前瓶颈可由低维博弈结构直接描述 |
| 再做静态专家混合 | V12D 的 LOO/maximin 退化为 100% 单一专家；这没有利用 opponent-branch 交互 |
| 重新加入 shop-product throttle gate | A2 的核心收益正是删除该 gate；shop 应进入路线价值/需求预测，而不是成为某商品节流的布尔开关 |
| 固定延迟 2 回合或长期 hold | V9 已证明时间尺度无法抵消数百单位 dump；必须以 demand clock、对手供给和现金/仓位约束计算 |
| 公开 bank 领先就取消节流 | V13D 对 r002/A2 得分率只有 38.19%/48.61%；bank 不是 liquidation-adjusted wealth |
| 716 terminal fill | 18 个已探测末段状态零新增订单；不是当前损失机制 |
| 用市场库存攻击当前 step72 Router | 当前 Router 所有 market 系数为 0，动作无法通过市场特征改变其选择；除非先更换 Router，本机制没有作用通道 |

## 6. 对“纯胜率 65%”目标的现实约束

V13C 对 A2 是 95/55/50，纯胜率 47.5%。在同样 200 场口径下，65% 需要至少 130 胜，即在不新增失败的理想情况下还要净增加 35 胜。G1 主要攻击 20 个 V5/V5 平局和 11 个 V5→V8 失败；它很重要，但单独未必足够。V8/V8 的 35 个平局与 30 个失败仍需要 G3 或真正新的兼容完整专家。

因此建议把 65% 写成**最终确认门**，而不是反复看同一 holdout 后调到 65：

1. 用已暴露 V13 结果只做机制诊断；
2. 在新 screen 上比较预注册的 G1、G3、G1+G3，最多选一个；
3. finalist 在另一批从未暴露的 source 上做 200–400 场 A2 双席位确认；
4. 报告纯胜率与 source-cluster 95% CI，门槛应为纯胜率点估计 ≥65%，并同时对 r002/V13C 及谱系外 sentinel 不出现灾难回归；
5. 如果失败，回到新的训练/screen source 重新提出机制，不能复用已经打开的 confirmatory 做阈值搜索。

如果只为了击败已知 A2，identity-aware best response 很可能提高直接胜率；如果目标是 Kaggle 金牌，必须再加 unknown-opponent fallback 和多谱系 guard，否则得到的只是 A2 专用 exploit。

## 7. 证据层级与出处

### 已验证的本地事实

- V13C 对 A2 为 95/55/50，纯胜率 47.5%、得分率 61.25%；对 r002 为 155/0/45。[VERIFY: `model/v13_dual_anchor_search/FINAL_VALIDATION.md:3-14`]
- V13C 只在 V8 分支删除 WOOL throttle，其余 A2 路径保持。[VERIFY: `model/v13c_a2_v8_no_wool_throttle/main.py:14-59`]
- A2 throttle 仍是 day10/17/24、V5/V8、最小出售量与 shed guard 的稀疏残差。[VERIFY: `model/v12a_terminal_branch_guard/main.py:303-379`]
- learned Router 的 61 个特征中只有 seat 与 8 个 shop 系数非零；这是本次直接读取服务权重得到的事实。权重文件：`model/v10_replay_lolo_router/learned_router_weights.npz`。
- 市场 lockstep、价格曲线、town demand、floor 与 shop RNG 来自本机安装的官方 `kaggle-environments==1.32.7`，源码 SHA256 见上文。

### 社区作者自报，尚未独立复核

- 对手库存估计的商品级 MAE：[737027](https://www.kaggle.com/competitions/kaggriculture/discussion/737027)。
- 六专家非传递对局与 PPO plateau：[736439](https://www.kaggle.com/competitions/kaggriculture/discussion/736439)。
- shop demand/revenue、walking 与 win-risk 讨论：[734412](https://www.kaggle.com/competitions/kaggriculture/discussion/734412)。
- MELON Decision Tree 指标：[737128](https://www.kaggle.com/competitions/kaggriculture/discussion/737128) 及其公开 Notebook。
- compatible-continuation、route portfolio、CMA-ES 等创意清单与作者自报数字：[VERIFY: `competition_description/community_solution_catalog_20260822.json:9-88`]

### 本文原创、待证伪

- A2 opponent-perspective 分支预测 + branch-pair best response；
- opponent sale decoder 驱动 product-aware counter-slot；
- 结构化 robust MPC、route-obligation liquidity guard、late liquidation-risk policy；
- supply attack 的外部性条件与 shop RNG 方向的拒绝结论。

这些都不能在正式新 panel 之前称为有效改进。
