# CDeotte XGBoost recipe 严格五折诊断

## 预注册

- 实验 ID：`TEMP_CDEOTTE_XGB_RECIPE_3ARM_SEED42`
- 来源：`cdeotte/fable-5-1-xgb-starter`，下载快照 SHA-256
  `08cc650a222b62385a18226871a4481c3050f790d01f7006c6562240c815ae96`。
- 唯一主要问题：在相同 XGBoost 特征、参数、seed42 五折下，把冻结生成公式作为
  `base_margin` 是否比普通 XGBoost 增加可复现信号，并形成对 v90 有用的独立家族。
- 三臂：A 普通 XGB；B 相同 XGB + generator `base_margin`；C 相同 XGB +
  generator score 单列特征。C 与三臂等权只作来源配方复现，不反向修改 B。
- 诊断验证：`StratifiedKFold(5, shuffle=True, random_state=42)`，完整 pooled
  OOF；不生成 test prediction、submission 或可复用 OOF 文件。
- 形式化门槛：B 相对 A 至少 `+0.0001` 且至少 4/5 折提升；或三臂等权 OOF
  不低于 `0.9452`，且其与 v90 的 fit-only mid-ECDF 嵌套元融合至少
  `+0.0001`、5/5 元折提升。否则不建立正式 40 折版本。
- 资源预算：1800 秒、16 GiB、8 CPU threads、0 次提交。
- 禁止：使用 Public LB 选臂/权重、从完整 OOF 调权后回报同一 OOF、参数扫描、
  保存诊断预测供后续融合。

运行：

```bash
pytest -q model/diagnostics/cdeotte_xgb_recipe_probe_20260905/test_cdeotte_xgb_recipe_probe.py
python model/diagnostics/cdeotte_xgb_recipe_probe_20260905/probe.py --mode audit
python model/diagnostics/cdeotte_xgb_recipe_probe_20260905/probe.py --mode run
```

## 结果

- 状态：`COMPLETE / NO_GO`，耗时 142.80 秒，峰值 RSS 1.33 GiB，预算内完成。
- A/B pooled OOF：普通 XGB `0.9418808099`，generator base-margin
  `0.9419104821`，仅 `+0.0000296721` 且 3/5 折提升，未过强度门槛。
- 三臂等权 OOF `0.9420130318`；与 v90 的 fit-only 嵌套元融合仅
  `+0.0000028970`、4/5 折提升，未过互补性门槛。
- 结论：不建立正式版本、不保存 OOF、不生成 test prediction、不提交。
- 证据：`evidence.json` SHA-256
  `b0c12177790f094179fa92da00174c362a5611d83f8e327ed593d07c27222a40`。
