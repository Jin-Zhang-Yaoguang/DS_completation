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

## 比赛总览

收录本仓库及关联开发工作区的 2026 年比赛。成绩核对日期：**2026-10-01**，数据依据见 [比赛记录](competition_registry.json)。`finish` 表示参赛提交阶段已结束；`ongoing` 表示仍在参赛。Kaggriculture 虽已截止提交，最终锦标赛仍在进行。表格先列 ongoing，再按提交截止时间倒序排列；ongoing 的时间是预计截止，finish 的时间是提交截止，均为台北时间。

| 平台 | 比赛 | 状态（finish、ongoing） | 完赛时间（台北） | 成绩 | 复盘文件 | 优胜方案总结 |
| --- | --- | --- | --- | --- | --- | --- |
| Kaggle | [Gemma 4 Developer Agent](https://www.kaggle.com/competitions/gemma-4-developer-agent) | ongoing | 未完赛；预计 2026-12-03 07:59 | Public **0.05**；ID 56575684；Private 尚未公布 | 参赛中 | 尚未到赛后整理阶段 |
| Kaggle | [ARC Prize 2026 · ARC-AGI-2](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2) | ongoing | 未完赛；预计 2026-11-03 07:59 | Public **28.47**；ID 56712831；Private 尚未公布 | 参赛中 | 尚未到赛后整理阶段 |
| Kaggle | [ARC Prize 2026 · ARC-AGI-3](https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3) | ongoing | 未完赛；预计 2026-11-03 07:59 | Public **4.69**；ID 56715571；Private 尚未公布 | 参赛中 | 尚未到赛后整理阶段 |
| Kaggle | [Predicting Electric Vehicle Purchases · S6E9](https://www.kaggle.com/competitions/playground-series-s6e9) | finish | 2026-10-01 07:59 | 私榜 **34**；Private AUC **0.94568**；Public 最佳 **0.94677** | [HTML](kaggle_Predicting_Electric_Vehicle_Purchases/比赛总结/index.html) · [Markdown](kaggle_Predicting_Electric_Vehicle_Purchases/比赛总结/参赛复盘.md) | [HTML](kaggle_Predicting_Electric_Vehicle_Purchases/比赛总结/solutions.html) · [Markdown](kaggle_Predicting_Electric_Vehicle_Purchases/比赛总结/优胜方案总结.md) |
| Kaggle | [Kaggriculture](https://www.kaggle.com/competitions/kaggriculture) | finish | 2026-10-01 07:59（提交截止；最终定榜待完成） | 当前 **167**、**2404.2** 分；最终名次待定；历史最高评级 2778.8 | [HTML](kaggle_Kaggriculture/比赛总结/index.html) · [Markdown](kaggle_Kaggriculture/比赛总结/参赛复盘.md) | [HTML](kaggle_Kaggriculture/比赛总结/solutions.html) · [Markdown](kaggle_Kaggriculture/比赛总结/优胜方案总结.md)；初步公开方案，待定榜 |
| Kaggle | [Predicting Smartphone Addiction · S6E8](https://www.kaggle.com/competitions/playground-series-s6e8) | finish | 2026-09-01 07:59 | 私榜 **789**；Private AUC **0.96976**；Public 最佳 **0.96997** | 待整理；[实验台账](kaggle_Predicting_Smartphone_Addiction/model/experiments.md) | [已归档榜首方案](kaggle_Predicting_Smartphone_Addiction/discussion/s6e8_rank01_chris_deotte_solution/README.md) |
| Kaggle | [ROGII · Wellbore Geology Prediction](https://www.kaggle.com/competitions/rogii-wellbore-geology-prediction) | finish | 2026-08-06 07:59 | 调研项目；本账号未查到正式提交，暂无成绩 | 待整理 | 待整理 |
| Kaggle | [Predicting Student Health Risk · S6E7](https://www.kaggle.com/competitions/playground-series-s6e7) | finish | 2026-08-01 07:59 | 私榜 **428**；Private Balanced Accuracy **0.95026**；Public 最佳 **0.95081** | 待整理；[实验台账](kaggle_Predicting_Student_Health_Risk/model/experiments.md) | [已有公开方案调研](kaggle_Predicting_Student_Health_Risk/competition_description/public_solutions_survey.md)；赛后总结待整理 |

Public 最佳是本账号已完成提交的最高公榜值；Private 与名次来自官方私榜，二者不一定属于同一份提交。模拟赛的历史最高评级也不等于最终参评成绩。不同比赛的指标不能横向比较。

### 复盘维护

以 **Markdown 维护正文，HTML 提供阅读体验**。每个比赛的 `比赛总结/` 下保留参赛复盘、公开优胜方案总结、已审阅 JSON 与证据清单。Kaggriculture 的初版页面保留原有交互；新页面可离线打开，左侧页签在两类总结之间切换。

```bash
pip install -r scripts/requirements-reviews.txt
python scripts/build_competition_reviews.py
```

源码和提交包的完整性，以各方案的归档说明为准；复盘摘要不是完整可复现训练包。

本地完整归档保留在 `archive/full-local-before-cleanup-20261001` 标签与本地对象库；远端发布版收录源码、复盘和关键结果，训练缓存、回放及大模型文本留在本地归档或按批准清单清理。治理记录见 [归档治理](archive/governance_20261001/README.md)。

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
- 本地 AI 配置、会话及 Skill（`.claude/`、`.codex/`、`.agents/`、`CLAUDE.md`）不纳入发布版本；上传前运行 `python scripts/check_publication.py`。旧历史中的文件不会因本次忽略规则自动消失。

## License

仅供个人学习与比赛研究使用。赛题数据版权归 Kaggle 及数据提供方所有。

## 存储治理

2026-10-01 已完成获批归档清理：项目及工作区总占用从 **1,635.88 GiB** 降至 **32.21 GiB**。具体范围、保留材料及实测口径见 [清理报告](archive/governance_20261001/CLEANUP_REPORT.md)。
