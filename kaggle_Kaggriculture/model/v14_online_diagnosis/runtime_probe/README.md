# V14 Q2b online runtime probe

只读诊断已下载 Kaggle replay：

```bash
PYTHONPYCACHEPREFIX=/tmp/v14-runtime-probe-pycache \
PYTHONPATH=. .venv/bin/python \
  kaggle_Kaggriculture/model/v14_online_diagnosis/runtime_probe/probe_replays.py \
  --input kaggle_Kaggriculture/model/v14_online_diagnosis/raw/v14
```

关键证据：

- `candidate_action_exact`：提交 archive 能否按步复现线上动作；必须为 100%。
- `recorded_opponent_exact_a2`：用对手真实 private observation 运行 exact A2 后的动作一致率。
- `shadow_predicted_opponent_action`：V14 实际 shadow 预测的动作与对手真实动作是否一致。
- `first_prediction_mismatch` / `first_shadow_fault_step`：公开状态何时暴露差异并触发永久回退。
- `reordered_steps`：新增 SELL 队列 best-response 是否在线上真正执行。

默认模式在回放动作等于 exact parent A2 时跳过“无变化”排列的重复枚举；只要
回放动作不同于 parent，就调用 archive 原始 `_best_sell_permutation` 完整核验。
对关键单局做完全枚举可增加 `--full-search`。

汇总结论可复现生成：

```bash
PYTHONPYCACHEPREFIX=/tmp/v14-runtime-analysis-pycache \
  .venv/bin/python \
  kaggle_Kaggriculture/model/v14_online_diagnosis/runtime_probe/build_runtime_analysis.py
```

脚本拒绝显式 test 路径/标记，不运行新游戏、不提交、不修改策略。
