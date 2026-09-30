# R10 P2/P3 评测框架

该目录只评测 R10 候选，不读取 Replay、不复制历史动作，也不改写候选或历史 gold 模型。
每局都通过 `build_executor(params=None, mode=...)` 创建全新候选实例，通过现有
`agent_factory` 创建全新 gold 对手实例，在 `kagsim 1.32.7` 中进行双座位实时对局。

## 固定面板

- P2：`7100–7103, 1641819451, 915926955`，4 个 mode，idle，双座位，共 48 局；
- P3：`1641819451, 915926955`，4 个 mode，18 个 gold，双座位，共 288 局；
- 最多 8 workers；任何异常都按非胜处理；输出逐局 719 calls、候选/对手 action schema、
  银行、margin、末局实际生产资产和候选 diagnostics。

P3 的 outcome-oracle 只在三个固定专家中，对同一 `opponent + seed + seat` 取“至少一个专家
获胜”；它是专家集合诊断，不是可部署模型成绩。对手 schema 仅诊断历史兼容性，不污染候选
机械门；候选 schema、ERROR 或非 719 calls 会直接使门槛失败。

## 运行

```bash
.venv/bin/python \
  kaggle_Kaggriculture/model/v116_heuristic_gold_search/r10_enterprise_queue_hmoe/evaluation/evaluate.py \
  --panel p2 \
  --workers 8 \
  --output-dir /absolute/path/to/new_run
```

将 `--panel p2` 改成 `p3` 可运行 P3。先用 `--dry-run` 检查候选、engine、gold 路径、hash、
任务数与 mode 接口；正式运行拒绝覆盖已存在目录。每次运行生成：

- `run_manifest.json`：候选、评测器、engine、对手 hash 与完整任务口径；
- `games.jsonl`：逐局原始证据；
- `summary.json`：整体、mode、座位、对手及 P3 专项统计；
- `decision.json`：逐项门槛和下一步，P2/P3 通过也明确不是最终金牌证据。

只有 P2、P3 均通过后，才能由独立 Replay 协议打开 Replay development；本框架永不授权
`golden_model.md` 注册。
