# V116 R13：RC8 Safe-Throughput Hierarchical MoE

## 状态

R13 已通过唯一一次授权的 killfast，但这不是金牌证据：

- `seed=7100 / router / seat=0 / idle`；
- bank `95,060 >= 60,000`；
- step144 生产资产 `22 >= 12`；
- 终局生产资产 `67 >= 58`；
- 719 calls；
- runtime、schema、语义非法动作、漏水变杂草均为 0。

后续 P2 已执行并严格失败；当前状态为
`REJECT_P2_ECONOMIC_HEALTH_NOT_GOLD`。未运行 P3、Replay 面板或金牌对战，
不得称为金牌模型，也未注册 `golden_model`。

## 自包含与原创性边界

`main.py` 是独立策略文件，`STRATEGY_PARENT = None`。运行时不导入或调用
RC8、R12、历史金牌 agent、Replay 动作、逐步坐标路线或父模型。

R13 使用五个完整生产专家：

- `wool`
- `dairy_berry`
- `tomato_market`
- `root`
- `grain_egg`

五个专家共享健康 opening：`WHEAT 8 + MELON 7 + SHEEP 4`。首次公开商店
在 step72 左右触发浅树 Router；切换只改变后续聚合目标，不废弃 opening 资产。

## 核心执行链

每步从当前 observation 重新构造：

1. 专家日级作物、动物、土地和劳动力缺口；
2. WATER、FEED、HARVEST、CARE、建设、放置和公平补种任务；
3. 基于优先级、截止时点、距离和 sticky 的全局 unit-job auction；
4. projected shed、饲料储备、融资出售、容量释放和终局清算；
5. typed action guard 后输出动作。

没有硬 tranche、持久任务票据、持久角色白名单、每次收获强制 DROP 或全局
单一 plant-water bundle。

## R13 新增安全机制

- 并行种植硬上限为 3；每批 admission 先扣除所有 open
  WATER/FEED/CARE 的最近距离与执行成本，再为每个候选扣除目标距离、PLANT
  和 WATER 工时；hour 18 后不再种植。
- non-ongoing 作物只有在下一 observation 看到产品库存增加后，才登记 bounded
  replacement continuity；总 credit 不超过 3，失败 HARVEST 不登记。
- hour 18 后若无法补种，有限作物 HARVEST 不得把生产资产压到 58 以下。
- 收获物默认批量携带；只有现金低于 750 且 carried inventory 至少 12，或进入
  终局清算时才回仓。
- BUY/HIRE/LAND 指令登记一观察边界 receipt，防止把未确认采购当成真实资产。
- WATER、FEED、CARE、PLACE、PLANT、HARVEST 和 BUILD 在输出前做类型与资源
  校验，非法动作 fail closed 为 PASS。

## 机制证据

`test_r13.py` 的 16 项静态和机制检查全部通过，覆盖：

- `strategy_parent=null`、标准库单文件、五专家和六模式；
- 健康 opening；
- 并行种植上限、维护/距离工时预算和晚间 cutoff；
- typed action guard 和 purchase receipt；
- 成功/失败 HARVEST 的 bounded continuity；
- 终局生产资产保护；
- 批量携带而非强制逐次 DROP。

逐局证据保存在 `killfast_result.json`，日级快照保存在
`daily_diagnostics.json`。本轮只运行过一次 killfast；在父流程决定下一阶段前
不得重复消费测试。

## P2 正式结论

- 6 mode × 6 seed × 双座位，`72/72` 局完成；全部 719 calls，零 ERROR/schema；
- 对 idle 为 `72/0/0`，最低终局生产资产 62；
- Router mean/CVaR25 bank 为 `76,393/55,153`，低于 `100k/80k`；
- 五个 fixed 的 mean bank 在 `64,781–84,604`，全部低于 90k。

决策为 `REJECT_P2_ECONOMIC_HEALTH`。逐局证据、冻结 manifest 和工件哈希见
`evaluation/runs/r13_p2_exposed_001/`。按顺序门停止，不运行 P3 或 Replay。
