# V14 / A2 / V13C 线上数据清单

- 生成时间（Asia/Taipei）：`2026-08-24T21:30:00.253064+08:00`
- 排名查询时间（Asia/Taipei）：`2026-08-24T21:29:19.418007+08:00`
- 当前团队：rank **1602**，rating **1519.3**
- 当前 active latest-two：`55743133, 55743125`
- pre/post-game Rating：Kaggle episode/replay API 未提供；逐局只记录查询时 leaderboard team rating，并明确标注其不是赛时 Rating。

| 版本 | Submission | Public score | Active | Public episodes | W/T/L | 纯胜率 | Replay | 自方 logs | 对手 logs |
|---|---:|---:|:---:|---:|---:|---:|---:|---:|---:|
| v14 | 55722630 | 1885.2 | 否 | 87 | 66/0/21 | 75.86% | 87/87 | 87/87 | 0/87 |
| a2 | 55713355 | 2429.0 | 否 | 63 | 41/0/22 | 65.08% | 63/63 | 63/63 | 0/63 |
| v13c | 55719781 | 2062.9 | 否 | 86 | 53/0/33 | 61.63% | 79/86 | 0/86 | 0/86 |

## 口径与缺失

- Episode 总表保留 validation/public，胜负统计只使用 completed public。
- 胜负由双方 reward 比较，margin = candidate reward - opponent reward；平局不算纯胜。
- Replay 要求 EpisodeId 一致，并交叉核对双方 rewards 与 `[DONE, DONE]`。
- 两个 seat 的 logs 都尝试下载；Kaggle 通常只授权本队 seat，对手日志的 403 会保留在 manifest，不能当作运行错误。
- 逐局原始字段和覆盖状态位于 `data_inventory.json -> versions.<version>.episodes`。
