# 官方规则摘录

查询时间：2026-09-26（Asia/Taipei）。来源：Kaggle 官方 CLI `competitions pages arc-prize-2026-arc-agi-2 --content`、`competitions list -s arc-prize-2026-arc-agi-2`、`competitions files -c arc-prize-2026-arc-agi-2`。

- 任务：根据每题示例输入输出对推断新 `test` 输入的输出网格。颜色为 0–9，网格尺寸 1×1 至 30×30。
- 评测：每个 test 输入输出恰好有 `attempt_1` 和 `attempt_2` 两次预测；任一次与真值完全一致即得 1 分，按所有 test 输入平均。必须覆盖全部 task ID，多个 test 输入要按原顺序输出。
- 提交：仅 Notebook，输出文件名 `submission.json`。Notebook 禁用网络；CPU/GPU 运行不超过 12 小时。公开 `arc-agi_test_challenges.json` 是占位数据；Notebook 重跑时替换为 240 道隐藏题。
- 频率：每天最多正式提交 1 次，最终可选 2 次提交。
- 时间：2026-10-26 23:59 UTC 报名/合并截止；2026-11-02 23:59 UTC 最终提交截止。应以最新官方 Timeline 为准。
- 报名：规则要求在比赛网站注册并同意规则。2026-09-26 首次查询曾返回 `userHasEntered=False` 和 403；随后 CLI 复查为 `userHasEntered=true`，已完成正式提交并取得评分。
- 数据：官方文件含 training/evaluation challenges 和 solutions、test challenges 及 sample submission。比赛数据使用依官方规则及 Apache 2.0 条款。不可发布未参赛可获取的比赛数据。
- 官方页面：<https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/overview>、<https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/rules>、<https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/data>、<https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-2/overview/evaluation>。

注意：官方 `data-description` 文案使用连字符文件名，但 CLI 文件清单实际是下划线文件名。脚本依实际下载文件名运行。
