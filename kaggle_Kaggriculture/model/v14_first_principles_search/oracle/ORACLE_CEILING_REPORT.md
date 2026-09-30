# V14 queue best-response：已暴露数据 perfect-information oracle

日期：2026-08-24  
结论状态：**机制 GO，部署仍 BLOCK**  
边界：只使用已经被 V13 消耗的 confirm100 与 screen36；没有读取或运行任何新 screen / confirm / test；没有提交 Kaggle。

## 结论

知道 A2 当回合真实 market queue 与真实 private shed 时，仅重排我方既有全 SELL 队列，就足以把纯胜率推过 65%：

| 测算 | 原始基线 | perfect-information oracle | 纯胜率变化 | 结论 |
|---|---:|---:|---:|---|
| V13C parent vs A2，已暴露 confirm100×双席 | 95W / 55T / 50L，47.50% | **151W / 20T / 29L，75.50%** | +28.00pp | 超过 65%；100-source cluster bootstrap 95% CI 为 68.50%–82.00% |
| A2 parent vs A2，已暴露 screen36×双席 | 16W / 40T / 16L，22.22% | **52W / 10T / 10L，72.22%** | +50.00pp | 排除 V13C parent 混杂；36-source cluster bootstrap 95% CI 为 59.72%–83.33% |

A2-parent 因果隔离是关键证据：queue residual 本身把 30 场平局和 6 场失败变成胜局，16 个原胜局全部保留。它不是靠 V13C 的 WOOL 改动“搭便车”。

但这仍然**不能提交**。oracle 直接读取对手当前动作与私有库存，是现实 agent 不可见的信息。它证明“机制有足够天花板”，不证明当前 `prototype_queue_solver.py` 能预测这些真值。

## oracle 的精确定义

每个闭环回合按以下顺序执行：

1. 从同一个真实 environment state 分别调用 parent 与 A2，取得双方真实动作；
2. 只在双方整条 market queue 都是 SELL、我方有 2–7 个 SELL 且至少两种商品、双方 farmer/hands 当回合无 `DROP/PICKUP/PLACE` 时进入 oracle；
3. 读取双方 observation 中的真实 private shed，以及真实 market inventory；
4. 枚举我方现有 SELL orders 的全部唯一排列；SELL 数量、market 槽集合、farmer 与 hands 完全不变；
5. 用官方单位级锁步市场语义计算双方当回合 SELL 收入；候选必须满足我方收入不低于原排列，再最大化“我方收入−对方收入”；
6. 只把选中的排列送入真实 environment，之后双方都根据已经变化的真实 observation 继续闭环决策。

因此这是“当前回合收入目标下的 perfect-information oracle”。它对当前回合的排列搜索是穷尽的，但不是对整局 719 步的动态规划全局最优，不能称为所有 queue 策略的数学绝对上限。

## V13C confirm100：逐局翻转

单局转换：

| 原结果 → oracle 结果 | 场数 |
|---|---:|
| W → W | 95 |
| T → W | **35** |
| T → T | 20 |
| L → W | **21** |
| L → L | 29 |

没有任何 W/T 被改坏。双席位 source-pattern 转换如下：

| 双席模式转换 | source 数 |
|---|---:|
| TT → WW | **17** |
| LL → WW | **6** |
| LW → WW | **5** |
| WL → WW | **4** |
| WT → WW | **1** |
| TT → TT | 10 |
| LW → LW | 9 |
| WL → WL | 20 |
| WW → WW | 28 |

触发覆盖为 171/200 局（85.50%）、87/100 sources（87.00%），共 2,754 个真实改序回合；9,166 个回合满足可枚举资格。累计 oracle 相对收入增益为 157,654，我方自身收入增益为 69,046。

### 分支、日期与席位

| V13C/A2 分支 | W/T/L | 纯胜率 | 有触发局/总局 | 触发回合 |
|---|---:|---:|---:|---:|
| V5 / V5 | 3/20/3 | 11.54% | **0/26** | 0 |
| V5 / V8 | 6/0/11 | 35.29% | 14/17 | 24 |
| V8 / V5 | 11/0/6 | 64.71% | 17/17 | 105 |
| V8 / V8 | **131/0/9** | **93.57%** | 140/140 | 2,625 |

| 切片 | W/T/L | 纯胜率 |
|---|---:|---:|
| 2026-08-18 | 51/8/9 | 75.00% |
| 2026-08-19 | 45/10/11 | 68.18% |
| 2026-08-20 | 55/2/9 | 83.33% |
| seat 0 | 81/10/9 | 81.00% |
| seat 1 | 70/10/20 | 70.00% |

收益几乎全部来自 V8/V8：原来的 75W/35T/30L 被改成 131W/0T/9L。V5/V5 一次都不触发，说明 queue residual 不是全分支通用增强器；它应当是 V8-conditioned 专家，而不是全局 wrapper。

## A2-parent screen36：因果隔离

原始 A2-vs-A2 为 16W/40T/16L。加入同一个真实动作 oracle 后变为 52W/10T/10L：

| 原结果 → oracle 结果 | 场数 |
|---|---:|
| W → W | 16 |
| T → W | **30** |
| T → T | 10 |
| L → W | **6** |
| L → L | 10 |

双席 source-pattern 为 `TT→WW 15`、`LW→WW 3`、`WL→WW 3`；未完全翻转的为 `TT→TT 5`、`LW→LW 6`、`WL→WL 4`。

触发覆盖为 56/72 局（77.78%）、30/36 sources（83.33%），942 个改序回合。两席均超过 65%：seat 0 为 25W/5T/6L，纯胜 69.44%；seat 1 为 27W/5T/4L，纯胜 75.00%。三天分别为 62.50%、75.00%、79.17%。

分支归因再次一致：V8/V8 为 46W/0T/4L（92.00%，50/50 局触发），V5/V5 为 1W/10T/1L（0/12 局触发）。

## 引擎一致性核验

除红队已做的 SELL 内核静态审查外，又从真实闭环中取两局、6 个实际触发回合，把“原排列”和“oracle 排列”分别送入官方 environment 深拷贝走一步：

- 6/6 回合的我方现金增益逐元相等；
- 6/6 回合的相对现金增益逐元相等；
- 核验值依次为 relative gain `3, 9, 5, 5, 7, 5`，没有近似误差。

这排除了手写 SELL simulator 在实际触发路径上虚构收益的最直接风险。默认 market parameters 之外的配置仍未覆盖。

## 对正式候选的含义

下一步不是继续调排列目标，而是解决**可观测性**：

1. 只在 V8/V8（或高置信预测为 V8/V8）启用；V5/V5 明确回退 parent；
2. 从 step 0 维护独立 opposite-seat A2 shadow，预测对手完整 current action，而不是复制我方 queue；
3. 维护对手 private shed 的状态估计；只要公开校验、动作预测或可执行数量任一不一致，永久 fail-closed；
4. 在已暴露轨迹上要求触发点的 opponent queue 与各商品 executable quantity 100% 命中，再进入新 frozen screen；
5. 正式 65% gate 必须在新面板上用可部署候选达成，继续按纯胜率计，不用平局得分率替代。

perfect-information 结果说明值得继续工程化；它没有给当前镜像假设解禁。`prototype_queue_solver.py` 仍把我方 queue/shed 当作对手真值，在 deployable shadow 完成前保持 BLOCK。

## 产物与指纹

| 产物 | SHA-256 |
|---|---|
| `strict_games.jsonl` | `ccb929b9953d77f683e045a1e536668542196ef7b0f4912b67a73f1e67410317` |
| `strict_summary.json` | `16d9542ad64424d5bef848896e9c64097b715d7de0e5e865581f2de4a81f6e3e` |
| `a2_parent_baseline_games.jsonl` | `bc565be0457bf483759525780fe2ae59b98681aefd77064f4987104ff6234215` |
| `a2_parent_oracle_games.jsonl` | `a8d0482aacdc2272cf1e68138412aad1731745d056a1657481c3f5baafa46554` |
| `a2_parent_summary.json` | `b919ce5180ef6604a15231f2502096edfdb7e55d5e72b8f0929c22df11f64bdc` |
| `official_counterfactual_check/strict_games.jsonl` | `26497d8a61b87cc8719e4dbf5bd6f9b24a7d8bdb32dc7d4f8fca06fb658ea63d` |
| `run_exposed_queue_oracle.py` | `46159b72d1043ce60525025438ff7f968370d6f5175d030b5fc21b8887e99667` |
| `run_a2_parent_causal_oracle.py` | `2b992e24b6e297fff102427a796135089dc444ce9d6acbe4971af1ab7d22264b` |
| Kaggriculture 1.32.7 engine | `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e` |

