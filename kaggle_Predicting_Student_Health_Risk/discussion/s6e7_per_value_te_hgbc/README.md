# S6E7 | Per-Value TE + HGBC | Single Model

对外发布的 Kaggle notebook（源于本项目方案 **v6**）。

## 发布信息

| 项 | 值 |
| --- | --- |
| 平台 | Kaggle Code（比赛 playground-series-s6e7） |
| 作者 | yaoguang516（队伍 datatuu） |
| URL | <https://www.kaggle.com/code/yaoguang516/s6e7-per-value-te-hgbc-single-model> |
| kernelId | 126478260 |
| 可见性 | **私有草稿**（待人工审阅后在 Kaggle 页面点 "Make Public" 才公开） |
| 首次上传 | 2026-07-04 |
| Kaggle 云端跑通 | 是（262s，无报错，产出 submission.csv） |
| 云端复现 CV | 加权 OOF **0.95034**（本地 v6 = 0.95031，二者基本一致；亦等于原配方作者自报值） |

## 内容范围

- 帖子只含 **v6**（逐值 TE + HGBC 单模），即社区已公开的配方（署名致谢 redamountassir），加上我们标配的决策权重后处理。
- **有意不含**本项目的独有成果：v10 的 rulecell 联合键 TE、天花板五项判决性计算、多种子 bagging 等——避免竞赛期泄露核心优势。

## 文件

- `s6e7_per_value_te_hgbc.ipynb`：发布的 notebook 本体（英文正文，Kaggle 惯例）。
- `kernel-metadata.json`：Kaggle `kernels push` 的元数据（数据源、可见性等）。

## 如何更新已发布版本

修改 `.ipynb` 后，用 `kernels push`（slug 字段 = `yaoguang516/s6e7-per-value-te-hgbc-single-model`）覆盖推送即产生新版本号；同一 slug 不会新建重复 notebook。
