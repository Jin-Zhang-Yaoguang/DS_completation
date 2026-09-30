# v17 定向融合提交（线下 OOF 引导）

本次提交采用 2 模型线性融合：

- `submission.csv` = `0.13 * v13_xgb + 0.87 * v8`
- 生成来源：`model/v15_targeted_blend/submission_pair_v13xgb_13pct_v8_87pct.csv`

Kaggle 提交
- ref: **55588591**
- Description: `v17 candidate: v13_xgb 13% + v8 87% (OOF-targeted)`
- Public LB: **0.96977**（当前最佳）

