# RC9 对手路径配对诊断

## 结论

这是只读机制诊断，不是晋级、金牌或新模型结果。

在 R3 已暴露的两个 seed、双座位上，p0064 对 idle 与 V21 的表现出现明显
结构性分叉：

- idle：平均候选 bank `80,887.25`，平均 margin `+77,887.25`；
- V21：平均候选 bank `49,107.50`，平均 margin `-79,936.25`；
- 同 seed/seat 的 `V21 - idle`：候选 bank 平均 `-31,779.75`，margin 平均
  `-157,823.50`。

## 关键机制证据

对手不仅改变价格，还改变候选第一次看到的 shop，从而直接改变 Router 路径：

| Seed | Idle 路径 | V21 路径 |
| --- | --- | --- |
| 1641819451 | ICE_CREAM → dairy_berry | FARMERS_MARKET → tomato_market |
| 915926955 | PIZZA → tomato_market | BAKERY → grain_egg |

因此这里的差值不是同一专家上的纯市场扰动，而是“公开世界状态 → 首店 → 专家 →
生产路线”的闭环漂移。这正是后续 opponent-path predictor 应优先建模的变量。

平均候选 money 差在前 10 天接近零；day 11 开始持续转负，day 19 为
`-10,120.75`，day 23 为 `-19,925`，最终为 `-31,779.75`。累计动作差还显示：

- V21 路径下多执行 55 次 PLANT、32 次 HARVEST、127 次 WATER；
- 多下 66 次 WHEAT 种子单，并多卖 178 单位 WHEAT；
- 少卖 186 单位 MILK，少卖 75 单位 FERTILIZER；
- 两个 seed 的最终作物/动物组成均随专家切换显著改变。

这说明损失不是单个出售阈值造成；首店路由改变、共享市场库存/价格冲击以及由此
引发的劳工任务路径变化同时发生。

## 数据完整性

- 8/8 局完成，每局 719 calls，无 ERROR；
- 候选 action schema 违规为 0；
- V21 严格 schema 审计记录 8 次违规：每局 step 25 的
  `BUY_SEED WHEAT 0` 和 step 137 的 `BUY_SEED STRAWBERRY 0`。引擎接受了这些
  零数量单，但不能报告为 schema 零错；
- 每局包含 30 个日界快照：候选 money、双方公开 crops/animals/land/hands、
  market inventory/prices、own shed/seeds、候选完整 market orders 与 unit
  action counts；
- `paired_v21_minus_idle` 保存四个同 seed/seat 的逐日完整配对差；
- 未读取或使用 Development/Confirmation seed。

完整证据见 `diagnosis_results.json`。
