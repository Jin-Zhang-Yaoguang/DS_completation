# 规则与协议快照（2026-09-26）

来源：Kaggle 官方 CLI `competitions pages -c arc-prize-2026-arc-agi-3 --content --format json`，比赛地址 <https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3>。正式执行前再查当前页面，规则可能更新。

- 任务：在未知交互式网格游戏里探索、学习并完成多关卡；一帧最大 64×64，色值 0–15。每局动作由环境公布，简单动作 `ACTION1`–`ACTION5`、`ACTION7`，坐标动作 `ACTION6(x,y)`，以及 `RESET`。
- 评测：每关完成度和相对人类动作数效率；单关原始比值 `min(human_actions/agent_actions, 1)` 后平方，关卡按序号加权，再平均游戏分数。比赛专用隐藏评测共 110 个游戏，公开/私有榜各一半。
- 提交：通过 Kaggle Notebook；CPU/GPU 均不超过 9 小时，禁用互联网；官方环境自动生成结果文件。附件有 `ARC-AGI-3-Agents/`、`arc_agi_3_wheels/` 和 25 个 `environment_files/` 公开游戏。
- 配额：每天正式提交 1 次，最终可选 2 次提交。队伍最多 8 人。
- 时间线：2026-10-26 23:59 UTC 前报名；2026-11-02 23:59 UTC 截止提交；2026-09-30 23:59 UTC 为可选第二里程碑。
- 外部数据：须公开且合理可得；获奖方案要求公开系统、模型、权重与代码，并符合官方许可要求。
- SDK：官方 `arc-agi` 的 `Arcade()` 获取游戏、创建 scorecard、逐局 `make`/`step`，最后关闭 scorecard；Notebook 使用比赛附件里的离线 wheel。
- 2026-09-26 提交 API 实测：Notebook commit 必须输出名为 `submission.parquet` 的文件；隐藏评测重跑设置 `KAGGLE_IS_COMPETITION_RERUN`，官方示例通过 `http://gateway:8001` 与评测服务交互，由 gateway 生成正式评分文件。示例来源为 Kaggle CLI 拉取的 `inversion/arc3-sample-submission-random-agent`。普通 commit 的公开局 parquet 只是可提交性与结构验证，不能代替隐藏评测分数。

2026-09-26 Kaggle CLI 报名状态由协调线程复核为 `userHasEntered=true`。本目录只保存公开数据和代码，不包含凭证。
