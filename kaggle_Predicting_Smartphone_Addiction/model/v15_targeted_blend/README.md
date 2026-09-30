# v15 目标性融合尝试（OOF 引导）

本轮不是“全量一锅端”，而是基于 OOF 结果做 2~3 模型的定向搜索，减少无效尝试。

### 使用的基模型

- `v8`（三模型 rank 融合，OOF 0.968358）
- `v7`（CatBoost 双 seed 袋装）
- `v3`（CatBoost dual representation）
- `v13_xgb`（FE 版本 XGBoost）
- `v12_rank`（v8 与 v11 的 rank 融合）

### 生成文件

- `submission_pair_v13xgb_13pct_v8_87pct.csv`
- `submission_pair_v7_3pct_v8_97pct.csv`
- `submission_tri_v8_v3_v13xgb_0.8408_0.0670_0.0922.csv`
- `submission_pair_v12rank_20pct_v8_80pct.csv`
- `submission_v8_ref_copy.csv`

### OOF 评估（参考）

- `v13_xgb(13%) + v8(87%)`：0.9686565
- `v7(3%) + v8(97%)`：0.9683588
- `0.8408*v8 + 0.0670*v3 + 0.0922*v13_xgb`：0.9686352
- `v12_rank(20%) + v8(80%)`：0.9684479

均未显著超过当前 best (`v12_rank` 上线提交 OOF 0.968366，Public 0.96959)。

### 运行方式

```bash
cd /Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Predicting_Smartphone_Addiction
python model/v15_targeted_blend/v15_targeted_blend.py
```
