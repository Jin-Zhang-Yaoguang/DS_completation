# 24-step labor planner：第一性结论

## 结论

**列为 P0 基础设施，但不能把它误当成单独的金牌策略。**

冻结同一份 `best_genome.json`、只替换工人执行层后，24 个同 seed、同 seat、idle-opponent 配对局中：

| executor | mean bank | 日均静态 target occupancy | 最差终局 occupancy | 每次决策 |
|---|---:|---:|---:|---:|
| stock greedy | $33,756 | 61.27% | 25.71% | 78.9 us |
| corrected greedy | $53,153 | 69.63% | 25.71% | 144.1 us |
| joint MPC prototype | **$57,129** | **70.02%** | 22.86% | **277.0 us** |

`joint MPC` 对 stock 的 bank delta 为 **24/24 为正**，均值 `+$23,373`，中位数 `+$21,731`；对 corrected greedy 为 `20/24` 为正、均值 `+$3,976`。所以联合分配本身有独立增益，不只是修掉晚间返仓。

在 4 个去重强路线市场流、4 seeds、双 seat 的 32 个配对局中，joint MPC 相对 stock：

- `24/32` bank 提升；
- mean `+$7,205`，median `+$4,898`；
- 4/4 家族 mean delta 为正；
- stock 与 joint MPC 对强路线都仍为 `0%` score rate。

因此执行层是实质瓶颈，但不是唯一瓶颈。按 relaxed upper `$229,450` 计算，捕获率只从 stock 的约 `14.7%` 提到 `24.9%`，仍远低于 top route 的 `65.8%`。剩余差距属于 blueprint/时点/市场价值选择，不能继续归咎于工人走路。

机器结果：[`prototype_results.json`](prototype_results.json)、[`route_benchmark_results.json`](route_benchmark_results.json)。

## 旧 target realization 指标为什么不能作为 95% 硬门

旧指标在每天 hour 23 检查“目标地块上是否仍是指定作物”。但非 ongoing 作物成功 `HARVEST` 后，规则会立即把地块置空；成功完成生产的地块会被记成未兑现。

24 局累计 hour-23 缺口：

| 原因 | stock | joint MPC |
|---|---:|---:|
| plant empty | 5,313 | **5,701** |
| animal missing | 1,827 | **291** |
| plant other/locked/structure | 3,984 | **2,496** |
| weed | 66 | **0** |

joint MPC 的 bank 大幅增加，同时 `plant_empty` 也增加，说明该 occupancy 指标把部分成功收获当成失败。正确证书应拆为：

1. job deadline completion：该日 WATER/FEED/CARE/DIG/BUILD/PLACE 是否按时完成；
2. lifecycle yield capture：实际 harvest units / 在当前种植和照料状态下可收获 units；
3. sale availability：SELL 时 shed 中实际可卖数量 / 计划数量；
4. travel、PASS、silent no-op 与库存溢出；
5. 最终 bank 和强 meta 的 family-equal score。

静态 target occupancy 只能作为诊断字段，不能再设 `>=95%` 晋级门。

## 规则导出的 24-step 状态模型

每天的执行问题不是“最近任务”问题，而是带资源与截止期的多工人 pickup-delivery scheduling：

```text
state(t)
  = 每个单位的位置、背包
  + shed、seed、cash
  + 每个 tile 的作物年龄/水/产量、动物 feed/care/产量
  + 剩余 job DAG、market/town 状态

job
  = release time + deadline + location + 1-step service
  + resource precondition + successor + marginal bank value
```

硬约束：

- 每单位每 step 只能移动或服务一次；
- `FEED` 先从 shed 取 WHEAT，`PLACE` 先取动物；
- `PLANT` 受共享 seed pouch 的原子批量校验约束；
- WATER/FEED/CARE 在午夜结算，漏两日水会死亡；
- 每日结束背包自动回 shed、hands 消失并在次日重雇，因此为次日 hour-0 SELL 主动返仓是零价值动作；
- shed 容量、同一步并发动作、现金与 market 顺序必须进入状态。

目标函数应是：

```text
max expected terminal bank
  = job 的边际可售价值
  - travel / missed-deadline / overflow / no-op penalty
  - 对手供给后的价格冲击风险
```

## 三条求解路线

| 路线 | 判断 | 用法 |
|---|---|---|
| CP-SAT | 不适合在线主策略 | 位置、背包、任务先后、共享库存与作物动态会产生大量整数变量；本环境没有 OR-Tools，打包也不应依赖外部 solver。适合离线小局面 oracle，给 MPC 提供 regret 标签。 |
| time-expanded min-cost flow | 适合做松弛层，不足以单独求解 | 单位-任务匹配和移动是 flow；但 PICKUP→FEED/PLACE、多商品背包、共享 seed、任务 precedence 使完整问题变成多商品耦合流。原型的 Hungarian 联合匹配就是可用的 flow kernel。 |
| beam / MPC | **生产路线** | 每步重读真实状态，保留 6–12 step 任务序列，用 joint matching 生成少量联合动作，滚动到午夜。能自然吸收 weeds、静默拒单和对手市场变化，且可保持纯 Python、亚毫秒级。 |

最终架构应是 **CP-SAT 离线 oracle + value-aware beam/MPC 在线策略 + min-cost matching 内核**，而不是三选一。

## 原型做了什么

[`prototype.py`](prototype.py) 保持原 genome、blueprint、finance 和 market 层不变，只改 labor dispatch：

- 识别 EOD auto-drop，取消无价值的跨午夜返仓；
- 对 FEED/PLACE 显式加入 shed pickup mission；
- 保留 under-foot 零旅行服务；
- 每步以 Hungarian 求联合单位→任务最小成本匹配；
- 用 deadline slack 和轻量 target persistence 降低换目标；
- 无外部运行时依赖。

当前只是 horizon-1 MPC kernel，还不是完整 24-step beam。它证明了“联合调度值得做”，没有证明当前规则已经最优。

## P0 里程碑

### M0：重建执行证书

- 逐 action 对比前后 observation，记录 success/no-op；
- 建立 job deadline completion、yield capture、sale availability；
- 保留 occupancy 仅作诊断。

门槛：官方/Cppsim parity；统计可逐步复算；不再用 `95% occupancy`。

### M1：冻结 dependency DAG

- 将 BUILD→PICKUP ANIMAL→PLACE、PICKUP WHEAT→FEED、WATER→HARVEST→auto-drop→SELL 编成任务 DAG；
- 为每个 job 估算 deadline 与 market-adjusted marginal value；
- 处理 seed 原子校验和 shed capacity。

门槛：固定 blueprint 上 deadline miss 和 silent no-op 显著低于原型。

### M2：6–12 step beam/MPC

- 每单位只扩展 top-K mission；
- Hungarian 生成联合首步；
- beam 保留 32–128 个 joint states；
- 状态变化或任务完成后重规划，午夜完整重置。

门槛：决策 P99 `<5 ms`；同 24 局 bank 不低于本原型，且最差局不退化。

### M3：重新搜索完整计划

- planner 与 production/capital/market genome 联合评价；
- 先优化绝对 bank / CVaR，再过 4 家族等权 meta；
- 不用 A2 做目标函数。

门槛：upper capture `>=45%` 后再做大规模强 meta；如果仍远低于 top route，转向 blueprint/market timing，而不是继续堆 planner。

### M4：金牌晋级门

- 未见 seeds、双方 seat、行为去重家族；
- family-equal score `>50%`，worst-family 不出现结构性崩溃；
- mean margin 与 CVaR 同时改善；
- raw-loader、官方环境、运行时和资源证书全部通过。

## 复现

```bash
.venv/bin/python kaggle_Kaggriculture/model/v16_gold_strategy_research/next_gold/labor_planner/prototype.py
.venv/bin/python kaggle_Kaggriculture/model/v16_gold_strategy_research/next_gold/labor_planner/route_benchmark.py
```

