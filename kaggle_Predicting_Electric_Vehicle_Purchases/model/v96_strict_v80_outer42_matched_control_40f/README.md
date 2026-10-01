# v96_strict_v80_outer42_matched_control_40f

## 状态

- 预注册日期：2026-09-04
- 状态：`COMPLETE / ELIGIBLE_FOR_SEPARATE_PREREGISTRATION_ONLY`
- 研究周期：`C01` 第 13 个正式普通版本，已在独立终审通过后计数。
- 正式训练与显式 verify 已完成；没有 Kaggle 提交，提交预算仍为 0。
- preflight revision：`R3_ALL_SOURCE_PREFLIGHT_BEFORE_ANY_CANDIDATE_LOAD`
- runner SHA-256：`5e7d3f17c1f3ded4f802b65ea25d01288d1d3d1338cb757e85521573560d1ade`
- frozen config SHA-256：`660d34e3a0f787547380a5f9d2ec670e8497a47606d3a7de8a6123b1f167a8b7`
- tests SHA-256：`ad461abdb2ed8c9939c0fd5f6147d8dfaecab7bc5ef798c810854d5cabd50a4c`

R1 只加固证据与关闭边界，科学协议、模型配方和门槛均未改变：

- `prediction_artifact_access` 精确冻结 strict-v80 OOF/test 与 v90/v92/v93 comparison OOF/test；audit/smoke 只能做 hash-only 字节检查。
- v80 显式冻结 runner/config/cv_results/sources/OOF/test 六个 SHA 和唯一 verifier 入口 `verify_complete`；所有四个来源都必须在原生完整 verifier 前后核哈希并重读 metadata，之后本 runner 才可首次解析预测。
- FAILED verifier 强制 phase/fold 是完整冻结序列的合法前缀、elapsed/RSS 单调、breach 可由预算重算；每个在场失败产物都冻结 SHA/size，独立 verify 实时复算。
- 最终 COMPLETE pending 在追加 staged 后资源记录并重写后，必须以 COMPLETE 模式再次完整验证；verifier 前后 SHA/size 不变、最终资源 guard 通过后，才可经唯一入口原子提交。

R2 修复独立审计复现的 final-guard TOCTOU：完整 verifier 前后会封印常规文件的 device/inode/mode/size/mtime/SHA 与完整字节；资源 guard 返回后必须再次逐项等同，才允许提交。提交后立即对最终路径复核同一封印；guard 期间、提交期间或提交后的任何差异都会删除未可信 COMPLETE，并以统一 `FAILED_EXCEPTION` 原子关闭，不留下伪 COMPLETE。

R3 修复四来源验收顺序：train 与 verify 统一通过一个编排入口，先对 v80/v90/v92/v93 全部执行首轮冻结哈希，再依次执行固定原生 verifier，并在每次返回后复核四者哈希、metadata、行身份和来源产物。四者全部验收且最终再核哈希后，本 runner 才允许第一次 `np.load`。真实 `_train_impl` 顺序攻击逐一篡改四个来源，均在解析 0 个预测数组时拒绝。

## 历史去重

结果为 `GO_NO_EQUIVALENT_PURE_STRICT_V80_SEED42`。

- v80、v81、v82 是纯 strict-v80 配方，但 outer seed 分别为 `104395303`、`7`、`2026`。
- 已有 seed42 版本均不等价：v85 是 Naji/`sklearn.TargetEncoder`；v86 是 CatBoost；v87、v92 增加静态特征；v93 改变收入 exact TE 的回退语义。
- 因此历史中没有“62 static + 51 strict nested TE + v80 LightGBM 参数 + outer seed42”的完整产物。
- audit 会实时重读上述冻结配置并 fail closed；不得把 v87/v92/v93 当成无特征 matched control。

## 预注册

- 实验 ID：`v96_strict_v80_outer42_matched_control_40f`
- 类型：`SINGLE_MODEL / MATCHED_CONTROL / SPLIT_SEED_ROBUSTNESS_REPLICATION`
- 科学目的：补齐统一 seed42 协议下的无新增特征严格基线，使 v92/v93 能在完全相同 outer-valid 行上做逐折比较，并为后续另行预注册的小融合提供可审计原子预测。
- 基准：`v80_strict_v61_outer104395303_40f`，冻结严格 OOF `0.946240610976364`。
- 唯一主要变量：`outer_split_seed: 104395303 -> 42`。
- 不变项：62 个 static、17 个 TE key × 3 smooth = 51 个 strict nested TE、列序、inner folds、`INNER_TE_SEED_BASE=104395303`、one-based inner seed 公式、四个 LightGBM seed、全部 LightGBM 参数、early stopping、LightGBM 4.6.0、40 folds、checkpoint、staged verify、flock、60 分钟、16 GiB、8 threads、提交预算 0。
- 泄漏边界：inner-hold 的 prior/count/target sum 仅来自 inner-train；outer-valid/test 只应用完整 outer-fit 的统计。测试集仅参与 v80 原配方的无标签编码。
- 特征守卫：零列适配器必须证明返回的 train/test static frame 与 v80 builder 在列名、列序、shape 和数值上逐元素相同；总宽度固定 `62 + 51 = 113`。
- 外层切分：`StratifiedKFold(n_splits=40, shuffle=True, random_state=42)`。
- futility：禁用。matched control 必须跑满 40 折才能成为可复用的配对基线；保留的旧 10 折边界仅用于失败 schema 回归测试，不参与正式决策。
- 可观测性：每 5 折输出一条 `INTERIM_DIAGNOSTIC_NOT_FINAL`，不得作为正式结论。

## 冻结比较与门槛

正式 train/verify 必须先对 v80、v90、v92、v93 的 runner/config/cv/sources/OOF/test 做第一遍冻结 SHA 核验，再执行各自固定入口的完整 verifier；verifier 返回后重读 metadata 并做第二遍 SHA、行身份、来源产物和 OOF AUC 核验，全部通过后本 runner 才首次调用 `np.load`。任一来源漂移必须在本 runner 解析 0 个预测数组时关闭。audit/smoke 只流式计算文件 SHA，不调用这些 verifier、不用 `np.load` 解析真实预测。

- 相对 v80：报告完整 OOF delta、OOF/test Spearman，以及把 v96 固定 seed42 的 40 个 validation 行桶同时应用于 v96/v80 后的 `40` 个桶差和胜桶数。这不是跨 seed 的同编号模型折配对。
- 相对 v92/v93：三者 outer seed 与行切分相同，报告每个相同 validation row fold 的 AUC 差、完整 OOF delta、胜折数和 OOF/test Spearman。
- 相对 v90：只报告完整 OOF 差与 OOF/test Spearman；v90 是 5 折元融合，禁止伪称 40 折逐折配对。
- strict-family 门槛：OOF `>=0.9458`。
- matched-control 稳健门槛：相对 v80 的绝对 OOF delta `<=0.0001` 且 test Spearman `>=0.998`。
- 项目单模晋级门槛保持不变：相对 v80 整体 OOF 至少 `+0.0001`，且固定 seed42 行桶至少 `24/40` 胜出。
- 未过项目门槛不得直接融合或提交；若达到独立多样性屏幕，只能标记为“可另立小融合预注册”，不能在本实验调权。

## 工程与停止条件

- 每折原子 checkpoint，配置/代码/输入合同 hash 不一致时拒绝恢复。
- 取得 `flock` 后再次检查终态；已有非 COMPLETE 结果必须人工审计，禁止覆盖。
- 每折前后、全部折后、staged verify 前后和最终提交前检查墙钟和 peak RSS；达到 3600 秒或超过 16 GiB 即原子关闭为 FAILED，不写 COMPLETE。
- 完整结果先写 staged 文件，从 40 个 checkpoint 逐元素重建 OOF/test、复算折 AUC/均值/标准差/best iterations、全部比较和权限；追加 staged 后资源记录、重写为 COMPLETE pending 后，再对该实际文件执行一次相同强度的完整 verifier。验证前后常规文件身份与完整字节封印必须不变；最后一次不回写 payload 的资源 guard 返回后再次核对同一封印，才允许一次原子提交。提交后若最终路径未保持完全相同封印，立即删除伪 COMPLETE 并写 FAILED_EXCEPTION。
- 所有 FAILED 产物明确标记无效；独立 verifier 要实时复核每个在场产物的 SHA/size，以及完整资源 phase/fold 前缀、单调性和 breach。普通异常必须在同一 flock 持有区内写 `FAILED_EXCEPTION`。
- 任何 strict prior、特征同一性、版本、来源 hash、行身份、checkpoint、概率、比较指标、资源或 schema 核验失败立即停止。

## 运行方式

```bash
python model/v96_strict_v80_outer42_matched_control_40f/v96_strict_v80_outer42_matched_control_40f.py --mode audit
python model/v96_strict_v80_outer42_matched_control_40f/v96_strict_v80_outer42_matched_control_40f.py --mode smoke

# 已执行并完成：
python model/v96_strict_v80_outer42_matched_control_40f/v96_strict_v80_outer42_matched_control_40f.py --mode train

# 已执行并通过：
python model/v96_strict_v80_outer42_matched_control_40f/v96_strict_v80_outer42_matched_control_40f.py --mode verify
```

## 当前结论

- 严格 OOF AUC：`0.9462430073165773`。
- 相对 v80：`+0.0000023963402133`，固定 seed42 行桶 `22/40`；未通过项目单模门槛 `+0.0001` 且 `24/40`。
- 相对 v92：`-0.0000049688515653`、同行折 `19/40`；相对 v93：`+0.0000019601638114`、同行折 `22/40`；相对 v90：`-0.0001290672600115`。
- test Spearman vs v80：`0.9999753988662251`；matched-control 与多样性屏幕通过。
- 40 个 checkpoint、seed42 validation 索引、668,665 行一次覆盖、OOF/test 逐元素重建、严格 TE AST、来源哈希、83 项资源记录与显式 verify 均经独立终审通过。
- 资源：`1640.65057025s`，peak RSS `9.2993927002 GiB`，未越过 `3600s / 16 GiB`。
- 决策：计入 C01 第 13 项；不得直接融合或提交，只能在新的、独立预注册小融合中作为原子候选。
