# v89：v88 行身份口径修复重试

## 失败确认与重试边界

- 实验 ID：`v89_v88_row_identity_fix_retry`
- `retry_of`：`v88_strict_v80_v85_cv_blend`
- 研究周期：`C01`
- 周期位置沿用：`9`
- `counts_toward_cycle=false`：v88 已作为第 9 个正式版本计数，本次同配置实现修复不得重复计数。
- 状态：`DESIGN_READY_NOT_STARTED`
- 日期：2026-09-04
- 新候选代码 SHA-256：`a397c7cbaa242688a8ebb43d1fbcabf2cdcabf254a17b4dc8f1bc41464cb7409`
- 冻结配置 SHA-256：`ef3a73543b2df61dd0e5466381475cbf57829968da4a449bc9de62a2585e2d2e`
- audit candidate snapshot SHA-256：`715ced7fe2801240cf1a56658078c1c80a4b735930e247fb4425c376e846fe6c`
- 提交预算：`0`

v88 已真实关闭为 `FAILED_EXCEPTION`，禁止重跑、删除、覆盖或修改其失败证据。冻结确认如下：

- `model/v88_strict_v80_v85_cv_blend/cv_results.json` SHA-256：`1b88a95c5d81c74ddee4f3734fc89a217adcbb4aea6b6887981a07401711cad4`
- `error_type=ValueError`
- `error=成员行身份不一致：v80_strict_v61_outer104395303_40f`
- v88 runner SHA-256：`2ac29faf8637c87d3bab6a0cc9617069c1ee12e1fb9ca12b5fcf08e3097f077b`
- v88 config SHA-256：`2787bf3f69ab105e75745f00d609f5d247a9c69c416945a388eb7abddcc08908`

归因：v80/v85 `sources.json` 的 `row_identity` 完全相同；v88 却用“每个 ID 加 8 字节长度前缀”的本地重算口径，而成员来源使用 `str(value)` 后追加换行的 SHA-256 口径。因此这是 v88 行身份校验实现错误，不是数据或成员行序不一致。

## 唯一实现修复

v89 只允许以下建模实现变化：

1. `sha256_ids` 改为与 v80/v85 来源完全相同的 `str(value).encode("utf-8") + b"\n"` canonical newline 哈希。
2. 在读取任何成员预测数组之前，直接比较 v80 与 v85 的完整 `row_identity` 对象；随后再与本地 train/test canonical-newline 重算结果比较。

除此之外，模型假设、两个原子成员、五折 meta 切分、fit-only mid-ECDF、权重网格、平局规则、test 聚合、等权诊断、晋级门槛和资源预算全部与 v88 完全相同。配置测试会逐项比较这些字段，防止借重试改变研究方法。

## 原协议保持不变

- 成员仅为 `v80_strict_v61_outer104395303_40f` 与 `v85_naji_v74_40f`。
- 固定 `StratifiedKFold(n_splits=5, shuffle=True, random_state=42)`。
- 每个 meta fold 内分别只在 meta-train 拟合两个成员的 mid-ECDF，再变换 train/holdout/test。
- v85 权重固定搜索 `0, 0.05, ..., 1`，v80 权重为 `1-w_v85`。
- 权重仅由 meta-train AUC 选择；并列先取最接近 `0.5`，再取较低 v85 权重。
- 五个 holdout 拼成主 OOF；test 为五个 fold-specific 预测的算术平均。
- 固定等权仅作诊断，禁止事后替换主方法。
- 最佳输入基准仍为 v85，OOF `0.9462702273556288`。
- 只有相对 v85 至少 `+0.0001` 且五个 meta holdout `5/5` 全部提升才 `PROMOTE`，否则 `REJECT`。
- 资源预算仍为 900 秒、4 GiB peak RSS、单进程、1 CPU 线程协议。

## 证据、schema 与验证

audit 必须只做哈希和 JSON 元数据校验，不得加载真实 OOF/test 数组。它会同时确认：

- v88 失败结果 SHA、错误、失败状态、计数状态与失败产物不可用标志；
- v80/v85 的冻结文件 SHA；
- 两成员 `row_identity` 直接相等；
- 两成员身份等于冻结的 canonical-newline 行身份。

正式模式沿用 v88 的 staged verify + atomic COMPLETE、资源硬停、两类 FAILED 产物治理和统一 `failure_attribution`。所有 v89 结果必须包含 `retry_of=v88_strict_v80_v85_cv_blend` 与 `counts_toward_cycle=false`。`COMPLETE + PROMOTE` 的归因为 `null`，`COMPLETE + REJECT` 及两类 FAILED 使用冻结归因。

## 运行方式

```bash
python model/v89_v88_row_identity_fix_retry/v89_v88_row_identity_fix_retry.py
python model/v89_v88_row_identity_fix_retry/v89_v88_row_identity_fix_retry.py --mode smoke

# 本次禁止；以后获得明确授权才允许：
python model/v89_v88_row_identity_fix_retry/v89_v88_row_identity_fix_retry.py --mode run
python model/v89_v88_row_identity_fix_retry/v89_v88_row_identity_fix_retry.py --mode verify
```

## 当前结论

只完成失败归因、独立修复预注册与代码验证。没有运行 v89 正式融合，不能据此判断 v85 是否带来增益；v89 无论最终成功或失败均不重复计入 C01 常规版本数。
