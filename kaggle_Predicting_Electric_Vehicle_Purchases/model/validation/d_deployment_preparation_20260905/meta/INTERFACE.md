# D 最终融合接口

状态为 **PREPARATION_ONLY_NOT_AUTHORIZED**。本目录没有真实运行 CLI；无参数运行 `final_meta.py` 只返回准备状态。未创建真实合同、授权、CT 模型或实际 test 预测。

## 纯计算与复算

`final_fit(y, v90_oof, ct_oof, v90_test, ct_test)` 返回最终权重、两个排序 ECDF 状态、融合 test 数组和训练拟合 AUC。输入形状为 `(n,)`/`(m,)`；V90 两组 float64，CT OOF 必须 float32，CT test 必须 float64，二分类训练标签为整数。

主实现直接加载原 `v100_v90_ctboost_nested_cv_blend.py`，SHA 固定为 `ad5cd07b64bf69fd08b9636c0a72138463b2506987155d3939395b5ce246a817`，只调用三个无文件副作用的纯函数 `fit_mid_ecdf`、`transform_mid_ecdf`、`choose_weight`。不会调用真实 runner、`load_inputs` 或旧 verifier；不会重新计算 V90 内部元权重。

`independent_fit()` 用唯一值频数和区间累计独立实现 mid-ECDF，用独立 ROC 阈值累计与梯形面积复算每个网格 AUC。保留 sklearn 去共线点的算术次序，避免改变旧选择规则。两路都严格按 `np.arange(0.0,0.5000001,0.025)` 的有序网格选最大 AUC，精确同分取最小权重，**没有 isclose 并列容差**。

`verify_final()` 要求选中权重完全相同，ECDF 状态和融合数组逐元素相等。训练 AUC 的 1e-12 只用于复算数值核验，不参与选权；如独立算术产生不同权重，直接拒绝，不用容差重新挑一个。训练拟合 AUC 标为 apparent，不作为新增 OOF 资格。

## CT 同批数组

`validate_global_arrays(train_id,test_id,y,v90_oof,v90_test,cache,fold_predictions)` 先验 ID、dtype、概率和形状，再用官方位置重新构造 seed42 的五折。

- `cache` 精确包含 `train_id/test_id:int64`、`oof_proba:float32`、`test_proba_foldmean:float64`、`atom_fold:int8(0..4)`。
- `fold_predictions` 按 fold01→05 排列，每项精确包含 `fit_idx/hold_idx/fit_id/hold_id/test_id:int64`、`oof_proba/test_proba:float64`。
- OOF 按 hold 位置转 float32 拼接；test 从 float64 零数组开始依次 `mean += fold_test / 5`。两者都必须与 cache 精确相同。缺折、重复折、改变折序、错 ID、旧 OOF 配新 test 或聚合精度变化均拒绝。

这些纯数组检查不能代替来源验证。未来本地生产调用先经过 CT 的 `authorize_archived()` 和 `require_successful_completion()`；后者先验证最终父监督、预算和运行记录，再调用 `check_cache()` 校验模型/状态/预测/manifest/同批身份与逐元素重建。本工具再核它返回的完整文件 SHA，才读取五份 test。

`authorize_archived(config_path,auth_path,expected_config_sha,expected_auth_sha,archive_map_path,expected_archive_map_sha)` 保留远端 config/auth 的原字节和 SHA，通过独立可信归档映射绑定本地官方输入、代码、资格凭据和完整归档文件树。meta 必须取得 `ARCHIVE_READ_ONLY` 上下文并使用 `artifact_root`；不会把远端 `/kaggle/...` 路径改写进合同，也不会把它直接当本地目录。映射、批次、原 config/auth 或归档字节不匹配时拒绝。

## 未来生产库入口

`compute_authorized(contract_path, authorization_path, expected_contract_sha, expected_authorization_sha)` 只供未来独立监督器调用，返回数组和复算证明，不发布文件，不提交比赛。两个可信预期 SHA 必须由父任务在未来合同冻结后传入，不能从待验证文件自报值抄取。缺合同、START_AUTHORIZATION 或可信 SHA 时，先于预测读取/选权拒绝。

未来父级还必须负责预算、进程树与父进程死亡监督、一次性 STARTED 排他、错误记录、运行中不可变输入和最终原子发布。本目录没有实现这些独立执行设施，返回状态仍是 `D_FINAL_META_REBUILT_REQUIRES_PARENT_FINALIZATION`、`allowed_for_submission=false`；不能绕过未来总合同直接把返回数组当可提交产物。

最终 meta 合同需包含以下字段；本说明只定义接口，不在本轮生成该合同：

- `status=FROZEN_D_FINAL_META_CONTRACT`，`candidate=D`，`method=OLD_V90_NEW_CT_FULL_TRAIN_V100_FINAL_META`，`synthetic=false`，固定 `weight_grid`，`submission_allowed=false`。
- `meta_runtime_versions`：实际 Python、NumPy、scikit-learn 版本，运行时精确核对。
- `source_files`：项目相对路径→SHA，至少包含本目录代码/测试/接口/准备说明、原 V100 源码、R01、官方 train/test/sample、旧 V90 OOF/test及完整来源、下面所有指针。
- `readiness_gate` 必须指向准备目录根的 `readiness_gate.py`；`qualification_receipt` 为未来资格回执。入口实际调用 `readiness()`，要求 eligible/selected/candidate=D，并与回执逐项核对 `bound_sources`、`terminal_artifacts`、`readiness_gate_sha256`。时间字段不要求相等。回执本身仍不是执行授权。
- `ct_adapter` 必须是同准备目录 `ct/ct_runner.py`；`ct_config`、`ct_start_authorization` 是本地归档的远端冻结原字节文件，`ct_archive_map` 是独立可信归档映射，三者都列入 `source_files`。`ct_cohort_id` 固定唯一批次。meta 与 CT 绑定同一资格回执 SHA；本地 CT 输出位置来自归档上下文的 `artifact_root`。
- `v90_verified_sources` 为下述未来旧 V90 输入审计回执路径。

START_AUTHORIZATION 必须为 `action=RUN_D_FINAL_META_ONCE`、`authorized_by=parent`、`contract_sha256=可信合同SHA`、`qualification_receipt_sha256=合同绑定回执SHA`、`preparation_only=false`、`competition_submission=false`。仅准备状态、synthetic 标记或资格布尔值不能解锁。

## 旧 V90 输入审计回执

本工具固定复用旧 V90 OOF SHA `c0057fc23fb130cd0bbbc05c6849893d5b79ff3a7ad786715d68fc1a6de4628f`、test SHA `6fa740955ac5997455e8e4b18aa181adbd9dd6da719e0cc80d858963e002f363`。完整来源回执仍需在未来执行前重新核验，不只凭这两个数组 hash。

回执接口：`status=VERIFIED_OLD_V90_GLOBAL_INPUTS`、`independent_reconstruction_passed=true`、`cpu_fit_rule=F_TRAIN_H_EARLY_STOP_SAME_MODEL_NO_REFIT`、`v90_test_aggregation=five_meta_folds_mean`；还须有 `train_rows/test_rows`、`train_id_sha256/test_id_sha256` 和 `source_files`。

ID SHA 沿用旧 V90：按官方行序把每个整数 ID 的十进制文本及换行逐个加入 SHA256。来源锚点 `model/v90_v89_member_verify_budget_retry/sources.json` 的 SHA 固定为 `57e7a7713386b1a1e8f6429f54ed88fcddba1c802811d72f628fdb8c7a775b70`。代码递归提取其全部 path/sha256 引用，重复路径的 SHA 必须一致，回执和最终合同均须逐项覆盖。实际 JSON 有 26 个唯一嵌入引用，加锚点自身共 27 项；校验依据完整引用集合，不以总文件数代替，填充无关文件不能弥补缺少的成员输出。原 JSON 的 row_identity、expected_row_identity 和全部 member_row_identities 也必须与 canonical ID 一致。每个来源实际字节在授权时核验。meta 不重新训练 V90，也不从旧 0.2 或外层 C/D 权重初始化。

最终返回包含 `test_id`、`meta`、`independent_verification`、CT 批次/完整文件快照和 V90 来源、合同/授权 SHA。新 CT 与历史 OOF 不相同不自动失败，但不得宣称旧 CT/V100 的逐位重现；本工具不为此重跑或选更接近的一批。
