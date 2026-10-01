# Strict MLP community-mechanism probe

- 状态：`COMPLETE_NO_GO`。
- 类型：一次性五折、三模型种子的三臂诊断，不计 C01。
- 重开依据：社区报告 spike/value 特征让 MLP 约提升 `+0.006`；本地 v78 没有 original-frequency trace，且其 inner-hold smoothing prior 使用了完整 outer-fit 均值。
- A：修复 prior 后的 MLP 基线，另放 3 个零占位和 7 个零 flag，确保三臂输入宽度相同。
- B：只把 3 个零占位换成 income original-frequency trace。
- C：在 B 上仅对 7 个原始数值做训练期 `mask_prob=0.2`，同时打开对应 flag；验证不遮蔽。
- 外层 5 折 seed42；inner 5 折，prior/count/sum 只来自 inner-train；每臂 3 个相同模型种子。
- 单项 GO：pooled delta `>= +0.0001` 且至少 `4/5` 折提升；B 另需 OOF `>=0.9452`。
- 预算：1800 秒、16 GiB、0 次提交；不保存 OOF/test，不生成 submission。

结果：

- A strict baseline：`0.945398742482`。
- B + income trace：`0.945412168076`，delta `+0.000013425594`、`4/5`。
- C + mask 0.2：`0.945407636882`，相对 B `-0.000004531193`、`3/5`。
- B/C 与 v90 Spearman：`0.992630/0.991775`；有多样性但强度离 v90 约
  `0.00096`，不满足“近同强度多样性”条件。

两项均裁决 `NO_GO`，不升级 40 折。耗时 `393.97s`，peak RSS `2.113 GiB`。

```bash
python model/diagnostics/strict_mlp_community_probe_20260905/probe.py --mode audit
pytest -q model/diagnostics/strict_mlp_community_probe_20260905/test_strict_mlp_community_probe.py
python model/diagnostics/strict_mlp_community_probe_20260905/probe.py --mode run
```
