# R19 evaluator-only 精确经济账本结论

## 结论

这是 **seed 7100、双座位、router 对 idle 的诊断面板**，不是 P2、Replay 或金牌证据。6 局均完整结束；候选只接收标准 observation，特权账本只在候选动作已提交后由 evaluator 读取。[VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/evaluation/economic_ledger/evaluate_economy.py:297] [VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/evaluation/economic_ledger/evaluate_economy.py:315]

R19 的主要退化不是花费增加、雇佣失败或丢弃，而是生产组合与执行吞吐偏移导致的销售收入不足：

| 双座位均值 | R17 | R18 | R19 | R19-R17 |
|---|---:|---:|---:|---:|
| 终局 bank | 99,507 | 90,774 | 76,874 | -22,633 |
| sell revenue | 118,769 | 109,936.5 | 95,580 | -23,189 |
| total spend | 22,262 | 22,162.5 | 21,706 | -556 |
| produced | 947.5 | 856 | 849.5 | -98 |
| sold | 783 | 715.5 | 691.5 | -91.5 |
| discarded | 3 | 0 | 0.5 | -2.5 |
| successful hires | 290 | 290 | 290 | 0 |
| seed units bought | 170.5 | 170 | 196 | +25.5 |
| animal units bought | 12 | 11 | 11 | -1 |
| sale-through | 82.64% | 83.59% | 81.40% | -1.24pp |

精确汇总证据见 R17、R18、R19 各自 economy block，以及差值 block。[VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/evaluation/economic_ledger/summary.json:449] [VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/evaluation/economic_ledger/summary.json:967] [VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/evaluation/economic_ledger/summary.json:1485] [VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/evaluation/economic_ledger/summary.json:1593]

## 根因证据

1. **现金损失来自收入侧。** R19 比 R17 少花 556，但少收入 23,189，终局 bank 正好低 22,633；所以不是超支。successful hires 同为 290，也不是 hire 失败。[VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/evaluation/economic_ledger/summary.json:1593]
2. **产出从动物服务/肥料偏向种植。** 相对 R17，R19 的产品产量变化为：WHEAT +81、MELON +24、CARROT +5，但 FERTILIZER -114.5、MILK -84.5、STRAWBERRY -5、WOOL -4。实际卖出也同步表现为 FERTILIZER -113、MILK -84.5、WHEAT +86。账本只暴露商品级 sold units 与总 sell revenue，不能把总收入损失伪分解为商品级金额。[VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/evaluation/economic_ledger/summary.json:1498] [VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/evaluation/economic_ledger/summary.json:1513]
3. **动作证据与该偏移一致。** R19-R17：PLANT +27.5、WATER +146、HARVEST +11.5；同时 CARE -93.5、COLLECT_FERTILIZER -114.5、FEED -12.5，PASS +206.5。移动方向也明显重排（EAST +160、NORTH -107.5、SOUTH -143.5、WEST -116.5）。[VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/evaluation/economic_ledger/summary.json:1607]
4. **代码机制与动作偏移相符。** R19 从 day 8 开始计算 growth debt，把 PLANT/HARVEST/PLACE/BUILD 划为 primary tier，把 CARE/COLLECT_FERTILIZER/DIG 划为 secondary tier。[VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/main.py:39] [VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/main.py:511] [VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/main.py:826]
5. **执行器会先抢占 WATER/FEED，再分配一个 growth lane，之后无论局部还是全局分配都穷尽 primary tier 后才进入 secondary tier。** 这给出了 CARE/COLLECT_FERTILIZER 被系统性延后的直接机制，与精确账本中的奶/肥料产量塌陷一致。[VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/main.py:1041] [VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/main.py:1061] [VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/main.py:1073] [VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/main.py:1089]

因此，当前最强根因判断是：**growth-debt + primary-before-secondary 的调度结构，以更多种植、浇水和 PASS 为代价，挤压了 CARE/COLLECT_FERTILIZER，造成高价值动物链产出与销售收入下降。** 这是单 seed 双座位下由“代码机制 + 真值账本 + 动作轨迹”共同支持的诊断，不宣称已完成跨 seed 因果识别。

## 逐日资产与信息边界

`summary.json` 为每个版本保留 day 0-29 的逐日均值：money、production assets、shed、hand、weed，以及 produced/sold/revenue/spend/discarded 累计值。R19 在 day 29 仍有 47 个 production assets，高于 R17 的 45，但累计产出、卖出和收入更低；这说明“资产数量更多”不等于“有效吞吐更高”。[VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/evaluation/economic_ledger/summary.json:420] [VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/evaluation/economic_ledger/summary.json:1456]

信息边界采用双保险：候选源码静态扫描禁止 accounting token；每一步递归检查 observation 不含 accounting key。候选先决策，evaluator 后读特权真值。manifest 明确记录 `candidate_truth_visibility=NONE` 和三份候选 SHA。[VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/evaluation/economic_ledger/evaluate_economy.py:126] [VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/evaluation/economic_ledger/evaluate_economy.py:311] [VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/evaluation/economic_ledger/run_manifest.json:10]

## 测试状态

5/5 PASS：候选不可见 accounting、引擎和产物哈希锁定、6 局完整且商品/种子/现金守恒、精确六局面板、summary 与逐局数据一致且仅为诊断。[VERIFY: kaggle_Kaggriculture/model/v116_heuristic_gold_search/r19_growth_debt_throughput_hmoe/evaluation/economic_ledger/test_results.json:8]

本次未运行 P2、Replay，未编译引擎，未修改 R17/R18/R19 候选 main。
