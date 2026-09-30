# kaggriculture-cppsim：V15 L1 fidelity pilot

日期：2026-08-26

## 结论

**模拟器 fidelity 检查通过，但禁止直接接入 V15。**

- 在官方 `kaggle-environments==1.32.7`、默认 `episodeSteps=720` 的受测范围内，公开 C++ 引擎通过 bundled tests、fresh L0 逐步验证，以及 fresh L1 官方 callback 验证。
- A2 作为复杂 archive agent，分别位于 seat 0、seat 1 时，719 个回合的完整 observation、action、reward/final bank 均与官方环境完全一致。
- `kagsim.Game` 本身并不能直接承载现有复杂 archive：至少需要 Kaggle `Agent` 生命周期适配、`dict -> Struct` callback 边界适配，以及 timeout/日志/错误状态处理。因此结果是 `FIDELITY_PASS_INTEGRATION_BLOCKED`，不是“可替换 evaluator”。

机器可读证据见 `fidelity_result.json`；fresh 官方 trace 见 `replay_starter_2026082601.txt`；上游 validator 的长度防护 wrapper 见 `strict_trace_wrapper.py`。

### Truth 数量复核与更正

早期结果中的 `truth_states: 1` **不是只有一个状态真值**，而是错误地统计了 `TRUTH` 分隔标记的数量。复核文件结构后，fresh trace 的实际内容是：

- header 声明 719 个 acting turns；
- 1,438 行双席 action；
- 1 个 `TRUTH` 分隔标记；
- **720 行状态真值，即 `truth_state_count == turns + 1`**；每行包含双方 money 和 9 个 market inventory 值。

因此 fresh trace 本身没有缺行。但上游 `tools/validate.cpp` 在读取后直接索引 `money[t]`、`inv[t]` 和最后一个 truth state，没有显式检查 marker、解析完整性或 `truth_count == turns + 1`；短 trace 可能越界，单独依赖它的 `PASS` 不足以形成 fail-closed 证据。

本项目现已增加独立 strict wrapper。所有 trace 必须先通过结构和精确长度检查，C++ validator 才会运行。另将 fresh trace 删除最后一个 truth state 构造反例：wrapper 以退出码 1 拒绝，明确报告 `truth_state_count=719 but declared_turns+1=720`。重新通过这一门槛后，才恢复“719 步逐步 exact”的结论。

## 固定输入与隔离边界

| 项目 | 固定值/处理 |
|---|---|
| 公开仓库 | `https://github.com/destbreso/kaggriculture-cppsim.git` |
| cppsim commit | `812e50c58543e436828465f89e4cf808a388874f`，工作树 clean |
| 许可证 | Apache-2.0；本地 LICENSE SHA256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` |
| 官方引擎 | `kaggle-environments==1.32.7` |
| 官方 `core.py` | SHA256 `0922c4599a1b6e0d8c3dadf06ae5297f98138d859d686f00daee6f36e6d45d0e` |
| 官方 `kaggriculture.py` | SHA256 `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e` |
| 复杂 agent | 冻结 A2 archive，SHA256 `e4c8e07fc607ccff3d9592c5774cbd866a11de096a7b12a7c3c642eda76adbf8` |
| binding 构建 | 临时目录内从固定本地 commit 独立构建，不安装到项目环境 |
| strict wrapper | SHA256 `b8beb3c5be52897add08ac16e38cfc3a4b2bdf2f6333e84e68248d35684a402b`；在 C++ semantic validator 前执行 |
| V15 隔离 | 未读取 `strategy_generator_002` 输出，未消费 fresh V15 source，未修改 evaluator、候选或模型 |

脚本对 commit、dirty 状态、官方版本和两份官方源码哈希采用 fail-closed 校验，任一漂移均退出非零。

## 验证结果

### 1. Bundled tests

| 检查 | 结果 | 覆盖 |
|---|---:|---|
| 本地 strict trace wrapper | PASS | 6/6 traces；每条 `719 turns / 1,438 action rows / 720 truth states` |
| C++ `tools/validate.cpp` | PASS | 6/6 traces；每条 719 步 money 与 market 精确一致 |
| Python L0 `tests/test_golden.py` | PASS | 6/6 traces；双方 final bank 精确一致 |
| Python L1 `tests/test_l1.py` | PASS | 6/6 traces；每条 10,066 个 observation field-block 精确一致 |

这些测试均使用临时构建出的 binding；没有复用当前环境里可能存在的其他 `kagsim` 安装。

### 2. Fresh L0：官方双席 trace

- seed：`2026082601`，双方均为官方 built-in `starter`。
- trace SHA256：`ae29ab8af635f6aa674c0b1c3bcaf3cf0f2a62ce347bc5e86a93d5bd8365044b`。
- strict wrapper：`declared_turns=719`、`truth_marker_count=1`、`truth_state_count=720`、`expected_truth_state_count=720`，PASS。
- 缺少最后一个 truth state 的反例：`truth_state_count=719`，wrapper 退出码 1，PASS（成功 fail-closed）。
- 结构门槛通过后运行 C++ validator：719 步双方 money 与 market 精确一致。
- 官方 final bank：`[3633, 3633]`；Python binding：`[3633, 3633]`。

### 3. Fresh L1：官方 agent callback

| case | seed | observations | actions | 官方 final bank | kagsim final bank | 结果 |
|---|---:|---:|---:|---:|---:|---:|
| starter vs starter | `2026082602` | 1,438 | 1,438 | `[3476, 3476]` | `[3476, 3476]` | PASS |
| A2 seat 0 vs starter | `2026082603` | 1,438 | 1,438 | `[155841, 3526]` | `[155841, 3526]` | PASS |
| starter vs A2 seat 1 | `2026082604` | 1,438 | 1,438 | `[3622, 161465]` | `[3622, 161465]` | PASS |

每个 case 均按以下顺序验证：

1. 用正式 `env.run` callback 记录 agent 实际收到的 observation 与实际返回的 action；
2. 检查 callback action 与官方 `env.steps[1:]` 存储 action 一致；
3. 用 `kagsim.Game` 同 seed 逐回合生成 observation，完整比较后再调用同一策略；
4. 逐 action 比较，最后比较 `done`、reward/final bank。

这里特意以**真实 callback observation**为基准，而不是直接把 `env.steps[t][seat].observation` 当作 callback 输入。官方 `env.run` 会通过 shared state 给回调注入 `step`；存储在 episode history 中的 seat 1 observation 缺少 `step`，不代表正式 seat 1 callback 的 `step` 恒为 0 或缺失。

## 发现的 L1 接入差异

首次将 `game.observe(seat)` 直接交给 A2 时，A2 在 turn 0 报错：

```text
AttributeError: 'dict' object has no attribute 'remainingOverageTime'
```

原因不是引擎状态漂移，而是 callback API 类型不同：

- `kagsim.Game.observe()` 返回普通 Python `dict`；
- 正式 Kaggle callback 收到 `kaggle_environments.utils.Struct`，支持 `observation.remainingOverageTime` 等属性访问。

pilot 在比较 plain JSON 值后显式调用官方 `structify`，A2 双席随即全量通过。这说明 `Game` 可作为 L1 引擎核心，但“复杂 agent 无修改直连”并不成立。

## 阻止直接接入 V15 的事项

1. `Game` 不负责加载、隔离 submission archive；本 pilot 借用了官方 `kaggle_environments.agent.Agent`。
2. 必须保留 `dict -> Struct` 的 callback 边界，否则使用属性访问的复杂 agent 会立即失败。
3. `Game` 不实现 `Agent.act` timeout、remaining-overage 扣减、stdout/stderr 捕获、`ERROR/TIMEOUT` 状态和 crash-as-loss 语义。
4. `Game(seed, steps)` 没有覆盖完整官方 configuration；生产接入必须拒绝非默认配置，或建立并核验 config fingerprint。
5. 每局必须重新建立 archive/module 状态，并复现 Kaggle 的 last-callable 与 `__raw_path__` 行为，防止跨局污染。
6. 本 pilot 没有实现 V15 sealed task/result/source-integrity 协议，也没有接触 V15 候选，因此不能据此放行 evaluator backend。

## Fail-closed 决策

当前可采用的边界是：**允许把本结果作为后续 adapter 设计的证据；不允许将 cppsim 直接替换正式 evaluator。** 后续只有在上述生命周期、配置和错误语义均有独立 parity tests，且真实官方环境继续作为 fallback/最终复核时，才应重新审查接入资格。

## 复现

从项目根目录运行：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v15_cleanroom_search/simulator_fidelity/run_fidelity_pilot.py
```

脚本会重建 binding、重新编译 C++ validator、重跑全部检查，并覆盖本目录的结果 JSON 与 fresh trace。成功时进程退出码为 0，但决策仍为 `FIDELITY_PASS_INTEGRATION_BLOCKED`；任何检查失败时退出码非 0，决策为 `BLOCK`。

单独检查 trace 结构可运行：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v15_cleanroom_search/simulator_fidelity/strict_trace_wrapper.py \
  kaggle_Kaggriculture/model/v15_cleanroom_search/simulator_fidelity/replay_starter_2026082601.txt
```
