# v1_baseline_lgbm

首个端到端基线方案，使用原始 12 个特征和 5 折 `StratifiedKFold`：

- LightGBM 使用 31 leaves 和 1,500 棵树，避免小容量欠拟合；
- 数值缺失值交给 LightGBM 原生处理，不添加显式数值缺失标记；
- 三个低基数类别列做无监督 one-hot，不使用 target encoding；
- 保存 OOF 概率、测试集折均概率、gain importance 和 `cv_results.json`；
- 在本目录生成 `submission.csv`，与方案代码一一对应。

完整调研依据见 [公开方案调研](../../competition_description/public_solutions_survey.md)。

## 运行

```bash
cd kaggle_Predicting_Smartphone_Addiction/model/v1_baseline_lgbm
python v1_baseline_lgbm.py
```

## 产物

- `submission.csv`：Kaggle 提交文件；
- `cv_results.json`：每折与总体 OOF AUC、参数、耗时；
- `feature_importance.csv`：5 折平均 gain importance；
- `oof_proba.npy` / `test_proba.npy`：后续消融与融合使用的概率。

## 验证结果

- **运行环境**：LightGBM 4.6.0，CPU
- **训练耗时**：209.4 秒
- **编码后特征数**：20
- **5 折 AUC**：`0.961904 / 0.962503 / 0.962977 / 0.963475 / 0.962309`
- **总体 OOF AUC**：`0.962633`
- **Public LB**：`0.96383`
- **提交 ref**：`55575008`
- **提交状态**：`COMPLETE`
- **提交文件 SHA-256**：`653138a9e4fd1fdbfbe44515663dcacb181fed9c768aae3c84b0d60ccd5140f5`

Public LB 比 OOF 高约 `0.00120`，方向与公开同配方参考一致，但当前只有一次线上观测，不能据此修改验证方案或推断私榜表现。
