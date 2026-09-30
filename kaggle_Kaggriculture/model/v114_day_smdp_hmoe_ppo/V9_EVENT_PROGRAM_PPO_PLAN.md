# V114 V9：Event-Program PPO 独立谱系执行计划

> **2026-08-30 Replay 最终准入口径（覆盖全文）**：只允许实际对局日期 `>=2026-08-20` 且与当前
> 线上规则配置一致的 Replay。高置信度主面板为本账号提交模型产生的线上对局，包括 CLI 增量数据与
> 本地已保存的历史提交数据；次高置信度独立确认面板为
> `kaggriculture_episodes_index/date>=2026-08-20` 的官方按日 Replay。两面板按
> `episode_id + replay_sha256` 全局去重并分别按日期切 Train/Dev/Blind。正式门控和晋级以本账号主
> 面板为主裁决，官方面板只扩充商店/需求/对手轨迹覆盖，不能凭样本量、合并指标或权重优势覆盖主
> 面板失败。身份、日期、规则配置或 SHA 不完整时 fail closed。当前所有训练、评测、下载和数据重建
> 已按用户命令停止；没有新的明确重启命令时不得执行，未经用户授权不得提交 Kaggle。

## 1. 决策

V8 在配对筛选中改善了生产路线 option2 的自身金币和灾难尾部，但两个 option 的 Starter
得分率都只有 62.5%，低于预注册 75% 生存线。V8 淘汰，不追加 seed、不调阈值。

V9 不继承 V6/V8 参数，不把历史 Agent 包装成动作源。V9 从第一性原理重建：

```text
公开 observation
  → 日界/现金/终局事件检测
  → 随机初始化五头 PPO Manager
  → production line / worker cap / cash reserve / sell style / terminal mode
  → Production Program Expert + Market Program Expert
  → 官方规则安全投影
  → 合法 action
```

`strategy_parent=null`。只有符合上述两面板准入且未进入 Blind 的 checkpoint 才可作为对手；Replay
可用于校准状态分布、事件频率和 reward 尺度，不提供在线动作回退。当前计划处于停止等待状态。

## 2. 宏动作

Manager 仅在 day boundary、带防抖的现金危机、option contract failure 和 step 671 终局边界
决策。普通 turn 保持同一计划。

五个互相独立的离散 head：

1. `production_line`：WHEAT / CARROT / TOMATO / STRAWBERRY / MELON；
2. `worker_cap`：1 / 2 / 4；
3. `cash_reserve`：0 / 500 / 1500；
4. `sell_style`：IMMEDIATE / PRICE_GATE / HOLD；
5. `terminal_mode`：CONTINUE / LIQUIDATE。

市场 STOP 不与交易动作共用一个高频 token loss。交易意图由宏 head 决定，确定性市场专家只
生成必要订单；终局 LIQUIDATE 为吸收状态。

## 3. 两个独立程序专家

### Production Program Expert

只负责单位、地块和作物闭环：成熟收获、每日浇水、清除 weed、播种、最近任务分配和确定性
路径。一次性作物成熟必须同时满足 `day-planted_day >= first_yield_day` 与 `yield_units>0`。

### Market Program Expert

只负责出售、雇工、种子采购和预算。订单顺序固定为安全出售、雇工、种子采购；总支出不得
使现金低于 reserve，出售不得超过 shed，工人数不得超过 worker cap。step 671 起禁止购买、
雇工和买地，并优先清仓。

两个 expert 无共享动作 decoder、无共享 PPO ratio、无历史 Agent fallback。

## 4. 官方时间合同

- observation step 0–718 可执行动作，step 719 为 DONE；
- 24 turn/day；商店解锁和作物/动物新产出都在日末发生，并在下一日 hour 0 可见；
- 最后 48 个可执行动作从 step 671 开始；
- 同 turn 对手动作不可见，未来商店、seed、对手 private、episode/team/opponent id 禁止入模；
- SMDP `D=gamma_day**(duration/24)`，`L=lambda_day**(duration/24)`，
  `gamma_day=0.99`，`lambda_day=0.95`。

## 5. 奖励与约束

Manager actor：终局 outcome + policy-invariant potential shaping - 约束成本。

- outcome：胜 +1、平 0、负 -1；
- potential：`D*Phi(next)-Phi(current)`，terminal potential=0；
- 约束：终局自身金币<3000、现金危机、shed overflow、生产链断裂；
- 自身金币和金币差只做独立 critic target 与晋级护栏，不用大权重污染 actor；
- “双方经济同时降低”只在同 seed/seat 配对门检查，不伪装成单局 reward。

## 6. 执行阶段

### 2026-08-30 分级门控修订（覆盖后续基础专家筛选）

V9 后续生成的完整基础专家先按 PPO V4 的 L0/L1/L2 分级门控执行：

1. L0 用 Starter/基础锚点做硬生存门；
2. L1 用行为去重并冻结 SHA 的 V1–V10 代表做硬基础能力门；
3. Stage20、V32、V37 等完整高分模型降级为 L2 影子压力测试，低胜率或全负不再单独淘汰
   尚未装配 Residual 和 Manager 的专家；
4. 只有运行错误、合同违规、无法形成生产—出售闭环、持续现金崩溃或终局系统性失败，才可依据
   L2 结果退回基础专家阶段；
5. 已经启动的强对手评测不打断，结果保留并按 L2 诊断解释；从下一道门开始不得再把它作为
   V4-2 的一票否决条件。

目标是冻结 4–6 个行为不同的 `FOUNDATION_EXPERT_CANDIDATE`；至少两个通过 L1 后即可分别
进入有界 Residual PPO。至少两个不同职责专家通过 Residual 门后，优先启动日级/事件级
Manager，不再继续无上限堆积基础专家。

### V9-0 合同闭环

- 修正官方事件语义；
- 建立 `MacroDecision`、mask、recipe、plan state、program executor 和 safety audit；
- 建立五头 JAX Manager、masked joint log-prob、duration GAE、PPO/KL 数学测试；
- 100 个官方随机状态动作 closure，零 contract violation。

### V9-1 确定性程序生存

先枚举固定宏计划，不训练。8 fresh seed × 双座位对 Starter；淘汰工具，不登记 expert。
至少两组不同 production line 的固定计划达到：score rate≥75%、P10≥3000、灾难局≤1/16、
零错误。若不足两组，修改程序编译器的通用合同后用全新 seed 重测；禁止根据某个 seed 写补丁。

### V9-2 随机 Manager 生存

随机初始化五头 Manager 在合法 mask 内随机采样，8 fresh seed × 双座位。要求零错误、零非法
宏组合、终局禁买 100%、每局高层决策约 30–60 次。随机策略不要求胜率，但灾难率若超过
50%，不得进入 PPO。

实际结果：首轮与一次仅针对通用生产承诺 mask 的复验均为 16/16 灾难局。两轮均零运行
错误、零合同违规且五头覆盖率 100%，说明失败来自“五个职责同时均匀探索会摧毁跨日经济
闭环”，而不是动作编码或模拟器异常。V9-2 淘汰；不再按已见 reward 追加规则补丁。

### V9-3a 多程序 BC 安全预热

PPO 前增加一次不计作强化学习成果的安全初始化：用 V9-1 已通过的 WHEAT、TOMATO、
STRAWBERRY、MELON 四条程序，采集 8 fresh seed × 双座位共 64 局、预计 1,792 个日级
状态—宏动作样本。Manager 仍从随机参数开始，只学习“完整经济闭环附近”的动作分布；不加载
任何历史 checkpoint。CARROT 无训练标签，并在后续 PPO 合格专家 mask 中禁用但保留输出维度。

训练/验证按 seed block 隔离。只有数据零错误、零违规，且验证集五头联合准确率≥94%、主要
职责 head 准确率达到预注册阈值，才允许在另一组 fresh seed 上做 BC 生存筛选。BC checkpoint
只能标记 `WARMSTART_NOT_PPO_NOT_GOLD`。

### V9-3 Event PPO 生存课程

每轮 64 fresh seed × 双座位，只更新 Manager；程序专家冻结。初始对手按实测难度：

- 30% 易，但 PASS≤5%；
- 60% 当前胜率 30%–70% 的可学习对手；
- 10% 困难压力，Gold 初期 5%–10%；
- V76≤10%，单一非课程锚点≤12.5%。

一个 iteration、一个预注册更新分支；actor lr `1e-5`、critic lr `3e-5`、clip 0.10、
target KL 0.01、entropy 0.01。advantage 按实测难度层标准化。

### V9-4 Gate A

开发 Screen：8 fresh seed × 双座位 × Starter/易/中三对手，共 48 局，只淘汰。

正式 Gate A：32 fresh seed × 双座位 × Starter/两个不同谱系中等对手，共 192 局；另加
16 seed × 双座位 Gold-Train 压力测试。门槛：

- 零错误、零 contract violation；
- Starter score≥75%、灾难率≤3.125%、P10≥3000；
- 两个中等对手 pooled score≥55%，95% CI 下界≥50%；
- 每个对手 P10≥3000，中等池灾难率≤5%；
- Gold 压力灾难率≤10%；
- 相对固定程序基线配对 score CI 下界>0，自身金币不退化；
- 五个 head 均有真实激活，不得退化为单一固定计划。

本节 Gate A 仅适用于已经进入 Manager PPO 的完整组合模型。对 V4-2 单个基础专家，必须使用
前述 L0/L1/L2 协议，不得提前套用本节 Gold 压力硬门。

### V9-5 动态联赛与金牌确认

Gate A 后按 PPO V4 的生存期→提升期→最终 `40/30/15/10/5` 联赛推进。Gold-Dev/Blind
保持隔离；Blind 仍执行 256/512 全新 seed 双座位确认。未经用户授权不提交 Kaggle。

## 7. 立即停止当前分支

- 宏程序依赖 V6/V8 或历史 Agent 动作；
- seed、未来状态或对手 private 入模；
- 随机策略 contract violation>0；
- 所有固定宏计划都无法稳定完成生产—出售闭环；
- PPO 连续两个 iteration 无行为变化或 fresh-seed 增益；
- 需要按已看过的 seed 增补特例才能解释失败。

## 8. V10：单谱系完整闭环基础专家

首次正式 L1 已证明三条 scratch rule program 虽稳定，但经济量级不足，不能靠有界 Residual
跨越到本地 V1–V10 基线。因此停止规则补丁，先训练两个互不共享策略参数的完整闭环专家：

- V10A：`demand-timing-preemption`，负责需求时机与出售顺序；
- V10B：`procurement-slot-ordering`，负责采购槽位、现金与扩张顺序。

两条分支只使用各自教师已执行的离线闭环轨迹；`teacher_family`/`teacher_id` 仅用于离线拆分，
不得进入模型。输入只含当前公开状态、时间和确定性的执行动作历史；参数从零初始化，不加载历史
checkpoint，线上不得调用历史 Agent。训练/验证按 seed episode 整组隔离，teacher-forced 指标只作
诊断，必须通过闭环 Screen 后才能消耗 fresh seed 进入 L0/L1。

若两条分支均失败，下一轮不得重新混合谱系；应改为 V2/V8 官方 Replay 的单谱系离线数据，或
修复因果 phase/state contract。至少两个不同职责基础专家通过 L1 后，才允许分别启动第三层
bounded Residual PPO；至少两个 Residual 专家通过后，优先启动第一层日级/事件级 Manager。

## 9. V11：V2/V8 真实 Replay 单谱系基础专家

V10A 在 L0 失败，V10B 在 L1 以 `0/0/64` 失败，故按预注册回退切换到两个互不混合的真实
Replay 谱系：V2 生存闭环与 V8 Kawa 市场槽位闭环。每个 Replay 只取该提交版本的真实座位，
严格用 observation index `t` 对齐 action index `t+1`，保留每局 719 个动作。

Router 标签只由执行前可知的 step phase 产生，不读取当前动作、教师身份、未来状态或终局分数；
市场 STOP 尾部全部设为吸收监督。两个网络均从零训练，线上不调用历史 Agent。V2/V8 同时属于
L1 对手，因此同源对局只算协议内压力，不能单独作为跨谱系能力证据；硬门仍要求四个冻结代表的
pooled 胜率、最差对手胜率、经济闭环与灾难率全部通过。

首次已暴露 seed 工程 Screen 发现 serving 仍每 step 自由选择 phase expert，与上述因果 phase
训练 contract 不一致：采购 expert 4 在终局前长期滞留，出售 expert 3 未按 step 480 启用。
该结果保留为 `FAIL_TRAIN_DEPLOY_PHASE_MISMATCH`，不得用于淘汰 V11。只允许一次非参数语义
修复：低层 foundation executor 严格执行预注册 phase schedule；随后只复用相同工程 seed，
不得调 checkpoint、阈值或 fresh gate。

## 10. V12：Event-Ledger HMoE 新谱系

V11 证明逐 turn 解码完整 market queue 即使 token 准确率约 98.5%，仍会在 719 次机会中把
低概率不可逆错误复利成经济崩溃。V12 不继承 V11 checkpoint，不再预测每 turn market STOP，
而把市场动作改成事件级、一次性、可确认的 `TransactionIntent`：

- Manager 在日界或关键事件输出企业经营 contract，而不是原子动作；
- 单位专家按 6–24 turn 任务周期输出 task/target，由确定性编译器生成一步合法动作；
- 市场专家只在日界、商店解锁、库存/现金阈值、contract failure、终局事件上输出交易意图；
- 交易账本用 `event_id + generation + operation + product` 去重，记录 commit/ack/reject/expiry，
  未授权 turn 的 market 结构性为空，同一意图不得逐 turn 重试；
- 预算、工人、土地、动物和采购上限按 day/option/season 累计，而非只检查当前动作；
- 先分别训练单位技能 PPO 与事件交易 SMDP PPO，至少两个职责专家通过后再训练 Manager；
  Residual PPO 最后只在市场事件或单位阻塞事件上做有界修正。

V12 结构门：G0 要求 100 次重复输入最多一次 commit、未授权 market turn=0、重复/未确认重试=0、
累计预算和终局采购违规=0；G1 要求单位任务完成率至少 95%、非法动作=0、阻塞率不高于 1%；
G2 要求事件交易职责完成且不可逆采购 precision 至少 95%。通过后才允许使用已暴露 seed 做整局
工程 Screen，再按既有 fresh L0/L1 硬门晋级。历史 Agent 只可作离线数据和对手，线上不得调用。
