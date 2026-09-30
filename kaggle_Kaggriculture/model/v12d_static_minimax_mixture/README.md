# V12D：完整专家静态混合（否决）

结论：不实现、不打包、不进入 formal/test、不提交 Kaggle。

这个方向检验社区帖子 736439 提到的“循环克制可用混合策略”能否迁移到我们的
完整专家池。预先限定候选至少包含
`r002_learned_router_topday_animal_throttle` 和 `baseline_v8`，可加入
`baseline_v5`、`learned_router`；每局只能在 step 0 选择一次完整专家，之后整局保持。

## 证据结论

- Round 1–3 共同存在的 `baseline_v5 / baseline_v8 / learned_router` 做三折
  leave-one-round-out maximin，三个留出折都退化成 `learned_router=100%`；混合相对
  当轮最佳固定专家的总体与最差对手增益均为 `0pp`。
- `r002` 只在 Round 3 首次正式参赛，现有三张完整矩阵无法诚实识别“包含 r002”
  的三折 LOO；不能把缺失表现补成 parent 表现。
- 在 Round 3 的完整矩阵中加入 r002 后，maximin 又退化成 `r002=100%`。
  强制 `r002/V8=50/50` 相对纯 r002：总体得分率下降约 `3.93pp`，最差对手得分率
  下降约 `7.63pp`。
- 已打开的 v3/v4 screen 中，r002 对 V8 分别为 `63.89%`、`69.44%`；没有显示
  加入 V8 能对冲 r002 的弱点。
- 对 Round 1–3 的 300 个公开 seed、双席位做 step-0 审计，公开初始观测只有一个
  唯一哈希；runner 暴露的 `configuration.seed` 为 `None`。`player` 只是可预测的席位
  标签，不是公平随机源，也只能实现可被针对的固定 50/50 分配。

因此该方向同时失败于“混合优于最佳固定专家”和“可部署公平熵源”两道门槛。
社区的循环克制是值得保留的研究假设，但不能从他人的六专家池直接外推到我们的
V11 池。

| 留出轮 | LOO 权重 | 总体得分率 | 最差对手得分率 | 相对最佳固定总体 | 相对最佳固定 worst |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | learned 100% | 71.61% | 47.75% | 0.00pp | 0.00pp |
| 2 | learned 100% | 74.30% | 44.00% | 0.00pp | 0.00pp |
| 3 | learned 100% | 74.05% | 46.00% | 0.00pp | 0.00pp |

Round 3 在四专家 support 上的纯 r002 为总体 `79.22%`、worst `57.75%`；强制
r002/V8 各 50% 后变为总体 `75.28%`、worst `50.13%`。所有比例均来自配对 seed、
双席位后的得分率（胜 1、平 0.5、负 0），不是金币差。

## 复现

```bash
PYTHONPYCACHEPREFIX=/tmp/kaggriculture-v12d-pycache \
  .venv/bin/python \
  kaggle_Kaggriculture/model/v12d_static_minimax_mixture/analyze_mixture.py
```

结构化结果在 `mixture_audit.json`。脚本只读取 V11 Round 1–3 和已经打开的 v3/v4
screen control；代码中没有 formal/test 路径。
