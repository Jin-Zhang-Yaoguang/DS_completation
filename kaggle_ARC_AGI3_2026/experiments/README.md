# 实验与提交记录

| 日期 | 版本 | 输入 | 验证 | 结果 |
| --- | --- | --- | --- | --- |
| 2026-09-26 | v1_exploration | 官方公开 25 游戏，SDK 0.9.9，240 动作上限 | 本地 scorecard | 1 个关卡，`lp85`；score `0.04750164365548981`，结果 `public25_v1.json` |

| 2026-09-26 | Notebook v3 | 官方 wheel、25 个公开游戏 | Kaggle commit COMPLETE | 25/25 局无错误、score `0.04750164365548981`；缺少 `submission.parquet`，提交 API 返回 400，未产生提交 |
| 2026-09-26 | Notebook v4 | 官方示例的 gateway 重跑协议；相同策略 | Kaggle commit COMPLETE；正式提交 COMPLETE | 25/25 公开局无错误，真实公开局 `submission.parquet` 25 行；正式提交 ID `56576143`，线上 `publicScore=0.09` |

公开环境分数不等于隐藏评测分数。v4 Notebook SHA256 `83f6c865c664c9b34525e39ff8e2cbbe4c63b08a5ce13d9d7994840d2a689211`；公开预览 parquet SHA256 `5bf935f84b5eb68fd11fd4583457616eb6f0a61de1fd8f113e0fe98c1f3a5036`。
