# supervised-GAM 主导块替换诊断

## R1 新假设与确认块

- 实验 ID：`TEMP_GAM_DOMINANT_JOINT_REPLACEMENT_5FOLD_SEED42`；这是新候选，
  不是 R0 原地重试。
- R0 已在第 2 折因优化未收敛关闭。归因是把完整联合 one-hot 叠加在其全部主效应
  上造成强冗余；不通过增加 `max_iter` 修补。
- 新的唯一变量：B 不再“追加”联合键，而是把
  `Environmental_Concern_Level` 线性主效应和 Home/Subsidy/Anxiety 三组类别主效应
  替换为一个 50 水平四元联合 one-hot。其他 spline、线性、类别、Logistic 参数与 A
  完全不变。
- 可证伪判断：若低容量先验真正需要这个主导交互，解除冗余后的 B 应相对 v98 加性 A
  pooled OOF 至少 `+0.0001`，且至少 4/5 折为正；否则关闭，不进入 residual
  LightGBM 诊断。
- 预算：seed42 五折、600 秒、8 GiB、0 次提交；不读 test、不保存 OOF、不改
  solver/C/max_iter，不搜索其他联合键。
- R1 候选 runner SHA 必须在正式运行前冻结，并与 `evidence.json` 一致；完整结果出来
  前，不使用 R0 首折作为晋级证据。

运行：

```bash
pytest -q model/diagnostics/gam_dominant_joint_replacement_probe_20260905/test_probe.py
python model/diagnostics/gam_dominant_joint_replacement_probe_20260905/probe.py --mode audit
python model/diagnostics/gam_dominant_joint_replacement_probe_20260905/probe.py --mode run
```

## R1 结果

- `COMPLETE / STAGE2_GO`：A `0.9386637127547616`，B
  `0.9388127984728055`，增量 `+0.0001490857180440`，5/5 折全部为正。
- 232.72 秒、peak RSS 3.795 GiB，均在预算内；runner/evidence SHA 为
  `e5f5901b...` / `46c42466...`。
- 仅通过阶段 1：允许下一步做 matched v96 residual-LightGBM A/B；尚不授权正式
  40 折、融合或提交。
