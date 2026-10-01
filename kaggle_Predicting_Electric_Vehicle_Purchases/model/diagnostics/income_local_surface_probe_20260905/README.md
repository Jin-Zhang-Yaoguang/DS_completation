# Strict income local-surface probe

- 状态：`COMPLETE_NO_GO`。
- 类型：一次性五折配对诊断，不计 C01。
- 基准：strict-v96；候选追加位置、中心、对称邻域、左、右、斜率、曲率、log-count 共 8 列。
- 外层：5 折、seed 42；inner seed=`104395303 + outer fold`。
- 泄漏修复：每个 inner-hold 的统计与 prior 都只来自对应 inner-train；outer-valid 只使用完整 outer-fit。
- 与 v73 的区别：v73 是固定宽度收入类别 TE；本实验是 16,384 线性局部区间上的左右非对称曲面。
- GO：pooled delta `>= +0.0001` 且至少 `4/5` 折提升。
- 预算：1800 秒、8 GiB、0 次提交；不保存 OOF/test，不生成 submission。

结果：strict-v96 控制 `0.945969234823`，严格局部曲面 `0.945989083805`，
pooled delta `+0.000019848982`，`4/5` 折为正。增量未达到 `+0.0001`，
裁决 `NO_GO`；不建立 40 折版本。耗时 `362.29s`，peak RSS `3.678 GiB`。

```bash
python model/diagnostics/income_local_surface_probe_20260905/probe.py --mode audit
pytest -q model/diagnostics/income_local_surface_probe_20260905/test_income_local_surface_probe.py
python model/diagnostics/income_local_surface_probe_20260905/probe.py --mode run
```
