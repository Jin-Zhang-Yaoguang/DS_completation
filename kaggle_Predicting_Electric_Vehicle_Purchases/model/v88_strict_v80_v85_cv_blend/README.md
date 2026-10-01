# v88 strict v80 + v85 交叉拟合小融合

## 预注册

- 实验 ID：`v88_strict_v80_v85_cv_blend`
- 研究周期：`C01`
- 实验类型：`SMALL_BLEND`
- 周期内预留序号：`9`
- 正式关闭后计入周期：`true`
- 状态：`DESIGN_READY_NOT_STARTED`
- 日期：2026-09-04
- 候选代码 SHA-256：`2ac29faf8637c87d3bab6a0cc9617069c1ee12e1fb9ca12b5fcf08e3097f077b`
- 冻结配置 SHA-256：`2787bf3f69ab105e75745f00d609f5d247a9c69c416945a388eb7abddcc08908`
- 假设：v85 Naji 的预测多样性，在严格防止元层泄漏的前提下，能为 v80 核心带来相对最佳输入 v85 至少 `+0.0001` 的可复现 OOF AUC 增益。
- 唯一问题：v85 多样性是否给 v80 带来可复现边际增益。
- 最佳输入基准：`v85_naji_v74_40f`，冻结 OOF `0.9462702273556288`。
- 提交预算：`0`。
- 资源预算：900 秒、4 GiB peak RSS、单进程、1 CPU 线程协议。

本目录创建任务只允许预注册、audit、smoke 和测试；禁止 `--mode run`，没有读取真实预测数组或运行真实融合。

## 成员与血缘

仅允许两个冻结原子单模：

1. `v80_strict_v61_outer104395303_40f`：strict v61-family 核心，OOF `0.946240610976364`。
2. `v85_naji_v74_40f`：Naji 40 折单模，OOF `0.9462702273556288`。

两者都是独立训练的单模型预测节点；v61 和 v74 只是各自的配方/机制祖先，不作为本实验预测成员。禁止引入 v61、v64、v72、v74、v83，避免父子重复和已有集成套娃。正式运行与 verify 必须逐项检查成员 ID、runner/config/results/sources/OOF/test SHA、`COMPLETE` 状态、冻结 decision、成员自身 verifier 和 sources 输出哈希。

## 冻结元验证方法

- 固定 `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`。
- 每个 meta fold 内，对 v80 和 v85 分别只使用 meta-train 拟合 mid-ECDF。
- 同一 fold 的 meta-train、meta-holdout、test 都使用该 fold 的 fit-only ECDF 状态变换；禁止在全量 OOF 上拟合变换。
- v85 权重只允许从 `0, 0.05, ..., 1` 的非负网格选择，v80 权重恒为 `1-w_v85`。
- 只用 meta-train AUC 选权重；若并列，先选最接近 `0.5`，仍并列时选较低的 v85 权重。
- 所选权重应用到该 fold 的 holdout；5 个 holdout 拼接为主 OOF。
- test 预测为 5 个 fold-specific ECDF 与权重所得 test 预测的算术平均。
- 固定 `0.5/0.5` 等权结果只作诊断对照，绝不用于事后替换主方法或选择更有利结论。

## 晋级和停止条件

主指标为完整交叉拟合 OOF ROC AUC。只有同时满足以下条件才 `PROMOTE`：

- 相对最佳输入 v85 至少 `+0.0001`；
- 固定 5 个 meta holdout 全部严格优于 v85，即 `5/5`。

任一条件不满足即 `REJECT`。不得降低门槛、切换到等权对照、修改权重网格、删除不利折或提交。

所有 `cv_results.json` 终态都必须显式写入并由 verifier 复核 `failure_attribution`：`COMPLETE + PROMOTE` 为 `null`；`COMPLETE + REJECT` 固定归因为未通过预注册的 `+0.0001` 和/或 `5/5` 门槛；`FAILED_RESOURCE_BUDGET` 固定归因为资源预算超限；`FAILED_EXCEPTION` 固定归因为实现或运行异常。不得用事后解释替换这些冻结归因。

## 产物与验证

正式模式必须生成并验证：

- `candidate_snapshot.json`：成员、runner/config 与全部成员文件哈希；
- `lineage.json`：原子成员和无父子重复声明；
- `meta_folds.json`：固定五折索引哈希；
- `oof_proba.npy`、`test_proba.npy`、`submission.csv`；
- `sources.json`、`train_log.txt`、`cv_results.json`。

`COMPLETE` 必须先写全部非结果产物，再用独立重建 verifier 验证，最后 staged + atomic 提交 `cv_results.json`。结果包含统一 schema、每折搜索表与权重、主 OOF、相对 v85 增量、5 折胜数、等权对照、相关性、校准、来源 SHA、资源和验收决策。

资源超限或异常必须写 `FAILED_RESOURCE_BUDGET` / `FAILED_EXCEPTION`。失败结果列出 expected/present/missing artifacts，固定 `present_artifacts_are_invalid_for_use=true`；任何残留 OOF/test/submission 都不得进入候选扫描。两类失败以及 `COMPLETE` 下的 `PROMOTE`/`REJECT` 均由统一 schema 和独立 verifier 严格检查冻结归因。

## 运行方式

```bash
python model/v88_strict_v80_v85_cv_blend/v88_strict_v80_v85_cv_blend.py
python model/v88_strict_v80_v85_cv_blend/v88_strict_v80_v85_cv_blend.py --mode smoke

# 本次禁止；以后获得明确授权才允许：
python model/v88_strict_v80_v85_cv_blend/v88_strict_v80_v85_cv_blend.py --mode run
python model/v88_strict_v80_v85_cv_blend/v88_strict_v80_v85_cv_blend.py --mode verify
```

## 当前结论

只完成设计与代码验证，没有任何真实融合结果；不能据此判断 v85 是否带来增益，也不计入正式周期完成数。
