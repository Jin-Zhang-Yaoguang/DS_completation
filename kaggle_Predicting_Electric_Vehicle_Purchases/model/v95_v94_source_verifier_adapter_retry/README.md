# v95：v94 source verifier adapter 非计数重试

## 预注册结论

- 实验 ID：`v95_v94_source_verifier_adapter_retry`
- 状态：`COMPLETE`；显式 verify 与独立 post-run 审计均 `PASS`
- 研究周期：`C01`，沿用 v94 的位置 `12`
- 类型：`SMALL_BLEND`（implementation retry）
- `retry_of=v94_strict_v80_v85_v87_cv_blend`
- `counts_toward_cycle_when_formally_closed=false`
- 提交预算：`0`
- 时间 / 内存 / CPU：`900s / 12 GiB process peak RSS / 1 thread`
- preflight revision：`R1_V87_EXACT_SUMMARY_CONTRACT`
- runner SHA-256：`26165cf1031bffb9c4b3ffd7002374b79aa2bbad557106453e5bbe1d3487fb93`
- frozen config SHA-256：`fcd3379f13a4f79c4b1e5be5a9ab6e32661ec6661238894a0d05ce16ab473496`
- tests SHA-256：`763aa7e7e0b416cd1e244b8457d1aa6cd8308185d69d1f35c16f9109f8913add`

本目录完成同模型的来源 verifier 入口适配、正式非计数重试、显式 verify 与独立 post-run 审计。v94 保持冻结未修改。

## 失败边界与重试资格

v94 已正式关闭为 `FAILED_EXCEPTION`：它把所有来源都硬性要求为 `verify_complete_payload`，而历史 v80 只提供 `verify_complete`。失败发生在任何成员预测加载前，因此可以使用相同模型合同进行一次纯实现适配重试，但不得再计入 C01。

冻结失败证据：

- path：`model/v94_strict_v80_v85_v87_cv_blend/cv_results.json`
- SHA-256：`76e97ae375c065cdf8dd186e4da4e0bae3ad972df2cbca58ec2e7ea8ef055ad8`
- error：`来源缺少 verify_complete_payload：v80_strict_v61_outer104395303_40f`

v95 的唯一功能改动是来源 verifier 适配；不修改任何建模或选择逻辑。

## 冻结的 verifier 适配

| 来源 | 唯一允许入口 | 返回合同 |
| --- | --- | --- |
| v80 | `verify_complete()` | 必须返回 `None`，然后重读 `cv_results.json` |
| v85 | `verify_complete()` | 必须返回 `None`，然后重读 `cv_results.json` |
| v87 | `verify_complete()` | 核验完整重建 summary，然后重读 `cv_results.json` |
| v90 | `verify_complete_payload()` | 返回值必须与重读 `cv_results.json` 完全一致 |

调度只由冻结的 experiment ID 决定，禁止探测其他候选方法或在入口失败后降级。v80/v85 的 `None` 是历史接口合同，不是跳过验证：返回后必须重读结果并独立核验：

- `status`、`experiment_id`、`decision`、`model`、`n_folds` 和 OOF AUC；
- `allowed_for_fusion`、`eligible_for_separate_preregistration` 及 `allowed_for_submission`；
- runner、config、cv_results、sources、OOF 和 test 的冻结 SHA；
- cv_results 内嵌的 runner/config/sources/artifact hash。

### R1：v87 summary 精确合同

独立审计发现 R0 对 v87 只检查 summary 的 status 和 experiment ID，会放过缺少完整重建证据的返回值。R1 改为十字段精确 schema，缺失或额外字段一律拒绝：

- `status=COMPLETE_REBUILT_FROM_40_CHECKPOINTS_AND_VERIFIED`；
- `experiment_id=v87_strict_v80_commute_charging_burden_40f`；
- `fold_auc_recomputed=40`；
- `oof_elementwise_equal=true`、`test_elementwise_equal=true`、`strict_prior_self_check=true`；
- `oof_auc` 必须与重读 v87 cv_results 精确一致；
- `resource_checks_verified` 必须等于 cv_results 资源记录数；
- `wall_clock_elapsed_seconds` 和 `peak_rss_gib` 必须同时等于 cv_results 顶层摘要与 `final_resource_check`。

对三个真值字段使用 `is True` 检查，折数严格拒绝 bool 伪装，所有数值要求有限且与重读证据精确相等。攻击测试逐一篡改十个字段，并覆盖每个缺失字段、额外字段、任一 false、bool-as-count 与 cv 资源摘要漂移。

## 预测加载前的强制顺序

1. 先用流式 hash 核验四个来源的 runner/config/results/sources/OOF/test，并检查冻结 row identity 和结果元数据。
2. 按 `v80 → v85 → v87 → v90` 执行四个完整原生 verifier；任一失败都立即 fail closed。
3. 四个 verifier 全部返回后，再次核验全部来源 hash、row IDs 和结果元数据，并要求 verifier 前后一致。
4. 只有上述检查全部通过，才允许 v95 自身首次 `np.load` 融合输入（原生 verifier 内部的重建读取属于必须验证）。

audit 和 smoke 不调用原生 verifier，也不解析真实预测：audit 只做流式 hash/JSON/schema；smoke 用合成数组验证融合逻辑和四种返回合同。

## 完全不变的模型协议

- 成员仍为 v80、v85、v87；v90 只是 comparison-only strict baseline。
- `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`。
- 每个 meta-train 内分别拟合 fit-only mid-ECDF，再应用到 train/holdout/test。
- 三成员非负 simplex 步长 `0.05`，共 `231` 个固定权重；目标、tie-break、test 五折平均均与 v94 相同。
- 唯一基准为 v90 `0.9463720745765888`；晋级仍需 OOF 至少 `+0.0001` 且五个 meta holdout `5/5` 提升。
- 等权仍只是诊断；提交预算仍为零。
- 完整继承 v94 R6 的 staged COMPLETE、四次文件 verifier、post-seal resource guard、flock、失败关闭和 sealed archive provenance 合同。

## 预运行攻击测试

- v80/v85 返回非 `None`、只提供错误入口；
- v87 summary 伪造 experiment ID/status；
- v90 返回 payload 与重读结果不一致；
- 重读结果中的 status/experiment/model/fold/AUC/权限/预测 hash 漂移；
- 四个 verifier 未全部完成就进入二次 hash 或预测加载。

## 运行方式

```bash
python model/v95_v94_source_verifier_adapter_retry/v95_v94_source_verifier_adapter_retry.py --mode audit
python model/v95_v94_source_verifier_adapter_retry/v95_v94_source_verifier_adapter_retry.py --mode smoke

# 正式运行已经完成，不得重复执行或计数：
python model/v95_v94_source_verifier_adapter_retry/v95_v94_source_verifier_adapter_retry.py --mode run
python model/v95_v94_source_verifier_adapter_retry/v95_v94_source_verifier_adapter_retry.py --mode verify
```

## 当前边界

这是 v94 的非计数实现重试，不是新的研究假设。正式 OOF 为 `0.9463838901455106`，相对 v90 `+0.000011815568922`，五个 meta holdout 全部提升；但低于冻结的 `+0.0001` 门槛，最终决策为 `REJECT`。独立审计从三个原子成员重建 231 点 simplex、五折权重、OOF/test，均与落盘结果逐元素一致。完整运行耗时 `684.817` 秒、peak RSS `8.282 GiB`，资源合同通过；不得融合、提交或增加 C01 计数，C01 保持 `12/20`。
