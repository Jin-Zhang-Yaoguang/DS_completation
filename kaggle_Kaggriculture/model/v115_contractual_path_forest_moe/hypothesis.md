# V115：Contractual Path Forest Hierarchical MoE

状态：`BUILDING / PRECONSTRUCTION`

## 原创身份

- `strategy_parent=null`；冻结强度比较器为 V76，V76 只参与闭环对战，不向候选提供动作。
- 研究祖先只有失败证据：V86 证明回合级恢复会破坏生产—融资协同；V90 证明逐动作浅树模仿会闭环漂移；V97 证明滞后公开市场冲击可预测对手上一回合路径，但单生产蓝图尾部不足。
- 候选提交包不导入或调用任何历史完整 agent。离线仅嵌入四条动作字典形式的生产蓝图和一棵冻结浅树；运行时 Router、状态契约、出售控制器和安全执行器均由 V115 自己执行。

## 第一性原理机制

金牌级生产路径的劳动、融资、库存和空间动作是共同适应的时间序列，不能逐动作重组。真正允许低风险 MoE 的位置只有完整蓝图共享前缀后的同步边界。因此 V115 的主假设是：

> 首店需求决定生产价值方向，滞后公开市场冲击提供对方买卖路径信号；浅树只在共享前缀边界选择并承诺一个完整生产专家，对手预测只控制商品出售节奏。这样能保留生产协同，同时获得需求适配和对手错峰收益。

## 架构

```text
public observation
  -> StateEncoder
  -> ShopDemandRouter
       -> default complete blueprint
       -> yarn complete blueprint
       -> dairy complete blueprint
       -> smoothie complete blueprint
  -> RouteContract
       -> shared-prefix boundary
       -> one-way commitment
       -> hand-count/schema compatibility
  -> OpponentPathTree
       -> opponent_buy / neutral / opponent_sell
  -> ProductSellController
       -> preempt / same-slot / one-step-wait / due-release / terminal-release
  -> StateSafeExecutor
       -> hands alignment / market cap / non-negative quantities / deterministic fallback
  -> complete action
```

### 与既有失败方案的区别

- 不像 V86：不做回合级单位修复、不在生产中途往返切换、不重排融资链。
- 不像 V90：浅树不预测 farmer/hands 动作，只预测对手上一回合的公开市场路径。
- 不像 V97：不是单生产蓝图；首店 Router 在完整专家之间做一次有契约的承诺。
- 不像 V21/V29：V21 是固定 YARN/非 YARN 后在 step 216 切 lucaskna；V115 将“完整专家承诺”和“逐商品对手路径出售控制”放进同一候选自有状态机，并用最佳单专家门防止假 MoE。

## 合法信息边界

仅使用 `step/player`、己方 `private`、双方公开 `farms`、公开 `town.unlocked_shops`、公开 `market.inventory/prices` 和候选自己上一回合的市场订单。对手动作只可作为离线标签训练浅树；运行时不读取对手 shed、seed、携带库存、当前动作或环境 seed。

## 状态契约

1. step 0–71 固定 `default` 共享开局。
2. step 72 首店公开时，只有 YARN 分支可一次性承诺 `yarn`；否则保持共享开局。
3. step 216 非 YARN 局只允许在 `dairy` 与 `smoothie` 中承诺一次；之后整局不再切换。
4. 目标专家必须拥有 719 行完整动作、当前 hands 可对齐、当前动作 schema 合法；失败时进入候选自有 `default/dairy` 保守承诺，而不是调用历史 agent。
5. 对手预测只能改变 SELL 的时点/顺序；不得改变生产、劳动力、购买总量或生产专家身份。

## 预注册消融与单专家门

- 主消融：固定 `dairy` 完整专家，关闭首店 Router 与对手路径出售控制；保留同一个执行器。
- 单专家：`default/yarn/dairy/smoothie` 各自独立整局运行，同一个执行器且关闭动态出售控制。
- 构造前要求：静态无父代调用；全部 719 calls；零 schema 违规；至少三个生产专家真实覆盖；`BEU > 0` 且正翻转多于负翻转；full 相对消融 `MCU > 0`；PanelScore ≥60%；直接 V76 ≥50%；灾难率不高于 V76 +1pp。

## 正式晋级指标

若构造前门通过，使用冻结 `originality_panel.json`：

- Development：64 个未暴露 official source、6 个冻结对照、双座位；要求 POU>0、PanelScore≥50%、任一原创代表退化不低于 −3pp、灾难率不高于 V76 +1pp。
- Confirmation：256 个再次未暴露 official source；唯一主 KPI 为 POU。金牌门：POU≥+1pp 且 cluster bootstrap 95% CI 下界>0；PanelScore≥52% 且 CI 下界>50%；对 V76≥50%；每个原创代表≥48%；MCU≥+0.5pp 且 CI 下界>0；BEU>0；尾部、包、官方引擎与延迟门全通过。
- 任一门失败即淘汰，不读取下一阶段、不追加 seed、不写入 `golden_model.md`。

## 证伪条件

- 最佳固定专家支配 Router（`BEU<=0`）；
- 对手路径控制虽触发但 MCU≤0，或尾部风险恶化；
- 生产专家没有至少三个真实覆盖；
- 任何完整历史 agent 调用、状态契约越界、运行错误或安全违规；
- 不能达到金牌强度和置信区间硬门。

