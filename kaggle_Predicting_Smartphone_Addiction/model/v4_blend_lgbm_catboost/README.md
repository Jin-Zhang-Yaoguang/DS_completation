# v4_blend_lgbm_catboost

v2 LightGBM 与 v3 CatBoost 的 rank blend 候选。

融合不是直接在全量 OOF 上选择并汇报同一个权重，而是：

1. 留出一个外层折；
2. 在其余四折选择权重；
3. 将该权重应用到未参与选择的折；
4. 汇总五个真正 held-out 的融合预测计算 OOF AUC；
5. 测试集使用五次所选权重的平均值。

## 准入门槛

- v2/v3 OOF Spearman correlation `< 0.995`；
- cross-fitted blend 相对 v3 至少提升 `+0.0001`；
- 只有同时满足才生成 `submission.csv`。

## 运行

```bash
cd kaggle_Predicting_Smartphone_Addiction/model/v4_blend_lgbm_catboost
python v4_blend_lgbm_catboost.py
```

## 结果

- **v2 OOF**：`0.963559`
- **v3 OOF**：`0.967965`
- **OOF Spearman correlation**：`0.984420`
- **五次留一折所选权重**：均为 v2 `0.12` / v3 `0.88`
- **Cross-fitted blend OOF**：`0.968055`
- **相对 v3**：`+0.000089`
- **Held-out 折结果**：5/5 折提升
- **裁决**：未达到预注册 `+0.0001` 门槛，不生成或提交融合文件。

融合存在真实但很小的互补性。为避免看到结果后降低标准，本轮保留实验记录，等待第三种低相关模型加入后再重新评估融合。
