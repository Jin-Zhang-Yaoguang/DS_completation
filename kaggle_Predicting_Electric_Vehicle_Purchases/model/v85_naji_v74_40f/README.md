# v85_naji_v74_40f

## Preflight revision

- `R0 / 2026-09-04`：只完成预注册、独立 TargetEncoder prior 审计、runner 实现、静态审计与 smoke；未启动正式训练，未生成效果证据，未修改历史目录、台账或周期计数。
- `R1 / 2026-09-04`：修正独立审计发现的门槛语义阻断。v74 门槛降为机制信号；项目强度只由 strict v80 门槛决定；diversity-only 不再获得融合许可，并补齐统一 base schema。R1 仍未训练。
- runner SHA-256：`cadadf826262fbf3f253778bc5764bd48e95b7386f0b92a86eaad02a53f5d30b`
- 冻结配置 SHA-256：`0ed289568d8718b4548442aa843284d31b2282c7ed37a129343cd82a3efcdd8f`

## 预注册

- 实验 ID：`v85_naji_v74_40f`。
- 研究周期：`C01`，预留为第6个普通版本候选。只有正式运行并以可核验的 `COMPLETE` 或 `FAILED` 关闭后才计数；预注册时不计数。
- 类型：单模型；预注册状态：`DESIGN_READY_NOT_STARTED`；提交预算：`0`。
- 机制参考及统一 schema 的 `base`：`v74_naji_income_bin10_100_lgbm_20f`，历史完整 OOF AUC `0.9462245318765949`。未来 `cv_results.json` 必须同时写 `base`、`base_oof_auc`、`oof_delta_vs_base`，并逐项重算；这些标准别名均指向 v74。
- 项目严格基准：`v80_strict_v61_outer104395303_40f`，完整 OOF AUC `0.946240610976364`。v80 决定项目单模强度，不能与 v74 的机制 base 混用。
- 唯一主要变量：outer folds `20 → 40`。
- 机制假设：Naji 配方每折 outer-fit 覆盖率由 `95%` 提高到 `97.5%` 后，模型和完整 outer-fit TE 映射获得更多训练数据，可能提升诚实 OOF；若增益不稳定，则20折与40折差异主要是方差而非有效信号。

## 完全保持 v74 的合同

- outer split seed 固定 `42`。
- sklearn `TargetEncoder` 的 `cv=5`、`shuffle=True`、smooth=`auto` 和 `10`、每折 `random_state=42+fold` 保持不变。
- Naji v68/v69 特征配方与 income bins `[10, 100]` 保持不变：pre-TE `109` 列、需 TE `39` 列、最终 `148` 列；列序均有冻结哈希。
- LightGBM 全部基础参数、early stopping `350`、四个 fold seed 字段及 `42+fold` 公式保持不变。
- 不引入 `v6_multiscale_te_lgbm` 的手工 TE，不增加特征、不调参数、不改 seed、不调融合权重。

## TargetEncoder 1.7.2 prior 独立确认

- 运行时强制 `scikit-learn==1.7.2`，并冻结 `TargetEncoder.fit_transform` 源码 SHA-256：`0c6563ad597ef2d36b5ee4d9378d3c112c598f27aa6314205b18d77accaf36dd`；源码漂移即拒绝运行。
- 源码审计结论：`fit_transform` 创建固定的 stratified inner folds；每个 inner hold 的 encoder 都以该 fold 的 `y_train` 计算 `y_train_mean`，再对 hold 做 transform。因此 inner hold 的 prior 和类别统计均不读取 inner-hold 标签。
- 独立实证：构造23行、每行类别唯一的数据，以相同5折切分手工计算 inner-train 正类率。smooth=`auto` 与 `10` 的 hold 编码都与对应 inner-train prior 逐元素一致，最大绝对误差均为 `0.0`。
- outer-fit 使用 `fit_transform` 获得交叉拟合训练编码；outer-valid/test 只调用已在完整 outer-fit 上拟合的 `transform`。这满足 inner prior 与 outer validation 泄漏边界。

## 验收与决策

- `mechanism_signal`：`OOF(v85)-OOF(v74) >= 0.00003`，且在 seed42 固定的40个 outer buckets 上严格胜过 v74 至少 `24/40`。v74 的既有完整诚实 OOF 只按 v85 的40个 validation buckets 重评分，不重训 v74。该信号只回答40折是否改善 Naji v74 机制，永远不授权项目强度晋级或融合。
- `project_strength_gate`：必须相对 strict v80 同时达到完整 OOF `>= +0.0001`，且 seed42 固定40 buckets 严格胜出 `>=24/40`。只有此门槛通过才输出 `ADVANCE_PROJECT_STRENGTH_PATH`，并令 `allowed_for_fusion=true`；提交权限仍为 false。
- 多样性路径：若项目强度未通过但 v85 OOF `>=0.9452`，决策为 `ELIGIBLE_FOR_SEPARATE_V80_SMALL_FUSION_PREREGISTRATION_ONLY`。此时必须写 `allowed_for_fusion=false`、`eligible_for_separate_preregistration=true`。
- 任何实际小融合都必须另起实验、预先冻结成员、变换与权重，并相对最佳输入成员达到 `+0.0001` 且 fit-only 元验证 `5/5`。v85 本身不调权、不执行融合，也不声称融合通过。
- 低于多样性下限且未过项目强度：`STOP`。v85 的 `allowed_for_submission` 始终为 false。
- 同时报告两套清晰分离的基准字段：v74 的 `base/base_oof_auc/oof_delta_vs_base` 和 mechanism signal；v80 的 `strict_project_baseline/oof_delta_vs_v80_strict` 和 project strength gate。

## 恢复、资源与完整校验

- 每折原子写一个 checkpoint；checkpoint 绑定候选代码、冻结配置、v68/v69/v74 配方、train/test、v74/v80 结果与预测、Python/NumPy/Pandas/SciPy/sklearn/LightGBM 版本的完整运行合同哈希。任一来源漂移都拒绝恢复。
- 使用内核 `flock` 阻止并发实例；获得锁后重新检查 `cv_results.json`。若已有 COMPLETE，只重建 verify 后退出；非 COMPLETE 证据要求先人工审计。
- 每5折写 `INTERIM_DIAGNOSTIC_NOT_FINAL`，报告当前 candidate/v74/v80 同行 OOF、逐 bucket 胜数、训练/恢复折数、墙钟、peak RSS 和粗略 ETA。
- 墙钟硬预算 `50分钟`，进程 peak RSS 硬门槛 `12 GiB`。每折前后（包括第40折）、全部折结束后及 COMPLETE 前均检查；达到墙钟或超过内存门槛时原子写 `FAILED`，不得写 COMPLETE，已完成 checkpoint 保留。
- COMPLETE verify 必须从40个 checkpoint 逐元素重建 OOF/test，复算每折 AUC、均值/标准差、best iterations、v74/v80 bucket 分数、统一 base 别名与 delta、Spearman、mechanism signal、project strength gate、diversity eligibility、decision、fusion/preregistration/submission 权限、submission schema、feature importance、sources 与所有哈希。

## 运行方式

```bash
python model/v85_naji_v74_40f/v85_naji_v74_40f.py --mode audit
python model/v85_naji_v74_40f/v85_naji_v74_40f.py --mode smoke

# 本次实现任务禁止执行：
python model/v85_naji_v74_40f/v85_naji_v74_40f.py --mode train

# 仅供正式40折完成后使用：
python model/v85_naji_v74_40f/v85_naji_v74_40f.py --mode verify
```

## 当前状态

- 正式训练：已于 2026-09-04 完成 40/40 折；`cv_results.json` 状态为 `COMPLETE`。
- 完整 OOF AUC：`0.9462702273556288`；相对 v74 `+0.00004569547903388`、27/40 桶，`mechanism_signal=true`。
- 相对 strict v80：`+0.000029616379264796`、24/40 桶，低于项目强度 `+0.0001`，因此 `project_strength=false`、`allowed_for_fusion=false`。
- 裁决：`ELIGIBLE_FOR_SEPARATE_V80_SMALL_FUSION_PREREGISTRATION_ONLY`；只能另立小融合预注册，不能直接入池或提交。
- runner 自带重建和独立 `--mode verify` 均通过：40 个 checkpoint 重建 OOF/test 逐元素一致，82 个资源点核验通过；墙钟 `1449.2823` 秒，peak RSS `8.9874 GiB`。
- 独立 post-run 审计复算一致；本实验已计入 `research_cycle.json`，为 C01 `6/20`。
