# v4h_tape_ledger_hybrid — OceanMix 金牌 tape × 账本卖出层（轨道 A）

> **2026-09-02 修正**：本文下方的 25.0%/23.4% 与 raw tape 18.0% 均在**错位一回合的
> tape** 上测得（replay 提取 off-by-one，详见 `model/v5_tape_tree_hmoe/README.md` §2）。
> 修正 `tape.json` 后重跑 M6：**vs V76 108/20 = 84.4%，vs V20 112/16 = 87.5%**
> （`eval_m6_v4h_tape_fixed.json`），40% 预测实际早已达成。下文保留作过程记录。

> 2026-09-02。蒸馏方案轨道 A 的完整实现与验收。**M6 可证伪预测（对 V76/V20 胜率
> ≥40%）未达成**：实测 25.0%/23.4%。失败原因已定位（单 tape 底盘对商店分布敏感，
> 真实场景基线远低于随机 seed 基线），过程中的方法论收获与可移植资产见下。

## 构成

- 底盘：排行榜第 2 名 OceanMix 的纯开环 tape（82 场跨 seed/对手/席位逐步一致；
  来源 episode `102549659`，hash `be03c18c`）。`tape.json` 与 `main.py` 同目录。
- field 层：tape 原样 + hands 对齐 + C92 式 weed 修复（原格挂起，单位离开即弃）。
- market 层（最终版）：**tape 原样原序** + 一回合 premium 前移（boatlee V16-RC5
  配方：下一回合有卖单、本回合无需求 tick、shed 有货 → 提前一回合，等量记账扣除）
  + 终局 714+ 兜底清算。

## 关键教训（消融实录，对 V76，seed 11/42/101 margin 合计）

| 版本 | margin 合计 | 结论 |
| --- | ---: | --- |
| 初版（计划流 + race 跟跑 + 现金流阀 + 价格挂起） | −38.3k | 每个"聪明"机制都在放血 |
| 关 race 跟跑 | −26.9k | **跟跑是滞后信号**：看到对手在卖再跟 = 追着砸盘 |
| 关现金流阀 | −21.4k | tape 自身资金链自洽，阀只会多余贱卖 |
| RAW tape | −17.8k | 基线 |
| 最终版（tape 原样 + V16-RC5 前移 + 终局） | −33.7k→修复后优于 RAW | 见下两条 |

两个决定性 bug（对后续所有 tape 类方案通用）：
1. **卖单不要做 obs-shed 库存预检**。引擎按 field 结算后的新 shed 成交并自动截断
   超量；obs 里的旧 shed 会错杀"同回合入库→卖出→用回款买地"的资金链。本 bug 曾
   导致 NE 象限购地静默失败 → 牛羊无处放置 → 生产腰斩（−80k 级）。
2. **DIG 替换会改变空地数 → 重掷商店抽签**（survey §3.3 的坑在 agent 内部重现）。
   随机 seed 上 weed 修复的 ±5k delta 大部分是商店重掷噪声——评测必须钉商店。

## M6 验收（64 真实场景 × 双席位，商店钉住）

| 候选 | vs V76 | vs V20 |
| --- | --- | --- |
| RAW tape（母体） | 23/105 = **18.0%**，margin −20.2k | — |
| 本方案 | 32/96 = **25.0%**，margin −15.5k | 30/98 = 23.4%，margin −17.4k |
| 对照：V4H（v1am 底盘） | 43/85 = 33.6%，margin −4.6k | 43/85 = 33.6%，margin −4.2k |

- **层的净贡献 +7.0pp / +4.7k margin**（25.0% vs 母体 18.0%）——lead + weed 修复 +
  终局兜底在 tape 底盘上是干净的正收益，**可移植**。
- **底盘是瓶颈**：OceanMix tape 在随机 seed 上中位 −4.6k（≈45% 档），但在 64 个
  真实商店场景上只有 18%——单 tape 无法适应商店分布（yarn=1 场景带中位 −23.7k）。
  v1am 底盘的双路线适应使它在同场景 33.6%。
- 按 yarn 分层（vs V76）：v1am 在 yarn≥3 场景 8/8 全胜；yarn=1 是两个底盘共同的
  最大弱点带（v1am 11/40，tape 6/40）。

## 结论与下一步

1. 轨道 A 关闭：单 tape 蒸馏底盘不如 v1am 双路线复刻底盘，40% 门槛未过。
2. 可移植资产：+7pp 的市场层；两条 bug 教训；分层评测方法。
3. 后续最有希望的方向（按证据强度）：
   - **tape 内省式 lead**：v1am 底盘是查表 agent，其未来卖单可从路线表读出——
     旧 V4H README 指名的缺失能力，配合对手收获预报（tiles 公开）做真正的
     "抢在对手供给到达之前"，而非本方案已证伪的"跟跑"。
   - **yarn=1 场景带专项**：40 场 × 28% 胜率是最大的可挖掘弱点。
   - 多 tape 条件路由蒸馏（yukino 式）：oracle 上限 38%（修正解析后需重算），
     且受"开局前无商店信息"约束，优先级降低。

## 复现

```bash
.venv/bin/python model/v4_demand_race/harness/arena.py \
  --candidate model/v4h_tape_ledger_hybrid/main.py \
  --opponents v76=model/v76_adjacent_safe_buy_lead/main.py v20=model/v20_demand_timing_moe/main.py \
  --scenarios model/v4_demand_race/harness/scenarios_64.json --workers 10 \
  --out model/v4h_tape_ledger_hybrid/eval_m6_v4h_tape.json
```
