# GAM 主导块替换 + residual LightGBM 二阶段诊断

## 预注册

- 实验 ID：`TEMP_GAM_JOINT_REPLACEMENT_RESIDUAL_LGBM_5FOLD_SEED42`。
- 上游证据：replacement standalone GAM 相对 v98 additive GAM 为
  `+0.0001490857180440`、5/5，已过阶段 1；R0 叠加式联合键的优化失败不作强度
  证据。
- 唯一问题：在完全相同的 strict-v96 113 列特征、seed42 五折、LightGBM 参数和
  residual 重建合同下，把 A 的 v98 39 列加性 GAM `init_score` 替换为 B 的 81 列
  主导联合块 GAM `init_score`，能否把先验增益传递到最终树模型。
- A/B 都在各自 outer-fit 内拟合 GAM；outer-valid 只 transform。两臂都以
  `expit(GAM margin + LightGBM raw residual)` 形成预测。
- 晋级门槛：B 相对 A pooled OOF 至少 `+0.0001` 且至少 4/5 折提升；否则关闭，
  不建立正式 40 折版本。A 必须复现 v98 已冻结五折结果，漂移即失败。
- 预算：1200 秒、12 GiB、8 threads、0 次提交；不读 test prediction、不保存 OOF、
  不扫 C/knots/联合键/LightGBM 参数或 seed。

## 结果

- `COMPLETE / NO_GO`：A 精确复现 v98 五折 `0.9461008204503822`；B 为
  `0.9460408030211953`，相对 A `−0.0000600174291869`，0/5 折提升。
- B 五折都需要比 A 更多树，且增量全部为负；说明 saturated joint 虽提升 standalone
  GAM，却给 residual learner 留下更难拟合的残差，不能把先验排序提升等价成最终模型
  提升。
- 524.67 秒、peak RSS 4.911 GiB，预算内完成；evidence SHA-256
  `ea9531ee427f28012a0e8d486b2872b2c54411a3db7e75bd15b47b543f4c9314`。
- 分支关闭：不建立正式 40 折、不调联合键/C/knots/树参数、不提交。
