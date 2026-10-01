# CT 库接口：准备版

`PREPARATION_ONLY_NOT_AUTHORIZED`。没有真实运行命令。以下描述未来由父任务审查、冻结并签发正式文件后的接口，不是现有授权。本目录不安装包、不打包 kernel、不计算 AUC、不产 submission。

## 入口

```python
context = authorize_contract(
    config_path, auth_path,
    expected_config_sha, expected_auth_sha,
)
result = run_authorized(
    config_path, auth_path,
    expected_config_sha, expected_auth_sha,
    lease,
)
checked = require_successful_completion(output, context)
```

`expected_*_sha` 必须由可信父监督的冻结配置传入，不能从待验文件自身摘取。这里的签署指父任务持有的外部 SHA 锚及显式授权记录，不是密码学签名系统；任何持有主机写权限者都能修改代码，不声称对恶意主机提供安全隔离。

`authorize_contract` 不读取真实 CSV 标签。生产入口没有可注入 backend/factory 参数；fake backend 仅在测试调用内部 `_fit_five`，测试自己生成 100 行 train、20 行 test、负数 ID。生产没有 `--synthetic` 开关。

## 未来正式配置字段

这些是字段说明，不生成可执行的正式 config。

| 字段 | 合同 |
|---|---|
| schema_version/status/role | `1` / `FINAL_AUTHORIZED_CONTRACT` / `D_CT_GLOBAL_5FOLD` |
| cohort_id | 父任务指定的唯一、长度至少 16 的批次 ID |
| recipe | 与代码 `RECIPE` 精确一致，来自冻结 GPU R01 |
| inputs | `train/test/original` 各 `{path,sha256}`，必须匹配固定官方文件字节 |
| source_recipe | `{path,sha256}`，GPU R01 config SHA `00a51bdb…` |
| worker_sources | 恰 `ct_runner.py/ct_features.py/resource_guard.py` 的 SHA；正式打包前最后审查再固定 |
| source_files | 历史 Notebook、R01、其他父级审计来源的命名 `{path,sha256}` 映射；实际打包保留所有路径可解析 |
| qualification_receipt | `{path,sha256}`，来自根 readiness_gate 的完整 D/C 资格凭据 |
| runtime_versions | numpy2.0.2、pandas2.3.3、scikit-learn1.6.1、ctboost0.1.58 |
| installation_wheel | `{path,sha256}`，正式环境实际安装并保留的 wheel；worker 不下载或安装 |
| remote_execution | `provider=kaggle,kernel_ref,kernel_version`，未来单次 kernel 的固定版本身份 |
| output_dir | 新的绝对输出目录；不复用历史 CT 或 E2E cache |
| budget | 整数 seconds/memory_bytes/threads，不能超过 R01 的7200秒/24GiB/4线程；最终值由父级合同决定 |
| replay | `scope=ALL_H_AND_TEST, rtol=1e-7, atol=1e-8`；来源为历史模型保存/加载校验，扩大为全部查询 |

正式 `START_AUTHORIZATION` 必须包含：`action=START_CT_GLOBAL5_D_ONCE`、`authorized_by=parent`、`config_sha256`、相同 `cohort_id`、`qualification_receipt_sha256`、`preparation_only=false`。不创建或自动补全授权文件。

资格 receipt 必须为 `VERIFIED_D_REBUILD_ELIGIBLE`、`candidate_rebuild_eligible=true`、`selected_candidate=candidate=D`、`baseline=C`，含 `bound_sources/terminal_artifacts/readiness_gate_sha256/checked_at_utc`，其 `execution_authorized/allowed_for_submission` 仍为 false。父级启动前重新调用完整资格 API，远端检查父级打包的不可变凭据及其 SHA；单独自称 PASS 的结果不足以签发授权。

## 父监督 lease 与完成合同

父级使用新进程组启动 worker、完整采集 `worker.log`；lease 传入 `parent_pid,parent_created,config_sha256,start_authorization_sha256,prior_seconds,prior_peak_bytes`。父 PID + create_time 必须匹配当前父进程；worker 必须为自己进程组首进程。此前耗时/RSS也计入累计预算。

父级启动前必须在 **output_dir 之外** 捕获完整日志；真实 worker 要求输出目录为空，提前在其中打开 `worker.log` 会被拒绝。退出后由父级把外部日志归档为 output_dir/worker.log，再做退出/清理/预算核验并生成最终监督结果。

独立 `resource_guard.py` 在数值计算前启动，用另一个进程持续检查父存活、worker树 RSS 和墙钟。父死亡或超预算将杀死整个 worker 进程组，包括长 native 调用；父级仍须从 worker 启动前到进程退出、所有子进程回收后覆盖完整生命周期。本准备包不实现实际远端父监督的启动或恢复。

worker 先独占写 `RUN_STARTED.json`。现有 STARTED 的二次调用失败，失败状态与 `.partial` checkpoint 保留；恢复必须由未来父任务另审，不存在自动重启。完整 fold checkpoint 可读校验，但不能让公开真实入口跳过单次启动边界。

最终父级写 `SUPERVISOR_RESULT.json`，必须包含：

- `status=CT_DEPLOYMENT_SUPERVISOR_COMPLETE, exit_code=0, phase=AFTER_EXIT_AND_CLEANUP, completed_folds=5`；
- 绑定 `config_sha256/start_authorization_sha256`；有限且不超合同的 `seconds/peak_process_tree_rss_bytes`；
- `instance={worker_pid,worker_created,parent_pid,parent_created}`，必须与 STARTED、worker完成和guard报告逐项一致；
- `file_sha256` 精确包含 `WORKER_COMPLETE.json,RUN_STARTED.json,cache_manifest.json,runtime/manifest.json,guard_report.json,worker.log`。

`require_successful_completion` 先核上述最终监督合同，再调用 `check_cache`。实际 meta 合同还应把这份最终监督结果 SHA 作为外部锚，避免仅信任输出目录自述。worker `WORKER_COMPLETE` 和 cache 完整均不单独赋予消费资格。

## 产物与只读检查

每个 `folds/fold_01..05/` 包含：

- `model.json`：真实 CTBoost 模型；`feature_state.joblib`：同折所有类别/频次/外部映射和交叉拟合 TE 状态；
- `predictions.npz`：`fit_idx/hold_idx/fit_id/hold_id/test_id` 均 int64，`oof_proba/test_proba` 均 float64；
- `manifest.json`：折号、cohort/config/auth/输入/特征来源/runtime/splits 身份、三个产物 SHA、特征列顺序及 SHA、全部 H/test 保存模型回放行数和最大误差。

`splits.npz` 在任何 fit 前保存 `train_id/test_id(int64),atom_fold(int8,0..4)`。正式行数固定 668665/286571，fold 用真实 train 标签和固定 seed42 构造；保存 split SHA 进入每个 fold 身份。检查器不为重建 split 再读取标签，使用经过冻结代码生成、被最终监督绑定的 split。

`cache.npz`：`train_id/test_id(int64),oof_proba(float32),test_proba_foldmean(float64),atom_fold(int8)`。

`cache_manifest.json`：`status=CT_GLOBAL5_CACHE_COMPLETE_UNSCORED`、身份、cache SHA、固定5个 fold manifest SHA、每个数组的规范化 dtype/shape/bytes SHA、固定顺序聚合说明。`allowed_for_submission=false/deployment_verified=false`。

`runtime/manifest.json` 记录 Python 完整版本/可执行文件 SHA、平台、真实包版本、CT CUDA build、`nvidia-smi -q` GPU/driver/CUDA信息、实际安装文件 SHA。CT wheel 被复制归档；安装的 CT 包/动态库逐文件与 wheel 字节比对。仅记录旧 expected wheel SHA 不算实际安装证据。

`check_cache(output,context)` 不读真实目标、不算 AUC；核官方 CSV id、dtype/概率/长度、全部折产物哈希与 identity，然后逐元素重建 OOF 和按 fold01→05 的 float64 `mean += test/5`。返回：

```text
status = CT_GLOBAL5_CACHE_REBUILT_UNSCORED
arrays = 上述 cache 五个数组
files = 输出目录内被核文件的相对路径 → SHA
identity = 同批来源身份
allowed_for_submission = false
```

`require_successful_completion` 返回同结构，并将 status 改为 `CT_GLOBAL5_SUPERVISED_COMPLETE_UNSCORED`，files 增加最终监督链。后续 meta 只能从该返回及其绑定的 fold 预测生成独立重建；不能旧 CT OOF 搭新 test。

## 跨主机只读归档接口

Kaggle 运行后，原始 config 的 `/kaggle/...` 路径在本地不存在。必须保留原 config/auth 字节及 SHA，用新的、父级独立核验的归档映射：

```python
context = authorize_archived(
    config_path, auth_path, expected_config_sha, expected_auth_sha,
    archive_map_path, expected_archive_map_sha,
)
checked = require_successful_completion(context['artifact_root'], context)
```

返回 `mode=ARCHIVE_READ_ONLY`、本地 `artifact_root` 和精确 `local_path_map`；`context['config']` 保留原远端字段。`run_authorized` 不接收 context，也不接受映射；它重新校验原同机文件及授权，归档上下文不能变成训练通行证。

归档映射 JSON 必须包含：

- `schema_version=1,status=VERIFIED_CT_DEPLOYMENT_ARCHIVE,config_sha256,start_authorization_sha256,cohort_id,remote_output_dir`；
- `remote_execution`：与正式 config 相同 `provider/kernel_ref/kernel_version`，加 `status=COMPLETE,download_version_before,download_version_after`，下载前后必须为固定版本；
- `artifact_root`：本地归档根，禁止 symlink；`files` 为根下**全部文件**的相对路径→SHA，严格核对无缺项、无未绑定新增文件；
- `path_map`：键集恰为原 config 的 `source_recipe,qualification_receipt,installation_wheel,source_files,inputs` 所引用的路径。每项 `{path:本地路径,sha256:原SHA}`；禁止额外路径，禁止改原来源 SHA。官方 CSV 可映射到本地官方文件；已归档 wheel 可映射到 `runtime/` 中对应副本。

映射本身应放在 artifact_root 之外，避免自引用文件树 SHA。未来父级负责真实单次下载/版本核验及签发映射；本接口不下载、不生成归档映射。meta 正式合同还必须绑定映射、原 config/auth 和最终监督结果 SHA。

当前合成测试覆盖远端路径不存在但合法本地映射可读、错映射 SHA、版本漂移、缺文件、额外路径、错 cohort、symlink 和 fake 归档无法取得正式权限。所有 fixture 都是临时生成的小文本和假数组；没有把正式输入标签搬入测试。
