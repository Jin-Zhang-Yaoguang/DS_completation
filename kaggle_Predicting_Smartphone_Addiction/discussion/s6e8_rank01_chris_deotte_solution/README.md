# S6E8 第一名方案归档

本目录归档 Chris Deotte（`@cdeotte`）在 Predicting Smartphone Addiction 比赛结束后发布的冠军方案帖：**1st Place - Distributed Intelligence - NVIDIA Inference Hub**。

## 身份与成绩核验

- Kaggle Topic：`738592`；根消息：`3518992`；
- 发布时间：2026-08-31 23:59:39 UTC，即台北时间 2026-09-01 07:59:39；
- 官方最终排行榜：Chris Deotte，第 1 名，Private AUC `0.97176`；
- 最终冠军提交：456 模型 + NVIDIA cuML Logistic Regression，`CV 0.97098 / Public 0.97207 / Private 0.97176`；
- 最佳单模型：RealMLP，`CV 0.97070 / Public 0.97174 / Private 0.97145`；
- XGBoost 单模型：`CV 0.97020 / LB 0.97030`，帖子未披露其 Private AUC。

来源：[Kaggle 方案帖](https://www.kaggle.com/c/playground-series-s6e8/writeups/1st-place-distributed-intelligence-nvidia-inference-hub)。最终名次另由 Kaggle CLI 官方 leaderboard 返回结果交叉确认。

## 文件说明

| 文件 | 内容 |
| --- | --- |
| `solution_original.md` | 英文原文，标题结构与正文不改，图片改为本地路径 |
| `solution_zh-CN.md` | 中文完整翻译，并整理翻译作者在评论区的关键技术补充 |
| `source/solution_original.html` | Kaggle API 返回的逐字节原始 HTML 正文 |
| `source/thread.json` | 完整 49 条消息：根正文 + 48 条评论/回复 |
| `source/topic_metadata.json` | 帖子元数据及带作者名的评论树 |
| `source/leaderboard_top20.json` | 官方最终排行榜前 20 名快照 |
| `source/cdeotte_s6e8_kernels.json` | 作者在本比赛公开的四个 starter Notebook 清单 |
| `assets/*.png` | 正文四张原图和作者回复中的最终提交截图 |
| `source_manifest.json` | 来源、获取命令、大小与 SHA-256 |

## 阅读边界

这不是一份可直接运行的冠军代码。作者公开了多智能体研究流程、模型家族和最终分数，但尚未公开：

- 冠军 RealMLP 的完整代码和参数；
- 456 模型集成的模型清单、OOF 和权重；
- 把 RealMLP 从常规公开方案推到 `CV 0.97070` 的具体高级特征；
- 最终训练 Notebook、模型文件或数据包。

目前最具体的新线索是：缺失值相关特征成为重要信号，并同时改善 CV 与 LB；不同模型需要不同的特征和搜索方式；智能体持续围绕错误样本做定向特征工程。作者账号已有的 S6E8 公开 Notebook 都是 starter，不能当作冠军模型。

## 来源查询命令

本次使用 Kaggle CLI `2.2.3`，没有使用 Chrome：

```bash
kaggle competitions topics list playground-series-s6e8 \
  -s top --format json

kaggle competitions topic-messages playground-series-s6e8 738592 \
  -s old -n -1 --format json

kaggle competitions topics show playground-series-s6e8/738592 \
  --page-size 200 --format json

kaggle competitions leaderboard playground-series-s6e8 \
  --show --page-size 20 --format json

kaggle kernels list --competition playground-series-s6e8 \
  --user cdeotte --page-size 200 --format json
```

CLI 的两个输出需要合并理解：`topic-messages` 含完整根正文，但作者字段为空；`topics show` 能确认作者 Chris Deotte 和评论作者。因此归档同时保存两份响应，并通过 Topic ID、消息 ID 对齐。

抓取时间：`2026-09-02T11:18:19Z` / 台北时间 `2026-09-02 19:18:19`。
