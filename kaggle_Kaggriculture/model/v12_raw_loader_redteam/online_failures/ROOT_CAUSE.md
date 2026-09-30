# V12 线上失败根因（raw-loader 红队）

时间：2026-08-23（Asia/Taipei）

## 55713093 / A2

- 提交状态为 `COMPLETE`，验证局为 `97566762`，但最终公开分只有 `600.0`。
- Replay 恰好 720 个状态，双方终局奖励均为 `3000.0`；所有动作都等价于不操作。
- 最后一步的原始 action 是 `model_status()` 返回的诊断字典，而不是策略 action：
  `{"kind":"v12a2_no_shop_gate","model_id":"v12a2_no_shop_gate","status":"not_started",...}`。
- 根因：`kaggle_environments.agent.get_last_callable()` 执行 `main.py` 后选择执行环境中“最后定义的 callable”。提交包的 `main.py` 在 `agent()` 之后定义 `model_status()`，因此线上实际调用的是 `model_status`。它接受零参数，loader 会按其 `co_argcount=0` 调用，返回的诊断字典未形成合法农场指令，环境退化为全局 no-op。
- 证据：`episode-97566762-replay.json`、双席位 agent logs，以及提交目录 `v12a2_no_shop_gate/main.py` 的函数顺序。

## 55713101 / r002 incumbent

- 提交状态为 `ERROR`，验证局为 `97566763`，两边都在第一个 agent 调用报错，Replay 仅 2 个状态。
- 双席位日志完全一致：
  `NameError: name '__file__' is not defined`，位置是线上 `/kaggle_simulations/agent/main.py` 第 19 行 `HERE = Path(__file__).resolve().parent`。
- 根因：Kaggle raw Python loader 使用 `compile(raw, path, "exec")` 后在空字典 `env={}` 中执行；`path` 只用于 traceback/`sys.path`，不会注入 `__file__`。因此顶层读取 `__file__` 必然失败。
- 证据：`episode-97566763-agent-{0,1}-logs.json`、`episode-97566763-replay.json`。

## 修复包必须满足的 fail-closed 条件

1. 用真实 `get_last_callable(read_file(main.py), path=clean/main.py)` 加载，返回对象必须明确是 `agent`，不能是诊断/helper callable。
2. 顶层和首调用路径不依赖 loader 未注入的 `__file__`；通过 `configuration["__raw_path__"]` 或显式安全路径解析定位 bundle。
3. 第一条及整局 raw action 必须符合 `farmer/hands/market` schema，且至少有非 no-op 动作。
4. 干净解包、无项目源码 import、双席位 720 状态/719 次调用、`DONE/DONE`、零 stderr。
5. 同 seed/席位下，clean raw-loader 与源码策略的逐步动作及终局奖励完全等价。

