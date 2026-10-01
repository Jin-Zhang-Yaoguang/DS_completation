# v83_strict_three_split_equal_bag

## 状态

- 预注册日期：2026-09-04
- 状态：`DESIGN_READY_NOT_STARTED`
- 默认入口：`--mode audit`，只验证冻结设计与代码/config 哈希，不读取成员真实预测。
- 正式入口：仅显式 `--mode run`；本次实现任务禁止运行。
- 当前不生成 `candidate_snapshot.json`、`sources.json`、`lineage.json`、真实 OOF/test、`submission.csv` 或 `cv_results.json`，也不更新台账与周期计数。

## Preflight R1

- 预运行修订：`R1`，已冻结于 `preflight_r1.json`。
- runner SHA-256：`f07c625e62ef8998b15adaadce0719bbba7f5a334bc543742fdfca3d99208b0f`。
- config SHA-256：`cc033b6a5e124e806317d25939ff1b00319a6031449ce3182e093eb6cad493c9`。
- verifier 额外逐项核对顶层 `oof_auc`、`base`、`base_oof_auc`、`oof_delta_vs_base`，以及全部 `artifact_validation` 字段。
- verifier 核对资源字段、冻结预算及 `sources` 的 schema/experiment ID。
- formal 资源检查覆盖成员/数据加载、预测加载与评估、全部非结果产物写入、最终重建验证、COMPLETE 暂存和原子提交后检查。
- `cv_results.json` 只在最终重建验证通过后原子提交为 `COMPLETE`；任一异常或超过 900 秒/4 GiB 时原子改写为 `FAILED`。
- 本轮只运行静态 audit、合成 smoke 和单元测试；没有执行 formal run，也没有读取真实成员预测。

## 预注册

- 实验 ID：`v83_strict_three_split_equal_bag`
- 研究周期：`C01`
- 周期内序号：第 4 个常规版本
- 实验类型：`SMALL_BLEND`
- 是否计入本周期 20 个普通版本：只有正式 `run` 后以 `COMPLETE` 关闭才计数；audit、smoke、测试和等待状态不计数。
- 假设：三个只改变 outer split seed 的 strict v61-family 原子 sibling，在原始概率空间固定等权平均，可以降低测试侧切分方差并改善完整 OOF 排序。
- canonical 基准：`v80_strict_v61_outer104395303_40f`。
- 唯一主要变量：将 v80、v81、v82 三个原子预测在原始概率空间固定按 `1/3` 算术平均。
- 固定成员：`v80_strict_v61_outer104395303_40f`、`v81_strict_v61_split7_40f`、`v82_strict_v61_split2026_40f`，顺序和权重均冻结。
- 禁止成员：历史 v61、v64、v72 及任何父集成；它们只能作为历史文字背景，不得加载预测或参与指标。
- 固定方法：OOF 与 test 均使用 `(p80 + p81 + p82) / 3`；不选成员、不拟合权重、不做 rank/ECDF、不校准或变换预测。
- 正式触发：三成员均为 `COMPLETE` 且各自冻结 `verify_complete()` 通过；v81、v82 还必须满足 `split_seed_robustness_gate.passes=true` 且决策为 `ROBUSTNESS_REPLICATION_PASSED`。
- 泄漏边界：融合算子完全冻结且不使用标签；seed42 五个 meta bucket 只用于事后验收，不选择成员、变换或权重。
- 主要指标：完整 OOF ROC AUC。
- 逐桶判定：固定 `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`，比较每个留出桶上的 v83 与 canonical v80 AUC；五桶 delta 必须全部严格大于 0。
- 晋级门槛：完整 OOF 相对 canonical v80 至少 `+0.0001`，且五个预注册 meta bucket 全部为正；否则无条件 `REJECT`。
- 附加报告：相对最佳输入成员的 OOF delta；三成员和融合的 OOF/test Spearman；Brier、log loss、均值偏差和固定 20 概率区间 ECE。附加指标不改变晋级裁决。
- 计算预算：无模型训练；单进程、1 CPU，正式 run 最多 900 秒、peak RSS 4 GiB。
- 提交预算：`0`；即使 `PROMOTE` 也只允许进入下一层严格研究，不自动允许提交。
- 停止条件：成员未 COMPLETE、任一冻结 verifier/哈希/robustness gate 失败、成员或方法合同改变、行序/schema/概率范围异常、输出无法由三个原子预测逐元素重建，或超过预算。

## 不可变产物合同

正式 `run` 首先逐一执行三个冻结 verifier，从各自 40 个 checkpoint 重建并验证原子 OOF/test。触发通过后，runner 才会在本目录创建：

- `preflight_r1.json`：预运行 R1 记录与 runner/config SHA-256；audit 和 formal 都要求完全匹配。
- `candidate_snapshot.json`：仅含三个冻结 sibling、原子输出路径与 SHA-256、verifier/gate 证明；若已存在但内容不同则拒绝。
- `lineage.json`：三条原子 prediction edge 指向 v83，明确没有父集成和历史 v61/v64/v72 预测边。
- `sources.json`：v83 代码/config、规范数据、成员 cv/source/oof/test 与正式输出的路径和 SHA-256；创建后不可覆盖。
- `oof_proba.npy`、`test_proba.npy`、`submission.csv`：三成员原始概率固定等权平均。
- `cv_results.json`：完整 OOF、固定五桶、最佳输入比较、相关性、校准、门槛与决策。
- `train_log.txt`：只记录正式触发、成员 verifier 通过和最终裁决。

`--mode verify` 会再次执行三个冻结 verifier，并从成员输出重建 v83 OOF/test，逐元素核对所有结果与哈希。

## 实现检查

- [x] 新目录独立，未修改 v80/v81/v82、台账或历史产物
- [x] 成员 allowlist 精确等于 `[v80, v81, v82]`，禁止父集成和历史 v61/v64/v72
- [x] OOF/test 使用同一原始概率固定 `1/3` 算术平均
- [x] 无成员选择、权重拟合、rank/ECDF 或预测校准
- [x] formal run 硬调用三个冻结 verifier，并检查 v81/v82 robustness gate
- [x] 候选快照、lineage 和 sources 使用不可变写入与 SHA-256
- [x] 加载原子输出后验证 schema、行数、有限值、概率范围和规范行序证明
- [x] seed42 五桶仅用于固定验收，不参与方法选择
- [x] verify 从原子成员重建融合输出并复算 AUC、相关性、校准和门槛
- [x] verify 逐项核对顶层指标、完整 artifact_validation、资源字段与 sources header
- [x] COMPLETE 最后原子提交；资源超限或异常原子记录 FAILED
- [x] Preflight R1 冻结 runner/config SHA-256
- [x] 默认 audit；smoke 仅使用合成数组，不读取真实预测或产生效果证据

## 运行方式

```bash
python model/v83_strict_three_split_equal_bag/v83_strict_three_split_equal_bag.py
python model/v83_strict_three_split_equal_bag/v83_strict_three_split_equal_bag.py --mode audit
python model/v83_strict_three_split_equal_bag/v83_strict_three_split_equal_bag.py --mode smoke

# 只有三成员正式触发全部满足后才允许；本次实现任务禁止执行：
python model/v83_strict_three_split_equal_bag/v83_strict_three_split_equal_bag.py --mode run

# 仅在 v83 已正式 COMPLETE 后使用：
python model/v83_strict_three_split_equal_bag/v83_strict_three_split_equal_bag.py --mode verify
```

## 结果与决策

- v80/v81/v82 正式触发：等待 formal run 时逐一验证
- v83 OOF、vs v80、vs 最佳输入、五桶结果：—
- OOF/test 相关性与校准：—
- 资源与产物 SHA-256：—
- 当前决策：仅完成设计和代码验证；不运行、不计数、不融合、不提交
