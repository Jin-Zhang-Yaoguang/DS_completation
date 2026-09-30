# V86：多时间尺度需求—任务 Hierarchical MoE

状态：`THINKING / PRECONSTRUCTION_ARCHITECTURE_AUDIT`

## 原创性身份

- 版本：`v86_multiscale_demand_task_moe`
- `strategy_parent=null`
- 冻结强度比较器：`v76_adjacent_safe_buy_lead`
- 谱系槽位：`J_INDEPENDENT_HIERARCHICAL_MOE_ARCHITECTURE`
- 预注册原创性：`NEW_LINEAGE_PENDING_AUDIT`
- 不允许调用、加载或委托任何历史完整 agent。

V86 不是“V76 先出动作，再做修改”。它自己从公开 observation 生成完整的 farmer、hands 和 market 动作。历史 Replay 路线只被压缩为三个**生产蓝图专家**的目标动作序列；它们不携带历史 agent 的 Router、状态、市场后处理器或 fallback。原创算法层是多时间尺度 Router、任务状态契约、事件级恢复专家、商品级市场专家和安全执行器。

## 第一性原理假设

V76 的优势来自一条极强但固定的完整栈；它不等于“唯一正确生产制度”。比赛的真实决策可拆成三个时间尺度：

1. 赛季级：公开商店需求决定羊毛、乳品/瓜果、综合供给三种生产制度的相对价值；
2. 事件级：杂草、拒单、库存断供、作业过期会使静态路线偏离，必须由状态兼容的恢复专家闭环纠偏；
3. 回合级：SELL、融资购买、肥料副产品和对手公开供给共同决定商品级市场动作。

若这三层由同一个候选自有 Router 协调，而不是把局部补丁叠在历史 agent 上，则能够在保持强生产蓝图的同时减少静态路线失配，并通过肥料和需求时机产生真实胜负翻转。

## 架构与调用图

```text
public observation
  -> StateEncoder
  -> RegimeRouter
       -> WoolBlueprintExpert
       -> DairyFruitBlueprintExpert
       -> SmoothieBlueprintExpert
  -> EventRouter
       -> OnPlanTaskExpert
       -> WeedRecoveryExpert
       -> InventoryRecoveryExpert
       -> FertilizerByproductExpert
  -> ProductMarketRouter
       -> FinancingExpert
       -> DemandTimingExpert
       -> RivalSupplyExpert
       -> TerminalConversionExpert
  -> CandidateSafeExecutor
  -> complete action
```

源码和运行时都不得出现 `historical_agent(obs)`、`v76.agent(obs)` 或“parent action”。每回合只执行一个候选控制器。

## 三个生产专家与状态契约

| 专家 | 公开触发 | 生产重点 | 合法切换点 |
|---|---|---|---|
| `wool` | 首店为 `YARN_STORE` | 羊、WHEAT、WOOL | step 72 后；目标前缀在首次差异前一致 |
| `dairy_fruit` | 非 YARN、非 Smoothie | 羊/乳品/瓜果综合现金流 | step 216 后；沿共同 opening 进入 |
| `smoothie` | 已公开 `SMOOTHIE_SHOP` | MILK/STRAWBERRY 相关供给 | step 260 后；与 dairy 前缀到 step 259 一致 |

Router 只能使用已公开商店、step、己方公开/私有合法状态和对手公开 farm。切换要求：历史目标前缀兼容、当前单位数量可对齐、未完成恢复事务为空；否则留在当前专家。

## 事件级专家

- `on_plan`：执行当前蓝图在本回合的生产动作。
- `weed_recovery`：若蓝图在 WEED 上要求 PLANT/BUILD，先 DIG，并把原任务放入有期限的恢复队列。
- `inventory_recovery`：对并发 PICKUP 做共享库存原子上限；对 FEED/PLACE 缺货只允许进入取货—返回的显式事务。
- `fertilizer_byproduct`：只接管当前由候选自己判定为安全 PASS、且脚下肥料可收集的单位；它不是历史 agent PASS 后处理。

## 商品级市场层

市场层从生产专家的计划订单开始，但由候选自己的商品 Router 负责：

- SELL 先于依赖现金的购买，维持同回合融资链；
- 已公开需求窗口前可延迟部分非终局出售；
- 对手公开供给接近时可在合法库存范围内抢先出售，并在未来计划中偿还；
- 合并同商品重复购买，并只跨越不会依赖先行现金的固定安全支出；
- step 715–718 对 projected shed 做商品级终局兑现。

## 主机制消融

`ablation_main.py` 保留同一安全执行器和单一 `dairy_fruit` 蓝图，但移除：

1. 商店需求生产 Router；
2. `wool` 与 `smoothie` 专家；
3. 事件级恢复 Router；
4. 商品级动态专家，仅保留原蓝图 market 订单。

因此 MCU 衡量的是完整 Hierarchical MoE 架构，而不是“恢复成 V76”。

## 构造前硬门

在消耗任何新官方 Replay 前，必须用 synthetic seeds 和已冻结对手完成：

1. 静态扫描：无完整历史 agent import/load/call；
2. 运行时：每回合只有 V86 controller，719/719 调用；
3. 三个生产专家各至少在 8 个 synthetic game 中被选中；
4. 生产、劳动力、市场三个动作域均由 V86 自主生成；
5. full 相对 ablation 有非零奖励变化，正翻转多于负翻转；
6. full 相对 V76 的 synthetic panel 不出现灾难性崩溃；
7. P99 <250ms 且不超过 V76 的 1.25 倍。

未通过即 `REJECT_PRECONSTRUCTION`，不消费 Development Replay。

## 正式评测冻结项

只有构造前硬门通过后才冻结唯一 submission archive，并按 `loop_model.md`：

- Development：64 个全新 official source，六对手、候选/比较器、双座位，共 1,536 局；
- Confirmation：Development 通过后一次性抽 256 个全新 source，共 6,144 局；
- 主指标 POU，原创性指标 MCU；
- 正式门槛、bootstrap、尾部风险和官方 Python parity 完全沿用手册；
- 未获用户授权，不提交 Kaggle。

## 明确证伪条件

- 三专家中任一从未真实触发；
- full 的有效增益全部来自肥料收集，而生产 Router/恢复专家 MCU 小于 0.5pp；
- standalone 控制器明显弱于 V76，无法达到 Development 门；
- route payload 实际包含完整历史 agent 代码或运行时委托；
- 任一安全、确定性、调用计数、延迟或 package parity 门失败。
