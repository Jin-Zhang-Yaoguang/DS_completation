# D 候选重建工具准备

状态：`PREPARATION_ONLY_NOT_AUTHORIZED`。本目录目前只准备代码、只读检查和合成测试，不是正式部署合同、真实训练结果或提交产物。原 A/B、C/D 配置、代码与预测归档均保持冻结。

研究选择规则仍以 `../e2e_legacy_comparison_20260905/PREREGISTRATION_R01.md` 为准：B−A 完整算力门槛通过后才运行 C；D−C 整体为正且 5/5、独立复算及完整监督通过后，才另立 D 实际重建合同。当前没有该合同或启动授权。

## 已完成准备的组件

- `readiness_gate.py`：固定来源 SHA，调用冻结的 `require_successful_comparison()`，再次检查 D/C 身份与 B−A、D−C 完整五折条件。只读输出，不创建授权或启动进程。缺终态返回 `NOT_READY`。
- `ct/`：全局 CT 五折同批重建 worker；保存配套 OOF、每折 test、模型、特征状态、身份、实际运行环境和来源。真实入口须同时持有未来正式合同及父级启动授权，完成缓存也仍需最终监督成功。
- `meta/`：保留旧 V90 OOF/test，使用同批新 CT OOF 和 foldmean test 重建原 V100 的最终 ECDF 与固定网格权重。原 V90 内部元层不重拟合；原 CT OOF、旧 0.20 权重及外层对照权重均不能搬入。

原三个组件共通过 74 项合成测试和源码审查（资格 11、CT 39、meta 24）。新增父监督库另通过 22 项合成/短进程故障测试和独立审查，共 96 项；原 74 项未重复运行。CT 首版的守护与归档缺口已修正；证据见 `PREPARATION_REVIEW.json`，首版问题保留在 `CT_REVIEW_R01.json`。新增证据见 PARENT_SUPERVISION_REVIEW.json 和 supervision/。这仍不是实际运行验收；监督库已准备，真实启动器集成、私有 GPU 打包与归档、最终合同及候选验收还未执行。

## 资格检查的边界

`readiness_gate.readiness()` 无参数，不提供其他目录、假数据或执行模式。成功返回 `VERIFIED_D_REBUILD_ELIGIBLE`，其中 `candidate_rebuild_eligible=true`、`selected_candidate=D` 只允许进入定义实际合同的下一步。

凭据始终保留 `execution_authorized=false`、`allowed_for_submission=false`。真实启动之前，父级仍须重查最新完整资格，将代码、实际输入与凭据绑定进另立的合同，并创建单次启动授权。远端检查父级绑定凭据；本地元层同时重新调用只读资格 API。不能把合成测试中的合格字典当成真实凭据。

研究晋级的 `+0.0001` 与用户的条件提交权限分开。正向但低于该值的候选，仍可在其他完整条件全部通过时取得实际重建资格。真实候选产物复核、线上最佳刷新、当天次数与重复 SHA 检查以及最终一次提交，均尚未执行。

## 当前已完成的检查

`readiness_gate.py` 已通过 11 项合成测试及独立源码审查；实机只读检查因缺 C/D 终态返回 `NOT_READY`，没有读取真实目标或预测数组。证据为 `READINESS_REVIEW.json`。该检查不证明候选有效。

新的 CT 运行无需逐位复现历史 GPU 结果；必须保存实际环境和同批预测来源，差异如实记录，不能重跑挑分。数组重建、模型抽样回放与全量模型回放应分别报告覆盖范围。
