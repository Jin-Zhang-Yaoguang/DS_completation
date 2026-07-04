# Overview — Predicting Student Health Risk

- **比赛名称**：Predicting Student Health Risk
- **赛事系列**：Playground Series - Season 6, Episode 7（S6E7）
- **主办方**：Kaggle
- **类别**：Playground
- **Competition ID**：125223
- **来源链接**：<https://www.kaggle.com/competitions/playground-series-s6e7/overview>

## Description（赛题介绍）

本赛题属于 Kaggle **Playground Series（第 6 季第 7 集）**，是面向初学者、以练手为目的的**表格数据（tabular）分类竞赛**。

目标：根据学生的相关特征，**预测学生的健康风险（Student Health Risk）**——3 分类任务（`at-risk` / `unhealthy` / `fit`）。

数据字段与目标类别的具体定义见 [data.md](data.md)。

## 数据来源与生成方式（关键洞察）

比赛数据由生成模型基于以下**外部真实数据集**合成：

- **数据集**：[ziya07/college-student-health-behavior-dataset](https://www.kaggle.com/datasets/ziya07/college-student-health-behavior-dataset)
- **文件**：`student_health_dataset_50k.csv`（已下载至本比赛 `data/external/`）
- **规模**：50,000 行 × 16 列 = 1,000 名学生 × 逐小时时间戳（2025-01 → 2030-09）
- 字段与比赛数据完全一致，另含 `student_id`、`timestamp` 两列（比赛数据已去除）

### 原始数据的目标生成规则（已逆向验证，外部数据上 100% 准确）

`health_condition` 在原始数据中是**确定性规则**，不含任何随机性：

```
fit       ⟺ sleep_duration ≥ 7 且 stress_level = low 且 physical_activity_level = active
unhealthy ⟺ sleep_duration < 6 且 stress_level = high
at-risk   ⟸ 其余所有情况
```

即：目标只由 3 个字段决定（`sleep_duration`、`stress_level`、`physical_activity_level`），
其余 10 个特征在原始数据中与目标**完全无关**（各类别下均值几乎相同）。

### 比赛数据相对原始数据的变化（合成过程引入）

| 维度 | 外部原始数据 | 比赛数据 |
| --- | --- | --- |
| 规模 | 50k | train 690k + test 296k（放大 ~20 倍） |
| 缺失值 | **无** | 13 个特征全有缺失（train 共 44.9 万个缺失单元格，**人为注入**） |
| 目标规则 | 确定性，100% 成立 | 近似保留：规则字段完整的行（74.1%）上规则的 balanced acc = **0.96741**；全量为 0.81741（缺失按 False 处理时） |
| 特征-目标关系 | 仅上述 3 字段有信号 | 合成过程**额外创造**了 step_count、bmi、calorie_expenditure 等与目标的相关性（可作为缺失时的间接信号） |
| 数值范围 | heart_rate ≤ 120、exercise ≤ 120 | 被轻微压缩（heart_rate ≤ 107.7、exercise ≤ 99.8），分布更平滑 |
| 目标分布 | at-risk 87.4% / unhealthy 7.6% / fit 4.9% | at-risk 85.9% / unhealthy 8.4% / fit 5.8% |

### 对建模的启示

1. **规则特征是最强特征**：`sleep≥7`、`sleep<6`、`stress=low/high`、`activity=active` 及组合规则输出，应直接喂给模型；
2. **本题核心难点 = 缺失推断**：规则 3 字段缺失的行（约 26%）才是模型真正需要「学」的部分，
   可利用合成过程创造的间接相关性（step_count、bmi 等）推断缺失的规则字段；
3. **外部数据可作辅助训练数据**（50k 干净样本，无缺失、标签严格符合规则）。

## Evaluation（评估指标）

- **指标**：**Balanced Accuracy Score（平衡准确率）**
- **定义**：即 scikit-learn 的 `sklearn.metrics.balanced_accuracy_score`
  （各类别 recall 的宏平均，能缓解类别不平衡带来的偏差）。
- 参考：<https://scikit-learn.org/stable/modules/generated/sklearn.metrics.balanced_accuracy_score.html>
- **提交格式**：见 `data/sample_submission.csv`（接受规则并下载后补全具体列名）。

## Timeline（时间线，UTC）

- **开始时间**：2026-07-01
- **提交截止（Final submission deadline）**：2026-07-31 23:59
- **组队截止（Team merger deadline）**：2026-07-31 23:59

## Rules & Submission（规则与提交）

- **每日最大提交次数**：10 次/天
- **最大团队人数**：3 人
- **奖励**：Swag（周边礼品，非现金）
- **标签**：`beginner`、`tabular`、`balanced accuracy score`

> ⚠️ **下载数据前需在 Kaggle 网站上「Join Competition / 接受比赛规则」**，否则 API 会返回
> 403：*"You must accept this competition's rules before you'll be able to download files."*
