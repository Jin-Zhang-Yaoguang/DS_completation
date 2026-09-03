# Overview — Predicting Smartphone Addiction

- **比赛名称**：Predicting Smartphone Addiction
- **赛事系列**：Playground Series - Season 6, Episode 8（S6E8）
- **主办方**：Kaggle
- **类别**：Playground
- **Competition ID**：125218
- **来源链接**：<https://www.kaggle.com/competitions/playground-series-s6e8/overview>
- **本地初始化日期**：2026-08-17

## Description（赛题介绍）

本赛题是面向初学者的表格二分类竞赛。目标是根据个人的手机使用、生活方式和人口属性，预测其手机成瘾标签 `addicted_label`。

模型需要为测试集每一行输出 `addicted_label = 1` 的概率，而不是直接输出硬分类标签。

## 数据来源与性质

比赛数据是合成表格数据，灵感来自以下公开数据集：

- [Smartphone Addiction Prediction Dataset](https://www.kaggle.com/datasets/algozee/smartphone-addiction-prediction-data)

官方措辞是 *inspired by*，不能假定比赛数据与原始数据逐行一致。合成数据可能保留原始变量语义，也可能引入新的平滑关系、缺失模式和生成器伪影，因此本地验证应以比赛训练集为准。

字段与文件详情见 [data.md](data.md)。

## Evaluation（评估指标）

- **指标**：ROC AUC Score，越高越好。
- **含义**：评估预测概率对正负样本的排序能力，不依赖固定分类阈值。
- **随机排序基线**：约 0.5；完美排序为 1.0。
- **官方说明**：<https://www.kaggle.com/competitions/playground-series-s6e8/overview/evaluation>

提交格式：

```csv
id,addicted_label
691369,0.2
691370,0.3
691371,0.1
```

## Timeline（时间线）

| 事项 | UTC | 台北时间（UTC+8） |
| --- | --- | --- |
| 开始 | 2026-08-01 00:00 | 2026-08-01 08:00 |
| 报名截止 | 2026-08-31 23:59 | 2026-09-01 07:59 |
| 组队截止 | 2026-08-31 23:59 | 2026-09-01 07:59 |
| 最终提交截止 | 2026-08-31 23:59 | 2026-09-01 07:59 |

## Rules & Submission（规则与提交）

- **每日最大提交次数**：10 次。
- **最大团队人数**：3 人。
- **奖励**：前三名可获得 Kaggle 周边；本赛不授予积分或奖牌。
- **提交方式**：标准预测文件提交，不限制为 Kaggle Notebook 提交。
- **当前账号状态（2026-08-17）**：已加入比赛并接受规则；Kaggle CLI 已成功下载官方数据。

> 本赛规则已接受。后续可以直接使用 Kaggle CLI 下载数据和提交预测。

## 初始化后的建模原则

1. 使用 Stratified K-Fold，并以 OOF ROC AUC 作为主要本地验证结果。
2. 先建立可复现的 LightGBM/CatBoost 基线，再做特征工程和模型融合。
3. 所有插补、编码和统计特征必须在折内拟合，避免验证泄漏。
4. 测试集只用于生成最终概率，不利用排行榜反复探测标签。
5. 合成数据中的生成器伪影可能提高比赛分数，但必须与真实领域解释分开记录。
