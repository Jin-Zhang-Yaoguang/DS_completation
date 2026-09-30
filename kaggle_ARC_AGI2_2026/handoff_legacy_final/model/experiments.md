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
