# V113 PPO 一夜训练深度复盘

日期：2026-08-30  
状态：`STOPPED_BY_USER / NOT_GOLD`  
Kaggle：未打包、未提交  
当前最强已验证 checkpoint：Stage20 `unit3_starterppo_lr1e6/ppo_checkpoint.msgpack`

## 一、结论先行

一夜训练有明显的研究和工程进展，但没有形成模型强度进展，更没有得到金牌模型。

- 已经建立可复现的混合对手联赛、行为家族隔离、fresh-seed 双座位门控、逐参数冻结审计和
  Gold-Train/Dev/Blind 隔离。
- 找到了两个真实信号：市场状态记忆能改善混合池 screen；多教师 MoE 的逐 turn Router
  对基础经济闭环确实优于单专家。
- 但 Stage27–37 没有任何 checkpoint 替代 Stage20 incumbent；Stage31 是唯一进入
  Gold-Dev 的新 PPO expert，最终仍对 V54 0/128；Stage35/36 多教师路线也分别败在混合
  screen 和 Starter 基础门。
- Stage37 的训练分布已经失效：128 局 on-policy rollout 为 4胜6平118负，score rate
  5.46875%，平均自身金币 26.40，平均金币差 −115,065.31，128/128 局都低于 3,000
  金币灾难线。虽然 PPO 更新的 KL 很小，但它是在全面坍塌的轨迹上学习，不能解释为进步。

所以答案是：训练流程比昨晚更可靠了，但策略能力没有跨过金牌门，当前主训练逻辑需要重构。

## 二、一夜训练到底取得了什么

### 2.1 策略结果

| 阶段 | 主要尝试 | 最好结果 | 最终结论 |
|---|---|---|---|
| Stage27 | shared-worker 混合池 PPO | 分差改善，但 pooled score 下降 | `REJECT_SCREEN` |
| Stage28 | 只训练 32 维历史残差 | screen 自身金币 CI 为正 | V54 0/128，`REJECT_GOLD_DEV` |
| Stage29 | 现金安全 market expert | 灾难率下降或 score 上升不能同时成立 | `REJECT_SCREEN` |
| Stage30 | 共享市场冲击 expert | `lr=1e-5` 自身金币 CI 为正 | pooled score 退化，`REJECT_SCREEN` |
| Stage31 | 36 维市场状态记忆 | screen 8/0/24 → 12/0/20，自身金币 +6,667，CI 下界为正 | V54 仍 0/128，`REJECT_GOLD_DEV` |
| Stage32 | unit+market 终局协调 expert | 两分支都降低自身金币 | `REJECT_SCREEN` |
| Stage33/34 | 最后 48 turn 的终局 option | 修正部署后最好 9/0/23，经济 CI 跨 0 | `REJECT_SCREEN` |
| Stage35 | 三行为家族均衡的 full-action BC HMoE | Starter 16/0/0；单专家只有 8/0/8 | 混合池金币显著退化、Gold 0/12，`REJECT_SCREEN` |
| Stage36 | candidate-state 多教师 DAgger | 69,024 行合并训练 | Starter 从 16/0/0 退化到 11/0/5，`REJECT_BASIC_GATE` |
| Stage37 | 全 expert projection 混合池 PPO | 完成 128 局和一次严格受限更新 | rollout 全面坍塌；用户在 screen 前停止 |

最值得保留的能力信号是 Stage31 和 Stage35：

1. Stage31 证明“上一时点逐商品库存/价格变化”是有用状态，而不是无效特征；只是单独调整
   market expert 不足以击败完整金牌策略。
2. Stage35 证明多个职责 expert 的切换对基础闭环有贡献，因为同 checkpoint 的单专家消融
   从 16/0/0 降到 8/0/8。但这只是 MoE 机制激活，不是金牌强度。

### 2.2 工程和研究方法上的进展

这些成果是有效的，建议保留：

- 官方引擎已在 100 个 Replay、72,000 个状态上零差异；动作 codec 覆盖和可执行闭包均为
  100%。
- 混合池固定为 Gold/PPO History/Self-play/Exploiter/Anchor=`40/30/15/10/5`；每轮
  64 fresh seed、双座位，同 seed 两个座位面对同一对手。
- Stage37 实际配额为 `52/38/18/14/6`，V76 为 12/128=9.375%，没有再次变成只会针对
  V76 的训练。
- Gold 按行为谱系拆成 Train/Dev/Blind；V54 只在 Dev 使用，V66 Blind 未被消费。
- 所有关键数据和 checkpoint 固定 SHA；失败 checkpoint 只允许作为训练对手，不冒充冠军。
- 评测使用 same-seed/same-seat 配对增益和 seed-block bootstrap，同时看 pooled、最差金牌、
  自身金币、金币差和灾难率，避免靠压低双方经济制造“进步”。
- Stage37 叶子级参数审计确认只修改 unit/market expert projection 的 kernel+bias 共 4 个
  参数叶，其余 70 个参数叶逐位不变。

### 2.3 没有取得的进展

- 没有新 incumbent；最佳已验证 checkpoint 仍是 Stage20。
- 没有任何新 expert 同时通过 mixed screen 与 Gold-Dev。
- 没有至少两个合格 PPO expert，因此没有资格训练 option-level Router。
- 没有访问 Gold-Blind，没有最终 Confirmation，也没有金牌登记。
- Stage37 的 11401000 mixed screen 没有运行；被中断的 Starter 诊断没有最终 JSON，不能
  作为正式结论。

## 三、当前训练是逐 step 还是逐天

答案：当前低层 PPO 是逐 step/turn 训练，不是逐天训练。

Kaggriculture 的官方配置是：

- `episodeSteps=720`；实际有 719 次动作决策。
- `turnsPerDay=24`；即 24 个 step/turn 才是一个游戏日，整局约 30 天。
- 每个 turn，Actor 一次生成当前 farmer、所有 hands 和最多 10 条 market order。
- SequenceAction 模型在同一个 turn 内先自回归生成最多 16 个单位槽，再生成 10 个市场槽；
  环境随后一次性提交这个联合动作。
- rollout 每个 turn 保存一条 PPO transition，并在每个 turn 计算 potential 差；整局结束时
  才把终局金币/金币差目标加入最后一条 transition。
- 当前 SequenceAction Router 使用 `router_period=1`，也就是每个 turn 都可以重新选择
  unit expert 和 market expert。旧 factorized/option 默认 `router_period=24`，才接近“一天
  选一次专家”。

因此，Stage35/37 的结构实际上是：

`每 turn 选 expert → 在该 turn 内自回归生成全部单位和市场动作 → 每 turn 做 GAE`。

Stage33/34 的“最后 48 步 option”只是最后 48 turn，也就是最后约 2 天；它不是以一天为
一个 transition 的高层 PPO。

## 四、当前 PPO 是否合理

### 4.1 合理的部分

PPO 作为低层动作优化器仍然可以使用，当前实现也有几项正确设计：

- 使用真实官方模拟器做闭环 on-policy，而不是把 Replay 动作当固定环境。
- 采用合法 action mask、数量编译和异常 PASS 闭包。
- 用旧策略 log-prob、clipped ratio、target KL 和 fresh-seed 部署门控制更新幅度。
- 对手池覆盖金牌、历史 PPO、自博弈、专项 Exploiter 和基础锚点。
- 单次只更新预注册参数范围，并验证其他参数逐位不变。

这些解决了“能不能安全、可复现地做 PPO”，但没有解决“PPO 是否在正确的时间尺度、正确
的状态分布和正确的目标上学习”。

### 4.2 根本问题一：信用分配时间尺度错位

当前 Stage37 使用 `gamma=0.995`、`lambda=0.95`，所以 GAE 的主要传播系数为：

`gamma × lambda = 0.94525`

其有效 trace 长度约为：

`1 / (1 - 0.94525) = 18.26 turn = 0.76 天`

半衰期只有 12.31 turn；终局信号向前传播时：

- 24 turn、即 1 天前只剩 25.89%；
- 48 turn、即 2 天前只剩 6.70%；
- 72 turn、即 3 天前只剩 1.74%；
- 216 turn、即 9 天前只剩约 0.00052%；
- 开局几乎收不到终局金币信号。

但种植、成熟、动物产出、商店解锁、现金周转和终局兑现都是跨天因果链。现在的 PPO 更容易
学到“这个 turn 的现金/库存看起来更好”，很难学到“九天前的采购和土地决策最终赢了比赛”。

### 4.3 根本问题二：探索方式会破坏整条经济轨迹

Stage37 对每个 turn 内大量 unit/market token 使用温度 0.2 采样。一个 turn 最多包含 16 个
单位动作和 10 个市场订单，还附带数量选择。独立的小概率偏差会在后续 719 turn 中累积，
导致单位位置、库存、现金和生产节奏全面偏离 BC 分布。

实证就是 Stage37：确定性 Stage35 尚能稳定击败 Starter，但温度 0.2 的混合池 rollout
128/128 局全部低于 3,000 金币，平均只剩 26.4。此时 PPO 学到的不是“如何从正常经济中
变强”，而是“如何在已经死亡的轨迹里相对少死一点”。

### 4.4 根本问题三：没有有效 critic，却把每层 advantage 强制中心化

Stage37 因 BC value head 未训练，设置 `ignore_value_baseline=true`、`value_coef=0`。这使更新
更接近带 handcrafted potential 的高方差 REINFORCE，而不是有可信状态价值基线的 PPO。

随后又按对手层分别做 `(advantage-mean)/std`。当同一层所有轨迹都灾难时，中心化仍会把
“较不差”的一部分动作变成正 advantage，抹掉了这一层整体失败的绝对信息。分层标准化本身
没有错；错误是“零 critic + 全层灾难 + 强制减均值”的组合。

### 4.5 根本问题四：层级 MoE 的时间结构不是真正层级

当前 expert 主要是共享 trunk/decoder 前的 projection slice。它们没有完全独立的长期记忆、
预算状态和 option 终止条件；Router 又每 turn 重选。结果更像“每 turn 换一个特征投影”，
而不是“选择一个生产计划并执行一天或一个生产阶段”。

Stage35 的 Router 24→1 修复说明逐 turn 标签必须逐 turn 部署，但也反向证明：当前专家定义
本身是 turn-level functional label，不是能跨天承诺的生产专家。它和我们目标中的
Hierarchical MoE 仍有距离。

### 4.6 根本问题五：固定强对手池适合最终训练，不适合从脆弱 BC 启动

40% Gold-Train 对最终联赛是合理的防过拟合约束；但当 candidate 对 Gold 仍是 0 胜、随机
采样后连 Starter 经济都无法维持时，这个分布太难。PFSP 应把大多数训练量放在胜率约
30%–70% 的学习边界，同时保留金牌最低曝光；等基础策略稳定后，再升到最终
40/30/15/10/5。否则强对手只会放大失败轨迹数量。

## 五、建议的新 PPO 逻辑

建议把下一版定义为“日级 Manager + turn 级低层 Actor 的 Constrained League PPO”，而
不是继续在当前 Stage37 上调学习率、温度或奖励权重。

### 5.1 两层时间尺度

高层 Manager：

- 只在每天开始、商店解锁、主要生产阶段切换或终局窗口选择 option。
- 默认一天承诺 24 turn；允许少量状态触发的提前终止，但不每 turn 抖动。
- 整局只有约 30 个高层 transition，使用 day-level critic 和真正跨天的回报。

低层 Actor：

- 仍逐 turn 生成 farmer/hands/market 全动作。
- 条件输入增加当前 option、日内剩余 turn、当日现金预算和生产目标。
- unit 与 market 使用独立 PPO loss/KL budget；不要把几十个 token 的概率乘成一个极脆弱
  joint ratio。

### 5.2 真正独立的专家

- 共享公开状态 encoder，但每个 expert 至少拥有独立 adapter、循环状态和 value head。
- 首批只训练两个互补专家：`生产/物流执行` 与 `市场/现金管理`；终局兑现作为第三个短
  horizon option。
- 每个专家先在多对手 fresh-seed 门控中单独稳定，通过后才训练 Manager。
- 安全执行器只做预算可行性、合法 mask、库存容量和数量封顶，不替专家偷偷生成父代动作。

### 5.3 先把 critic 训练好

- 用官方 Replay 和大量模拟器轨迹预训练 opponent-conditioned value model，预测：终局自身
  金币、金币差、灾难概率和每日企业价值。
- PPO 时启用 value loss；不同 opponent layer 使用独立 value normalization 或 PopArt，
  不再用“全层减均值”代替 critic。
- 可用同 seed/seat 的 incumbent 闭环结果作为 control variate 降低方差，但不能把 incumbent
  动作喂给候选。

### 5.4 奖励改成日级、约束式目标

主目标仍是官方终局金币和胜负；辅助信号只在日边界结算：

1. 每日 mark-to-market 企业价值变化；
2. 当日生产兑现、缺水/缺粮、库存溢出和现金断裂；
3. 最终自身金币与金币差；
4. 低于现金/产能安全线作为独立 constraint cost，而不是和主 reward 随意相加。

若继续使用 potential shaping，必须保持 `F=gamma*Phi(s')-Phi(s)` 的 potential-based 形式，
并让 gamma 与日级目标一致。训练门采用词典序：先禁止灾难退化，再比较自身金币，最后比较
胜分率和金币差，防止靠压低双方经济获利。

### 5.5 探索改成“相关探索”，而不是每个 token 独立扰动

- 每天采样一次 latent/option 噪声，日内低层动作保持低温或近确定性。
- 对 market budget、扩张规模、生产目标做宏观探索；单位移动和已承诺任务使用低熵执行。
- 使用 adaptive KL 约束新策略到可生存 BC；只有随机采样策略通过基础生存门，才允许收集
  金牌混合池 PPO 数据。

建议增加一个训练前硬门：16 fresh seed × 双座位、按训练温度采样，要求 Starter score
不低于 75%、灾难率不高于 5%、自身金币中位数高于 3,000。Stage37 会在这个门直接被拦下，
不会浪费 128 局去学习死亡轨迹。

### 5.6 对手课程分三段

原固定混合池保留为最终目标分布，但训练从易到难：

| 阶段 | Gold | History/近邻 | Self-play | Exploiter | Anchor | 目的 |
|---|---:|---:|---:|---:|---:|---|
| 生存期 | 15% | 35% | 10% | 5% | 35% | 保住经济闭环和动作支持 |
| 提升期 | 30% | 35% | 15% | 10% | 10% | 在 30%–70% 胜率区间学习 |
| 最终联赛 | 40% | 30% | 15% | 10% | 5% | 防过拟合并冲击金牌 |

各层内部继续 PFSP，困难金牌保留最低抽样概率，V76 在最终联赛仍控制在 8%–10%。任何只
战胜单一金牌的 checkpoint 只能登记专项 Exploiter。

### 5.7 新版门控顺序

1. `Stochastic Survival Gate`：训练温度下对 Starter/基础锚点保持经济闭环。
2. `Expert Role Gate`：每个低层 expert 在多对手 fresh seed 上证明自己的职责增益，并且
   非职责指标不退化。
3. `Mixed Development`：64 seed × 双座位，同 seed/seat 与 incumbent 配对；同时看 pooled、
   最差 Gold、自己的金币和灾难率。
4. `Gold-Dev`：只在 screen 通过后使用。
5. 至少两个独立 expert 通过后，训练 day-level Manager。
6. 最终 256/512 fresh seed Gold-Blind Confirmation；失败后更换确认集，禁止反复调参。

## 六、建议停止哪些旧路线

- 不再从 Stage20/35 上继续尝试 `lr`、clip、temperature 的小范围 sweep。
- 不再使用每 turn Router 来冒充日级 Hierarchical MoE。
- 不再把 stateful 金牌教师当 candidate-state DAgger oracle；Stage19 和 Stage36 已两次证明
  教师内部状态与候选轨迹不一致。
- 不再用 value=0、整层 advantage 强制中心化训练全面失败的轨迹。
- 不再把“KL 很小”“参数只改 4 个叶子”“DONE/DONE”解释为策略进步；这些只证明更新可控、
  程序可运行。

## 七、最终判断

当前 PPO 的工程框架值得保留，但训练逻辑不应继续沿用。根本矛盾不是模型还不够大，也不是
学习率没调好，而是：

`跨天经济目标 + 每 turn 独立探索 + 不足一天的 GAE 信用长度 + 无有效 critic + 过强训练分布`

下一版应该把“天”作为高层决策和信用分配单位，把“turn”留给低层执行；先让低层策略在
随机采样下保持经济生命，再逐步进入混合金牌联赛。这样才是真正符合 Kaggriculture 因果结构
的 Hierarchical MoE PPO。

## 八、证据索引

- 当前状态：`run_state.json`
- 完整协议和 Stage27–37 记录：`TRAINING_PLAN.md`
- Stage37 rollout：
  `model_data/v113_simulator_hmoe_ppo/sequence_action_stage37/mixed_pool_iter11_64/rollouts_merged.json`
- Stage37 PPO 更新：
  `model_data/v113_simulator_hmoe_ppo/sequence_action_stage37/ppo_expert_projection_lr3em6/ppo_update.json`
- Stage35 mixed screen：
  `model_data/v113_simulator_hmoe_ppo/sequence_action_stage35/full_bc/mixed_screen16_analysis.json`
- Stage36 Starter 基础门：
  `model_data/v113_simulator_hmoe_ppo/sequence_action_stage36/dagger_merged_bc/`
- 环境时间配置：本地 `kaggle_environments` 1.32.7 的 `kaggriculture.json`
