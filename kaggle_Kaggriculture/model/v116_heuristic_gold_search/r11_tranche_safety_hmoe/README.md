# R11 Tranche-Safety HMoE

## 结论

`NOT_GOLD_KILLFAST_REJECT`。

R11 修复了 R10 已确认的票据安全问题，机制回归全部通过；但唯一获准的
`seed=7100 / router / seat0 / idle / 719 calls` kill-fast 没有达到经济和资产门槛，
因此停止本轮，不运行 P2、P3 或 Replay，也不登记 `golden_model.md`。

## 自包含边界

- `strategy_parent = null`；
- 运行时仅 Python 标准库；
- 不导入 R10、历史 agent 或 Replay；
- 保留 `build_executor(params=None, mode=...)`；
- 四种 mode：`router`、`fixed_root_exchange`、`fixed_dairy_berry`、
  `fixed_fiber_grain`。

## 实现的安全改动

1. 跨日取消 daily ticket；WATER 仅允许 PLANT，FEED/CARE 仅允许存活动物；
   actor 每步重新验证 owner、日期、tile 类型和携带资源。
2. expert、phase、land 或 tranche 改变时重建 layout lease，并取消不再属于当前
   lease 的 PLANT/BUILD/PLACE 票据。
3. HARVEST 不再因 tile 消失而完成：必须观察到 carried inventory 增量，随后
   DROP；日界自动入仓作为确定性的 overnight DROP。无增量记
   `FAILED_ASSET_LOSS`。
4. Router 在首次商店提交后按 commit-relative day 进入 phase 0/1/2。
5. service-cap 从 12 个槽开始，每两个提交后日增加 2；WAIT_RESOURCE 只能触发
   对应资源采购，不能触发 HIRE/BUY_LAND。
6. 截止期将被突破时，priority-0 的浇水/喂食任务可安全抢占普通生产任务。

## 机制回归

`test_r11.py` 的 12 项检查全部通过：4 项静态边界和 8 项机制不变量。覆盖
daily rollover、类型约束、layout orphan、HARVEST 失败/交付、Router 相对阶段、
资源采购门、维护抢占。

## Kill-fast 真实结果

| 指标 | 门槛 | 实际 | 结果 |
| --- | ---: | ---: | --- |
| agent calls | 719 | 719 | 通过 |
| 运行错误 | 0 | 0 | 通过 |
| step 144 生产资产 | >=12 | 5 | 失败 |
| 漏水转 weed | 0 | 23 | 失败 |
| 终局 bank | >=60,000 | 14,288 | 失败 |
| 终局生产资产 | >=30 | 12 | 失败 |
| 无效 WATER/FEED/PLACE | 0 | 0 | 通过 |
| 终局 live orphan/expired | 0/0 | 0/0 | 通过 |

真实逐日证据显示：bootstrap 到 day 3 仅建立 11 个资产；提交 dairy_berry 后
day 6 降至 5。规划 service-cap 最终增至 36，但实际终局只有 12 个资产。
全局累计方向移动 3,013 次、票据分配 749 次、安全抢占 28 次，仍发生 23 个
“前一日未浇水的 plant 在日界变 weed”，说明下一版需要解决“晚种后无当日浇水
窗口”和空间批处理/路线压缩，而不是继续放大 tranche。

## 证据文件

- `main.py`：冻结候选源码；
- `test_r11.py` / `mechanism_results.json`：机制回归及结果；
- `evaluate_killfast.py` / `killfast_result.json`：唯一一次 kill-fast；
- `daily_diagnostics.json`：day 0–29 的逐日资产、现金、weed、任务状态与诊断。

本次结果只是一局对 idle 的淘汰门证据，不是对金牌模型的胜率证据。
