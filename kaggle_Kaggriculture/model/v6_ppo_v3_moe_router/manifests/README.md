# PPO v3 数据清单约定

- `split_policy.json` 定义 D2/D3 的不可变 group split。`seat` 不是 group key，因此同 seed 的双席位绝不跨分区。
- `opponent_pilot.json` 仅登记可由本地模拟器完全复现的 pilot 对手。它不等于生产联赛的 24–32 个对手池。
- 每一份生成的数据目录还必须有同目录的 `manifest.json`，其中记录输入 schema、专家 ID、文件 SHA-256、状态数和错误数。
- D4 公开 Replay 与未见策略族群只能登记在单独 holdout manifest 中；不得被 `collect_states.py` 或 `fork_counterfactuals.py` 读取。
