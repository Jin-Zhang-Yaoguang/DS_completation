# 实验与提交记录

| 日期 | 版本 | 输入 | 验证 | 结果 |
| --- | --- | --- | --- | --- |
| 2026-09-26 | v1_exploration | 官方公开 25 游戏，SDK 0.9.9，240 动作上限 | 本地 scorecard | 1 个关卡，`lp85`；score `0.04750164365548981`，结果 `public25_v1.json` |
| 2026-09-26 | Kaggle Notebook v1 | 私有 Notebook | `ERROR` | 写死的 wheel 路径错误；未正式提交 |
| 2026-09-26 | Kaggle Notebook v2 | 私有 Notebook | `ERROR` | 正确安装 wheel，但默认 `Arcade()` 在无网络环境请求 `three.arcprize.org` 失败；未正式提交 |
| 2026-09-26 | Kaggle Notebook v3 | 私有 Notebook | `KernelWorkerStatus.COMPLETE` | 使用公开游戏离线模式，Notebook SHA256 `63c1fda9723ca5483962f35b661b2f071f6fad6b9af35a219b38d0131308cffb`；尚未核对输出、正式提交或得到隐藏评测分数 |

正式提交尚未执行。公开环境分数不等于隐藏评测分数。协调线程已要求本任务在 v3 完成后交接给新会话，避免并发操作。
