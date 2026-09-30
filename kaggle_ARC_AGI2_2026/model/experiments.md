# 实验记录

## rule_search_v1 — 2026-09-26

方法：对每题分别枚举 D4 几何变换、前景/颜色裁剪、最大/最小连通块、1–4 倍缩放与拼贴、行列提取、示例一致时的常量输出；在示例对上拟合颜色映射，按规则复杂度选不同的前两项预测。完全离线，无预训练权重、外部数据、题目 ID 或公开答案硬编码。

官方 Kaggle CLI 下载的 `arc-prize-2026-arc-agi-2.zip`，解压后验证：

| 集合 | task | test 输出 | 两次预测命中 | 分数 |
| --- | ---: | ---: | ---: | ---: |
| training | 1000 | 1076 | 22 | 0.02045 |
| evaluation | 120 | 172 | 0 | 0.00000 |

训练集记录为公开题目上的独立 test 预测，不等同于训练示例拟合率。evaluation 真值只用于最后计分，不进推理。该基线对 ARC-AGI-2 公开 evaluation 集无命中；线上得分待 Notebook 正式评测后填写。

数据 SHA256：training challenges `779eaba89790ebad9af02514a7efc0aef2cf8236f046a31bbf8b9ec48f20f5`，training solutions `9f07a38bd25af5e83aa5bf85c5cb1a1fefdb30f6a755256fa65429e697ca97f9`；evaluation challenges `e7c62a4bd211867c6b538f66b8013b81f299663c82ca062f49a52bf439d6e4e8`，evaluation solutions `84be4f4f39b79e82c36d565fc878830988b094917f052ee7069aef30b33ca8f1`。

## 线上首个正式 baseline — 2026-09-26

- Notebook：`yaoguang516/arc-agi-2-rule-search-v1` v2，`COMPLETE`；源码 SHA256 `2d1d1dbddb7c09218fd72ca584a77c268c6da5e91dfe6631b3b83623de4d6ef3`，Notebook SHA256 `b1dc50c62f0ad56269cc9fbb1b841f9762ce63eb83640791157c66daa2679d58`。
- v2 输出 `submission.json`：240 task、259 个 test，均有合法 `attempt_1` 和 `attempt_2`；SHA256 `3c8a871b86365760157a4ce8ac14e812b26ed1768f8fb4da807e04d1f69981dd`，与本地 solver 对公开占位 test 的输出完全一致。
- 正式提交：ID `56575976`，`COMPLETE`，`publicScore=0.00`。公开 evaluation 是 `0/172`，因此零分如实保留。
- 正式提交命令：`kaggle competitions submit arc-prize-2026-arc-agi-2 -k yaoguang516/arc-agi-2-rule-search-v1 -v 2 -f submission.json -m "Rule search v1 baseline, Notebook v2"`。最终 CLI 结果见 `../submission_result.json`。
- `kaggle kernels pull .../2` 返回 403，未从远端直接拉取 Notebook 源码；版本身份由 v2 完成状态、交接记录和明确 v2 输出确认。
