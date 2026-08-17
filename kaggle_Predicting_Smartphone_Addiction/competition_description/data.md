# Data — Predicting Smartphone Addiction

- **比赛名称**：Predicting Smartphone Addiction（Playground Series S6E8）
- **数据类型**：含缺失值的表格二分类数据
- **目标列**：`addicted_label`
- **来源链接**：<https://www.kaggle.com/competitions/playground-series-s6e8/data>

## Files（官方文件清单）

| 文件 | 官方文件大小 | 说明 |
| --- | ---: | --- |
| `train.csv` | 44.9 MB | 训练集，包含特征与目标列 `addicted_label` |
| `test.csv` | 18.7 MB | 测试集，需要预测成瘾概率 |
| `sample_submission.csv` | 7.7 MB | 提交格式样例 |

三个 CSV 合计 71,232,415 bytes。数据已于 2026-08-17 通过 Kaggle CLI 下载并解压到本地 `data/`；原始 ZIP 同时保留，所有数据文件均由 `.gitignore` 排除。

## 本地核验结果

| 数据集 | Shape | ID 检查 |
| --- | ---: | --- |
| `train.csv` | 691,369 × 14 | `id` 唯一 |
| `test.csv` | 296,302 × 13 | `id` 唯一，且与训练集无重叠 |
| `sample_submission.csv` | 296,302 × 2 | `id` 与测试集顺序完全一致 |

训练集在 `id` 之外包含 12 个输入特征；目标无缺失且只包含 `0`、`1`：

| 目标值 | 数量 | 占比 |
| ---: | ---: | ---: |
| 0 | 200,895 | 29.0576% |
| 1 | 490,474 | 70.9424% |

属于轻到中度类别不均衡，交叉验证需使用分层抽样。

## Columns / Features

**人口属性**

| 字段 | 含义 |
| --- | --- |
| `age` | 年龄 |
| `gender` | 性别 |

**手机使用时长**

| 字段 | 含义 |
| --- | --- |
| `daily_screen_time_hours` | 工作日/日常屏幕使用时长 |
| `weekend_screen_time` | 周末屏幕使用时长 |
| `social_media_hours` | 社交媒体使用时长 |
| `gaming_hours` | 游戏使用时长 |
| `work_study_hours` | 工作或学习用途时长 |

**设备互动**

| 字段 | 含义 |
| --- | --- |
| `notifications_per_day` | 每日通知数量 |
| `app_opens_per_day` | 每日打开应用次数 |

**生活状态与影响**

| 字段 | 含义 |
| --- | --- |
| `sleep_hours` | 睡眠时长 |
| `stress_level` | 压力水平 |
| `academic_work_impact` | 对学习或工作的影响 |

**标识与目标**

- `id`：行标识，不作为模型特征。
- `addicted_label`：二分类目标；提交时填写 `1` 类的预测概率。

本地类型核验：`id` 与目标为 `int64`；9 个数值特征为 `float64`；`gender`、`stress_level`、`academic_work_impact` 为分类字符串。训练集与测试集的分类取值集合一致：

- `gender`：`Female`、`Male`、`Other`
- `stress_level`：`High`、`Low`、`Medium`
- `academic_work_impact`：`No`、`Yes`

## Missing Values

除 `id` 和目标外，所有输入字段均有缺失。训练集与测试集的缺失率存在明显差异：

| 字段 | Train 缺失率 | Test 缺失率 |
| --- | ---: | ---: |
| `age` | 4.184% | 5.784% |
| `daily_screen_time_hours` | 13.864% | 11.066% |
| `social_media_hours` | 19.381% | 15.996% |
| `gaming_hours` | 18.343% | 20.054% |
| `work_study_hours` | 7.452% | 9.375% |
| `sleep_hours` | 6.434% | 7.578% |
| `notifications_per_day` | 9.775% | 11.549% |
| `app_opens_per_day` | 11.674% | 8.675% |
| `weekend_screen_time` | 16.209% | 17.110% |
| `gender` | 4.199% | 4.796% |
| `stress_level` | 7.977% | 6.624% |
| `academic_work_impact` | 6.397% | 8.681% |

初始实验应同时比较：

1. LightGBM/CatBoost 原生缺失值处理；
2. 折内中位数/众数插补；
3. 缺失指示特征的消融实验；
4. 含缺失特征与不含缺失特征的 adversarial validation。

缺失指示可能只是在识别 train/test，而不是预测目标，因此不能仅凭训练集 CV 增益直接采用。

## Submission（提交格式）

```csv
id,addicted_label
691369,0.2
691370,0.3
```

必须满足：

- 行数和 `id` 顺序与 `test.csv` 一致；
- `addicted_label` 是 `[0, 1]` 内的概率；
- 文件名和列名与 `sample_submission.csv` 完全一致。

## 下载方式

先在 Kaggle 网站加入比赛并接受规则，然后执行：

```bash
kaggle competitions download \
  -c playground-series-s6e8 \
  -p kaggle_Predicting_Smartphone_Addiction/data/
```

## 文件完整性

SHA-256（2026-08-17 下载）：

```text
f4669147311c76eb03496061a852af283efcf0f12cf5c19274e775def81edd9c  train.csv
8b462dd47fe8165cd0b082bf33b56523c5811453070af48b9f86b2eb928de49e  test.csv
206763fe5786fb9c80d4e9289a3b812030d3dbb36450c6eb63348098154ce63e  sample_submission.csv
c89805bbfe9b8dfdbc8d0f96e8e1234edfe7b7ec87c437ace4c4354a900ad9a5  playground-series-s6e8.zip
```
