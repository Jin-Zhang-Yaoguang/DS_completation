# 2026-09-15 榜首 Majkel1337 全量公开 replay 审计

主报告：[REPORT.md](REPORT.md)。本地交互报告：[http://127.0.0.1:8876](http://127.0.0.1:8876)。

- 冻结快照：2026-09-15T11:12:52Z。
- 活跃提交 56156662：381 局已完成 PUBLIC；56216119：193 局；各自排除 1 个 Validation。
- 历史同名每日面板：去重后 246 局，提交 ID 未核实。
- 合计 820 局；574 局活跃公开清单覆盖 100%；不能声称穷尽队伍所有退役、改名、未公开的历史提交。

## 文件

- `raw/snapshot.json`：原始 CLI 快照；`raw/inventory.json`：采集来源与路径。
- `replays/`：本轮补下载的 362 局；其他 458 局引用原每日分区文件，不重复复制。
- **`metrics_v2/`**：恢复背包物品插入顺序后的正式逐局统计；包含实际成交量价、每日资产、行动指纹等。
- `metrics/`：初版核算留档，4 处 DROP 满仓序列化差异，**不要用于最终结论**。
- `summary.json`：正式分组统计；`deep_analysis.json`：开局反馈与同局归因。
- `episode_table.json`：820 局、路径、SHA；`case_decomposition.json`：案例量价分解。
- `validation.json`、`delivery_validation.json`：核验记录。
- `raw/previous_replay_report_20260905.md`：旧报告修改前备份；`old_report_update.json`：原文与追加后哈希。
- `report_app/`：交互报告源码、审查数据与 dist 构建。

## 复现与重新采集

在本目录依次运行 `python analyze.py`、`python summarize.py`、`python deepen.py`、`python build_report.py`。正式核算使用现有官方 1.32.7 纯动作/市场函数，每步从真实前帧开始；不运行 agent、不生成新比赛。

`collect.py` 和 `download.py` 用于采集。若要建立新时点，应复制到新的日期目录，保留本轮冻结清单、结果与哈希，避免覆盖历史证据。交互报告构建遵循 `report_app/AGENTS.md`；本地预览服务只绑定 127.0.0.1，服务整个 `report_app/dist` 目录。
