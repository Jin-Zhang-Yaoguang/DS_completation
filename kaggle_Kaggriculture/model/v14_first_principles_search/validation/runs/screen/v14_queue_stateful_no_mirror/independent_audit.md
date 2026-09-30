# V14 fresh screen 独立复算

结论：**GO_TO_CONFIRMATORY**。这是进入 confirmatory 的屏幕门结论，不等同于最终提交结论。

## 独立指标

| 对手 | W/T/L | 纯胜率（wins/all） | 比赛计分率 | 平均 margin | 独立 95% CI（纯胜率） |
|---|---:|---:|---:|---:|---:|
| v12_incumbent_r002 | 61/0/11 | 84.7222% | 84.7222% | +260.9722 | [75.0000%, 93.0556%] |
| v12a2_no_shop_gate | 59/8/5 | 81.9444% | 87.5000% | +789.3194 | [70.8333%, 93.0556%] |

纯胜率严格按 `wins / all games`；平局留在分母且不算胜。Bootstrap 为 10,000 次日期分层 source-cluster 重采样，每个 source 保留双席；本复算使用独立 SHA256 派生 seed，所以 CI 不要求与落盘审计逐点相同。

## 完整性

- 逐行任务：144/144；唯一 task_id 144；缺失 0；验证错误 0。
- 运行 fingerprint：`d0dfcd0478e8525c4f96cdef6c1e8d1e89573c1430cf624804aa6445cf671939`，与 manifest/consume lock/144 行完全一致。
- 状态：{'DONE/DONE': 144}；所有 schema、engine、双席、DONE、error、reward、margin、score 均由逐行原始字段重算。
- Panel：`35b729747ef27028280322835117d29bac246429419ae3a7bf33dcdd4a98917f`；records `325ce64af236f4d7c8c56e28a36cbcc30f3e55771eeed12027d6ac773b6aab4f`。
- Registry：文件 `e5459c0b892696c031d510e8fa6cbdce9de4f741f54a6577969c85c45f26f789`；reachable-code `1288b538190d0e4ac3f928d29f99d896568336873cf0f2b87f91fad8fbbda7bd`。
- Archive v12_incumbent_r002：`6ff786cbba1a6440f844f9c77da934f6dd10b55e43f57b2bd852753cd21ae136`；tar 成员、clean closure 与登记哈希均通过。
- Archive v12a2_no_shop_gate：`e4c8e07fc607ccff3d9592c5774cbd866a11de096a7b12a7c3c642eda76adbf8`；tar 成员、clean closure 与登记哈希均通过。
- Archive v14_queue_stateful_no_mirror：`d7d2e8210041d695a10ddc7797efbfd5c4ca3a0f8c33c70e0fd5d597fd4d4f9f`；tar 成员、clean closure 与登记哈希均通过。

## 日期与席位

### v12_incumbent_r002

| 分层 | games | W/T/L | pure | score | mean margin |
|---|---:|---:|---:|---:|---:|
| 日期 2026-08-18 | 24 | 21/0/3 | 87.5000% | 87.5000% | +247.4167 |
| 日期 2026-08-19 | 24 | 21/0/3 | 87.5000% | 87.5000% | +252.4167 |
| 日期 2026-08-20 | 24 | 19/0/5 | 79.1667% | 79.1667% | +283.0833 |
| 候选席位 0 | 36 | 33/0/3 | 91.6667% | 91.6667% | +436.2778 |
| 候选席位 1 | 36 | 28/0/8 | 77.7778% | 77.7778% | +85.6667 |

### v12a2_no_shop_gate

| 分层 | games | W/T/L | pure | score | mean margin |
|---|---:|---:|---:|---:|---:|
| 日期 2026-08-18 | 24 | 19/4/1 | 79.1667% | 87.5000% | +533.4167 |
| 日期 2026-08-19 | 24 | 20/2/2 | 83.3333% | 87.5000% | +376.2500 |
| 日期 2026-08-20 | 24 | 20/2/2 | 83.3333% | 87.5000% | +1458.2917 |
| 候选席位 0 | 36 | 32/4/0 | 88.8889% | 94.4444% | +966.0278 |
| 候选席位 1 | 36 | 27/4/5 | 75.0000% | 80.5556% | +612.6111 |

## 落盘审计与 recovery

- 落盘 audit 的总体、日期、席位点估计与独立复算：`True`；gate 一致：`True`。
- Recovery provenance 登记的全部 immutable input hash 与当前文件：`True`；audit 输出及 recovery 脚本 hash：`True`。
- 本次独立复算前后输入 hash 不变：`True`。
- 证据边界：静态脚本只调用原审计并写 audit/provenance，未发现环境或 run_tasks 调用；但历史进程是否绝对未启动游戏不能仅靠静态文件反证。现有 games hash、consume lock、任务闭包和 recovery 前后 hash 链均一致。

## Gate

- 完整性：`True`
- A2 纯胜率 >= 65%：`True`
- r002 纯胜率 > 50%：`True`

因此给出 **GO**：可按既定单次协议进入 confirmatory；不能据此跳过 confirmatory 或直接宣称达到最终 65% 目标。
