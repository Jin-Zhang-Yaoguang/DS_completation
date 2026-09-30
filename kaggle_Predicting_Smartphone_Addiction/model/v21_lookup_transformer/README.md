# V21：Lookup-Transformer 单模

## 状态

已完成五折完整训练、独立审计与 Kaggle 提交。该候选已晋级为正式 V21 单模型：

- OOF AUC：`0.9685596133944011`；折内 rank 诊断 AUC：`0.9685680355471754`；
- 五折 AUC：`0.96793614 / 0.96851307 / 0.96879427 / 0.96915670 / 0.96843999`；
- 相对 v3：OOF `+0.00059436`，5/5 折提升；
- 相对 v7：OOF `+0.00042734`，5/5 折提升；
- Kaggle Public AUC：`0.96997`，ref `55721780`，状态 `COMPLETE`；
- 当前总榜最佳仍为融合版 v20 `0.96998`，V21 仅低 `0.00001`。

正式记录位于 `submission_record.json`，独立终审位于 `full_run/validation_results.json`。最终提交采用与公开 Notebook 一致的“五折 raw logit 等权平均，再做全局 percentile rank”；复核没有发现 probability mean 或 fold-rank mean 更优的离线证据。

本目录只复现单个 Lookup-Transformer，不复现公开 Notebook 的 CatBoost、LightGBM 和三模型融合。代码从官方 `train.csv` 重新训练，绝不读取公开 OOF、test 预测或 submission CSV。

## 来源与审计

- 公开 Notebook：[`tamerlanomralinov/s6e8-lookup-transformer-insights-lb-0-97041`](https://www.kaggle.com/code/tamerlanomralinov/s6e8-lookup-transformer-insights-lb-0-97041)
- Kaggle CLI 拉取日期：2026-08-24
- 拉取版本：Kaggle 当前公开版本 4
- 原始 `.ipynb`：28,130 bytes
- SHA256：`a3b1d7468389bf9d53a7c49da1ba002636b48dcfcbb5deaa7af60c635b0b5806`

完整审阅后发现一处必须隔离的版本差异：Notebook 说明文字写“10-fold”，当前代码实际是 `N_FOLDS = 11`。因此公开 OOF 即使能够下载，也不能放入本项目五折模型池。本适配版只迁移架构和训练方法，从官方数据按项目约定重新训练。

## V21 固定数据契约

```python
StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
```

- 直接读取官方 `train.csv`，不排序、不按 id 重排、不 reset 后拼接 OOF；
- 每个训练行只接收所属验证折的预测；
- 保存 `fold_id.npy` 和 train/test id 哈希；
- 折分随机种子固定为 42；模型初始化、batch permutation 和随机缺失增强的各折训练种子为 `42 + fold`，即 42、43、44、45、46；
- train+test 联合拟合的只有无标签变换：精确值词表、rank-gauss 和预算特征；
- `id` 不入模；
- 每折结束立即原子保存 valid index、valid/test raw score 和 fold report；
- 仅当代码、数据、折分、配置、运行环境完全匹配 `run_signature` 时自动恢复；
- 完整训练后才写生产 OOF/test/submission 文件。

## 最小忠实配置

以下是建议用于 V21 正式验证的最小忠实配置，保留公开模型的全部关键机制：

| 项目 | 配置 |
| --- | --- |
| folds | 5，shuffle，seed 42 |
| exact lookup | 每个原始字段的精确值独立词表，NaN 为该字段 index 0 |
| raw numeric branch | train+test rank-gauss |
| derived tokens | `other_screen`、`sgw`、`other_frac`、`wk_minus_sgw`、`wk_other`、`sgw_frac` |
| model | d=128，PLR k=24，4 Transformer layers，8 heads，FFN=256 |
| optimization | AdamW，LR 0.002，OneCycle，gradient clip 1.0 |
| regularization | embedding WD 3e-4，其余 WD 1e-5，dropout 0.1 |
| missing augmentation | 训练期额外随机遮蔽 10% 原始字段 |
| EMA | 0.999 |
| epochs | 最多 32，每两轮验证，5 次无提升停止 |
| output | 原始 logit score、sigmoid probability、fold id、rank submission |

不能再削减 lookup embedding、PLR smooth branch、预算 token、attention 或随机缺失增强；否则测试的是另一种模型。用于 smoke 的 32 维单层版本只验证管线，不产生实验结论。

## 已知方法学差异与 caveat

1. **Checkpoint selection**：每个外层验证折同时用于选择最佳 EMA epoch 和 early stopping。因此保存的 raw OOF 虽然没有直接行级标签特征泄漏，但存在轻微的 checkpoint-selection 乐观偏差；判断 `1e-4` 量级融合增益时必须保守。
2. **5 折不等于公开 11 折**：公开 v4 代码实际训练 11 折，每个模型看到约 90.9% 训练数据并融合 11 个 test 预测；本项目固定 5 折，每个模型只看到 80% 数据并融合 5 个预测。公开 Notebook 的 OOF/LB 不能视为本地单模预期值。
3. **Missing augmentation 不完全遮蔽**：随机缺失只遮蔽 raw exact lookup 与 raw PLR，六个 derived budget token 仍由未遮蔽的原值计算。该行为继承公开实现，保留是为了不改变架构，但它不等价于完全模拟新的缺失模式。
4. **运行设备差异**：公开 Notebook 使用 Kaggle T4 AMP float16；本机 MPS 使用 float32。配置结构相同，但训练速度、数值噪声和最终随机结果不会逐位复现。
5. **OOF 双口径**：`oof_score.npy` 的跨折 raw logits 始终是主口径；另存 `oof_fold_rank.npy`，先在每个验证折内部做 percentile rank，用于诊断独立折 logit 尺度漂移，不替换主口径。

## 本机环境

- MacBook Pro，Apple M3 Max，40 核 GPU，128 GB unified memory；
- 系统 Python 3.13.9：PyTorch 2.12.1、scikit-learn 1.7.2、pandas 2.3.3、NumPy 2.3.5；
- CUDA：不可用；
- MPS：已编译且可用；
- 项目 `.venv` 当前没有 PyTorch 和 scikit-learn，不能运行本脚本；应使用当前系统 `python`，或先为 `.venv` 安装依赖。

公开代码把 `torch.autocast('cuda')` 写死，CPU/MPS 会失败。本适配版仅在 CUDA 开 AMP；MPS 使用 float32，避免当前 MPS autocast/GradScaler 差异。

因此，本机可以忠实复现模型结构、特征、优化、EMA 和五折 OOF 契约，但不能承诺与公开 T4/AMP 运行逐位相同。公开实现使用 `torch.manual_seed(fold)`；本项目把它平移为 `42 + fold`，保留逐折不同种子的设计，同时统一到 seed 42 基线。

## 完整训练结果与资源

以下均为本机 M3 Max/MPS 实测：

| 检查 | 结果 |
| --- | --- |
| 全量 train+test 只做预处理 | 5.79 秒；持久化 tensor 226.06 MiB；进程 max RSS 约 1.78 GB |
| 完整模型、batch 2,048、4,096/1,024 行 smoke | 通过；折内 1.15 秒；MPS driver allocation 约 2.32 GB |
| 完整模型、batch 2,048、65,536/16,384 行 smoke | 32 个 optimizer steps 加验证/推理共 4.18 秒；MPS driver allocation 约 4.93 GB |
| 模型规模 | 1,363,249 个参数；FP32 参数本体约 5.20 MiB |
| 完整五折 | 4,475.75 秒；每折均在 epoch 12 取得最佳 AUC，训练至 epoch 22 后早停 |

正式五折若全部跑满 32 epoch，共约 43,360 个 optimizer steps。按 64K smoke 外推，本机 MPS 预计约 75–110 分钟；早停可能缩短，首次完整运行仍应预留 2 小时。实测 MPS driver allocation 已到 4.93 GB，加上约 1.8 GB CPU 预处理峰值及运行时波动，建议至少预留 8 GB 可用统一内存；本机 128 GB 足够。CPU 可以作为兼容后备，但不建议用于正式五折。CUDA/T4 的实际时间需在 Kaggle 环境重新基准，不能由 MPS 数字直接保证。

## 命令

编译：

```bash
PYTHONPYCACHEPREFIX=/tmp/s6e8-v21-pycache \
python -m py_compile \
  kaggle_Predicting_Smartphone_Addiction/model/v21_lookup_transformer/source/v21_lookup_transformer.py
```

快速 smoke test：

```bash
python kaggle_Predicting_Smartphone_Addiction/model/v21_lookup_transformer/source/v21_lookup_transformer.py \
  --smoke-test \
  --device mps \
  --output-dir /tmp/s6e8-v21-smoke
```

用完整 128 维架构做小样本 smoke：

```bash
python kaggle_Predicting_Smartphone_Addiction/model/v21_lookup_transformer/source/v21_lookup_transformer.py \
  --smoke-test \
  --smoke-full-architecture \
  --device mps \
  --output-dir /tmp/s6e8-v21-smoke-full
```

正式五折训练：

```bash
python kaggle_Predicting_Smartphone_Addiction/model/v21_lookup_transformer/source/v21_lookup_transformer.py \
  --device mps \
  --output-dir kaggle_Predicting_Smartphone_Addiction/model/v21_lookup_transformer/full_run
```

同一命令中断后可直接重跑。只有 `run_signature.json` 完全一致时才复用已完成折；代码、输入 CSV、折分、参数、Python/依赖版本或设备任一变化都会 fail closed，拒绝混用缓存。

## 正式训练输出

- `oof_score.npy` / `test_score.npy`：EMA 模型原始 logit；
- `oof_proba.npy` / `test_proba.npy`：对应 sigmoid 概率；
- `fold_id.npy`：与官方 train 原始行序一一对应；
- `oof_fold_rank.npy`：每折内部 percentile-rank 后回填到官方行序的二级诊断 OOF；
- `submission.csv`：test logit 的全局百分位秩；
- `run_signature.json`：绑定代码、数据、折分、配置和环境的严格恢复签名；
- `fold_checkpoints/fold_XX/`：每折 valid index、valid/test score、报告、哈希和完成标记；
- `cv_results.json`：配置、折分、逐折 AUC、数据哈希、环境和耗时。

本次训练已完成上述比较并晋级为正式 V21。Public Notebook 的 `0.97041` 是三模型 blend 分数，不是本单模成绩；本地 V21 未读取或复用任何公开 OOF、test 预测或 submission。
