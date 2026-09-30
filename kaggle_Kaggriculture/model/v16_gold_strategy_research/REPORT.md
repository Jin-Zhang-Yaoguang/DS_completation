# Kaggriculture 金牌策略研究：第一轮收敛报告

状态：`RESEARCH_PASS / SUBMISSION_NOT_QUALIFIED`  
日期：2026-08-26  
引擎：`kaggle-environments==1.32.7`

## 结论先行

金牌策略不能再靠 A2 上叠一个局部 counter。当前证据支持四层结构：

1. **生产底座**：用 L0 搜索自有的静态生产 choreography；
2. **运行时修复**：用 L1 做 finance、feed、shed 和路线修复；
3. **市场控制**：把 town-drain 脉冲做市与 Crop 风格连续库存控制分开；
4. **对手与终局**：按复合谱系选择 market/terminal 分支。

S2 town-drain roundtrip 已被证明是真实、可复现的正收益机制，但它通常只贡献约百元到数百元，属于金牌策略的增量层，不是主引擎。最危险的误判是“对手两腿净流为零就安全”：退出 WHEAT 的 order slot 落后时，仍可能系统性亏损。

当前最大的可解释差距来自非 WHEAT 变现：小样本中顶尖策略比 A2 多约 39.5k 非 WHEAT 销售现金，而 WHEAT 净现金差只有约 2.2k。主攻方向应从“继续叠 WHEAT counter”转成“价格感知清算 + 情境化作物组合 + 劳动力资本调度”。

## 1. 第一性原理

官方每回合执行顺序为：

```text
unit actions -> market -> town consume -> decay -> end of day
```

[VERIFY: kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:913] [VERIFY: kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:941]

市场按 order slot 依次执行；同一 slot 的双方逐单位使用相同的 pre-commit inventory 报价，买 WHEAT 使用买后库存报价。[VERIFY: kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:544] [VERIFY: kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:598]

设当前 WHEAT 库存为 `I`，买入 `q`，本回合 town 确定消耗 `D`，下一回合等量卖出：

```text
cost    = sum(p(n), n=I-q ... I-1)
revenue = sum(p(n), n=I-q-D ... I-D-1)
profit  = revenue - cost
```

价格随库存单调不增，所以没有其他 WHEAT 流且完整平仓时 `D>=0 => profit>=0`；但整数报价使大量小仓位利润恰好为零。脚本按精确整数价格枚举 `q`，取达到最大利润的最小数量。[VERIFY: kaggle_Kaggriculture/model/v16_gold_strategy_research/run_l1_s2_pilot.py:122] [VERIFY: kaggle_Kaggriculture/model/v16_gold_strategy_research/run_l1_s2_pilot.py:188]

## 2. 当前顶尖生态

2026-08-25 分区有 688 局、21.47 GB，manifest 与 JSON 为 688↔688。[VERIFY: kaggle_Kaggriculture/model_data/kaggriculture_episodes_index/date=2026-08-25/dataset_metadata.json:2]

当前应按复合谱系去重，而不是只按队名或 field tape：

```text
production choreography
+ opening finance
+ market controller
+ terminal liquidation
```

建议的开发池：

| 宏观谱系 | 代表 | 主要特征 |
|---|---|---|
| crop continuous MM | Crop Dusta | 高作物吞吐、连续 WHEAT 库存控制 |
| animal low-turnover | Ryo | 畜牧、低市场换手 |
| mixed labor | Subramanya | 混合作物、大 labor |
| goose/livestock | tetsuya | goose/畜牧路线 |
| shared choreography | tyz / Blu3s / Kronki-like | 生产同源、市场层分叉 |

8 月 25 日样本对 Crop、Ryo、tetsuya 的当前版本覆盖较好；Sub、Blu3s 仍是小样本；Kronki 等 8 月 26 日新提交尚未进入完整分区。因此该池可用于 development，不可封成 current formal。

## 3. WHEAT 的因果结果

### 3.1 tyz 脉冲做市

选择 8 月 25 日 tyz 最大 EpisodeId 的 24 局，逐 transition 用官方 1.32.7 重放真实成交。共复核 `24*719=17,256` 个 transition，双方现金和市场 WHEAT 库存与 Replay 全部一致。

| 指标 | 结果 |
|---|---:|
| 触发局 | 24/24 |
| roundtrip | 2,270 |
| 配对 WHEAT | 108,778 |
| gross P&L | +11,293 |
| 每局 P&L 中位数 | +597 |
| P&L / 绝对胜差中位数 | 18.41% |
| 静态扣除后翻转的已有胜局 | 1 |

代表局 `99288516` 中，85 组实际完整往返贡献 472；移除这些同槽交易后 tyz 从 122,667 降至 122,195，对手仍为 121,233。[VERIFY: kaggle_Kaggriculture/model_data/kaggriculture_episodes_index/date=2026-08-25/data/99288516.json:1]

### 3.2 关键反例：净流为零仍会亏

tyz 对 `u` 的两局 roundtrip P&L 分别为 `-985` 和 `-871`。双方两腿净流可以为零，但对手若在更早的退出 slot 卖回 WHEAT，会先补库存、压低我方后续报价。[VERIFY: kaggle_Kaggriculture/model_data/kaggriculture_episodes_index/date=2026-08-25/data/99404999.json:1]

因此 opponent shadow 至少必须预测：

- 当前和下一回合 WHEAT 买卖量；
- 退出 WHEAT 所在 slot；
- 对手可售库存区间；
- 镜像/同步流概率。

### 3.3 Crop 不是 tyz 的缩小版

同口径的 24 局 Crop 样本只有 399 次 roundtrip、6,078 单位、总 P&L `+600`，每局中位 `+25.5`，没有翻转胜局。Crop 的核心更接近连续库存缓冲、feed 管理和共享市场控制，不能用单一 `BUY -> 下一步 SELL` 模块替代。

## 4. 生产与变现差距

这一节只使用 3 局、6 个顶尖 agent 的可审计画像，并让 A2/r002 在相同 3 个 seed、双席位运行；它用于提出候选，不用于估计胜率。三个 Replay 由官方 1.32.7 固定动作重放到最终奖励逐值一致。[VERIFY: kaggle_Kaggriculture/model_data/kaggriculture_episodes_index/date=2026-08-25/data/99288516.json:1] [VERIFY: kaggle_Kaggriculture/model_data/kaggriculture_episodes_index/date=2026-08-25/data/99288626.json:1] [VERIFY: kaggle_Kaggriculture/model_data/kaggriculture_episodes_index/date=2026-08-25/data/99288624.json:1]

| 指标 | Top6 | A2-6 | 差异/解释 |
|---|---:|---:|---|
| reward 中位数 | 106,979 | 52,010 | 对手不同，不作胜率解释 |
| 非 WHEAT 销售现金均值 | 123,077 | 83,607 | Top +39.5k |
| WHEAT 净现金均值 | 5,865 | 3,678 | Top +2.2k |
| 非 WHEAT 实际售量均值 | 963 | 987 | Top 反而少 2.4% |
| 非 WHEAT pooled 实现价 | 127.8 | 84.7 | Top +51% |
| 作物 harvest 均值 | 816 | 742 | Top +10.0% |
| 动物产品 harvest 均值 | 384 | 395 | Top -2.8% |
| hand-days 均值 | 289.7 | 277 | Top +12.7 |
| 第三块地中位日 | day 10 | day 11 | Top 早一天 |

核心不是“生产更多一切”，而是：

1. 生产更值钱的组合；
2. 在更好的库存区间和 slot 卖出；
3. 避免与高同源对手同步砸价；
4. 用更平滑的营运资本支撑作物和 labor。

市场价格会在每个 order slot、每个成交单位后变化，mirror self-play 会把同步抛售放大成极端低价，因此必须在混合谱系面板确认。[VERIFY: kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:562] [VERIFY: kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:612]

A2 在三个 seed 上成功购买的种子组合完全固定；同一 Crop Dusta 的两局则明显切换作物组合。这与 A2/r002 主要继承冻结动作带的实现一致：r002 只在指定日期缩减动物 SELL，不改变 farmer/hand/route/non-animal 生产骨架。[VERIFY: kaggle_Kaggriculture/model/v12_incumbent_r002/main.py:1] [VERIFY: kaggle_Kaggriculture/model/v12_incumbent_r002/main.py:74]

三个优先候选：

### P0 非 WHEAT 价格感知清算器

- 对 `CARROT/MELON/STRAWBERRY/EGG/MILK/WOOL` 计算未来 4/24-step town demand、对手流和 shed 压力；
- 预计涨价且预测 shed `<=85` 时延后；预计跌价或仓容紧时提前；
- 第一版关闭 WHEAT MM，隔离收益。

开发门：非 WHEAT pooled 实现价 `+15%`，实际售量不低于 A2 的 `98%`，shed 丢弃中位数 `<=12`，paired reward CI 下界 `>0`。

### P1 情境化 crop portfolio

- 按早期 shop multiset、当前价格/库存、动物 feed 负担，在 3–5 个完整可执行 crop 模板中选择；
- 必须连同 BUY_SEED、worker route、sell schedule 一起切换，不能只改种子单。

开发门：crop harvest `+5%`、非 WHEAT 收入 `+10%`、seed spend `<=A2+5%`、terminal seed 价值不高于 A2。

### P2 资本/劳动力调度

- 搜索“第三块地提前一天 + day10 后在任务积压充分时维持 12 hands”；
- 不做无条件多雇，新增成本必须由 harvest 增量覆盖。

开发门：新增 hire/land 成本 `<=2.5k`、crop harvest `+5%`、paired reward `+3k`、shed loss 不增加。

终局清仓和 overflow 继续作为 fail-safe，不作为主搜索轴：小样本中 Top 终局残货中位数反而高于 A2，说明继续挤压 terminal leftovers 不是 39.5k 主差距。

## 5. 本地闭环实验

所有实验由 [run_l1_s2_pilot.py](./run_l1_s2_pilot.py) 重跑。脚本把状态明确标为 `MECHANISM_PILOT_NOT_SUBMISSION_QUALIFIED`，且声明 controller 仍是 opponent-blind。[VERIFY: kaggle_Kaggriculture/model/v16_gold_strategy_research/run_l1_s2_pilot.py:506]

### 5.1 cppsim L1 实测吞吐

| live agent | 官方环境 | cppsim L1 | 实测加速 | 奖励 |
|---|---:|---:|---:|---|
| Island GA ReferenceExecutor，8 seeds | 1.348 eps | 15.610 eps | 11.58x | 8/8 逐值相同 |
| A2，4 seeds | 1.039 eps | 6.796 eps | 6.54x | 4/4 逐值相同 |

L1 每回合生成完整 observation dict，再接受两个实时动作；它不是固定 tape。[VERIFY: kaggle_Kaggriculture/model/community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim/python/kagsim.cpp:208]  
本报告的测速同时保留官方与 L1 奖励数组，并显式检查 equality。[VERIFY: kaggle_Kaggriculture/model/v16_gold_strategy_research/run_l1_s2_pilot.py:246]

因此可确认：**闭环研究路径能真实提速约 6.5x–11.6x**。但当前 V15 formal evaluator 仍走官方 `env.run`，这些加速尚未接入 formal。

### 5.2 S2 对照

冻结 pilot 参数：`D>=2, q<=80, minProfit>=2, cashFloor=3000`；只在当前和下一步父 market 为空、下一步无 `PICKUP/DROP/PLACE` 时触发。[VERIFY: kaggle_Kaggriculture/model/v16_gold_strategy_research/run_l1_s2_pilot.py:101] [VERIFY: kaggle_Kaggriculture/model/v16_gold_strategy_research/run_l1_s2_pilot.py:166]

| 对照 | 比较数 | 完整往返 | 自身结果 | 理论=实际 | 尾部 |
|---|---:|---:|---:|---:|---|
| A2 vs idle，40 seeds | 40 | 803 | 40/40 正，平均 +165.65 | 6,626=6,626 | 0 未平仓 |
| A2+S2 vs live A2，20 seeds×双席 | 40 | 940 | 40/40 正，平均 +196.2 | 7,848=7,848 | 0 未平仓 |
| A2 vs 5 局固定顶尖 tape×两席替换 | 10 | 241 | 自身 10/10 正 | 对手流导致不再相等 | 1 次 margin -48 |

固定 tape 只是一种市场压力测试，不是可执行 closed-loop 对手；不能把 9/10 margin 正向报告成胜率。

### 5.3 S2 安全门

进入交易前必须逐场景证明：

```text
entry fill == q
exit fill == q
父订单成功/失败状态不变
父 unit action 后状态不变
min cash >= floor
shed <= 100
feed reserve 不变
exit 后除现金外的自身状态回归 baseline
market WHEAT inventory 回归 baseline
worst-case own delta >= 0
worst-case margin delta >= 0
```

BUY_PRODUCT 受现金和 shed 容量约束；FEED 消耗单位库存，PICKUP 才从 shed 取 WHEAT。[VERIFY: kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:652] [VERIFY: kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:505] [VERIFY: kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:358]

现有 A2 prebuy 的成本循环从 `p(I)` 开始，但官方首单位买价是 `p(I-1)`；S2 必须使用修正后的索引。[VERIFY: kaggle_Kaggriculture/model/v1_adaptive_market/main.py:1063] [VERIFY: kaggle_Kaggriculture/model/v15_cleanroom_search/cleanroom/sessions/attempt_002/official_rules/kaggriculture.py:598]

## 6. 金牌搜索架构

```text
StaticPlan genome
  -> dependency DAG / finance certificate / worker tours
  -> cppsim L0 宽搜 + MAP-Elites
  -> 各复合谱系的 cell elites
  -> cppsim L1 自适应消融
       + finance/delivery repair
       + S2 pulse MM
       + continuous inventory MM
       + shop route
       + opponent/slot shadow
       + terminal controller
  -> 官方环境 formal confirm
```

L0 只能运行预先固定的 Stream，适合静态 schedule 和市场 delta 宽搜；L1 才能运行读取 observation 的动态 executor。[VERIFY: kaggle_Kaggriculture/model/community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim/python/kagsim.cpp:274] [VERIFY: kaggle_Kaggriculture/model/community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim/python/kagsim.cpp:208]

现有 Island GA 还不能直接作为金牌搜索器：默认 fitness 是对 idle 的自身平均 bank，cache 只按 `gid+seed`，没有 opponent/seat/engine/compiler 身份。[VERIFY: kaggle_Kaggriculture/model/community_research/2026-08-26/live_cli/external_repos/kaggriculture-island-ga/islandga/search.py:88] [VERIFY: kaggle_Kaggriculture/model/community_research/2026-08-26/live_cli/external_repos/kaggriculture-island-ga/islandga/search.py:124]

必须改为：

- block genome：layout / production / labor-route / capital / market / terminal；
- MAP-Elites：production signature / capital intensity / market footprint；
- 质量函数：谱系等权 margin utility - CVaR - failure - seat gap；
- cache key：`genome, compiler, engine, opponent, seed, seat, stage`；
- 每个必需购买给出 finance certificate，而不是依赖引擎静默拒单。

现有 compiler 明确采用“乐观下单、余额不足让引擎拒绝”，还不是 finance-coherent compiler。[VERIFY: kaggle_Kaggriculture/model/community_research/2026-08-26/live_cli/external_repos/kaggriculture-island-ga/islandga/compiler.py:7]

## 7. 正式晋级协议

1. 已查看的 8 月 23–25 日仅作 development；
2. 8 月 26 日只作 meta refresh，补齐当前版本；
3. 冻结 candidate、simulator、compiler、opponent package、pool manifest 和阈值；
4. 第一个未看完整日期作 `confirm_A`；
5. 只有 `confirm_A` 通过，才打开下一个日期 `future_B`。

同批必须使用完全相同的 source/seed/seat 清单，禁止事后求交集。Replay-derived 对手在通过双席合法性、719 callback、行为复现和 future 行为区间门前，只能做压力测试。

建议主门：

- Top-7 等权 score rate >=60%，source-cluster 95% CI 下界 >=55%；
- 宏观 family 等权也过同一门；
- 每个宏观 family 点估计 >=50%；
- 相对 A2 paired uplift >=10pp，95% CI 下界 >0；
- 任意未平仓、父订单改变、feed shortfall、shed overflow 直接淘汰。

## 8. 非 WHEAT 最小闭环的新证据

研究 adapter 只修改最终 A2 动作中的非 WHEAT `SELL`，并逐回合断言 farmer、hands、受保护市场槽和 10 槽上限不变。[VERIFY: kaggle_Kaggriculture/model/v16_gold_strategy_research/nonw_delay_planner.py:300] [VERIFY: kaggle_Kaggriculture/model/v16_gold_strategy_research/nonw_delay_planner.py:320]

评测先捕获 live A2 双方动作流，再做 identity replay；frozen 分支只替换自身非 WHEAT 时机，live 分支则让双方继续闭环执行。[VERIFY: kaggle_Kaggriculture/model/v16_gold_strategy_research/run_nonw_delay_pilot.py:63] [VERIFY: kaggle_Kaggriculture/model/v16_gold_strategy_research/run_nonw_delay_pilot.py:404]

结果已固化到 `RESULTS.json`：

- 无对手两步队列模型在 live A2 镜像上稳定亏损；把历史对手流缓冲从 0 提高到 4，40 个双席比较的平均 margin delta 仍由 -3495.65 只改善到 -3036.68；
- `SELL-only` fail-closed 版本无成交短缺，但 40 个比较只有 0 个 margin 正向，平均 -53.1；
- 完美知道未来两步双方动作、并用完整官方规则证明两步后非现金状态回归时，20/20 正向，但自身平均只 +139.7、margin 平均 +111.4；
- 因此短期出售时机是几十到几百金币的 residual，不是约 39.5k 主差距的解释。

完整 oracle 会逐候选执行当前与下一步官方 unit、market、town、decay/EOD 转移，并且只接受两步后除双方现金外全部状态相同的方案。[VERIFY: kaggle_Kaggriculture/model/v16_gold_strategy_research/run_nonw_delay_pilot.py:254] [VERIFY: kaggle_Kaggriculture/model/v16_gold_strategy_research/run_nonw_delay_pilot.py:347]

8 月 25 日另外 24 局严格 Replay 偏移审计也支持同一判断：4,429 个变体只有 3,059 个能保持生产/运输/成交结构，所有品类候选中位数均为 0；`town drain>0` 且对手无同品类 SELL 时才有小幅正期望，对手有供给时平均为负。该审计目前只保留于临时研究日志，尚未形成仓内可重跑脚本，因此不作为正式晋级证据。

## 9. 情境化产品组合的新证据

模板挖掘器只先读每份 8 月 25 日 Replay 的 JSON header，按团队选择最新 N 局后才完整解析动作；它统计早期商店、种子/动物购买、第三块地和峰值 hands，并明确标为 descriptive、非因果。[VERIFY: kaggle_Kaggriculture/model/v16_gold_strategy_research/mine_portfolio_templates.py:29] [VERIFY: kaggle_Kaggriculture/model/v16_gold_strategy_research/mine_portfolio_templates.py:176]

最新 12 局/团队中，Crop、Ryo、Sub、tetsuya 各出现 12 个不同的请求组合；Kronki 与 tyz 仅 3 个。自适应团队会随前两家商店显著改变 WHEAT/CARROT/STRAWBERRY/MELON 与动物购买，而 tyz 的中位组合固定在 `140/20/0/41/11 + 0/11/4`。这是描述性证据，不能直接证明因果收益，但它把下一阶段搜索变量从“一个全局路线”收敛为“商店、对手公开生产和市场库存条件下的完整组合模板”。

## 10. 更新后的下一步优先级

1. **P0 改为情境化产品组合与生产调度**：先构建 4–8 个 finance/resource-complete 模板，再由早期商店、对手公开作物/动物和市场库存路由；
2. 实现 `StaticPlan -> Stream + finance/resource certificate`，用 cppsim L0 搜完整作物、动物、land3 和 labor block；
3. 在 cppsim L1 做模板路由，目标是非 WHEAT 现金 +10%、作物 harvest +5%、失败为零，而不是继续微调卖单；
4. 非 WHEAT market selector 只保留 `town drain > opponent supply upper bound` 的小剂量 residual；MELON 优先做避开对手 dump 的提前出售；
5. S2 WHEAT 继续作为几百金币附加项，不与生产搜索混参；
6. 等新路线在 development 过门后，再使用官方环境和未见日期 formal confirm。

当前不应提交任何 v16 pilot。当前最可靠的判断是：**金牌主轴已经从短期清算器转移到“状态条件化的完整生产组合”，市场控制只负责保护已创造的价值。**
