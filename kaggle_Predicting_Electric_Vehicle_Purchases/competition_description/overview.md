# Overview — Predicting Electric Vehicle Purchases

- **比赛名称**：Predicting Electric Vehicle Purchases
- **赛事系列**：Playground Series - Season 6, Episode 9（S6E9）
- **主办方**：Kaggle
- **类别**：Playground
- **Competition ID**：125219
- **来源链接**：<https://www.kaggle.com/competitions/playground-series-s6e9/overview>
- **数据许可**：Attribution 4.0 International (CC BY 4.0)
- **本地初始化日期**：2026-09-03

## Description（赛题介绍）

本赛题是面向初学者的表格二分类竞赛。目标是根据消费者的人口属性、收入、通勤、充电条件、环保意识、补贴与里程焦虑等特征，预测其是否会购买电动车（`Will_Buy_EV`）。

模型需要为测试集每一行输出 `Will_Buy_EV = Yes` 的概率，而不是直接输出 `Yes`/`No` 硬标签。

> 说明：Kaggle overview 页面为前端渲染，初始化时脚本与内置浏览器均未能抓到正文；本节按 Playground 系列固定模板与 API 元数据整理。官方原文请人工在链接中核对一次。

## 数据来源与性质

比赛数据是合成表格数据，按 Playground 惯例由深度学习生成模型基于公开数据集生成。经字段名、字段类型、类别取值集合与目标分布逐项比对，原始数据集为：

- [EV Adoption Behavior and Range Anxiety](https://www.kaggle.com/datasets/itzzomkar/ev-adoption-behavior-and-range-anxiety)（`itzzomkar/ev-adoption-behavior-and-range-anxiety`，10,000 行 × 15 列，`Buyer_ID` 对应比赛的 `id`，目标 `Yes` 占 17.5%）

官方措辞通常是 *feature distributions are close to, but not exactly the same as, the original*，不能假定比赛数据与原始数据逐行一致。讨论区已证实合成数据存在明显的**生成器伪影**（见下文「社区已知发现」），本地验证应以比赛训练集为准。原始数据集副本已归档在 `data/original_dataset/`，可用于对照分布或作为额外训练数据的消融实验。

字段与文件详情见 [data.md](data.md)。

## Evaluation（评估指标）

- **指标**：ROC AUC Score，越高越好。
- **含义**：评估预测概率对正负样本的排序能力，不依赖固定分类阈值。
- **随机排序基线**：约 0.5；完美排序为 1.0。
- **官方说明**：<https://www.kaggle.com/competitions/playground-series-s6e9/overview/evaluation>

提交格式：

```csv
id,Will_Buy_EV
668665,0.174645
668666,0.174645
668667,0.174645
```

## Timeline（时间线）

| 事项 | UTC | 台北时间（UTC+8） |
| --- | --- | --- |
| 开始 | 2026-09-01 00:00 | 2026-09-01 08:00 |
| 报名截止 | 2026-09-30 23:59 | 2026-10-01 07:59 |
| 组队截止 | 2026-09-30 23:59 | 2026-10-01 07:59 |
| 最终提交截止 | 2026-09-30 23:59 | 2026-10-01 07:59 |

## Rules & Submission（规则与提交）

- **每日最大提交次数**：10 次。
- **最大团队人数**：3 人。
- **奖励**：Swag（前三名可获得 Kaggle 周边）；本赛不授予积分或奖牌。
- **提交方式**：标准预测文件提交，不限制为 Kaggle Notebook 提交。
- **当前账号状态（2026-09-03）**：已加入比赛并接受规则；Kaggle CLI 已成功下载官方数据。

> 本赛规则已接受。后续可以直接使用 Kaggle CLI 下载数据和提交预测。

## 社区已知发现（讨论区，截至 2026-09-03）

讨论区共 8 个主题，尚无官方帖。已核实或值得复核的要点：

1. **train/test 分布一致**：公开 notebook 的 adversarial validation（LightGBM）AUC 约 0.5012，本地 K 折可信。
2. **顺序切分**：`id` 训练集为 0–668,664、测试集为 668,665–955,235，按序而非随机切分；`id` 不可作为特征。
3. **确定性区域**：`Annual_Income_USD >= 170,537` 的 392 行训练样本全部为 `Yes`；收入 38k–42k 的 571 行全部为 `No`；`Annual_Income_USD = 30,000` 单值占约 9.2% 行、买率 4.4%。这些是生成器伪影，对 AUC 增益接近零，但说明收入分箱/精确值特征值得试。
4. **最强单特征**：`Environmental_Concern_Level = 1` 买率仅 0.57%（其余取值平均 22.3%）。本地核验另见 `Subsidy_Available = No` 买率 0.58%、`Range_Anxiety_Level = High` 买率 0.14%。
5. **公开基线水平**：折内特征工程 + LightGBM 的 OOF AUC 约 0.9417；讨论区称排行榜在 0.94 附近出现平台期。
6. **性别、拥车数量**单特征 AUC 接近 0.5，属噪声特征。

## 初始化后的建模原则

1. 使用 Stratified K-Fold，并以 OOF ROC AUC 作为主要本地验证结果。
2. 先建立可复现的 LightGBM/CatBoost 基线，再做特征工程和模型融合。
3. 目标编码、分箱统计等特征必须在折内拟合，避免验证泄漏。
4. 测试集只用于生成最终概率，不利用排行榜反复探测标签。
5. 合成数据中的生成器伪影（收入精确值、硬阈值）可能提高比赛分数，但必须与真实领域解释分开记录。
6. 原始数据集仅 1 万行，若作为额外训练数据需做单独消融并谨慎评估分布差异。
