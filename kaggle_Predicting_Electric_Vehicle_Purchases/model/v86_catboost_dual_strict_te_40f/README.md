# v86_catboost_dual_strict_te_40f

## 状态

- 预注册状态：`DESIGN_READY_NOT_STARTED`
- 研究周期：`C01` 第 7 个常规版本
- 类型：`SINGLE_MODEL`
- 默认入口：`--mode audit`，不读历史预测、不训练。
- 正式入口：仅显式 `--mode train`。

## 预注册假设与唯一变量

唯一模型/原始特征基线为已经独立验收通过的 `v77_catboost_dual_40f`。保留 v77 的 20 个 CatBoost 双表示原始特征、13 个类别特征、全部 CatBoost 参数和双模型种子 `[42, 2026]`，唯一变化是在每个 outer fold 内追加 v80 配方的 17 个 key × 3 个 smoothing，即 51 个严格 nested-TE 数值特征，总宽度固定为 71。

不改 CatBoost 超参数，不删改 v77 原始列，不增加别的特征，不做融合、权重拟合、rank/ECDF 或校准变换。

## 泄漏边界

- outer：`StratifiedKFold(40, shuffle=True, random_state=42)`。
- inner：每个 outer-fit 内 `StratifiedKFold(5, shuffle=True, random_state=42+outer_fold)`。
- inner-hold 的类别统计与 smoothing prior 都只能使用对应 inner-train；改变 inner-hold 自身标签不得改变其 TE。
- outer-valid 与 test 映射只使用完整 outer-fit 的标签、统计和 prior。
- test 不允许出现或读取目标列；标签只来自 train。
- 51 个 TE 为数值列；v77 原有 13 个类别列及 CatBoost ordered statistics 保持原样。

## 基准、止损和晋级

- 过程基准：v77 的相同 seed42 outer fold；每折 checkpoint 的 `valid_idx` 必须完全一致，才允许称为同折比较。
- 10 折止损：完成第 10 折后，若前 10 折 `mean(v86_auc-v77_auc) <= 0` 且胜折 `<=4/10`，立即以 `EARLY_STOPPED_REJECT` 关闭；两个条件为 AND。
- 项目强度基准：canonical strict v80。完整 OOF 至少 `+0.0001` 且固定 seed42 的 40 个共同样本桶至少胜 `24/40`，才 `PROMOTE_SINGLE_MODEL`。
- v80 训练时使用不同 outer seed，因此 40 桶只能称共同样本桶，不能称相同训练折配对。
- 多样性只作诊断：只有候选完整 OOF `>=0.9452`，且强度门槛失败但相对 v77 或 v80 的 OOF Spearman `<0.995`，才记录 `allowed_for_fusion=false`、`eligible_for_separate_preregistration=true`。低 OOF 即使低相关也必须 `REJECT`；这不授权直接融合。
- 任何小融合必须另立实验；门槛固定为完整 OOF `+0.0001` 且 seed42 五个 meta bucket `5/5` 全正。v86 本身不拟合、不评价融合。
- 提交预算：`0`。

## CatBoost 冻结设置

- `iterations=3000`
- `learning_rate=0.05`
- `depth=8`
- `l2_leaf_reg=6`
- `loss_function=Logloss`
- `eval_metric=AUC`
- `one_hot_max_size=4`
- `max_ctr_complexity=2`
- `od_type=Iter`、`od_wait=200`
- `thread_count=16`、`verbose=500`
- 双 seed：`42`、`2026`

以上逐项与 v77/v10 冻结配方核对。

## checkpoint、恢复与验证

- 每折在 `checkpoints/fold_XX.npz` 原子写入：fold、同折索引、候选/测试预测、两个 best iteration、特征重要性、AUC、资源与 config/run-contract SHA。
- 恢复前逐项验证索引、shape、概率、hash、特征宽度、AUC；不匹配即拒绝续跑。
- 每 5 折只输出一行汇总：该五折候选/v77 均值、delta、胜折和累计资源。单模型 seed 的 CatBoost 原生日志不算研究汇总。
- `verify` 必须从 checkpoint 重建 OOF/test，检查恰好一次覆盖、v77 同折索引、strict prior 自检、结果门槛、资源、行序、schema、来源与所有 SHA。
- `COMPLETE` 顶层统一输出并复算 `model`、`n_folds`、`fold_auc`、`params`、`elapsed_seconds`；其中 fold AUC 来自 checkpoint，参数来自冻结 config，elapsed 与最终资源记录一致。
- `EARLY_STOPPED_REJECT` 也使用冻结 schema：保留已观测的 10 个 fold AUC、参数、耗时与完整代码/输入哈希；完整 OOF、完整基准 AUC 和完整 delta 等不可用值明确写为 `null`。关闭前和后续 `verify` 都执行同一 schema 校验。
- v77 独立审计必须仍为 `PASS` 且冻结 audit/source 哈希不变；strict v80 必须运行自身冻结 verifier 后才能作为项目强度基准。

## 资源硬停

- formal 单实例 flock。
- 墙钟预算：21600 秒（6 小时），从取得锁到最终验证和 COMPLETE 前检查。
- peak RSS：24 GiB，使用 `resource.getrusage`。
- 每折前后、第 10 折止损前、写最终产物前后、最终 verify 后检查；超限原子写入 `FAILED_RESOURCE_BUDGET`，不得 `COMPLETE`。
- `FAILED_RESOURCE_BUDGET` 与 `FAILED_EXCEPTION` 也必须满足 phase2 最小顶层 schema：`model`、`n_folds`、`fold_auc`、`oof_auc`、`base`、`base_oof_auc`、`oof_delta_vs_base`、`params`、`elapsed_seconds`；失败后不可采信的指标固定为 `null`。
- 两类失败同时列出 `expected_artifacts`、`present_artifacts`、`missing_artifacts`，并固定 `present_artifacts_are_invalid_for_use=true`。即使 OOF/test/submission 已写出，也一律视为失败残留，候选扫描不得纳入；`verify` 可独立复算资源记录、代码/输入哈希、产物清单和权限边界。
- 普通中断保留已验证 checkpoint；再次显式 `--mode train` 可从下一折恢复。

## 运行方式

```bash
python model/v86_catboost_dual_strict_te_40f/v86_catboost_dual_strict_te_40f.py
python model/v86_catboost_dual_strict_te_40f/v86_catboost_dual_strict_te_40f.py --mode smoke

# 本次禁止；以后满足授权时才允许：
python model/v86_catboost_dual_strict_te_40f/v86_catboost_dual_strict_te_40f.py --mode train
python model/v86_catboost_dual_strict_te_40f/v86_catboost_dual_strict_te_40f.py --mode verify
```

## 当前结论

- 正式训练已完成 40/40 折，`cv_results.json` 状态为 `COMPLETE`；显式 `--mode verify` 与独立 post-run 审计均通过。
- OOF AUC `0.9459373682196069`；相对 v77 `+0.000238965940`，说明 strict TE 改善 CatBoost 家族本身，但仍相对 strict v80 `−0.000303242757`、共同样本桶仅胜 `3/40`。
- OOF Spearman vs v77/v80 为 `0.995607523 / 0.995076912`，没有低于 `0.995` 的冻结多样性信号。
- 最终裁决 `REJECT`；`allowed_for_fusion=false`、`eligible_for_separate_preregistration=false`、`allowed_for_submission=false`。
- 40 checkpoint 重建 OOF/test 逐元素一致；最终资源约 `4179.0s / 7.355 GiB`。本实验已按完成顺序计为 C01 第8个正式关闭项。
