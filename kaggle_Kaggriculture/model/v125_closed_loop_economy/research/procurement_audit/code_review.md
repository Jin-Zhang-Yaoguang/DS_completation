# V125-R0：资源、任务依赖与终局审查

结论：已用完整官方解释器复现三项局部故障：远端肥料阻塞近端保活、整条链的截止条件阻止仍可执行的保活，以及终局单品入仓遗留可卖产品。它们足以支持下一代的单机制预注册，不能直接证明完整对局收益或胜率改善。

审查对象为冻结 `candidates/V125-R0/main.py`，SHA256 `9898f724bd71abc91520c7ea29ac90734507236c2fa4237af76a5d87dad404fe`；本目录另存完全相同的 `snapshot/v125_r0_main.py`。本文代码引用优先指向该快照。没有改动 R0、R1 或策略注册表，没有打开 Replay 或 Blind。

## 已用官方引擎验证

`dependency_results.json` 保存初始完整观测、每帧任务、R0 动作、实际应用动作及结果。人工场景不是随机整场比赛：2 个席位，16 次短运行，共 64 次解释器状态转换，17 项检查全通过。只有可行操作对照手动替换了标明的 1–2 帧动作；对照不是新增策略候选。所有场景的自然发生频率均未知。

| 场景 | R0 实际行为 | 官方引擎结果 | 最小对照 |
|---|---|---|---|
| day11 h18，草莓已一天未浇，农夫在作物上，唯一肥料在 8 步外工人手中 | 农夫和工人均 PASS，整晚没有浇水 | 日终草莓变 WEED，已有 1 单位果实丢失 | 完全去掉肥料时，同一个 R0 执行 WATER、HARVEST，活苗且入仓 1 草莓 |
| 同状态，只把同一份肥料从远端搬给近端农夫 | FERTILIZE、WATER、HARVEST | 活苗，入仓 1 草莓，次日增加 2 单位新产量 | 资源总量不变，只改变可达位置 |
| day11 h21，近端农夫已有肥料，其他条件同上 | 3 步完整任务链过不了统一 deadline，仍 PASS | 日终草莓变 WEED | 完全相同观测，合法 WATER、HARVEST 两帧操作可以保活并入仓 1 草莓 |
| day29 h22，入口背包甜瓜、牛奶、羊毛各 1 | PLACE MELON，再 SELL MELON | 终局现金 250，牛奶和羊毛仍在背包 | 完全相同观测，DROP 加三个 SELL，现金 610，背包为空 |

复现命令（从仓库根目录运行）：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/run_dependency_microcases.py
```

脚本严格核对 R0 与官方规则 SHA，使用本目录 `run_microcases.py` 的完整解释器脚手架；报告保存两份脚本 SHA。运行约 1 秒，单进程。官方规则版本 `kaggle-environments==1.32.7`，规则 SHA 与实验 A 一致。

### P1：可选施肥成为浇水与收获的共同前置条件

持续作物把 `FERTILIZE → WATER → HARVEST` 放在同一个任务里，只要全农场任意库存存在肥料，就给整个任务加 `FERTILIZER: 1`。全农场库存计数包括别的工人的背包，但分配器只有“自己持有”或“仓库可领”两条供料路径，不能从其他工人的背包获得资源。于是近端、空手而能浇水的农夫被拒绝；远端带肥工人又因距离和截止时间无法完成整条链，导致任务完全无人执行。人工场景已经把这条代码路径转为日终枯死的实际结果。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:101] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:340] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:454]

在同一初始观测下，仅替换为 WATER、HARVEST 的可行操作对照也让作物存活，排除了“引擎规则本来就不允许保活”的解释。规则在连续未浇水达到 2 天时改为 WEED。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/rules_snapshot/kaggriculture.py:769]

下一代应让保活和现有产物采收各自拥有真实前置条件，可选增产施肥另行计算边际价值。不要通过虚构肥料库存、忽略材料消耗或把所有施肥全关掉来伪装修复。

### P1：把可选动作后的整条链截止时间当成保活动作的截止时间

危险作物 deadline 为 21；分配器用“旅行 + 补料 + 整条 ops 长度”判断可行性。day11 h21 的近端农夫已经持肥，但三步链满足 `21 + 3 > 21 + 1`，因此被整体拒绝。与此同时，单独在 h21 浇水、h22 采收仍是合法且有价值的操作。该场景与远端供料问题不同：材料就在当前工人手中，失败来自整条链统一的期限判断。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:370] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:467]

下一代应按动作的实际生效时点与必要依赖判断期限。修复应同时通过“近端无肥、远端有肥”与“近端有肥但只剩保活窗口”两个场景；只把 requirement 清空仍会留下第二个故障。

### P1：终局缺少整包入仓与对应的市场投影

R0 终局返仓后只选择一种产品 PLACE；市场投影也只理解 PICKUP 和单品 PLACE。官方存在 DROP，一步把所有随身物品入仓。空仓、三种产品各 1 的末帧场景中，DROP 加三笔 SELL 可实际兑出 610；R0 兑出 250，差额 360 在结束时仍留在背包。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:413] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:512] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/rules_snapshot/kaggriculture.py:343]

本规则在 step 718 的动作处理后即 DONE，记录出的 hour23 已经没有下一次决策，且 step718 不触发日终自动入仓。因此不能依赖“最后 23 点还有一次自动清算”。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/rules_snapshot/kaggriculture.py:945] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/rules_snapshot/kaggriculture.py:960]

该修复应独立于任务拆分候选。DROP 会清空所有物品，满仓时溢出被丢弃；应先计算剩余容量和实际舍弃顺序，不能无条件把所有 PLACE 替换成 DROP。当前 250→610 仅属于这个人工末帧状态，不能当作整场预计增益。

## 静态审查发现，尚未归因到自然诊断损失

1. **P2，品种选择会搁置已购买种子。** `economic_plan` 每帧只选一个 `crop_choice`；`make_tasks` 只为这个品种生成播种任务，没有为其他正库存种子生成候选。选择变化后旧种子会等待该品种再次入选，已投入现金和现存种子不参与选择价值修正。另一方面，播种前的行走/DIG 不按种子数预留，只有最终 PLANT 时才检查余额，可能形成过多前置劳动及跳过后的 PASS。应先从诊断统计“各品种期末种子成本、计划播种未成、被跳过 PLANT”，再确定影响大小。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:225] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:387] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:489]

2. **P2，动物采收也被完整喂养链限制。** 未喂动物的整个 `FEED → CARE → COLLECT_FERTILIZER → HARVEST` 任务需要 WHEAT；缺饲料时已有可收产物也不可分派。与肥料反例结构相同，但本文没有单独跑动物微场景，不应把它写成已证的完整现金死锁。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:305] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:318]

3. **P2，普通日终没有显式的全背包仓容预算。** 平日任务评分返仓成本为 0，只在较高货值且离仓不超过 3 步等条件下提前返仓。市场层只看当步实际入仓，不能看见稍后的自动入仓；所有工人日终汇总可能超过 100 容量而直接丢货。规则会按库存遍历顺序接收至上限后删除全部剩余，不会按价值选留。需对已有诊断 trace 统计实际溢出量，本审查未声称 R0 已频繁溢出。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:448] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:474] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/rules_snapshot/kaggriculture.py:843]

4. **P2，补料与放置没有跨帧资源承诺。** 在仓口先领动物的逻辑不验证空结构/放置任务；缺材料的多个工人可同时朝最后一份仓内材料移动，因为原子预留只发生在实际 PICKUP 帧。空结构任务还会减少 `in_transit`，但原 `empty_structure` 容量计数仍被后续建设判断再次使用，可能推迟扩建。此处是可检验的延迟风险；没有证据表明自然初始化中会形成永久结构死锁。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:320] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:377] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:431]

5. **P2，采购和任务指标不能当作完整成交/完成账本。** `task_*` 在分派 MOVE/PICKUP 时就加 1，不是任务完成量。种子确认把请求 PLANT 次数当作实际消耗加回；动物确认未校正跨日逃逸及溢出；BUY_PRODUCT WHEAT 不在成交确认统计里。R0 按真实资产重新计算目标，因此这些指标问题不等于旧 V22 的错误待办销账，但“所有完成以观测确认”的描述过强。饲料下单忽略 `fixed_order` 返回值后仍增加本地仓投影，也会在订单槽已满时产生一帧幻影库存。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:125] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:502] [VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:563]

## 打包 QA 必查，不属于经济策略失败

冻结主文件的最后一个顶层 callable 为 `diagnostics`，不是 `agent`。当前本地 Kaggle raw 文件加载器取 `env.values()` 中最后一个 callable。因此直接以该源码路径或 raw 源码作为提交入口，会选中诊断函数；显式 `module.agent` 的本地评测则不受影响。最终 tar 入口若已包装，这条可能已经被处理；必须审计实际归档入口并做 raw-loader smoke，不能根据本文件就宣称已提交失败。[VERIFY: kaggle_Kaggriculture/model/v125_closed_loop_economy/research/procurement_audit/snapshot/v125_r0_main.py:610] [VERIFY: .venv/lib/python3.12/site-packages/kaggle_environments/agent.py:64]

## 下一项单机制预注册建议

先锁定下一项实验的父候选 SHA，再只修作物任务的必要依赖与逐步截止时间：WATER 的前置条件来自植物当前状态，HARVEST 的前置条件来自成熟及现有产物，FERTILIZE 是单独的增产选择。保持市场、价格预测、动物目标、品种选择和参数不变；不要同时加入终局 DROP 或日终容量修复。

机制验收应复用本文三个肥料位置/截止场景，补充正常可施肥场景不得出现重复施肥或无效采收，并记录逐步实际状态变化。之后才由父代理按预注册面板跑配对收益、保活损失、有效收获及稳定性检查。未通过局部机制验收不进整场确认；局部通过仍不构成严格金牌门通过。
