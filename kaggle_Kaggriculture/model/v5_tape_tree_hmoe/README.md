# v5_tape_tree_hmoe — 前缀一致 tape 树路由（分层蒸馏）

> **部署警告（2026-09-03）**：本目录 `submission.tar.gz`（`main.py` + `lib/OceanMix.json.gz`）**不能直接提交**——
> Kaggle 加载器用 `exec(code, {})` 执行，无 `__file__`，相对路径加载 lib 会失败，且取命名空间最后一个可调用为 agent。
> 提交前需重打为单文件（tape 内嵌 base85，`agent` 置于文件末尾），并做干净解包 + 路径式自博弈验证（参考 `v10_rule_distill/build_submission.py`）。

> **2026-09-02 勘误**：本文 §1/§3/§8 中所有"M6"数字在失真的钉商店环境上测得（8 家商店从第 0 步
> 全部可见，见 `model/eval_m6_fixed/README.md`），一律作废。修复后：V5 vs V76/V20 = **87.5% / 87.5%**，
> V5 vs V120 = 43.8%；随机 seed 数字（95%/95%、33.8%）本来就有效。对 V120 的完整结论见
> `V120_LOOP_REPORT.md`。

> 2026-09-02。**loop 目标（对 V76/V20 胜率 ≥80%）已达成。** 但归因必须写清楚：
> 增益 100% 来自修复 replay 提取的 off-by-one（见 §2），分层路由与守卫层对本底盘
> 的贡献约 +100 金币、W/L 不变。

## 1. 结果

| 评测 | vs V76 | vs V20 |
| --- | --- | --- |
| M6（64 真实场景 × 双席位，商店钉住） | **108/20 = 84.4%**（Wilson LB 77.1%），+13.7k | **112/16 = 87.5%**（LB 80.7%），+14.1k |
| 全新 40 随机 seed × 双席位 | **76/4 = 95.0%**（LB 87.8%），+11.8k | **76/4 = 95.0%**（LB 87.8%），+12.3k |
| M6 vs `v1_adaptive_market` / `v4h_demand_race_hybrid` | 128/0，+28.9k | 128/0，+28.9k |

QA：打包 `submission.tar.gz`（1.39 MB：`main.py` + `lib/OceanMix.json.gz`）干净解包后，
官方 `kaggle-environments` 1.32.7 与 kagsim 同 seed 逐分一致（84013/69281，双方 DONE）。

## 2. 决定性修复：replay 动作的 off-by-one

`steps[i][seat].action` 是"产生 steps[i] 的动作"，即第 **i−1** 回合的动作。此前所有
tape（方案 A、蒸馏可行性报告里的 raw tape 快测）都整体延后了一回合——跨日边界处
（hour 23 的动作被推到次日 hour 0，而日终已重置单位与 hands）直接错乱。
修正为 `actions[t] = steps[t+1][seat].action` 后，6 场"同 episode 双方 tape → kagsim"
精确回放**全部 bit-exact 复现记录的 rewards**（此前 6/6 DIVERGE）。

受影响的历史数字（均已失效）：方案 A 的 25.0%/23.4%、raw tape 18.0%、
可行性报告里的"raw tape 对 V76 0/12、中位 −4.6k"。修正后同一份 tape 是 84.4%/87.5%。

## 3. 六队 tape 树 M6 对比（vs V76 / V20）

| 队（榜次） | 类型 | 库 | 胜率 |
| --- | --- | ---: | --- |
| **OceanMix (#2)** | 纯开环 tape | 171 场 | **84.4% / 87.5%** |
| yukino (#6) | 中度自适应（d10 分叉） | 108 | 48.4% / 50.0% |
| Driz Lo (#5) | 深度自适应 | 84 | 47.7% / 48.4% |
| tetsuya (#1) | 深度自适应（d5 起分叉） | 217 | 35.2% / 35.2% |
| MtN (#10) | 主体 tape + 窄适应 | 93 | 28.9% / 29.7% |
| Crop Dusta (#3) | 深度自适应（d1 起分叉） | 383 | 11.7% / 11.7% |

结论：**前缀一致树只能安全地在"分叉点"切换，而自适应队伍的分叉依赖商店之外的
信号（市场/对手），按商店相似度路由到的续盘在本局语境下失配**——榜首越自适应，
其轨迹越不可蒸馏。纯 tape 的 OceanMix 反而是最好的蒸馏目标。这与可行性报告的判断
一致，只是幅度比预想更极端。

## 4. 与用户提出的 HMoE 三层的对应

| 层 | 本实现 | 实测价值 |
| --- | --- | --- |
| L0 全局（开局家族） | 按 72 步前缀簇大小 × 胜率选起始对局 | 对纯 tape 队伍只有一个簇，退化为常量 |
| L1 每 3 天/每天（商店） | 前缀一致候选中按商店 Jaccard 重选续盘 | 纯 tape 无分叉；自适应队伍分叉但失配 |
| L2 每天/每回合 | weed 修复、hands 对齐、一回合前移、终局兜底 | +100 金币量级，W/L 不变 |
| CEM | 未启动 | 当前无可搜维度能改变 W/L |

## 5. 来源披露

生产骨架为 OceanMix 公开 replay（Daily Top Episodes，episode `102549659` 及其 82 场
逐步一致的同族对局；8/25–8/31 库 171 场）。公开资料 fair use 是本赛题惯例
[survey §3.6]；提交前按社区规范在方案说明中披露。

## 6. 复现

```bash
V5_TEAM=OceanMix .venv/bin/python model/v4_demand_race/harness/arena.py \
  --candidate model/v5_tape_tree_hmoe/main.py \
  --opponents v76=model/v76_adjacent_safe_buy_lead/main.py v20=model/v20_demand_timing_moe/main.py \
  --scenarios model/v4_demand_race/harness/scenarios_64.json --workers 10 \
  --out model/v5_tape_tree_hmoe/eval_m6_OceanMix.json
```

```bash
.venv/bin/python model/v5_tape_tree_hmoe/build_submission.py
```

## 7. 下一步（超出本 loop 目标）

- 线上对手池比 V76/V20 强得多（OceanMix 本身在线 2880，V76 约 1740）；对更强对手
  的胜率未知。用 `distill/` 里其他金牌队的对局做对手池评测。
- tape 每日刷新管线：`scan_teams.py` + `extract_library.py` 已可日更。
- 对自适应队伍，用"仅在其历史分叉点、且商店上下文精确匹配时切换，否则沿当前对局
  走到底"的保守路由，避免失配。

## 8. V120 门控对比（2026-09-02）

V120（`v120_hierarchical_top5_distillation`）：OceanMix 更新一局的 tape（episode
`104547425`，seat 0）+ V17/V19 系执行器与市场层，独立 `main.py` 174 KB；其金牌门为
64 随机 seed 上对 V76/V20 各 114/14。与 V5 同源（OceanMix）不同局，是最贴切的门控。

| 评测（双席位） | V5 vs V120 | V5 vs V76 / V20 | V120 vs V76 / V20 |
| --- | --- | --- | --- |
| M6 64 真实场景（商店钉住） | **60/68 = 46.9%**，−621 | **84.4% / 87.5%**，+13.7k / +14.1k | 74.2% / 74.2%，+13.7k / +13.9k |
| 同一组新 40 随机 seed | **27/53 = 33.8%**，−2.6k | 95.0% / 95.0%，+11.8k / +12.3k | **96.3% / 96.3%**，+10.8k / +11.2k |

读法：
- **直接对抗接近镜像局**（同队 tape），真实场景上 47%（margin −621，噪声级）；随机 seed 上
  V120 明显占优（66%）。镜像局胜负由市场时序决定，V120 的 V17/V19 市场层（多版打磨）
  在随机 seed 上更强。
- **对基准的优势 V5 在真实场景更大**（84/87 vs 74/74，M6 上 +10pp），随机 seed 上两者持平
  （95 vs 96）。V120 对真实商店序列更敏感（96%→74%），V5 更稳。线上天梯是真实商店抽签，
  M6 口径更贴近线上。
- 两者不构成支配关系：V5 = 更稳的骨架（episode 102549659）+ 极简守卫；V120 = 更新的
  骨架（104547425）+ 成熟市场层。**自然的下一步是把 V120 的市场层嫁接到 V5 的骨架/库上，
  或把 104547425 加进 V5 的 OceanMix 库让路由按场景选**——两者的强项正好互补。
