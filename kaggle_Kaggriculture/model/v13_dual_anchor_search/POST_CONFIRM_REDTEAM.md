# V13 confirmatory 独立红队复算

## 结论

**GO。`v13c_a2_v8_no_wool_throttle` 通过全部预注册 confirmatory gate。**

严格结论是：C 已按 Kaggle 对局得分口径显著优于 `v12a2_no_shop_gate`（A2）和 `v12_incumbent_r002`。由于对 A2 存在大量平局，不能把该结论改写为“对 A2 的纯胜率显著超过 50%”。

本次复核没有调用既有 `audit` 统计函数。所有任务、奖励、指标、分层结果和置信区间均直接从 confirmatory `games.jsonl` 的 400 行原始记录独立重建；没有修改候选、协议、results 或 `experiments.md`，也没有提交 Kaggle。

## 独立方法

- 对 JSONL 每一行启用重复 JSON key 拒绝。
- 独立根据封存 panel、候选、两个 anchor、两个席位、run fingerprint 重新生成 400 个 task ID。
- 逐行检查 task ID、run fingerprint、pair、source 全字段、候选席位、engine、closed-loop、trace、`DONE/DONE`、error、seat model 和奖励派生语义。
- 逐行重新计算 `reward_a`、`reward_b`、`margin_a` 和 `score_a`，拒绝 bool、非有限值或任何不一致。
- 以同一 source 对应的两个相反席位为一个统计 cluster，共 100 个 cluster；按日期分层，在每个日期层内有放回重采样。
- 每项 CI 独立执行 10,000 次 bootstrap，使用预注册的 SHA256 派生确定性随机种子；CI 为 2.5%/97.5% percentile。
- 胜率定义为 `W / games`；Kaggle 得分率定义为 `(W + 0.5 × T) / games`。

## 完整性

- 原始结果：400/400 行。
- 任务结构：100 source × 2 anchor × 2 候选席位。
- 400 个 task ID 全部唯一且与独立重建的 expected task set 完全相等。
- 无重复 JSON key、重复 task、foreign task、missing task、错误、非 `DONE/DONE` 或数值语义不一致。
- 400 行候选调用次数均为 719；residual fallback 总数为 0。
- confirmatory panel 的 `test_source_count=0`，并与官方 source manifest 逐条交叉核验：train 88、validation 12、test 0。
- 日期 source 数：2026-08-18 为 34，2026-08-19 为 33，2026-08-20 为 33。
- 独立复算的全部指标、CI 和 gates 与落盘 audit 逐字段一致。

## 总体结果

| 对手 | W/T/L | 纯胜率 | 纯胜率 95% CI | Kaggle 得分率 | 得分率 95% CI | 平均 margin | margin 95% CI |
|---|---:|---:|---:|---:|---:|---:|---:|
| r002 | 155/0/45 | 77.50% | [71.50%, 83.00%] | 77.50% | [71.50%, 83.50%] | +97.720 | [+81.299875, +114.495125] |
| A2 | 95/55/50 | 47.50% | [40.00%, 55.50%] | 61.25% | [56.00%, 66.50%] | +33.735 | [+20.750000, +48.235125] |

## 对 r002 的日期与席位分层

| 分层 | 局数 | W/T/L | 纯胜率 | Kaggle 得分率 | 平均 margin |
|---|---:|---:|---:|---:|---:|
| 2026-08-18 | 68 | 50/0/18 | 73.53% | 73.53% | +79.323529 |
| 2026-08-19 | 66 | 51/0/15 | 77.27% | 77.27% | +83.000000 |
| 2026-08-20 | 66 | 54/0/12 | 81.82% | 81.82% | +131.393939 |
| candidate seat 0 | 100 | 82/0/18 | 82.00% | 82.00% | +196.900000 |
| candidate seat 1 | 100 | 73/0/27 | 73.00% | 73.00% | -1.460000 |

## 对 A2 的日期与席位分层

| 分层 | 局数 | W/T/L | 纯胜率 | Kaggle 得分率 | 平均 margin |
|---|---:|---:|---:|---:|---:|
| 2026-08-18 | 68 | 30/23/15 | 44.12% | 61.03% | +24.647059 |
| 2026-08-19 | 66 | 28/18/20 | 42.42% | 56.06% | +27.333333 |
| 2026-08-20 | 66 | 37/14/15 | 56.06% | 66.67% | +49.500000 |
| candidate seat 0 | 100 | 53/27/20 | 53.00% | 66.50% | +132.410000 |
| candidate seat 1 | 100 | 42/28/30 | 42.00% | 56.00% | -64.940000 |

## 预注册 gates

| Gate | 独立复算 | 门槛 | 结果 |
|---|---:|---:|---:|
| integrity | 400/400 exact closure | 全部完整且零错误 | PASS |
| A2 得分率 point | 61.25% | 严格大于 50% | PASS |
| A2 得分率 CI 下界 | 56.00% | 严格大于 50% | PASS |
| r002 得分率 point | 77.50% | 严格大于 50% | PASS |
| r002 得分率 CI 下界 | 71.50% | 严格大于 50% | PASS |
| A2 最差日期得分率 | 56.06% | 至少 45% | PASS |
| A2 最差候选席位得分率 | 56.00% | 至少 45% | PASS |

所有预注册 gate 均为 `True`。

## 封存与哈希

| 产物 | SHA256 / 指纹 |
|---|---|
| protocol seal | `010e63413f67a90203c0b153ce46fe79d3a0be7d880ec19bd9ce9300cee63613` |
| candidate slate | `fb964dd0d195145a1189dec291b7530673e037952d66fdad8ff7846ee9f60dd2` |
| finalist seal | `192002b85d645eee2875d7994e4497208bcce5a04e289fd4477f37308a53f742` |
| confirmatory consume lock | `575523b8c7dfcf349b3e72cf8f6b71c7281ade2f16f56139460f97ce2aa625b6` |
| confirmatory panel file | `fe10f0cc72650084bc4d546f7ef111ea397d29566010d5020cb9bacc3fa3bcd8` |
| confirmatory panel records | `6b6ca237b99290ed1eecb5edb4d2a3350c9c018803153ca19e08c171e5965b55` |
| clean registry file | `bce8d87949b60f1934ca9dc9fd430c66525295f287e6ae8e307ad21606a906c8` |
| registry + reachable serving code | `9d8a332350ccd9edef2d9cffd1b080ad59ed3bb97051b1feb456a0eb22bec28d` |
| confirmatory run fingerprint | `3aecb38121aa7640643dd99cfac45781b98ba392f38d1b8a7f131a430f4b5be2` |
| run manifest | `fb5e5d9c839e745f60426a5bfffe2f2045cc23f9b3ec50c6370cecf37987c20b` |
| confirmatory games JSONL | `7a17d2effe873d8258c7e58e5e53b8250111b46c73ef10f3a3185c75893af36c` |
| stored confirmatory audit | `9aae4c0d87fcd76e991e25061bde13cba8cadf076229f2ea8b6be3fdd7b081e8` |
| C submission archive | `ef279bbc937c73027ce17293aba19eeaa419563d2093880487ec9849400af0c1` |
| C submission manifest | `23b3119059b155b314365d752def795b0e6f48bd452156233c1aec16cadd17cc` |
| C source `main.py` | `b879a21ef457da4c6de48eebcbceeba9bd6af54ace46a38051a63de71da0f9bb` |

C 的提交归档、归档成员、submission manifest、源 `main.py` 和 clean serving closure 均与候选冻结时相同。

## 严格措辞

可以陈述：**“C 在完全未用于筛选的 100-source confirmatory panel 上，按预注册 Kaggle 对局得分率口径，同时显著优于 A2 与 r002，并通过所有完整性、日期和席位 gate。”**

不可以陈述：**“C 对 A2 的纯胜率显著超过 50%。”** 对 A2 的纯胜率为 47.50%，95% CI 为 [40.00%, 55.50%]；显著改善来自包含平局半分的 Kaggle 得分率，其值为 61.25%，95% CI 为 [56.00%, 66.50%]。
