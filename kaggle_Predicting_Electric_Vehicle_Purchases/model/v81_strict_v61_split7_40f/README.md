# v81_strict_v61_split7_40f

## 状态

- 预注册日期：2026-09-04
- 状态：`DESIGN_READY_NOT_STARTED`
- 正式触发前提：`v80_strict_v61_outer104395303_40f` 完成40折、状态为 `COMPLETE`，且通过冻结 v80 R2 的 `verify_complete()` 全量重建验收。
- 当前触发状态：`WAITING_FOR_V80_COMPLETE`。audit/smoke 只验证设计，不读取 v80 的部分分数作为效果证据。
- 本次任务禁止训练；当前不计入周期。

## 预注册

- 实验 ID：`v81_strict_v61_split7_40f`
- 研究周期：`C01`
- 普通版本序号：第2个候选
- 实验类型：`SINGLE_MODEL / SPLIT_SEED_ROBUSTNESS_REPLICATION`
- 基准：`v80_strict_v61_outer104395303_40f`。`v61-family` 仅表示特征和模型血缘，v61 不作为本实验的严格基准。
- 唯一机制假设：只改变外层切分种子时，严格 v61-family 的完整 OOF 强度应保持稳定，同时产生一个划分独立但高度一致的测试预测，可供后续单独预注册的测试侧 bagging 验证。
- 唯一主要变量：`OUTER_SEED: 104395303 -> 7`。
- 不变项：严格 inner prior、`INNER_TE_SEED_BASE=104395303`、inner seed 公式、四个 LightGBM seed、全部特征、TE keys、smooths、模型参数、40 outer folds、5 inner folds、LightGBM 4.6.0、线程、墙钟/内存预算、checkpoint、verify、flock 和产物 schema 均继承冻结 v80 R2。
- 外层切分：40折 `StratifiedKFold(shuffle=True, random_state=7)`。
- 内层切分：one-based outer fold 的 inner seed 固定为 `104395303 + fold`，不随 outer seed 改变。
- 泄漏边界：inner hold 的 prior、count、target sum 仅来自 inner-train；outer-valid/test 仅使用完整 outer-fit 标签统计；train+test 联合信息只限无标签统计与编码。
- 主要指标：完整严格 OOF ROC AUC。
- 比较边界：v80 与 v81 外层训练/验证划分不同，只比较完整 OOF AUC、完整 OOF Spearman 和 test Spearman；禁止逐折配对或报告“提升折数”。
- 预期：不假设 seed7 会提高 OOF。预期 `abs(OOF_v81 - OOF_v80) <= 0.0001` 且 test Spearman `>= 0.998`。
- 完整验收：40 checkpoint 重建、严格 prior、来源/配置/行序/概率/资源验证全部通过；OOF `>= 0.9458`；相对 v80 的 OOF 绝对差 `<= 0.0001`；test Spearman `>= 0.998`。
- 决策：同时满足上述三项才记为 `ROBUSTNESS_REPLICATION_PASSED`，否则 `STOP`。无论结果如何都不自动允许融合或提交；bagging 必须另行预注册验证。
- 计算预算：与 v80 R2 相同；LightGBM `n_jobs=8`，单次正式进程自取得 `flock` 后的墙钟在每折前后（含第40折）及 COMPLETE 前检查，达到3600秒即 FAILED；进程 peak RSS 不超过16 GiB。
- 提交预算：`0`。
- 停止条件：v80 未完整验收；v80 runner/config 哈希改变；任何 prior、配置、来源、checkpoint、重建、行序、概率、墙钟或 peak RSS 验证失败。
- 计数：只有正式运行后以完整 `COMPLETE` 或保留完整证据的 `FAILED` 关闭，才作为 C01 第2个普通版本计数；audit、smoke 和等待状态不计数。

## 冻结继承合同

- v80 runner SHA-256：`808e4fe41ef033da6b6df14edcce3e9f67ced418f9958fddbd0788045af8204a`
- v80 config SHA-256：`79fc1e5451fb823cbde5a59e32b078e8e85cc0ebcef4c500694affab9195e5ab`
- v81 runner SHA-256：`4cde19eb46922cf6547e8e887e13bbe8c543a8eac7e9fb2a54c1c65cffbdff54`
- v81 config SHA-256：`0abe1e88cd915b6aa38ab0c6a26b44e3c111ab756a247cce1306b5f77442b8ee`
- formal run contract 会纳入已验收 v80 的 `cv_results.json`、`oof_proba.npy`、`test_proba.npy`、`sources.json` 及其 SHA-256；v80 未 COMPLETE 时不生成 formal contract。

## 实现检查

- [x] 目录独立，不修改 v80 或其他历史实验
- [x] formal train/verify 硬性调用冻结 v80 verifier，未 COMPLETE 或验收失败即拒绝
- [x] audit/smoke 可在等待 v80 时验证静态继承合同，但不产生效果证据
- [x] outer seed 独立为7；inner seed base和四个模型 seed仍为104395303
- [x] 严格 nested TE、特征、参数和 LightGBM 版本逐项对照 v80
- [x] checkpoint 含配置、代码/输入合同及 validation index 哈希
- [x] 使用内核 `flock`；取得锁后重新检查 COMPLETE
- [x] 每5折输出明确标记的中间诊断，不做跨 seed 逐折配对
- [x] 每折前后、全部折后及 COMPLETE 前检查墙钟和 peak RSS
- [x] 资源超限原子写 FAILED；第40折后超限保留 checkpoint，不写 COMPLETE
- [x] verify 从40个 checkpoint 重建 OOF/test，复算指标、Spearman、资源证据和全部 gate
- [x] 默认 audit；smoke 不拟合模型、不计算效果指标、不写正式产物

## 运行方式

```bash
python model/v81_strict_v61_split7_40f/v81_strict_v61_split7_40f.py --mode audit
python model/v81_strict_v61_split7_40f/v81_strict_v61_split7_40f.py --mode smoke

# 只有 v80 完整验收后才允许；本次任务禁止执行：
python model/v81_strict_v61_split7_40f/v81_strict_v61_split7_40f.py --mode train

# 仅在 v81 正式40折完成后使用：
python model/v81_strict_v61_split7_40f/v81_strict_v61_split7_40f.py --mode verify
```

正式运行使用 LightGBM 4.6.0。当前 shell 的 `python` 为 `/opt/anaconda3/bin/python`；共享父目录 `.venv/bin/python` 没有 LightGBM。

## 结果与决策

- v80 严格基准 OOF：等待 v80 COMPLETE 后读取并验证
- v81 OOF / delta / OOF Spearman / test Spearman：—
- 资源与产物 SHA：—
- 当前决策：等待 v80 完整验收，不训练、不计数、不融合、不提交
