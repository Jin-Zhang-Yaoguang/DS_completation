# V125 自然 RNG 评测器

`run_match.py` 是单进程、串行的比赛工具，不自动定义或宣布金牌晋级。默认使用完整已安装官方解释器，支持快引擎与同场逐帧保真核对。所有输出限定在本目录子目录，不读取公开 Replay、Blind 或固定商店情景。

运行时：仓库根 `.venv/bin/python`，当前 Python 3.12.13；`kaggle_environments==1.32.7`。`kagsim` 来自已有 `community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim/kagsim.cpython-312-darwin.so`。官方规则源码与此前保留的官方规则快照 SHA 相同：`bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`。

## 调用

从仓库根运行单场（例中的 seed 应按冻结协议选择；命令不是已执行结果）：

```sh
.venv/bin/python kaggle_Kaggriculture/model/v125_closed_loop_economy/evaluation/run_match.py \
  --candidate kaggle_Kaggriculture/model/v125_closed_loop_economy/main.py \
  --opponent PASS --seed 12345 --seat 0 \
  --backend official --daily --audit-actions --diagnostics --parity \
  --protocol kaggle_Kaggriculture/model/v125_closed_loop_economy/GATE_PROTOCOL.md \
  --output kaggle_Kaggriculture/model/v125_closed_loop_economy/evaluation/r0_pass_s0
```

- `--candidate` / `--opponent`：Python 入口文件或 `PASS`。支持 `agent(obs)`、`agent(obs, configuration=None)`，以及无参数 `create_agent()`。
- `--seed N --seat 0|1`：单场；`--seeds 11,23 --seats both`：同 seed 双席，全部串行。两种形式互斥。对局键包含候选/对手复合 SHA、seed、候选席位与引擎复合 SHA。
- `--backend official|fast`：默认 official。快引擎也按每步真实代理观测闭环，使用 `kagsim.Game(seed)` 的自然 RNG，不强制商店。
- `--parity`：在同一场已产生动作下驱动另一引擎，检查双方 720 个状态中的 player/day/hour/step/farms/private/market/town，任何差异中止。不会再调用第二次 agent；同场两引擎运行不视为两份独立强度证据。
- `--daily`：保存起始、每日 hour=23 和末帧状态。工人数不含主农夫；日终操作后的下一帧与 hour=23 观测并非同一个时点。
- `--audit-actions`：完整官方解释器真实调用钩子统计动作状态改变、非 PASS 无效操作、原子 PLANT 整批失败、申请订单、实际成交与采收量。快引擎模式下必须同时开启 `--parity`。每日状态附累计账本，可做相邻时点差分。
- `--diagnostics`：结束后在各自独立模块上下文中调用可选 `diagnostics()`，结果写入 `strategy_diagnostics`，仅作排错。诊断返回值应为 JSON 可序列化数据。
- `--trace`：保存本场双方已经生成的动作 JSON.gz，不包含未来情景；不自动把它登记为 Replay 面板证据。
- `--protocol FILE`：单独冻结实验协议的 SHA。`--candidate-file FILE`、`--opponent-file FILE` 可重复，用于明确加入外部配置或模型资产。

## 冻结、状态和错误契约

运行前创建 `run_manifest.json`。候选默认冻结入口目录下 Python 与二进制/权重文件，排除 evaluation、测试与运行输出目录；动态加载的外部文件和 JSON 配置必须用额外 file 参数登记。每场前后复查文件 SHA；协议与 harness 每场前复查。已有清单任何变化都会拒绝混合续跑，应为新候选 SHA 使用新实验目录。

同目录通过文件锁防止重复运行；`games.jsonl` 拒绝重复键或不在冻结任务表中的结果。已记录的错误也不会自动重跑。完全相同参数重启只续跑剩余任务；改变 seed 列表也是清单变化。

每席、每局重新创建策略模块；模块的本地依赖独立管理，随机状态按局与席位隔离。每次调用只调用代理一次，内部 `TypeError` 不会被误认为函数签名不符而重试。异常、无效动作结构或硬超时保留错误并中止该次运行，评测器不以 PASS 掩盖。代理源码自己吞掉的异常不能由外层自动还原，应由策略主动提供 diagnostics。

官方观察用框架的 `__get_shared_state` 构造，保持 `env.run` 的共享/隐藏字段语义。不能直接把 `env.state[1].observation` 当代理观察，因为第二席会省略共享 step 字段。

`agents[].latency_ms` 测量代理 callable 本身，`wrapper_inclusive_ms_total` 另计隔离与捕获开销。默认每次调用硬看门狗 10 秒，可用 `--hard-call-timeout` 调整。没有模拟 Kaggle 提交沙箱或 remainingOverageTime 预算；线上时延合规要独立验证。候选会收到引擎标准配置，但本地时延测量不等于线上时延。

## 输出

- `run_manifest.json`：候选、对手、引擎、运行时、配置、协议、seed/seat 和选项。
- `games.jsonl`：一场一行，包括双方现金、胜平负/错误、双方实际调用数、延迟、复合 SHA、可选状态与诊断。
- `summary.json`：完成数、错误数和纯胜率。纯胜率分母为预定全部局数，平局和错误不算胜；未完成/错误会明确标记。它不决定是否通过业务门槛。
- `validation_report.json`：本次基础设施验证记录与边界。

## 已做验证与限制

仅运行两场完整新对局：PASS–PASS（seed 195074021，seat 0），V22–PASS（seed 174509227，V22 seat 1）。分别终局 3000:3000、3000:140196，均 719 步，快/官每场 1440 席状态相同。另一次初始尝试在第 0 步发现第二席共享 step 缺失并拒绝执行，错误保留。

完整烟测后修正了动作审计的框架状态对象映射，以及排除模块隔离开销的时延计量。旧烟测文件的 `action_audit` 为空，不能用作动作有效性证据；其延迟也是旧 wrapper 口径。修正使用小步测试验证，未启动第三场完整比赛。当前三项测试全部通过：同模块与依赖独立、内部 TypeError 不重试、真实官方操作钩子正确记录采购与无效动作。

```sh
.venv/bin/python kaggle_Kaggriculture/model/v125_closed_loop_economy/evaluation/test_harness.py
```

这说明已核对的本地引擎轨迹相同，不证明所有未来状态都相同，也不证明与当前线上部署一致。模拟开发、独立确认、本账号线上主面板和稳定线上金牌必须分别报告。
