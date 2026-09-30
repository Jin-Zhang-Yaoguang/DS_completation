# v4_demand_race — 原创任务调度 agent（M0–M6 已完成，结果如实记录）

> 设计见 [DESIGN.md](DESIGN.md)。本 README 记录实现结果与 M6 验收。

## 实现状态

设计的全部机制已实现在单文件 [main.py](main.py)（~1000 行，自包含可提交）：

| 模块 | 状态 |
| --- | --- |
| MarketLedger（需求坑 + 对手卖出反解 + 对手收获推断 + 供给预报） | ✅ |
| WinLedger（终局 Δ 三模式 LOCK/NORMAL/GAMBLE） | ✅ |
| Router（商店信号 → herd/草莓调整，yarn 对冲仓位） | ✅ |
| Executor（严格分层指派 + 喂食/放置双供应链 + 收获截止 + FERTILIZE） | ✅ |
| Market（坑内 wait_gain 判据 + race + 分批自压控制 + 终局清算） | ✅ |
| 阶段化资本计划（herd_early → ipo_day → herd） | ✅ |
| CEM 参数搜索（26 维，40 代 × 24 个体，kagsim 上并行） | ✅ 最优参数已固化进 POLICY |

## M6 最终验收（用户指定协议）

64 个真实线上 episode 场景（1.32.7，seed + 钉住商店序列）× 双席位 = 128 局/对手：

| 候选 | vs V76 | vs V20 |
| --- | --- | --- |
| **V4（本目录，原创调度器）** | 0/128，margin −145,348 | 0/128，margin −146,058 |
| **V4H（[混合版](../v4h_demand_race_hybrid/)）** | **43/128（33.6%，Wilson LB 26.0%）**，margin −4,588 | **43/128（33.6%）**，margin −4,222 |

结果文件：`eval_m6_v4.json` / `../v4h_demand_race_hybrid/eval_m6_v4h.json`。

## 结论（诚实版）

1. **原创调度器架构没有在一个开发周期内追平精心手调的 720 步 tape。**
   从 −101k（初版）修到 −78k（供应链五连修）再到 CEM 天花板 −63k~−80k，
   每一步都有效但总差距是结构性的：tape 是把 720 回合当整体规划的产物，
   每回合贪心 + 分层指派的动作利用率仍差 ~30%。这正是 DESIGN §8 预判的最大风险。
2. **fallback 预案（市场层嫁接）如期兑现**：V4H 用同一套 MarketLedger 驱动
   race-reorder + 终局保险，对 V76/V20 拿到 33.6% 胜率、margin −4.4k，
   与 benchmark 进入同一量级。
3. **调试过程的可复用产出**（都进了代码）：喂食/放置双供应链强制派工、
   严格分层调度（线性加权会让 5 步距离翻转优先级）、种子-动物的阶段化预算、
   坑内 wait_gain 卖出判据、成熟一次性作物 = 资本事件。

## 基建（M0，可被后续任何版本复用）

- `harness/engine.py`：kagsim / kagsim_scenario / 官方引擎统一封装
- `harness/arena.py`：双席位配对多进程评测器（Wilson 区间、场景/seed 两模式）
- `harness/scenarios_64.json`：64 个真实 episode 场景（M6 固定基准）
- `search/cem.py`：CEM 搜索器（可断点续跑，26 维参数空间）

## QA

- 双引擎逐分一致：seed 911/912 官方 vs kagsim 终局银行完全相同。
- 打包干净解包 + 官方引擎：seed 911 = 76,145 / 3,721，双 DONE，0.18 ms/调用。
- 提交包：`main.py` 44,967 bytes，归档根目录仅 main.py。

## 复现

```bash
.venv/bin/python model/v4_demand_race/smoke_test.py
.venv/bin/python model/v4_demand_race/harness/arena.py --candidate model/v4_demand_race/main.py \
  --opponents v76=$PWD/model/v76_adjacent_safe_buy_lead/main.py \
  --scenarios model/v4_demand_race/harness/scenarios_64.json --workers 9
```
