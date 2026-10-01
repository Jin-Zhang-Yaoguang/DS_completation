# A/B 完成后的公开代码增量检查

通过 Kaggle 官方 CLI 留存最新 25 项和按 scoreDescending 排序的 20 项元数据，静态阅读两个更新时间晚于上次检查的 notebook。未执行外部代码，未下载预测，未提交。此前原始列表未落盘，本次不是穷尽差异扫描。

- [Magic Features](https://www.kaggle.com/code/miickey/advanced-lightgbm-magic-features-0-9468-auc)：0.946798 是作者报告的单次 80/20 holdout，当前 notebook 的 holdout 开关关闭，不是线上分数或完整 OOF。数字拆分、频率、双 TE、收入标志与现有 V85 重合；原始支持度与交叉类别未单独证明能提升 V100。
- [Cracking the Generator](https://www.kaggle.com/code/arizalfirdaus123/cracking-the-generator-0-944-auc)：数字拆分、精确频率与 max_bin 已有。权重优化和分数使用同一 OOF；后续每折伪标签来自已使用全体训练标签的最终 test ensemble，教师间接包含该折验证标签。对抗 AUC 接近 0.5 也不能证明所有分布相同或选模无偏。

结论：这两份更新没有提供足以开启新正式训练的机制证据。这个结论仅限本次检查，不代表所有公开方法都已穷尽。原 A/B 已完整结束，B−A 为 +0.000007822121、4/5 正向；未过固定门槛，C/D 未测试。
