# DS_completation

Kaggle 数据科学比赛解决方案仓库。每个比赛以独立文件夹组织，包含赛题说明、原始数据与多套可复现的建模方案。

## 仓库结构

```
<比赛名称>/
├── competition_description/   # 赛题介绍、评估指标、字段说明、方案调研
├── data/                      # 原始数据（需自行从 Kaggle 下载，不入库）
└── model/                     # 建模方案
    ├── <方案名>/
    │   ├── <方案名>.py        # 完整训练与推理脚本
    │   └── submission.csv     # 提交文件（运行脚本后生成，不入库）
    └── experiments.md         # 实验记录与结论
```

详细约定见 [CLAUDE.md](CLAUDE.md)。

## 当前比赛

### [Predicting Student Health Risk](kaggle_Predicting_Student_Health_Risk/)（Playground S6E7）

- **任务**：根据学生特征预测健康风险（3 分类：`at-risk` / `unhealthy` / `fit`）
- **指标**：Balanced Accuracy
- **赛题链接**：<https://www.kaggle.com/competitions/playground-series-s6e7>

| 方案 | 本地 CV | 线上 Public | 要点 |
| --- | --- | --- | --- |
| v6_te_hgbc | 0.95031 | **0.95057** | 逐值 Target Encoding + 慢/浅 HGBC |
| v13_bag_v10 | 0.95047 | 0.95033 | v10 配方 × 10 种子 bagging |
| v10_te_joint | 0.95052 | 0.95046 | rulecell 联合键 TE |

完整实验记录见 [`model/experiments.md`](kaggle_Predicting_Student_Health_Risk/model/experiments.md)。

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/Jin-Zhang-Yaoguang/DS_completation.git
cd DS_completation
```

### 2. 安装依赖

```bash
pip install pandas numpy scikit-learn lightgbm catboost torch category_encoders
```

按需补充其他库（各方案脚本头部有 import 说明）。

### 3. 下载比赛数据

在 Kaggle 网站 **Join Competition / 接受规则** 后，将以下文件放入对应目录：

```
kaggle_Predicting_Student_Health_Risk/data/
├── train.csv
├── test.csv
└── sample_submission.csv
```

也可使用 Kaggle API：

```bash
kaggle competitions download -c playground-series-s6e7 -p kaggle_Predicting_Student_Health_Risk/data/
```

### 4. 运行方案

```bash
cd kaggle_Predicting_Student_Health_Risk/model/v6_te_hgbc
python v6_te_hgbc.py
```

脚本会在同目录生成 `submission.csv`，可直接提交至 Kaggle。

## 注意事项

- 原始数据与大型中间产物（`.npy`、`submission.csv`）已加入 `.gitignore`，克隆后需自行下载数据并运行脚本。
- 请勿将 API Token、密钥等凭证提交至仓库；`.kaggle/kaggle.json` 等路径已被忽略。
- 建模时注意数据泄漏，本地 CV 策略尽量与线上评估口径一致。

## License

仅供个人学习与比赛研究使用。赛题数据版权归 Kaggle 及数据提供方所有。
