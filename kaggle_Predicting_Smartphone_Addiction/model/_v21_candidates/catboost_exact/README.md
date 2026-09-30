# V21 candidate: enhanced exact-value CatBoost

这是 V21 的 CatBoost 单模候选，当前只完成代码、静态检查和小样本 smoke test，尚未启动完整五折。

## 特征约定

- 保留 v3 的全部 12 个 `key_*` 精确值类别通道；9 个数值字段同时保留连续通道。
- 完整保留 v3 的三个预算特征：`component_sum_available`、`other_screen_available`、`n_components_observed`；后者视为预算可用性，不属于被禁用的全局 missing count。
- `freq_exact_*` 只使用无标签的 train+test 精确值频率；不读取目标。
- 六个小时类字段增加 `frac100`、十分位数字、百分位数字三类 decimal/lattice 表示。
- 增加 daily+social、social+weekend、daily+weekend 三个 0.1 网格 pair 类别 key；在 frequency 特征集默认增加无标签 pair frequency，可用 `--no-pair-frequency` 关闭。
- `id`、全局/行级 missing count、显式 missing flag 一律不入模。
- 类别缺失转成字符串 `__NA__`；数值缺失保持 NaN，由 CatBoost 原生处理。

12 个精确值列使用统一类别表的 `pandas.Categorical`，避免把约 100 万行 × 12 列保存成重复 Python 字符串。频次逐列统计，不构造 train+test 联合宽表。

全量只构建特征的实测结果：train `(691369, 60)`、test `(296302, 60)`，最终两个特征 DataFrame 合计 `241.36 MiB`；进程 maximum resident set size 约 `2.00 GiB`，无 swap，耗时约 `6.6s`。CatBoost 的 train/valid/test Pool 会额外占用内存，完整训练建议至少预留 `8 GiB`，更稳妥是 `12 GiB`。

## 验证命令

```bash
cd /Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Predicting_Smartphone_Addiction

PYTHONPYCACHEPREFIX=/tmp/v21-catboost-pycache \
python -m py_compile model/_v21_candidates/catboost_exact/v21_catboost_exact.py

python model/_v21_candidates/catboost_exact/v21_catboost_exact.py \
  --feature-set full --smoke
```

不带 `--smoke` 才会启动完整五折：

```bash
python model/_v21_candidates/catboost_exact/v21_catboost_exact.py \
  --feature-set full
```

完整样本只跑第 1 折进行候选筛选：

```bash
python model/_v21_candidates/catboost_exact/v21_catboost_exact.py \
  --feature-set full --fold-only 1
```

该模式只生成带 `fold1of5_screening` 的验证索引、验证预测和结果 JSON，明确写入 `is_complete_oof=false`、`must_not_submit=true`，不会生成 `oof_*.npy` 或 submission。

## 严格配对消融

完整训练时保持 v3 的 seed42 五折和 CatBoost 参数完全不变，依次运行：

1. `budget`：12 exact key + 3 pair key + 9 continuous + v3 三个预算量；
2. `budget_freq`：只增加无标签 train+test frequency；
3. `budget_lattice`：只增加 decimal/lattice；
4. `full`：frequency 与 lattice 同时加入。

三个 pair key 在四个特征集中始终保留；pair frequency 在 `budget_freq/full` 默认开启，可用 `--no-pair-frequency` 做配对关闭实验。每个方案都与历史 v3 的相同五折逐折比较；V21 只有在总体 OOF 至少提升 `0.00010`、至少 4/5 折获胜，且两个单因素分支没有明显相互抵消时，才进入第二 seed 或融合阶段。

第一轮推荐保持 v3 参数：depth 8、learning rate 0.05、最多 3000 轮、L2=6、`max_ctr_complexity=2`、early stopping 200。这样分数变化只归因于特征。通过 FE 门槛后，再单独验证 learning rate 0.04、3500 轮和 L2=7；不要把参数调整混入首次特征消融。
