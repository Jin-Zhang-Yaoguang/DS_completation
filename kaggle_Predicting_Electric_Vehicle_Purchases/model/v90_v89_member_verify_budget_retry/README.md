# v90：v89 成员核验内存预算修复重试

## 关闭证据与重试边界

- 实验 ID：`v90_v89_member_verify_budget_retry`
- `retry_of=v88_strict_v80_v85_cv_blend`
- 实现前序：`v89_v88_row_identity_fix_retry`
- 研究周期：`C01`，沿用位置 `9`
- `counts_toward_cycle=false`：v88 已计数，v89/v90 同配置修复均不得重复计数。
- 状态：`DESIGN_READY_NOT_STARTED`
- 日期：2026-09-04
- 新候选代码 SHA-256：`71618b688ba314510c55efee08d8f848d1658e67e195908792e35c0f8328a013`
- 冻结配置 SHA-256：`ec255f79707963c37909618fdfb20e2bdedcd9599b7fdd13ac03e34503b0536e`
- audit candidate snapshot SHA-256：`35fcb5f75b807e6c751254546497b2e137a8daebfe83e3951816ed642fc9e705`
- 提交预算：`0`

v88 与 v89 都是不可修改、不可重跑的正式关闭证据：

- v88：`FAILED_EXCEPTION`，行身份哈希实现错误；`cv_results.json` SHA-256 为 `1b88a95c5d81c74ddee4f3734fc89a217adcbb4aea6b6887981a07401711cad4`。
- v89：`FAILED_RESOURCE_BUDGET`，`AFTER_INPUT_LOAD` 检查发现进程 peak RSS `7291240448` bytes，即 `6.790496826171875 GiB`，超过旧 4 GiB；`cv_results.json` SHA-256 为 `51bf483470461f9722533daa91a52386089bc87ba65f19b245cf5d5c353482f2`。
- v89 仅留下 `train_log.txt`，没有 candidate snapshot、fold、sources、OOF、test 或 submission，确认尚未进入融合。

## 归因与唯一资源合同修复

v89 在 `load_formal_inputs` 中正式调用 v80/v85 各自的完整 verifier。它们会重建并核验历史原子模型产物，属于强制核验，不得跳过。特别是冻结的 v85 `cv_results.json` 记录历史 peak RSS `9650110464` bytes，即 `8.98736572265625 GiB`；v85 自身采用的冻结预算也是 12 GiB。

因此 v90 采用进程级 12 GiB peak RSS 预算，继续把同进程成员 verifier 纳入测量范围。没有把 verifier 拆到子进程，因为那会把子进程峰值排除在当前 `RUSAGE_SELF` 指标之外，表面降低读数却削弱全作用域资源约束。

唯一合同变化：

- `peak_rss_budget_bytes`：`4294967296` → `12884901888`
- `memory_budget_gib`：`4` → `12`

以下内容保持不变：900 秒 wall budget、完整成员 verifier、canonical newline ID 哈希、成员间 row identity 直接比较、模型假设、成员、meta 五折、ECDF、权重、晋级门槛、失败治理和 staged verify。

## 原研究协议保持不变

- 成员仅为 `v80_strict_v61_outer104395303_40f` 与 `v85_naji_v74_40f`。
- 固定 `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`。
- 每折只在 meta-train 分别拟合两个成员的 mid-ECDF。
- v85 权重固定搜索 `0, 0.05, ..., 1`；权重只按 meta-train AUC 选择。
- 并列先取最接近 `0.5`，再取较低 v85 权重。
- 五个 holdout 拼成主 OOF，test 为五折预测均值。
- 等权仅作诊断，不得替换主方法。
- 基准仍为 v85 OOF `0.9462702273556288`。
- 只有相对 v85 至少 `+0.0001` 且 meta holdout `5/5` 全部提升才 `PROMOTE`，否则 `REJECT`。

测试会把全部建模函数与 v89 逐函数比较，并逐项比较配置中的模型、成员、meta、变换、权重、门槛和 canonical ID 合同；另行断言只有 peak RSS 预算从 4 GiB 提升到 12 GiB，wall budget 仍为 900 秒。

## audit、schema 与失败治理

audit 只读取文件哈希和 JSON 元数据，不加载真实预测数组，并验证：

- v88、v89 关闭结果的 SHA、状态、错误、计数和残留产物；
- v89 确实在 `AFTER_INPUT_LOAD` 因 peak RSS 关闭且没有融合输出；
- v85 历史 8.987 GiB 峰值及其冻结结果 SHA；
- 12 GiB 新预算与 900 秒不变 wall budget；
- v80/v85 成员 SHA、canonical newline 行身份及成员间直接一致性。

所有 v90 COMPLETE/FAILED 结果都必须写 `counts_toward_cycle=false`、`retry_of=v88_strict_v80_v85_cv_blend`、`implementation_predecessor=v89_v88_row_identity_fix_retry`，并由独立 verifier 严格重建。资源或异常失败继续执行完整产物清单和 `present_artifacts_are_invalid_for_use=true` 治理。

## 运行方式

```bash
python model/v90_v89_member_verify_budget_retry/v90_v89_member_verify_budget_retry.py
python model/v90_v89_member_verify_budget_retry/v90_v89_member_verify_budget_retry.py --mode smoke

# 本次禁止；以后获得明确授权才允许：
python model/v90_v89_member_verify_budget_retry/v90_v89_member_verify_budget_retry.py --mode run
python model/v90_v89_member_verify_budget_retry/v90_v89_member_verify_budget_retry.py --mode verify
```

## 当前结论

只完成 v89 资源失败归因和 v90 预注册实现，没有正式运行 v90，也没有融合结果。v90 无论最终成功或失败均不重复计入 C01。
