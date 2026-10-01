# supervised-GAM 主导交互诊断

## 预注册

- 实验 ID：`TEMP_GAM_DOMINANT_JOINT_5FOLD_SEED42`。
- 归因：v98 的 39 列纯加性 GAM `init_score` 在正式 40 折相对 v96 为
  `+0.0000934995`、33/40，方向稳定但略低于门槛；其 GAM 明确不含交互，而已知
  主信号由环保等级、补贴、续航焦虑、家庭充电条件共同决定。
- 唯一问题：在同一外折训练数据上，仅给 v98 加性 GAM 增加一个冻结的
  `Environmental_Concern_Level × Subsidy_Available × Range_Anxiety_Level ×
  Home_Charging_Possible` 50 水平联合 one-hot，能否提高低容量先验排序。
- 阶段 1：seed42 五折，A 为 v98 原 39 列加性 GAM，B 为 A 加上述唯一联合键；
  Logistic 参数完全相同。只比较 standalone OOF，不训练 LightGBM。
- 阶段 2 门槛：B 相对 A pooled OOF 至少 `+0.0001` 且至少 4/5 折提升，才允许
  另立“相同 v96 residual LightGBM + 两种 GAM init_score”的配对诊断；阶段 1
  通过本身不授权 40 折正式版。
- 预算：600 秒、8 GiB、0 次提交；不读 test、不保存 OOF 数组、不扫描交互、C、
  knots、seed 或联合键变体。

运行：

```bash
pytest -q model/diagnostics/gam_dominant_joint_probe_20260905/test_probe.py
python model/diagnostics/gam_dominant_joint_probe_20260905/probe.py --mode audit
python model/diagnostics/gam_dominant_joint_probe_20260905/probe.py --mode run
```

## R0 结果

- 状态：`FAILED_IMPLEMENTATION / CLOSED`。第 1 折 B 相对 A 为
  `+0.0003016764`，但第 2 折 B 的 `lbfgs` 在冻结的 1000 次迭代上限内未收敛，
  因此没有完整 OOF，不能用首折结果宣称机制通过。
- 归因：完整联合 one-hot 与其全部主效应同时进入设计矩阵，存在强线性相关，增加了
  优化困难；这不是模型强度结论。
- 缺陷：R0 runner 没有在异常分支写结构化 evidence。失败已补记到
  `r0_failure.json`；禁止删除 marker、原地加迭代次数或重跑相同候选。
- 下一假设若继续，必须使用新目录和新 SHA，把四个主效应块替换为联合块以解除冗余，
  而不是单纯放宽优化预算。
