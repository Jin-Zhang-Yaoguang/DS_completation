# Data — Predicting Student Health Risk

- **比赛名称**：Predicting Student Health Risk（Playground Series S6E7）
- **数据类型**：表格数据（tabular），二/多分类任务
- **来源链接**：<https://www.kaggle.com/competitions/playground-series-s6e7/data>

## Files（文件列表）

数据已下载至本比赛的 `data/` 目录：

| 文件 | 行数 × 列数 | 大小 | 说明 |
| --- | --- | --- | --- |
| `train.csv` | 690,088 × 15 | 60 MB | 训练集：`id` + 13 个特征 + 目标列 `health_condition` |
| `test.csv` | 295,753 × 14 | 24 MB | 测试集：`id` + 13 个特征（无目标列） |
| `sample_submission.csv` | 295,753 × 2 | 4.4 MB | 提交样例：`id,health_condition` |
| `external/student_health_dataset_50k.csv` | 50,000 × 16 | 5.5 MB | **外部原始数据集**（比赛数据的生成源，无缺失、目标为确定性规则，详见 [overview.md](overview.md) 数据来源一节） |

> `test` 的 `id` 从 690088 起接续 `train`。
> 外部数据多出 `student_id`、`timestamp` 两列；`external/` 下另有 `enhanced_student_health_dataset_50k.xls`（同源增强版，暂未使用）。

## Target（目标变量）

- **列名**：`health_condition`（分类，3 类）
- **取值与占比（train，类别极不均衡）**：

| 类别 | 数量 | 占比 |
| --- | --- | --- |
| `at-risk` | 592,561 | 85.87% |
| `unhealthy` | 57,724 | 8.36% |
| `fit` | 39,803 | 5.77% |

> ⚠️ 严重类别不平衡，且评估指标为 **Balanced Accuracy**（各类 recall 的宏平均），
> 因此对少数类 `unhealthy` / `fit` 的召回至关重要——不能只优化整体准确率。

## Columns / Features（字段说明）

**数值特征（7 个，float，均存在缺失）**

| 字段 | 含义 | min | mean | max |
| --- | --- | --- | --- | --- |
| `sleep_duration` | 睡眠时长（小时） | 3.0 | 6.99 | 10.0 |
| `heart_rate` | 心率 | 50.0 | 75.10 | 107.7 |
| `bmi` | 身体质量指数 | 16.0 | 22.98 | 34.82 |
| `calorie_expenditure` | 热量消耗 | 1200 | 2226 | 3580 |
| `step_count` | 步数 | 1002 | 8616 | 14999 |
| `exercise_duration` | 运动时长（分钟） | 0.0 | 38.75 | 99.8 |
| `water_intake` | 饮水量（升） | 0.5 | 2.19 | 4.72 |

**类别特征（6 个，object，均存在缺失，各 3 个取值）**

| 字段 | 含义 | 取值 |
| --- | --- | --- |
| `diet_type` | 饮食类型 | `balanced` / `non-veg` / `veg` |
| `stress_level` | 压力水平 | `low` / `medium` / `high` |
| `sleep_quality` | 睡眠质量 | `poor` / `average` / `good` |
| `physical_activity_level` | 身体活动水平 | `sedentary` / `moderate` / `active` |
| `smoking_alcohol` | 吸烟/饮酒 | `no` / `occasional` / `yes` |
| `gender` | 性别 | `female` / `male` / `other` |

**标识列**：`id`（唯一，非特征，勿入模）。

## Missing Values（缺失情况，train）

所有 13 个特征均含缺失，需处理。缺失量较大的字段：

| 字段 | 缺失数 | 字段 | 缺失数 |
| --- | --- | --- | --- |
| `stress_level` | 82,811 | `water_intake` | 43,477 |
| `sleep_duration` | 75,999 | `physical_activity_level` | 36,621 |
| `sleep_quality` | 58,331 | `smoking_alcohol` | 28,582 |
| `calorie_expenditure` | 52,853 | `gender` | 21,373 |
| `bmi` | 13,898 | `step_count` | 13,916 |
| `heart_rate` | 7,833 | `diet_type` | 6,901 |
| `exercise_duration` | 6,901 | | |

## Submission（提交格式）

`sample_submission.csv` 结构：

```csv
id,health_condition
690088,at-risk
690089,at-risk
690090,at-risk
```

- 两列：`id`（对应 `test.csv` 每行）+ `health_condition`（预测的类别标签，取值 `at-risk`/`unhealthy`/`fit`）。
- 行数须为 295,753，与 `test.csv` 对齐。

## Dataset Description（数据集说明）

作为 Playground Series 赛题，数据集通常由深度学习模型基于某真实原始数据集**合成生成**，
特征分布与原始数据接近但不完全相同。

## 下载方式（Kaggle API）

> 前置条件：已在网站 **Join Competition / 接受规则**。当前环境 kaggle CLI 依赖包损坏，改用 Bearer Token 直连 REST API：

```bash
curl -L -H "Authorization: Bearer <KGAT_TOKEN>" \
  "https://www.kaggle.com/api/v1/competitions/data/download-all/playground-series-s6e7" \
  -o competition_data.zip && unzip -o competition_data.zip && rm competition_data.zip
```
