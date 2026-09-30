# v13 FE Single-Model Comparison

本轮实验聚焦**特征工程优先**，统一构建一版高容量特征，并用三种单模型做公平对比。

最新结果（5 折）：
- LightGBM OOF AUC：0.9648407
- CatBoost OOF AUC：0.9628394
- XGBoost OOF AUC：0.9664281

已按 FE 提交：
- ref=55585090，`submission_xgb.csv`（v13 single model compare xgb）

## 运行方式

```bash
cd /Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Predicting_Smartphone_Addiction
python model/v13_fe_single_compare/v13_fe_single_compare.py
```

## 输出

- `cv_results.json`：三模型 OOF AUC、折分位、最优迭代、特征数与排行榜。
- `feature_columns.csv`：LightGBM/XGB 的最终特征列。
- 各模型提交文件：
  - `submission_lgbm.csv`
  - `submission_cat.csv`
  - `submission_xgb.csv`
- 各模型 OOF / 测试概率：
  - `lgbm_oof_proba.npy` / `lgbm_test_proba.npy`
  - `cat_oof_proba.npy` / `cat_test_proba.npy`
  - `xgb_oof_proba.npy` / `xgb_test_proba.npy`

> XGBoost 的 OOF 与提交文件已出；建议与 `v12_xgboost_rank_blend` 做线上对照后再决定是否继续深挖。
