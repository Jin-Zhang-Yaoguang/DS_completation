# R12 Plant-Water Bundle HMoE

## 结论

`NOT_GOLD_KILLFAST_REJECT`。

R12 消除了 R11 的漏水转 weed 问题，但唯一获准的
`seed=7100 / router / seat0 / idle / 719 calls` kill-fast 仍未达到资产和经济门槛。
按预注册规则冻结并停止，不运行 P2、P3、Replay，不登记 `golden_model.md`。

## 自包含边界

- `strategy_parent = null`；
- 运行时仅 Python 标准库；
- 不导入 R11、历史 agent 或 Replay；
- 保留 `build_executor(params=None, mode=...)`；
- 四种 mode：`router`、`fixed_root_exchange`、`fixed_dairy_berry`、
  `fixed_fiber_grain`。

## 本轮限定改动

1. PLANT 成功后生成同 target、priority 0 的 WATER successor，并优先交给原
   owner；successor 未完成时不再分配新 PLANT；hour > 18 不执行或新分配 PLANT。
2. tranche 仅在上一日实际资产达到 admitted target、漏水 weed 为 0、维护按时率
   >=98% 时增加 2；不满足时冻结，维护不安全时允许降档。
3. 任务先按 safety priority，再按同 zone、最近距离和 bundle 连续性排序。
4. 种子、动物和饲料采购只统计当前 admitted layout lease 对应的 live ticket。

## 机制回归

`test_r12.py` 共 16 项检查全部通过：4 项静态边界和 12 项机制不变量。新增覆盖：

- PLANT → WATER 同 owner 闭环；
- open successor 阻止新 PLANT；
- 19 点后的 PLANT cutoff；
- 健康日扩 tranche、不健康日降档；
- 采购仅服务 admitted lease。

## Kill-fast 结果

| 指标 | 门槛 | 实际 | 结果 |
| --- | ---: | ---: | --- |
| agent calls | 719 | 719 | 通过 |
| 运行错误 | 0 | 0 | 通过 |
| step 144 生产资产 | >=12 | 5 | 失败 |
| 漏水转 weed | 0 | 0 | 通过 |
| 终局 bank | >=60,000 | 13,994 | 失败 |
| 终局生产资产 | >=30 | 7 | 失败 |
| 无效 WATER/FEED/PLACE | 0 | 0 | 通过 |
| 终局 live orphan/expired | 0/0 | 0/0 | 通过 |

相对 R11，漏水 weed 从 23 降为 0；方向移动从 3,013 降为 1,077，nonprogress
从 31 降为 6。但全局单 bundle 串行化过强，累计 PASS 达 627。资产在 day 3
达到 12 后，Router 切换 dairy_berry 与非持续作物收获/衰退使 day 6 降到 5；
tranche 在 12/14/16 间反复冻结或降档，终局只剩 7 个资产。下一版本不能重新
放宽浇水安全约束，而应允许“按可证明当日可维护容量”的多个并行局部 bundle，
并把成熟收获后的 replacement backlog 纳入 realized capacity。

## 证据文件

- `main.py`：冻结候选源码；
- `test_r12.py` / `mechanism_results.json`：机制回归；
- `evaluate_killfast.py` / `killfast_result.json`：唯一一次 kill-fast；
- `daily_diagnostics.json`：day 0–29 逐日现金、资产、weed、tranche 和维护诊断。

本结果只是对 idle 的淘汰门证据，不是金牌模型胜率证据。
