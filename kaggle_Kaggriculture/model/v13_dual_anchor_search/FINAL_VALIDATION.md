# V13 双锚点验证结论

## 结论

`v13c_a2_v8_no_wool_throttle` 是本轮唯一通过筛选及确认实验的候选。它继承 A2，只在 learned Router 选择 `baseline_v8` 完整专家时取消 WOOL 的固定日节流；`baseline_v5` 分支、MILK/EGG 节流、低层完整专家和其余安全守卫均保持不变。

在一次性、未暴露的 100-source 确认集上，它同时通过两个直接锚点：

| 对手 | W/T/L | 纯胜率（95% CI） | Kaggle 得分率（95% CI） | 平均 margin（95% CI） |
| --- | ---: | ---: | ---: | ---: |
| `v12_incumbent_r002` | 155/0/45 | 77.50% `[71.50%,83.00%]` | 77.50% `[71.50%,83.50%]` | +97.72 `[+81.30,+114.50]` |
| `v12a2_no_shop_gate` | 95/55/50 | 47.50% `[40.00%,55.50%]` | 61.25% `[56.00%,66.50%]` | +33.735 `[+20.75,+48.235]` |

严格结论是：C 按 Kaggle 对局得分口径显著优于 A2 与 r002。由于对 A2 有 55 场平局，不能写成“纯胜率显著超过 50%”。

## 候选与筛选结果

筛选集固定为 36 个从未用于候选设计或 QA 的 source；每名候选都在相同 source、双席位下直接对战 r002 和 A2，共 144 场。

| 候选 | 机制 | 对 r002 W/T/L、得分率 | 对 A2 W/T/L、得分率 | 决策 |
| --- | --- | --- | --- | --- |
| `v13a_a2_no_wool_throttle` | A2 的 V5/V8 两分支都取消 WOOL 节流 | 53/0/19，73.61% | 27/18/27，50.00% | 未证明优于 A2，淘汰 |
| `v13c_a2_v8_no_wool_throttle` | 仅 V8 分支取消 WOOL 节流，V5 保留 A2 | 53/0/19，73.61% | 27/26/19，55.56% | 唯一通过，进入确认实验 |
| `v13d_a2_public_winrisk_gate` | 公开金币领先时取消 A2 节流 | 27/1/44，38.19% | 15/40/17，48.61% | 双锚点失败，淘汰 |
| `v13b_a2_terminal_clearance_716` | 尝试把终局补单提前至 step 716 | 未运行 | 未运行 | 18 个既有末段状态零新增订单，打包前否决 |

C 的设计有效点不是“WOOL 永远不该节流”，而是不同生产分支需要不同市场残差：全局取消 WOOL 的 A 没有优于 A2；只在 V8 分支取消的 C 才通过。这保留了 V5 分支已经验证过的节流收益，同时修复 V8 分支的现金与库存链损失。

## 验证协议与完整性

- 数据：2026-08-18 至 2026-08-20 官方 Episodes Index 的 `train/validation` source；`test=0`。
- 暴露隔离：保守排除 Router-fit、V11 Round 1–3、V12 screen/formal/QA/消融及 V13 既有 QA source，共 652 个 source。
- screen：36 source，日期 12/12/12；每个候选 36 × 2 anchor × 2 seat = 144 场。
- confirmatory：100 source，日期 34/33/33，train/validation=88/12；唯一 finalist 运行 100 × 2 anchor × 2 seat = 400 场。
- 400/400 个任务唯一且完整，全部 `DONE/DONE`、719 次调用、零错误、零 residual fallback。
- 95% CI：按日期分层、以 source 为 cluster，10,000 次 bootstrap。
- 所有预注册门槛均通过：两个锚点得分率及 CI 下界严格高于 50%；对 A2 的最差日期 56.06%、最差席位 56.00%。

## 权威工件

- 协议封印：`protocol/protocol_seal.json`，SHA256 `010e63413f67a90203c0b153ce46fe79d3a0be7d880ec19bd9ce9300cee63613`。
- finalist 封印：`protocol/finalist_seal.json`，SHA256 `192002b85d645eee2875d7994e4497208bcce5a04e289fd4477f37308a53f742`。
- confirmatory 原始结果：`runs/confirmatory/v13c_a2_v8_no_wool_throttle/games.jsonl`，SHA256 `7a17d2effe873d8258c7e58e5e53b8250111b46c73ef10f3a3185c75893af36c`。
- confirmatory 审计：`runs/confirmatory/v13c_a2_v8_no_wool_throttle/audit.json`，SHA256 `9aae4c0d87fcd76e991e25061bde13cba8cadf076229f2ea8b6be3fdd7b081e8`。
- 独立复算：`POST_CONFIRM_REDTEAM.md`，SHA256 `9a413e581b35854d308b8f85cd9444fbe6348d7b22985f4241868e3f10962c60`；未调用既有审计器的统计函数。
- 最终候选归档：`../v13c_a2_v8_no_wool_throttle/submission.tar.gz`，293,034 bytes，SHA256 `ef279bbc937c73027ce17293aba19eeaa419563d2093880487ec9849400af0c1`。

归档已通过 Kaggle raw-loader、干净解包、双席位、720 states / 719 calls、动作 schema、非 no-op、零 stderr/fallback 和逐动作等价 QA。2026-08-24（Asia/Taipei）经用户授权提交为 Submission `55719781`；状态 `COMPLETE`，Validation Episode `97749443` 为 720 states、双席位 `DONE/DONE`、日志零 stdout/stderr，归档 SHA 未改变。
