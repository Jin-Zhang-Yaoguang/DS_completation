# Income original-frequency trace probe

- 状态：`R0_FAILED_PREFLIGHT_NO_TRAINING`；`R1_COMPLETE_NO_GO`。
- 类型：一次性五折配对诊断，不计 C01。
- 基准：strict-v96；候选仅追加 `income_original_frequency`、`income_comp_over_original_lift`、`income_original_novel`。
- 频率边界：competition frequency 只读取 train+test 特征；original frequency 只读取 original 特征；不读取 original 标签或 test 标签。
- 外层：5 折、seed 42；inner TE 完全沿用 strict-v96，inner prior/count/sum 仅来自 inner-train。
- GO： pooled delta `>= +0.0001` 且至少 `4/5` 折提升。
- 预算：1800 秒、8 GiB、0 次提交；不保存 OOF/test，不生成 submission。

R0 在读取真实 original 后、任何 LightGBM fit 前失败：原始收入有 178 个缺失值。
`RUN_STARTED.json` 与 `r0_failure.json` 永久保留。R1 不把 original 缺失当作
competition novel；频率分母使用 original 的 9,822 个非缺失收入值，并使用新的
`RUN_STARTED_R1.json`、`evidence_r1.json` 和候选代码 SHA。

R1 正式诊断结果：strict-v96 控制 `0.945969234823`，追加三列后
`0.945994371717`，pooled delta `+0.000025136894`，`5/5` 折为正。方向一致，
但只有冻结 `+0.0001` GO 门槛的四分之一，裁决 `NO_GO`；不建立 40 折版本。
耗时 `349.04s`，peak RSS `3.753 GiB`，没有保存 OOF/test 或生成 submission。

```bash
python model/diagnostics/original_frequency_trace_probe_20260905/probe.py --mode audit
pytest -q model/diagnostics/original_frequency_trace_probe_20260905/test_original_frequency_trace_probe.py
python model/diagnostics/original_frequency_trace_probe_20260905/probe.py --mode run
```
