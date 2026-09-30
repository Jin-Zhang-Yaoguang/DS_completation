# R8 已存轨迹主机制审计

仅核查新开发块中已经完成的 24 条 R7/R8 × PASS/V120 轨迹。所有结果来自同一批已保存动作，没有新增候选调用或独立比赛。官方解释器只重放保存动作以重建可核对物量账本；一次重放计 719 次官方状态转移。

聚合脚本与配置在读取 1950905801..5803 的新块结果前冻结，指纹见 `aggregation_freeze.json`。此前只读过旧 1950905001 的开放诊断；父任务已经告知完整 36 局的强度失败，未据此修改主机制阈值。`contract_validation.json` 的 11 条检查全部是合成算式反例，独立比赛数为 0。

## 固定口径

- 首次自产非麦实际 SELL 的 elapsed = 决策步 + 1。没有事件计 719，六局完整保留；实际第 718 步售出同样为 719，但另以事件标记区分。
- 每个对手分别比较 R7/R8 的六局 T = elapsed 总和 / 6。必须至少提前 20%，并且每个座位的三局平均不得更晚。程序以 `5 * R8 总和 <= 4 * R7 总和` 判定 20% 边界。
- 任何输入来源为 PENDING，则该对手组不能通过，不能删局或以 0 替代。
- 来源由已冻结首卖工具 v3 核查：非麦初始与外购必须全部为零，官方采收、消耗、溢出和实际卖出逐物量闭合。首卖可能只是少量肥料，它是时钟指标，不代表规模、净利润或竞争优势。
- 动物等待、照护、仓容与末日兑现均为伴随诊断。逐笔采购目标与确认链缺失仍 PENDING。正式 G1/G2/金牌没有在本报告裁决；完整 36 局强度由另一冻结工具独立裁决。

## 运行方式

使用项目 `.venv/bin/python -B` 顺序运行本目录 `replay_saved_batch.py`，为四个完整 run 分别传 `--run-dir`，输出到 `all_24_saved_traces/`。它只调用冻结 `analyze_trace.py`，不会调用候选。

根据 batch manifest 的 jobs，将每个 output 传为 `--audit-dir`，运行冻结 `summarize_first_produced_sale_v3.py` 和 `summarize_investment_latency.py`，分别输出 `all_24_first_sale/`、`all_24_latency/`。

正式使用修正版 `assess_first_sale_mechanism_v2.py --batch-dir all_24_saved_traces --first-sale-dir all_24_first_sale --latency-dir all_24_latency --output assessment_v2`。三个输入均为已保存文件；此聚合阶段引擎调用、候选调用、新比赛均为 0。

冻结文件一经使用不覆盖。需要修复时派生新版本，并保留失败证据及新旧 SHA；不能更改固定阈值。

初版聚合器和 assessment/ 已保留为伴随投放数重复合并的错误证据。修正版与原版逐局数据/首卖主指标完全一致，正式报告见 REPORT.md；修复详情见 companion_v1_failure.json。
