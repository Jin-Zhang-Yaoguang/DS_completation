# Data — Predicting Electric Vehicle Purchases

- **比赛名称**：Predicting Electric Vehicle Purchases（Playground Series S6E9）
- **数据类型**：无缺失值的表格二分类数据
- **目标列**：`Will_Buy_EV`（字符串 `Yes`/`No`；提交时填 `Yes` 的概率）
- **来源链接**：<https://www.kaggle.com/competitions/playground-series-s6e9/data>

## Files（官方文件清单）

| 文件 | 官方文件大小 | 说明 |
| --- | ---: | --- |
| `train.csv` | 44.7 MB | 训练集，包含特征与目标列 `Will_Buy_EV` |
| `test.csv` | 18.3 MB | 测试集，需要预测购买概率 |
| `sample_submission.csv` | 7.7 MB | 提交格式样例，`Will_Buy_EV` 全填 0.174645（训练集正类先验） |

三个 CSV 合计 70,743,425 bytes。数据已于 2026-09-03 通过 Kaggle CLI 下载并解压到本地 `data/`；原始 ZIP 同时保留，所有数据文件均由 `.gitignore` 排除。

另有原始数据集副本 `data/original_dataset/EV_Adoption_and_Range_Anxiety_Dataset.csv`（10,000 × 15，来源见 [overview.md](overview.md)），非官方比赛文件，仅供对照。

## 本地核验结果

| 数据集 | Shape | ID 检查 |
| --- | ---: | --- |
| `train.csv` | 668,665 × 15 | `id` 唯一，范围 0–668,664 |
| `test.csv` | 286,571 × 14 | `id` 唯一，范围 668,665–955,235，与训练集无重叠（顺序切分） |
| `sample_submission.csv` | 286,571 × 2 | `id` 与测试集顺序完全一致 |

训练集在 `id` 之外包含 13 个输入特征；目标无缺失且只包含 `No`、`Yes`：

| 目标值 | 数量 | 占比 |
| ---: | ---: | ---: |
| No | 551,886 | 82.5355% |
| Yes | 116,779 | 17.4645% |

属于中度类别不均衡，交叉验证需使用分层抽样。**所有字段在训练集和测试集中均无缺失**。训练集内无精确重复的特征行，测试集中没有与训练集特征完全相同的行。

## Columns / Features

**人口与经济属性**

| 字段 | 类型 | 取值范围 / 唯一值数 | 含义 |
| --- | --- | --- | --- |
| `Age` | int | 25–69（45 个整数） | 年龄 |
| `Gender` | cat | `Female` / `Male` / `Other` | 性别 |
| `Annual_Income_USD` | float（全为整数值） | 30,000–188,549（train 13,214 个唯一值） | 年收入（美元） |
| `City_Type` | cat | `Rural` / `Suburban` / `Urban` | 居住地类型 |

**出行与用车**

| 字段 | 类型 | 取值范围 / 唯一值数 | 含义 |
| --- | --- | --- | --- |
| `Daily_Commute_km` | float（1 位小数） | 5.0–98.7（train 805 个唯一值） | 日通勤距离（公里） |
| `Number_of_Cars_Owned` | int | 1–4 | 拥有汽车数 |
| `Current_Car_Type` | cat | `Hatchback` / `SUV` / `Sedan` / `Truck` | 当前车型 |

**充电条件**

| 字段 | 类型 | 取值范围 / 唯一值数 | 含义 |
| --- | --- | --- | --- |
| `Charging_Stations_Near_Home` | int | 0–14 | 家附近充电站数量 |
| `Charging_Stations_Near_Work` | int | 0–19 | 工作地附近充电站数量 |
| `Home_Charging_Possible` | cat | `No` / `Yes` | 家中是否可充电 |

**态度与政策**

| 字段 | 类型 | 取值范围 / 唯一值数 | 含义 |
| --- | --- | --- | --- |
| `Environmental_Concern_Level` | float（整数值 1–5） | 1–5 | 环保关注程度（等级） |
| `Subsidy_Available` | cat | `No` / `Yes` | 是否有购车补贴 |
| `Range_Anxiety_Level` | cat | `Low` / `Medium` / `High` | 里程焦虑程度 |

**标识与目标**

- `id`：行标识，按序切分 train/test，不作为模型特征。
- `Will_Buy_EV`：二分类目标；提交时填写 `Yes` 类的预测概率。

本地类型核验：`id`、`Age`、`Number_of_Cars_Owned`、两个充电站字段为 `int64`；`Annual_Income_USD`、`Daily_Commute_km`、`Environmental_Concern_Level` 为 `float64`；6 个分类字段为字符串。训练集与测试集的分类取值集合完全一致。测试集数值范围与训练集基本一致（`Daily_Commute_km` 测试集最大 103.9 略超训练集 98.7）。

## 单变量与目标关系（训练集）

分类字段的占比与 `Yes` 率：

| 字段 | 取值 | 占比 | Yes 率 |
| --- | --- | ---: | ---: |
| `Subsidy_Available` | No / Yes | 37.2% / 62.8% | **0.58%** / 27.47% |
| `Range_Anxiety_Level` | High / Medium / Low | 0.33% / 9.35% / 90.33% | **0.14%** / 4.17% / 18.90% |
| `Home_Charging_Possible` | No / Yes | 30.8% / 69.2% | 12.71% / 19.58% |
| `City_Type` | Rural / Suburban / Urban | 18.5% / 38.2% / 43.3% | 19.34% / 18.09% / 16.11% |
| `Current_Car_Type` | Hatchback / SUV / Sedan / Truck | 11.9% / 36.9% / 45.4% / 5.9% | 17.43% / 18.10% / 17.20% / 15.64% |
| `Gender` | Female / Male / Other | 44.2% / 55.0% / 0.8% | 17.76% / 17.23% / 17.37% |

数值字段按目标分组的均值：

| 字段 | No | Yes |
| --- | ---: | ---: |
| `Annual_Income_USD` | 81,795 | 98,827 |
| `Environmental_Concern_Level` | 2.630 | 4.377 |
| `Daily_Commute_km` | 32.55 | 30.29 |
| `Age` | 47.08 | 46.83 |
| `Charging_Stations_Near_Home` | 4.99 | 4.82 |
| `Charging_Stations_Near_Work` | 7.21 | 7.04 |
| `Number_of_Cars_Owned` | 1.711 | 1.719 |

结论：`Subsidy_Available`、`Range_Anxiety_Level`、`Environmental_Concern_Level`、`Annual_Income_USD` 是主导信号；`Gender`、`Number_of_Cars_Owned`、两个充电站计数、`Age` 单变量几乎无区分力，价值需通过交互特征验证。讨论区另外报告了收入维度的硬阈值伪影（≥170,537 全 `Yes`、38k–42k 全 `No`、30,000 单值占 9.2%），说明收入的精确值/细分箱统计值得作为特征试验。

## Submission（提交格式）

```csv
id,Will_Buy_EV
668665,0.174645
668666,0.174645
```

必须满足：

- 行数和 `id` 顺序与 `test.csv` 一致（286,571 行）；
- `Will_Buy_EV` 是 `[0, 1]` 内的概率（`Yes` 类）；
- 文件名和列名与 `sample_submission.csv` 完全一致。

## 下载方式

先在 Kaggle 网站加入比赛并接受规则，然后执行：

```bash
kaggle competitions download \
  -c playground-series-s6e9 \
  -p kaggle_Predicting_Electric_Vehicle_Purchases/data/
```

原始数据集（可选）：

```bash
kaggle datasets download itzzomkar/ev-adoption-behavior-and-range-anxiety \
  -p kaggle_Predicting_Electric_Vehicle_Purchases/data/original_dataset/ --unzip
```

## 文件完整性

SHA-256（2026-09-03 下载）：

```text
eae9eaa4e6378df405e755f853771d7e26d212bd93258349fc797b771021946a  train.csv
539263f6caabc40afd5e2f0bc0ab16b10a2d1177c565fc71b866f0181d836b34  test.csv
a9747a8b947e4e35505e3da4535a5a494978b012a7adb50973f13e598849dda5  sample_submission.csv
cd9e237625b074bc9e5dda6368bf948db2ba801c826c8ef81fa53714b733296a  playground-series-s6e9.zip
```
