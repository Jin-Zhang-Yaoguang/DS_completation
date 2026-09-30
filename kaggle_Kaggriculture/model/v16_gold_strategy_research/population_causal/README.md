# Population-causal paired development audit

## 结论边界

这里冻结的是 **development**，不是 formal：15 个环境 seed 来自已经暴露的 2026-08-25 Replay 面板，双方仅复用相同 seed、seat 和实时对手；Replay 没有作为对手 action tape。A2 只是回归锚点，不是优化目标。

Kaito v48 的 `main.py` 许可尚未核验，因此源码和 submission 均不进入仓库。运行脚本必须显式提供外部文件，且 SHA256 必须为 `dadee25a9840313218384208c53b2c4752f82c3209cc654632e0b96c65e2664a`。在许可、fresh seed、当前 top/meta live 谱系和预注册门槛全部补齐前，Kaito 只能是 **HOLD 的外部 sentinel/路线父本**，不能直接提交、不能称为 formal 晋级。

## 冻结结果

| 候选 | paired comparisons | A2 score | 候选 score | uplift | W→L / L→W | 决策 |
|---|---:|---:|---:|---:|---:|---|
| V13C | 210 | 63.33% | 62.38% | -0.95pp | 2 / 0 | REJECT |
| Kaito v48 | 180 | 69.44% | 75.00% | +5.56pp | 27 / 37 | HOLD |

V13C 的 cluster bootstrap uplift 95% CI 为 `[-2.86, 0]pp`；Kaito 为 `[-11.11, +21.11]pp`。两者均使用 `python.random.Random(seed=20260826)`、10,000 次按环境 seed 聚类重采样。Kaito 的均值提升主要来自 `v9_anti_mirror`（`+53.33pp`），而对 `v1/v3/v5_ppo` 各 `-10pp`、对 `r002` `-3.33pp`，所以不能用总体均值掩盖家族异质性。

cppsim/官方引擎 QA 使用 Kaito-vs-A2 的 2 seed × 双席位，共 4 局；奖励、双方 719 次调用全部 `4/4 exact`。这只验证本次 L1 小面板的仿真一致性，不把 development 变成 formal。

结果文件：

- `results/v13c_vs_a2_paired_dev.json`
- `results/kaito_v48_vs_a2_paired_dev.json`
- `results/kaito_a2_cpp_official_qa.json`

## 复现

在仓库根目录执行；把 `<KAITO_MAIN>` 换成外部、已自行取得的 v48 `main.py`：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v16_gold_strategy_research/population_causal/paired_live_pool.py \
  --experiment all \
  --kaito-main <KAITO_MAIN> \
  --output-dir kaggle_Kaggriculture/model/v16_gold_strategy_research/population_causal/results

.venv/bin/python kaggle_Kaggriculture/model/v16_gold_strategy_research/population_causal/official_parity_qa.py \
  --kaito-main <KAITO_MAIN> \
  --output kaggle_Kaggriculture/model/v16_gold_strategy_research/population_causal/results/kaito_a2_cpp_official_qa.json
```

快速回归只跑第一个 seed、第一类对手，并逐行对照冻结结果：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v16_gold_strategy_research/population_causal/paired_live_pool.py \
  --experiment kaito --seed-limit 1 --opponent-limit 1 --bootstrap-reps 200 \
  --kaito-main <KAITO_MAIN> --output-dir /tmp/population_causal_smoke \
  --verify-against kaggle_Kaggriculture/model/v16_gold_strategy_research/population_causal/results/kaito_v48_vs_a2_paired_dev.json
```

## 实现约束

`paired_live_pool.py` 每一局都通过 V10 的隔离 factory 新建双方 policy 实例，避免历史 agent 的模块全局状态跨局污染；L1 `Game.observe(player)` 后把双方实时动作交给 `Game.step`。引擎版本不是 `1.32.7` 或 Kaito SHA 不匹配时 fail closed。

下一步若要 formal，必须另封 future-date seeds、hash-pinned current strong live pool、按 opponent lineage 留出，并在运行前写死晋级门槛；本目录的任何数值都不得复用为 formal confirm。
