# P2-02 v77 训练后独立验收

## 预注册

- 实验 ID：`P2-02-v77-postrun-audit`
- 研究周期：`PRE-C01`
- 实验类型：`ROBUSTNESS / AUDIT_ONLY`
- 是否计入本周期 20 个普通版本：`false`
- 周期内序号：`N/A`
- 状态：`IMPLEMENTED_WAITING_FOR_V77`
- 日期：2026-09-03
- 审计代码 SHA-256：`f00497de6406a780e4f95864d346de8d548f6cd70ab76228190ed810859e04b6`
- 假设：v77 的 CatBoost 单模 OOF/test 产物可由 40 个 checkpoint 完整重建；将融合 rank 变换改为只在元训练块拟合的 mid-ECDF 后，才能无偏判断其对 v61 的边际贡献。
- 机制依据：v77 内置 `crossfit_blend` 在切分元验证折前对全量 OOF 排名，违反 `AGENTS.md` 的元训练折边界；单模训练路径不使用该融合结果。
- 基准版本与 OOF：`v61_income_bin10_te_lgbm_40f_depth4_seed104395303`，reported OOF `0.9462435667072661`，验收时必须从原始标签和 OOF 重新计算。
- 唯一主要变量：把 v77 内置的全量 percentile-rank 验收替换为 5 折、fit-only mid-ECDF 交叉拟合验收。
- 保持不变的设置：v77 的 40 折 seed42、CatBoost 配方、模型种子 `[42, 2026]`、v61 基准、权重网格 `0.00..1.00 step 0.01`。
- 外层/内层切分：候选训练外层为 `StratifiedKFold(40, shuffle=True, random_state=42)`；融合元验证为 `StratifiedKFold(5, shuffle=True, random_state=42)`。
- 泄漏边界：每个元折分别以该折 fit 块的成员预测拟合 ECDF 和权重，再应用到 valid 块；valid 的预测分布和标签均不得参与 ECDF、权重或并列选择。
- 主要指标：v77 raw OOF ROC AUC，以及 v77+v61 的 fit-only ECDF 交叉拟合 OOF ROC AUC。
- 逐折判定方式：融合的 5 个元验证折必须全部严格优于同一 fit-only ECDF 变换下的 v61。
- 晋级门槛：v77 raw OOF `>= 0.9458`；融合相对 `base_meta_oof_auc >= +0.0001` 且 5/5 元验证折提升。二者同时满足，且所有产物复算一致，才能进入候选池。
- 计算预算：单次最多 10 分钟 CPU、4 GB 额外内存；不训练模型、不使用 GPU。
- 提交预算：0。
- 停止条件：冻结输入哈希漂移、checkpoint 索引/shape/数值异常、最终产物不能由 checkpoint 重建、复算结果不一致，或预注册门槛未通过。

## 冻结输入

脚本读取以下输入，不写入 v77、v61、v10 或 `data/`：

1. `data/train.csv`、`data/test.csv`、`data/sample_submission.csv`；
2. v77 主脚本、训练日志、40 个 checkpoint，以及训练完成后生成的 OOF/test/submission/result/importance；
3. v10 配方脚本和结果；
4. v61 脚本、OOF/test/submission/result。

训练连续运行期间已冻结关键输入 SHA-256，完整值写在 `audit_v77.py` 的 `EXPECTED_FROZEN_SHA256`。其中：

- v77 脚本：`9aa3924a3f73f36ace5dfa280dd1ce0a8028d2782eee9f4fe7674291045b778c`
- v10 配方脚本：`b9a9b30a51e39acc9cab543b3f911a2929d498e9fe44ad237f45e13d85f40b60`
- train：`eae9eaa4e6378df405e755f853771d7e26d212bd93258349fc797b771021946a`
- test：`539263f6caabc40afd5e2f0bc0ab16b10a2d1177c565fc71b866f0181d836b34`
- sample submission：`a9747a8b947e4e35505e3da4535a5a494978b012a7adb50973f13e598849dda5`
- v61 OOF：`0b027d782c53b0f6fbef6cef930a3beef14d94effe18ff4957ca714382e111aa`

任一冻结输入漂移都返回 `AUDIT_FAILED`，不会用新输入解释旧 checkpoint。

## fit-only mid-ECDF

对每个元折、每个成员单独执行：

```python
ordered = np.sort(pred_fit)
left = np.searchsorted(ordered, x, side="left")
right = np.searchsorted(ordered, x, side="right")
transformed = (left + right) / (2 * len(ordered))
```

`pred_fit` 只能来自当前元训练块。fit 与 valid 都应用这一份有序数组；不能对全量 OOF 或 valid 自己排名。权重在 fit 块上遍历固定网格，AUC 并列时取更小的 v77 权重，然后只在对应 valid 块评分。整体 `blend_oof` 由五个 valid 预测拼接；整体和逐折基准均使用同一 fit-only 变换后的 `base_meta_oof`。

## 必须复算的证据

1. checkpoint 必须恰好为 `fold_01.npz` 至 `fold_40.npz`；每个 `valid_idx` 与预注册 40 折索引精确一致，全部训练行恰好覆盖一次。
2. 每折必须包含 `valid_idx`、`valid_pred`、`test_pred`、`best_iterations`、`importance`；概率必须有限且在 `[0,1]`，两个迭代数均为正，importance 长度为 20。
3. 用 checkpoint 拼接 OOF，并按 40 折算术平均 test；两者与最终 `.npy` 的最大绝对差必须不超过 `1e-15`。
4. `submission.csv` 的列、shape、ID 顺序必须与 test/sample 一致，预测与 `test_proba.npy` 的差不超过 `1e-15`。
5. 重新计算 40 折 AUC、整体 OOF、均值、标准差、相对 v61 增量和预测统计，并与 `cv_results.json` 对照。
6. 重新验证 v61 OOF/test 的长度、有限值、范围、哈希和 OOF AUC。
7. 运行 fit-only mid-ECDF 5 折融合并执行冻结门槛；v77 原脚本里的 `blend_with_v61` 与 `accepted_for_p2_06` 永久忽略。
8. 报告 v77 与 v61 的 OOF/test Spearman；40 个 seed42 共同样本桶只作诊断，因为 v61 的训练外层种子是 `104395303`，不得称逐折配对。

## 输出 schema

脚本只在本目录生成或原子替换：

- `sources.json`
  - `schema_version`、`audit_id`、`generated_at_utc`；
  - `frozen_sha256`、`frozen_hash_mismatches`；
  - `files[] = {role, path, exists, size_bytes, mtime_ns, sha256}`；
  - Python、NumPy、pandas、SciPy、scikit-learn、CatBoost 版本。
- `meta_folds.json`
  - splitter 类、折数、shuffle、seed；
  - 每折 fit/valid 行数、正类数和 little-endian int64 索引 SHA-256。
- `audit_results.json`
  - `status`：`ARTIFACT_INCOMPLETE`、`PASS` 或 `AUDIT_FAILED`；
  - `decision`：等待同一训练实例、按门槛接纳/拒绝，或产物/协议错误拒绝；
  - checkpoint 审计、缺失产物、冻结哈希、协议偏离；
  - 完成时包含逐项复算、单模结果、40 桶诊断、融合每折权重与增量、相关性和最终门槛。
- `blend_oof_fit_ecdf.npy`
  - 仅在 40 折产物完整且复算成功后生成；长度 668,665，为五个元验证折拼接预测；无论门槛通过与否都保留。
- `audit_log.txt`
  - 当前审计运行的时间戳、checkpoint 数量、复算结果和最终状态。

训练未完成时脚本以退出码 0 返回 `ARTIFACT_INCOMPLETE`，便于安全轮询；验证错误返回 `AUDIT_FAILED` 和退出码 1。训练完成时：

```bash
python model/p2_02_v77_postrun_audit/audit_v77.py
```

## 已知协议偏离

- v77 checkpoint 没有内嵌配置哈希；本审计用训练仍连续运行时冻结的源码、数据和基准哈希补偿，但不宣称旧 checkpoint 机制本身合规。
- v77 内置融合先对全量 OOF 排名，不作为任何验收证据。
- v77 不生成 `sources.json`，由本伴随审计补齐，且不回写历史目录。
- checkpoint 没有保存两个种子的独立预测，不能事后逐元素拆分；只能核验脚本、日志、两个 best iteration 与折级平均预测。
- v77 最终 `.npy/.csv/.json` 不是原子写入，必须通过 checkpoint 重建后才视为完整。
