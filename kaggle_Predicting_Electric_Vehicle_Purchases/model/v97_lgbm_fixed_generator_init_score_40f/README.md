# v97_lgbm_fixed_generator_init_score_40f

状态：`DESIGN_READY_NOT_STARTED`。本目录只完成预注册、实现、单元测试、synthetic smoke 与 hash/preflight；未运行正式训练，未生成真实 OOF/test/submission，也未更新 registry 或研究文档计数。

## 唯一假设

以已独立完成的 `v96_strict_v80_outer42_matched_control_40f` 为 seed42 同折 matched baseline。v97 完整保持 v96 的 62 static + 51 strict nested TE、40 个 outer folds、outer seed 42、inner seed 公式、LightGBM 4.6.0 参数与 early stopping。唯一科学变量是：

- fit：冻结生成公式 margin 子集传给 `init_score`；
- valid：同一公式 margin 子集传给 `eval_init_score=[valid_margin]`；
- valid/test predict：只取 `raw_score=True` 的 residual raw score，最终概率严格为 `expit(margin + raw_residual)`。

固定公式及公开来源的精确版本和 SHA 见 `public_source_evidence.json`。来源是 Kaggle notebook `cdeotte/fable-5-1-xgb-starter` v1，notebook SHA-256 为 `08cc650a222b62385a18226871a4481c3050f790d01f7006c6562240c815ae96`。只迁移公式，不使用公开 OOF/test、模型产物、融合权重或排行榜分数。

## 设计证据

`preflight_probe_evidence.json` 是 `TEMP_LGBM_INIT_SCORE_AB_SEED42` 的原始 5-fold 结果，文件 SHA-256 为 `6dfe8c02b75ad3c50ec4c0860b9cc8ecd094d3b83e3591ba1271e4f8a041f9e9`。它只证明值得进入正式候选设计：不是正式 CV，不复用其中 OOF，不得进入融合或提交。

历史去重快照覆盖 v1-v96 的 113 个可审计 Python 文件，并排除用户明确禁止查看的 v48 旧 seed lineage；没有发现同时包含该固定公式、LightGBM `init_score`/`eval_init_score` 与 `raw_score + margin` 重建的等价实现。XGBoost `base_margin` 属相关但不同的模型/API 机制。

## 正式门槛

必须完整完成同折 40-fold OOF，且同时满足：

- 相对 v96 的完整 OOF AUC 增量 `>= +0.0001`；
- 40 个完全相同 validation folds 中至少 `24/40` 个 AUC 增量为正。

结果必须同时报告相对 v80、v90、v95 的完整 OOF 差值和距绝对 `0.947` 的距离。主门槛未过时，`allowed_for_fusion=false`、`allowed_for_submission=false`。主门槛通过但仍低于 v90 时，只能标记为 `ELIGIBLE_FOR_SEPARATE_SMALL_FUSION_PREREGISTRATION_ONLY`，不得在本版本内融合或调权。

## 预算与运行边界

- 预算：3600 秒、16 GiB peak RSS、8 线程、0 次提交。
- 每折 checkpoint；每 5 折输出一次中间诊断。
- formal 运行沿用 v96 R3 的 source-first 全 verifier、首次 `np.load` 前统一验收、验收后复核、TOCTOU 文件封印、单实例 flock、资源失败原子关闭、staged verify、40 checkpoint 独立重建。
- checkpoint 额外保存 valid/test raw residual；恢复和 COMPLETE verify 必须逐元素重建 `expit(margin + raw_residual)`，并核对 LightGBM eval AUC。

## R3 完整性加固

- v96/v80/v90/v95 的 OOF/test 均先一次读成封印 bytes，核对该 bytes 的冻结 SHA-256，再从同一份 bytes 解析 NPY；不再存在按路径 hash 与按路径 load 分离的窗口。
- COMPLETE pending 通过全量 verifier 并完成最终字节封印后，立即执行 `POST_SEAL_COMMIT_GUARD`；超限会关闭为 FAILED，通过时不回写已验证的科学 payload，直接原子提交。
- formal 异常按 fold diagnostics、fold AUC、best iteration 和完整 BEFORE/AFTER 资源对的共同前缀关闭；被裁剪的中断窗口以 `interrupted_state` 明示记录。
- 候选 `sources.outputs` 的 verifier 对每个预期产物同时核对 `path`、`size_bytes`、`sha256`，任一字段漂移均拒绝。

默认命令只做只读预检：

```bash
python model/v97_lgbm_fixed_generator_init_score_40f/v97_lgbm_fixed_generator_init_score_40f.py --mode audit
python model/v97_lgbm_fixed_generator_init_score_40f/v97_lgbm_fixed_generator_init_score_40f.py --mode smoke
pytest -q model/v97_lgbm_fixed_generator_init_score_40f/test_v97_lgbm_fixed_generator_init_score_40f.py
```

`--mode train` 是正式 40-fold 入口，本轮明确禁止执行。
