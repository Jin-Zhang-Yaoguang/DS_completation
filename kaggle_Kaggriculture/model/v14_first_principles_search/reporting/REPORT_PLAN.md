# V14 技术报告契约

## 报告任务

- 决策：V14 是否已经获得“对 A2 纯胜率至少 65%，且对 r002 纯胜率高于 50%”的可信本地提交证据。
- 受众：技术审阅者。
- 时间与数据：2026-08-18 至 2026-08-20 的 train/validation source；test outcome 禁止读取。
- 对比基线：A2 与 r002；平局保留在纯胜率分母。
- 交付模式：单一 portable HTML，由 Data Analytics canonical artifact builder 生成。

## Required Structure 映射

| 技术报告角色 | 可见段落 |
|---|---|
| Title | `V14 Queue Best Response 证据报告` |
| Technical summary | `技术摘要` |
| Key findings with visual evidence | `65% 目前只在 oracle 与暴露开发层跨过`、纯胜率横向条形图、证据账本 |
| Scope, data, metric definitions | `口径、数据范围与证据层级` |
| Methodology | `可复现方法：同一数据管线服务 Notebook 与 HTML` |
| Model / validation details | oracle-gap、shadow、package QA、日期/席位切片 |
| Limitations, uncertainty, robustness | `当前结论的限制与稳健性检查`、哈希闭包 |
| Recommended next steps | `下一步只剩冻结验证与线上闭环` |
| Further questions | `仍会改变决策的问题` |

## Chart map

| 段落 | 问题 | family / type | 字段 | 支持的结论 | palette |
|---|---|---|---|---|---|
| 纯胜率比较 | 各证据层离 65% 有多远 | Comparison / horizontalBar | comparison, pure_win_rate；tooltip 保留 score、W/T/L、games | oracle/dev 跨线不等于 fresh confirm 跨线 | single-root preferred；单系列，无冗余 legend |

只有一个定量图，因为当前关键关系是“证据层级 × 纯胜率门槛”。W/T/L、日期/席位和 SHA-256 需要精确查询，使用表格比继续堆图更诚实。

## Evidence notes

- `report_snapshot.json` 是所有图表与数值叙述的单一派生源；其 `source_inventory` 保存每个上游输入的 SHA-256。
- fresh screen/confirm 仅从 schema 为 `kaggriculture-v14-dual-anchor-audit-1` 的现有审计文件加入；报告器不启动游戏。
- online 仅从显式保存的 V14 submission receipt 加入；报告器不调用 Kaggle API。
- `oracle_exposed`、`dev_exposed`、`fresh_screen`、`fresh_confirm`、`online` 不合并为一个“总分”。
- 缺失 fresh/online 时，portable artifact 使用 `partial` 状态和显式 access issue；不伪造占位结果。
