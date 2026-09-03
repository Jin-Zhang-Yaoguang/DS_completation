# v2_budget_lgbm

在 v1 原始特征 LightGBM 上，只加入时间预算结构表示，保持相同 folds、随机种子、one-hot 方式和模型参数，用于配对消融。

新增特征：

- `component_sum_available`：已观察到的社交、游戏、工作/学习时长之和；
- `other_screen_available`：日常屏幕时长减去上述组成之和；
- `n_components_observed`：三个组成字段中非缺失的数量。

## 通过门槛

- 总体 OOF 相对 v1 至少 `+0.0005`；
- 五个相同验证折中至少四折提升；
- 提交文件通过 ID、shape、列名、有限性与概率范围校验。

未通过门槛则不提交，转向数值连续值与精确值双重表示的 CatBoost。

## 运行

```bash
cd kaggle_Predicting_Smartphone_Addiction/model/v2_budget_lgbm
python v2_budget_lgbm.py
```

## 结果

- **5 折 AUC**：`0.962732 / 0.963387 / 0.963718 / 0.964518 / 0.963445`
- **总体 OOF AUC**：`0.963559`
- **相对 v1 OOF**：`+0.000926`
- **配对折结果**：5/5 折提升，折增益 `+0.000742–+0.001136`
- **Public LB**：`0.96467`
- **相对 v1 Public LB**：`+0.00084`
- **提交 ref**：`55575810`
- **提交状态**：`COMPLETE`
- **提交文件 SHA-256**：`9942d011beeafbb0ed6e4e144c063ae19b68c839daa17e2c0092f9140fc46525`

本地与线上提升方向一致，时间预算表示通过最小闭环验证。下一步可以在保留这三个特征的基础上，测试 CatBoost 的连续值/精确值双重表示。
