# v18：11 单模型 stacking + blending 实验

目标：不再用固定两模型配比（v17），改为使用 11 个单模型 OOF 进行二层融合。

## 使用的单模型

`v1_baseline_lgbm / v2_budget_lgbm / v3_dual_catboost / v5_hierarchical_lookup / v6_highres_lgbm / v7_catboost_bagging / v9_catboost_engineered / v11_xgboost_engineered / v13_lgbm / v13_cat / v13_xgb`

## 运行方式

```bash
cd /Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Predicting_Smartphone_Addiction
python model/v18_single_model_stacking/v18_single_model_stacking.py
```

## 产物

- `submission_stack_meta_lr.csv`：二层 Logistic Stacking OOF 外推得到的测试提交。
- `submission_blend_auc_opt.csv`：在单模型 OOF 空间内约束 `w>=0, sum(w)=1` 的 AUC 最优线性融合。
- `submission_uniform_avg.csv`：11 单模型等权平均（基线参考）。
- `submission_rank_uniform.csv`：rank 等权融合（基线参考）。
- `stack_blend_results.json`：OOF 指标、元模型系数、融合权重、候选选择摘要。

## 说明

- `stack` 与 `blend` 两种方案均保留 OOF 评估；
- 当前脚本会将二者中 OOF 更高者标记为默认候选；
- 由于是基于 OOF 的离线融合，提交决策仍需结合 Public/Private 行为；
- 本次实验已接入当前台账约定，后续可按 `v18` 版本继续提交与对比。

