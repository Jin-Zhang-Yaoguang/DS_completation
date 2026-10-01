# 周期性超级融合公共基础设施

本目录只提供 C-06 的公共、可测试组件，不代表已经触发或运行 `ME-Cxx`。当前 CLI 仅启用 `audit-only`；`meta-cv`、`ablation`、`final-fit` 在正式实验预注册和候选快照冻结前硬性拒绝执行。

## 安全边界

- 候选不是自动扫描结果。`audit-only` 虽会生成仓库清单，但只有显式 `candidate-config.json` 中的 allow-list 能进入快照。
- 候选必须同时有 OOF、test、结果 JSON、行序审计说明和有限的 `[0,1]` 概率；公开成员还必须标记为已审计。
- `candidate_snapshot.json`、`sources.json`、`lineage.json` 均以排他写入创建，已有文件不会覆盖。
- 下游加载时重新验证快照内容哈希、所有源文件 SHA-256、长度和概率范围。源文件被修改后立即失败。
- `.npy` 通过只读 memmap 校验。CSV/Parquet 必须使用 `path::column` 形式。
- 元变换只暴露 `fit(train)` 与 `transform(valid/test)`；选择器只接收调用方传入的内层训练块。
- 确认 seed `104743` 的索引默认锁定。旧 seed `104729` 已在 P2-05 公开成员审计中暴露，不再承担确认职责；`104743` 是严格大于它的首个素数，且冻结前确认未用于项目历史实验。`load_meta_folds` 需要同时显式请求并解锁才会返回确认折；本里程碑没有任何确认结果读取或评分入口。

## 候选配置最小示例

```json
{
  "schema_version": 1,
  "cycle_id": "C01",
  "candidates": [
    {
      "id": "v80_strict_v61_outer104395303_40f",
      "experiment_dir": "model/v80_strict_v61_outer104395303_40f",
      "artifact_type": "atomic_model",
      "family": "lightgbm",
      "feature_mechanism": "strict_nested_multiscale_te_income_bin10",
      "split_seed": 104395303,
      "source_scope": "local",
      "audited_public": false,
      "inclusion_reason": "strict frozen single-model benchmark",
      "row_order_evidence": {
        "oof": "source script writes validation indices into train.csv row positions",
        "test": "source script predicts test.csv without reordering"
      },
      "declared_parents": []
    }
  ]
}
```

`row_order_evidence` 是人工审计入口，不是自动推定。正式冻结前应引用具体源码行、ID sidecar 哈希或其他可复核证据。

## Audit-only CLI

输出目录必须尚不存在：

```bash
python model/superblend/run_superblend.py \
  --stage audit-only \
  --repo-root . \
  --candidate-config /path/to/frozen-candidate-config.json \
  --output-dir model/vNN_me_c01_selective_superblend \
  --expected-oof-rows 668665 \
  --expected-test-rows 286571
```

这一步只做审计、冻结和血缘解析，不计算相关矩阵、不选择成员、不拟合权重，也不生成 test 融合预测。

## 模块

- `registry.py`：显式候选注册、schema/长度/范围校验、SHA-256 快照。
- `lineage.py`：解析 `sources.json` 与显式父节点，检测环和父子重复计权。
- `transforms.py`：训练块拟合的 ECDF/rank 与标准化。
- `meta_cv.py`：固定外层/内层索引、索引哈希、确认 seed 锁。
- `selectors.py`：相关簇、等权、家族等权、最多 12 成员 greedy、预注册网格的非负受约束 ridge、家族分层。
- `ablation.py`：drop-one-member 与 drop-one-family 基础计算。
- `run_superblend.py`：四阶段 CLI；当前只开放 `audit-only`。
