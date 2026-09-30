# v10 official replay manifest

本目录把 2026-08-18 至 2026-08-20 的 Kaggriculture 官方回放转换为紧凑、可复核且无 seed 泄漏的索引。原始约 60 GiB JSON 不复制进模型目录。

## 数据范围

- 数据根目录：`model_data/kaggriculture_episodes_index/daily`
- 2026-08-18：697 局
- 2026-08-19：695 局
- 2026-08-20：698 局
- 合计：2,090 局、2,090 个唯一 seed

所有回放均为 720 步、两席位 `DONE`，顶层与末步 reward/status 一致，且没有缺失字段或解析错误。

## 输出

- `official_replay_manifest.jsonl`：每局一行，包含来源、seed、终局结果、拆分和两席位动作哈希。
- `data_quality_report.json`：唯一性、缺失值、DONE、一致性、seed 重复、谱系和泄漏审计。
- `evaluation_seed_manifest.json`：按 train/val/test 组织的完整评测记录。
- `evaluation_seed_manifest.jsonl`：与上一个文件等价的逐局流式版本，推荐 evaluator 使用。

正式拆分为 1,670/210/210。三份数据都覆盖三天；test 有 210 个唯一 seed，超过最低 100 个要求。episode ID 或 seed 相同的记录会先合并为不可拆的 identity group，因此不会跨 split。

拆分使用确定性的日期 + 常见 `prefix72` 生产轨迹多标签分层。只有至少出现 10 次的日期/谱系组合参与谱系配平，稀有谱系不伪装成可分层样本。

## 动作哈希定义

每个席位保存两种 SHA-256：

- 完整生产动作：全部 replay step 的 `farmer` 和 `hands`。
- `prefix72`：step index 0–71 的 `farmer` 和 `hands`。

市场动作被明确排除。动作按 canonical JSON 编码，并使用长度前缀消除拼接歧义。

这些哈希只是官方回放中“已观察动作轨迹”的 provenance，用于聚类和泄漏审计；它们不是 V1/V2/V5/V8 等人工定义的专家根谱系，也不能替代 LOLO 的 curated lineage 标签。

## 复现

从仓库根目录运行：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v10_replay_lolo_router/build_official_manifest.py --strict --progress-every 100
python -m unittest -v kaggle_Kaggriculture.model.v10_replay_lolo_router.test_build_official_manifest
```

脚本优先使用 `orjson`，未安装时自动回退到标准库 `json`。文件始终顺序读取，内存中只保留紧凑记录；输出通过临时文件原子替换。

测试覆盖：市场动作不影响生产哈希、第 72 步之后不影响 `prefix72`、生产动作变化会改变完整哈希、重复 seed 不跨 split、JSON/JSONL 两种 evaluator manifest 完全等价。

## Router outcome grid 与 LOLO

`collect_router_grid.py` 使用官方 manifest 的 train/validation seed 做闭环潜在结果采集，不重放历史动作。每个 seed、席位、对手根谱系下，V1 anchor 执行 step 0–71；候选完整专家同步影子更新，并在 step 72 的同一公开状态接管。只有完整前缀一致的候选进入训练。

collector 支持多进程、JSONL 逐局落盘、resume 和失败重试。collection fingerprint 同时覆盖 registry/底层专家代码、collector、agent factory、router 和运行时版本；代码变化不会误复用旧结果。训练 collector 和 `train_router.py` 都会拒绝官方 test split。

`train_router.py` 对 `baseline_v1/v2/v5/v8` 拟合 NumPy ridge value heads。LOLO 每折只留出一个对手根谱系，四个候选动作始终保留；报告 best-fixed、规则 Router、学习 Router 的 score、金币 margin、seed-cluster bootstrap 95% CI 和选择分布。LOLO 与 train-only validation 结束后，才用 train+validation 重拟合供最终冻结 test 矩阵使用的权重。

当前实际 smoke 为 1 个 train seed、双席位、V1/V2 候选对 V1，共 4 局：4/4 `DONE`、0 错误、2/2 上下文候选齐全、step72 特征一致、前缀兼容。该 smoke 只验证管线，不是效果证据。
