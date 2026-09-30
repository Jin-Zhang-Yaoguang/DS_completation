# V113 Simulator-trained Hierarchical MoE PPO：完整训练方案

## 0. 目标与不可变边界

目标是训练一个由神经策略自行生成 `farmer / hands / market` 全部动作的
Hierarchical MoE，在官方 Kaggriculture 1.32.7 模拟器中稳定战胜当前
`golden_model.md` 的可执行金牌池，并产出可独立提交的 NumPy 推理包。

- `strategy_parent=null`。训练与提交代码不得导入 V1–V112 的策略实现。
- Golden models 只作为训练/评测对手；其动作不得成为 V113 的在线回退动作。
- Replay 只用于引擎校准、离线预训练、专家发现和对手蒸馏，不作为运行时路线。
- Actor 只读取 Kaggle 提交可见字段；禁止对手私有库存、身份、submission id、seed。
- 安全层只构造合法 mask、规范化数量和提供 PASS 异常闭包；不得用父代动作替换策略。
- 未通过下述所有门槛前不登记金牌、不构建最终 challenger、不上传 Kaggle。

## 1. 模型：全动作 Candidate-Action Hierarchical MoE

### 1.1 状态编码

每个回合编码三组输入：

1. `global[ ]`：day/hour、双方公开现金/土地/雇工/作物/动物、己方 shed/seeds、
   市场库存/价格、商店实例与历史差分。
2. `board[10,10,C]`：己方每格的锁定、空地、杂草、作物/动物类别、成熟度、
   浇水/喂养/风险状态，以及双方公开生产结构摘要。
3. `units[N,U]`：主农与全部 hands 的位置、当前位置 tile、携带库存和角色位置。

Actor 与 Critic 默认使用完全相同的信息边界；首版不使用 privileged critic。

### 1.2 分层 MoE

- 日级 Manager 在 `hour=0` 选择一个当天持续的 latent expert。
- 六个候选专家初始语义为：作物增长、畜牧增长、物流维护、市场变现、现金防守、
  终局兑现；这些是可学习 head，不是规则路线。
- 回合级 Worker 接收共享编码、当前 expert embedding 和 unit embedding，生成所有
  unit 动作及市场动作。
- Router 与所有专家共享输入编码器，但拥有独立输出 head；PPO 同时优化 Router、
  被选专家和 Value。
- 防止专家坍缩：加入 Router balance loss、最小使用率和专家行为差异约束；晋级时
  还要求至少四个专家在独立确认集上真实触发并产生不同动作分布。

### 1.3 结构化动作空间

不直接生成任意 JSON，而是在当前状态下枚举合法候选并由策略选择：

- 每个 unit：`PASS/N/S/E/W/DROP/WATER/HARVEST/FERTILIZE/DIG/BUILD_*/FEED/
  CARE/COLLECT_FERTILIZER/PLANT_<crop>/PICKUP_<item>/PLACE_<item>`。
- 数量使用状态下所有可执行精确整数；训练标签与推理 mask 必须属于同一动作集合。
- 市场采用最多 10 个自回归 slot：`STOP/HIRE/BUY_LAND/BUY_SEED/BUY_PRODUCT/
  BUY_ANIMAL/SELL`，每个 slot 都在更新后的影子现金、库存和槽位状态上重新 mask。
- 同一 crop 的 PLANT 请求总数不得超过种子数；安全层在采样前完成联合约束，避免
  采样动作与最终动作不一致。

PPO 保存 Router、unit 和 market 每个被执行 token 的 mask、action、old logprob；
最终动作规范化后必须能反向编码为完全相同 token，否则该 rollout 整局拒收。

## 2. 环境与随机性

### E0 引擎一致性门

- 固定 `kaggle-environments==1.32.7`、环境 `0.1.0` 和规则 SHA256。
- 从本地 1.32.7 Replay 按日期/队伍分层随机抽 100 场。
- 用 Replay 的 `configuration + info.seed + 双方动作` 重放 720 状态。
- 逐步 observation hash、终局 reward、status 必须 100% 相同；任一不一致停止训练。

### 训练随机化

- 主训练只随机 fresh 31-bit seed、seat 和 opponent，不独立随机商店/杂草。
- 每个 seed 必须双席位成对；同 seed 的两席位永不跨 split。
- 训练、validation、Development、Confirmation 使用互不重叠 seed namespace。
- 规则参数扰动只进入 robustness 压力测试，不进入主训练或金牌指标。

## 3. 离线 Replay 预训练

### D0 数据范围

- 第一阶段只读取 `module_version=1.32.7` 的 8,970 场 Replay。
- 按 `episode + seed + team` group split 为 train/validation/test；先切分再抽帧。
- Actor 输入永不拼接另一席位的 `private`。
- 保留胜负双方，按最终分数、日期和策略簇加权；不能只模仿同一名榜首玩家。

### D1 Codec 与数据质量门

- unit 与 market 词表覆盖率分别 `>=99.9%`。
- Replay 原始指令先经过状态条件编译器清洗；非法/无效指令改为可执行标签，禁止模仿 no-op 噪声。
- 清洗后的标签满足 `decode(encode(clean_action)) == clean_action`，动作闭包率必须 100%。
- 清洗后动作 JSON schema 100% 合法；原始动作保持率作为数据质量诊断，不作为编码器失败条件。
- 数量标签记录精确整数；PPO 采样时再映射为候选数量并按可执行上限截断。
- 每个 split 报告动作熵、PASS 比例、hands 分布、market slot 分布和策略来源。

### D2 预训练任务

1. masked state reconstruction：预训练公开状态编码器。
2. behavior cloning：Router latent、unit token、market autoregressive token。
3. return/value：预测终局胜负和截断金币差。
4. expert diversity：用行为功能簇初始化六专家，并以负相关/均衡约束防止单专家独占。

闭环 BC 门：在 unseen seed 上对冻结金牌池运行至少 256 seed × 双席位；只有
`DONE/DONE=100%`、非空动作率和经济规模显著超过随机/Starter，才允许进入 PPO。

## 4. PPO 联赛训练

### P-1 分布外课程启动

BC 可能在弱对手状态上发生 covariate shift，因此将“允许 PPO 更新”和“允许进入金牌联赛”拆开：

- Codec、schema、`DONE/DONE` 通过后，可对 `pass/random/starter` 进行课程 PPO；这一阶段不计作金牌训练结果。
- 对手顺序为 `pass -> random -> starter`，每一级使用全新 seed、双席位；上一层 point score `>=60%` 且平均金币 `>=10,000` 才解锁下一层。
- 未战胜 Starter 前，金牌对手权重为 0，避免所有轨迹得到相同负终局奖励；通过后才进入 P0 联赛混合。
- 课程阶段仍由同一 Actor 独立生成全部动作，不能调用 Starter 或金牌动作做 fallback。

### P0 对手联盟

- 40%：`golden_model.md` 中行为去重后的冻结金牌代表，包括当前 V76。
- 30%：V113 自博弈历史快照，按 PFSP 优先抽取胜率 30%–70% 的对手。
- 20%：从高分 Replay 蒸馏的闭环 opponent clones。
- 10%：库存溢出、现金耗尽、动物断粮、终局未兑现等 exploiters。

训练代码可以动态加载这些对手；提交包不得包含或调用它们。

### P1 回报

```text
terminal = sign(gold_margin) + 0.05 * tanh(gold_margin / 25000)
step_reward = gamma * Phi(next_observable_state) - Phi(state)
```

`Phi` 只使用可观察的现金、可变现库存、成熟产物、存活生产资产和风险负债；终局
强制为 0。主目标始终是胜负，原始金币不能压过胜负符号。

### P2 PPO 参数起点

- rollout：每次 1,024–4,096 完整对局，双席位平衡。
- `gamma=0.999`（回合级719步）、`lambda=0.95`、`clip=0.2`。
- policy/value learning rate `3e-4/1e-3`，线性退火；gradient norm 0.5。
- 4 epoch，minibatch 16,384 token；target KL 0.015。
- entropy 分头设置；Router entropy 逐步衰减但保留最小值。
- 每 5 次迭代冻结 snapshot，validation 选择，不能用 Confirmation 选 checkpoint。

### P3 停止与恢复

- 每次 rollout、checkpoint、优化器、RNG、数据/代码 hash 原子落盘。
- 动作闭环不一致、compiler fallback、非法 schema、`DONE/DONE` 失败均为硬错误。
- 连续三次 validation 无提升则降低学习率；连续十次无提升停止当前训练分支。
- 任何单专家使用率 >85% 且其余专家无正贡献，判定 fake MoE，不得晋级。

## 5. 金牌门控

### G1 Development

- 固定 256 个训练未见 seed、双席位。
- 对 `golden_model.md` 所有可执行金牌版本逐一对战；同一 seed/seat 配对。
- pooled score rate `>=55%`，paired bootstrap 95% CI 下界 `>52%`。
- 对每个金牌：point score rate `>=52%`，CI 下界不得低于 50%。
- pooled 平均金币差 >0；灾难局（金币差 <= -25,000）不得高于最佳金牌 +1pp。
- 0 runtime error、0 schema error、0 action-closure mismatch。

### G2 一次性 Confirmation

- 重新生成 512 个 seed，双席位，继续对全部金牌；不得调参。
- pooled score rate `>=55%`，95% CI 下界 `>53%`。
- 最差金牌 point score rate `>=52%`；逐模型 CI 下界 `>=50%`。
- 至少四个 expert 使用率各 `>=5%`，且去掉任一主要 expert 后 pooled score 下降。
- 推理 P95 <100ms/turn、最大 <900ms；719 次调用、720 state、`DONE/DONE`。

只有 G1/G2 全通过，才登记 `golden_model.md`。Kaggle 提交仍需用户再次明确授权。

## 6. 运行阶段

1. `ENV_PARITY`：引擎/Replay 逐步一致性。
2. `CODEC_AUDIT`：动作空间覆盖与可逆性。
3. `OFFLINE_PRETRAIN`：encoder + BC + value + expert initialization。
4. `BC_CLOSED_LOOP`：新 seed 与金牌池的闭环最低生存门。
5. `PPO_LEAGUE`：fresh-seed on-policy + self-play/PFSP。
6. `DEVELOPMENT`：256 seed 全金牌门。
7. `CONFIRMATION`：512 全新 seed 一次性确认。
8. `PACKAGE_QA`：纯 NumPy 提交包与训练策略逐动作等价。

当前启动点：`ENV_PARITY`。

## 7. 执行修订：Factorized Product MoE（2026-08-29）

首轮执行证明，单一日级 Router 同时控制单位和市场是不成立的：生产、物流、扩张和
出售会在同一天并发；Replay 的无语义 KMeans 簇号与 DAgger 阶段号拼接后，还会让
同一 expert 接收冲突监督。该分支保留为反例，不再继承 checkpoint。

第二分支改为原创的双 Router 商品级 Hierarchical MoE：

- Production Router 按日选择 `WHEAT/CARROT/TOMATO/STRAWBERRY/MELON/ANIMAL`
  六个生产专家，保证跨回合生产连续性。
- Market Router 每回合独立选择六个商品控制器，商品级决定采购、出售和数量；因此
  允许“生产 A、同时兑现 B”，不再强迫跨域共用一个 expert。
- 基础动作干线只读取己方状态和公共市场；对手公开状态经预测支路进入，残差门硬限制
  在 `[0, 0.1]`，初值约 `0.0018`。对手信号只能修正，不能接管基础策略。
- 状态安全执行器仍只负责 legal mask、数量编译、影子现金和 PASS 闭包，不提供规则动作。
- Replay 与 DAgger 全部重标为稳定商品语义；旧簇号不进入新模型。

BC 仅用于获得可探索的完整动作初始化。通过 `pass/starter` 闭环生存门后，必须转入
fresh-seed PPO；最终模型仍以 PPO checkpoint 和金牌联赛结果为准，不以模仿准确率晋级。

## 8. 执行记录与下一阶段（2026-08-29）

已完成的事实门：

- 官方引擎 100 场、72,000 个状态逐步一致，Codec 闭包率 100%。
- 从零训练的五个商品动作专家均形成单地块闭环；20 局强制专家审计全部正常结束，
  五专家对全 PASS 的平均金币差均为正。
- 第一轮冻结动作专家的 Router PPO 使用 32 局 fresh-seed、双座位上下文 bandit
  rollout。全参数 Router 因小样本过拟合被拒绝；只更新 Router bias 的检查点在 16 局
  新种子双座位验证中，把 Starter 得分率从 87.5% 提升到 100%，平均金币差从
  `+120.375` 提升到 `+1512.75`。
- 同一 PPO 检查点对 V76 的 4 局 smoke 为 0%，平均金币差 `-173,605`。这证明 PPO
  更新链有效，但也证明单地块动作专家没有金牌经济规模。

当前进入 Scale Curriculum：原创多工人教师每天雇 8 个 hands，调度 9 块 NW 地块，
只为 V113 生成训练标签，不进入推理包。教师甜瓜闭环平均金币 24,268；首轮纯 BC
出现明显 covariate shift。Scale-DAgger round 1 在模型自身状态上重新标注后，胡萝卜
和甜瓜专家已独立战胜全 PASS，其他三专家仍未通过。

Scale-DAgger round 2 将教师执行率降到 10%。结合商品独立 checkpoint 和现金/雇工/
种子容量安全约束，五个规模化作物专家已全部在完全无教师执行时通过闭环。Router
选择甜瓜的 portfolio 对 Starter 4/4、平均金币 24,105；对 V76 0/2、平均金币
16,623、平均差 `-151,547.5`。经济规模仍不具备金牌强度。

完整动作 PPO 已完成三条探索分支。温度 0.05 与 0.30 的更新在 8/16 场全新配对中
逐动作等同基线；温度 0.50 使用 32 场、23,008 transitions、10 epoch，最终 KL
`0.00206`，16 场部署动作仍完全一致。将四个动作输出 head 等比例缩放为 0.1 后，
PPO 前 argmax 和 8 场闭环严格不变；校准后更新仅在离线状态改变 4/20,526 个 argmax，
16 场闭环仍未改变。因此这些 checkpoint 全部否决，不得称为 PPO 增益。

为补齐八商品谱系，已构造 EGG/MILK/WOOL 三条原创规则教师，8-seed 双座位均正常结束，
平均金币分别为 5,703、19,620、18,920。三个独立 BC 专家以及 25%/75% DAgger 课程
在教师执行率归零后仍发生角色漂移和现金耗尽；该分支判为 Worker 架构失败，不并入
portfolio。下一步固定为：增加“单位角色 + 目标 tile + 跨日 option”潜变量，动作安全
层只负责合法性和现金约束；随后从零训练三条动物专家，再执行完整动作 PPO。通过前
不进入金牌联赛、不消费 Development/Confirmation。

## 9. 执行修订：Role-Target Option 与规模蒸馏（2026-08-29）

角色—目标 Worker 已完成并通过课程闭环。Manager 为每个 unit 输出工作/闲置角色与
目标 tile，Worker 在 option 条件下生成原生动作；安全执行器只保证未到目标时沿合法
最短方向移动、到达后才执行任务动作，闲置角色只 PASS。该约束不调用任何父代动作。

执行中发现并修复动作空间硬错误：BC 数量标签允许 3、5 等精确整数，而旧推理 mask
只允许 `1/2/4/8/half/all`，导致离线 100% 正确仍被执行器改写。修复后动作空间允许
状态下全部可执行精确数量，相关单测通过。

三动物专家在 4 个全新 seed、双座位、teacher=0 下全部 8/8 战胜 pass：EGG/MILK/
WOOL 平均金币为 5,708/24,356/20,966。对 V76 的各 2 局 smoke 全败；MILK 最强，
平均金币 24,284、平均金币差 `-157,970`，尚未进入金牌联赛。

联合 Role/Target/Unit/Market PPO 已打通。第 1 轮 8 局、5,752 transitions、4 epoch，
KL 约 0.001，但 16 局新种子确定性行为和收益与 BC 完全一致，判为行为惰性。第 2 轮
提高 Manager 温度后 8 局仅 1 胜；6 epoch 更新虽改变部署收益，但在配对 8 局中平均
比 BC 低 32.75，拒绝继承。逐步随机 target 会破坏 option 持续性，因此采样器已改为
目标行进期间冻结、到达并执行一次后再开放 Manager 决策，并只在 option 边界计算
Manager PPO loss。

直接把动物教师从 3 格扩为 6/9/12 格全部失败；3→6 的分期扩产也没有提升，9 格以上
现金耗尽。这证明现有原创教师缺少融资、土地、商品组合与兑现协同，不能靠扩大同一
规则模板达到金牌经济规模。下一阶段使用 1.32.7 高分 Replay 离线数据学习阶段 option
和商品需求，但提交端仍 `strategy_parent=null`、不导入 Replay 路线或金牌动作；随后
从该独立 Actor checkpoint 继续 fresh-seed PPO。未产生配对正增益前不进入 Development。

首批 Replay 蒸馏执行结果：12 场多玩家数据包含 17,256 状态，双方金币均值 106,893，
但混合 24 个策略后闭环为 0/8。改用 Thomas Tschinkel 单一玩家 16 场、11,504 状态，
原策略金币均值 95,228；离线验证角色/目标/单位/市场准确率约
96.3%/54.3%/73.2%/63.5%，teacher=0 闭环仍为 0/8。失败轨迹出现跨回合重复买卖、
错误建造与目标阶段混淆。

因此下一结构门固定为：Manager role 从二分类扩展为建造、取动物、放置、取饲料、
喂养、照料、收获、物流、出售等阶段 option；market 从 10 个并行 slot head 改为读取
前序已执行 token、数量和更新后影子现金/库存的自回归 decoder。只有单玩家 Replay
蒸馏在 teacher=0 新 seed 闭环先战胜 pass，才恢复 PPO。多玩家混合和当前并行 market
checkpoint 均不得继承。

## 10. 执行修订：Timed Sequence Action 与联合 PPO（2026-08-29）

已实现读取前序已执行 unit/market token、精确数量和时序位置的联合自回归动作模型。
初始小数据基座对 PASS/Starter 可用，但对 V76 的 8 局均失败，平均金币约 17,225，
说明主要瓶颈是闭环暴露偏差与经济规模，而不是离线 token 准确率。

随后使用 256 个全新 V76 教师 seed、双座位采集 512 局、368,128 个状态；8 个分片
全部完成。大样本 timed BC 训练 6 epoch，每轮原子保存，最终验证损失 0.16524，unit/
market/market-quantity 准确率为 99.09%/97.95%/91.95%。在训练未见 seed 上：

- 对 PASS 16/16，平均金币从旧基座 23,923 提升到 108,164；配对 15/0/1，平均
  `+84,241`，bootstrap 95% CI `[+55,969,+112,576]`。
- 对 Starter 16/16，平均金币从 17,244 提升到 85,654；配对 15/0/1，平均
  `+68,410`，95% CI `[+46,055,+92,228]`。
- 对 V76 仍 0/16，自身平均金币 11,543，旧基座 13,221；配对 7/0/9，平均
  `-1,678`，CI 跨 0。该 checkpoint 只晋级为 PPO 课程基座，不是金牌模型。

联合 PPO 协议已改为：joint action ratio、rollout/trainer 温度强一致、异常轨迹拒收、
首轮 zero value baseline、训练后全 rollout 非负 KL 复算。32 局 V76 双座位 on-policy
rollout 共 23,008 transitions，零异常。三个分支均被独立新 seed 门控否决：

1. enterprise potential + own-log，lr=1e-7：16 对自身金币平均仅 `+12.8`，CI 跨 0；
2. 同回报 lr=3e-7：8 对自身 `-3,524`，margin `-11,329` 且 CI 全负；
3. pure terminal own-log：8 对自身 `-381`；smooth margin：自身虽 `+917`，但 margin
   `-6,772`，95% CI `[-12,175,-1,664]`。

因此不再沿单一 expert 的 719-step 高维联合 PPO 调学习率。下一结构门改为：保留大样本
timed BC 作为生产专家初始化，把 PPO 决策降维到跨日 option、商品生产 expert 和商品级
出售控制器；各专家拥有独立 head 与持续状态，Router 读取对手公开产能/路径预测。只有
至少两个独立专家分别产生配对正增益，且 Router 在 V76 与其他冻结金牌上优于最佳固定
专家，才恢复大规模 self-play/PFSP。

## 11. 执行修订：职责分离专家与直接 on-policy PPO（2026-08-29）

Stage 18 将 timed Actor 的 unit 与 market expert projection 物理分离，合并工具只允许
复制指定 expert slice，并校验其余参数逐字节一致。独立确认得到两个不同职责信号：

- market expert 2 在 24 局中相对基座自身金币 `+2,856`，95% CI 下界 `+607`；
- unit expert 3 在 24 局中分差 `+12,125`，95% CI 下界 `+4,351`；
- unit 3 + market 2 合并后，自身金币 `+2,292`，分差 `+12,744`，但仍 0/24 战胜 V76。

Stage 19 的 DAgger 只作为否证实验。V76 的内部路线状态依赖其动作被真实执行；当只把
它当候选状态标签器时，教师 PASS 比例由正常闭环的 5.47% 升至 39.66%，不再是有效
oracle。11,504 个候选状态上的所有全参数/投影 BC 均发生经济坍塌，因此禁止继续用该
方式制造“金牌教师”标签。

Stage 20 改为官方模拟器中的直接 on-policy PPO。Starter 与 V76 rollout 先按职责拆开，
只用 Starter 的 16 局、11,504 transition、own-log 回报更新 unit expert 3，market
expert 2 和共享干线冻结。`lr=1e-6` 候选在独立 V76 24 局配对中：

- 自身金币平均 `+4,748`，95% CI `[+1,655,+7,772]`，`19/1/4`；
- 分差平均 `+22,224`，95% CI `[+10,731,+34,276]`，`17/1/6`；
- Starter 防退化 8/8 胜，自身差 `-386`，CI 跨 0；
- 对 V76 仍 0/24，因此只晋级为训练 incumbent，不进入金牌池。

Stage 21 加入 checkpoint opponent，使历史快照可作为真正 on-policy self-play 对手。
训练 rollout 16 局为 9胜7负、平均分差 `+2,980`；但 `lr=1e-6` 更新在新 16 局中对
incumbent 恰为 8胜8负，对 V76 配对自身仅 `+304`、CI `[-2,243,+3,004]`，分差
`-633`、CI `[-13,954,+11,317]`，Starter 自身 `-971` 且 CI 跨 0。该 checkpoint
否决，不替换 Stage 20。

下一训练门不是扩大 self-play 轮数，而是在 V76 真实对抗状态中用 own-score 回报单独
更新 unit 专家，再用相同种子双座位检查自身金币、分差与 Starter 防退化。只有这三项
同时通过，才允许成为新的快照并进入 PFSP；任何只压低双方经济、只改善相对分差的候选
都必须淘汰。

Stage 22 已执行上述 V76-only 试验：16 局、11,504 transitions，分别以
`lr=5e-7/1e-6` 更新 unit expert 3。4 局全新 V76 screen 中，较 Stage 20 incumbent
自身金币分别 `-4,460/-5,286`，分差分别 `-13,893/-15,777`；两条分支的分差均为
`0/0/4`，立即淘汰。原因是所有 V76 轨迹均为失败，own-log 仍会强化失败集合里偶然较高
的动作序列，缺少可识别的反事实责任，不能靠继续缩小学习率解决。

因此下一结构门正式切换为 opponent-conditioned Router：冻结已确认的 unit 3、market 2
及其他独立 expert，只训练读取双方公开产能、市场状态和路径摘要的 unit/market Router。
Router 必须在同一状态选择完整专家，不允许拼接父代动作；先证明优于最佳固定 expert，
再恢复 PFSP 和联合微调。

## 12. 执行修订：可观测延迟 Router 与阶段 Option PPO（2026-08-30）

Router 可观测性审计发现，测试 seed 的 step 0 编码逐元素完全相同，且
`town.unlocked_shops=[]`；step 72 才首次出现 `FARMERS_MARKET`。因此用终局最优专家给
step 0 打标签属于不可学习的 seed 泄漏，已停止该实验。策略接口现支持按绝对 step 的
unit/market 专家日程，并用相同 seed、seat、共同前缀进行严格反事实比较。

冻结 U3/U4/U5 与 M2/M5 后，step 72 路由到终局的六组合在训练和独立验证面板上都存在
正 Oracle 空间；但两棵深度 2 树均未超过验证集最佳固定专家。把控制窗口缩短为
72–215 后，M2/M5 逐局完全相同，证明市场分支在该阶段是伪专家；unit 专家仍有 Oracle
空间，但浅树同样退化为固定 U4/U5。由此否决“继续增加树深或样本即可解决”的解释。

随后执行新的阶段 PPO 协议：完整闭环运行，训练数据只保留指定 option 窗口；势函数
回报在窗口内计算，zero value baseline，unit projection 单独更新，前后均恢复 U3/M2。
U4 使用 enterprise capacity，U5 使用 liquid asset，两者训练 KL 均低于 0.001。32-seed
双座位 seed-block bootstrap 中，U4 自身金币增益和 U5 分差增益的 95% CI 下界分别为
`-1,614.7/-955.5`，故均否决，不并入冻结 portfolio。

下一门只允许修改阶段回报结构，不继续调浅树或学习率：回报必须显式扣除候选动作通过
共享市场给对手带来的公开价格/库存外部性，并把 own economic gain 与 opponent public
capacity gain 分开记录。新专家只有在至少 32 seed 双座位上主职责指标 seed-block CI
下界 `>0`、另一指标下界不低于预注册容忍线时，才允许合并并训练 Router。

## 13. 执行修订：混合对手联赛与历史状态 Actor（2026-08-30）

Stage 26 的 opponent-impact U5 在 32 seed × 双座位确认中，自身金币增益 `+803.8`、
分差增益 `+1,246.1`，但两项 seed-block 95% CI 下界均小于 0，且仍 0/64 战胜 V76，
因此否决。随后加入 32 维动作历史以恢复首商店承诺、上一回合市场流、累计市场流和
单位动作角色；Stage20 incumbent 的零初始化历史 checkpoint 与原 Actor 在 4 局闭环
奖励、操作计数和胜负完全等价。旧 Stage17 历史初始化在强对手 smoke 中连续 8 局金币
为 0，已淘汰。只用 V76 轨迹训练的第 1 epoch 虽有高离线准确率，但在用户收紧防过拟合要求后
立即中止，只保留为诊断产物，不得作为 challenger 或金牌证据。

从本阶段开始，任何 PPO rollout 禁止使用单一 V76 对手，必须读取冻结的
`opponent_registry.json`。训练层目标权重固定为：Gold-Train 40%、PPO History 30%、
Self-play 15%、Exploiter 10%、Anchor 5%。默认每 iteration 使用 64 个 fresh seed、
每个 seed 双座位且面对同一对手，共 128 局；首轮配额为 26/19/9/7/3 个 seed，即
52/38/18/14/6 局。rollout 必须按对手层分别标准化 advantage，再合并更新，避免某个
全负强对手用量级支配梯度。

### 13.1 Gold Train/Dev/Blind

现有本地金牌共享 V17→V76 大祖先，不能伪装成独立谱系。本阶段按五个因果行为族去重：

- Train 60% 行为族：生产路线 Router、需求时点、采购槽位；训练代表为
  V19/V21/V32/V76。V76 目标占总训练池 9%，64-seed 首轮为 6/64=9.375%；单一对手
  不得超过 12.5%。
- Dev 20% 行为族：V54 终局物流，只用于开发验证，不参与训练或 checkpoint 选择。
- Blind 20% 行为族：V66 共享市场 margin 排序，仅在最终一次性 Confirmation 解锁。

若后续新增真正独立谱系，则重新冻结 60/20/20；不得把 V70–V76 近克隆重复加权。

### 13.2 PPO History、Self-play 与 Exploiter

PPO History 最多保留 12 个 SHA 固定里程碑，当前包含 Stage17 BC、Stage20 联合 PPO、
Stage21 self-play、Stage25 U4/U5、Stage26 U5。Stage21/25/26 已失败，只允许提供行为
分布，不得称为冠军。历史池先按“候选胜率 >70% / 30%–70% / <30%”分配 20/60/20；
在首轮混合校准前强度标签均标为 provisional，之后用 fresh-seed 实测和学习进度/PFSP
更新，困难金牌保持最低概率。

Self-play 只放当前 incumbent、最近行为不同的冻结快照和当前 challenger；每次晋级后
原子更新 registry 与 SHA，不允许运行中覆盖。Exploiter 分别覆盖现金耗尽、过度扩张、
商品挤兑/共享市场、低经济拖分和终局兑现。Anchor 为 Starter 4%、PASS 1%；后期可把
PASS 降为 0，但必须先通过基础经济防退化门。

### 13.3 防过拟合、进度面板与晋级

固定历史进度面板只展示 Stage17→Stage20→Stage26→新候选，不进入训练；逐对手报告
胜/平/负、score rate、自身金币、金币差、灾难率和辅助 Elo。checkpoint 先做 16 fresh
seed 双座位 screen，再做 Gold-Dev 多对手 Development；所有比较使用同 seed/seat 配对
增益和 seed-block bootstrap，同时检查 pooled 与最差金牌，不接受只压低双方经济得到的
分差改善。Gold-Blind 仅用于最终 256/512 fresh-seed 一次性 Confirmation；失败后确认集
永久封存。

低层动作继续由 PPO 直接生成。至少两个独立职责 expert 在多对手门上稳定通过后，才
训练 option-level Router；优先考虑 IQL/Fitted-Q，禁止回到无反事实责任的浅树补丁。
即使某 checkpoint 只战胜 V76，也只能登记为 V76 专项专家，不能登记金牌。未经用户
再次明确授权，不提交 Kaggle。

### 13.4 首轮联赛执行结果

首轮已按冻结 registry 完成 64 个 fresh seed、双座位共 128 局，零异常，形成 92,032
个 transition。实际配额严格为 Gold/PPO History/Self-play/Exploiter/Anchor=
52/38/18/14/6 局；V76 为 6/64 个 seed（9.375%）。同 seed 双座位对手一致，合并后
按层 advantage 标准化的均值约 0、标准差约 1。

基于同一批 rollout 训练 shared-worker、冻结 Router heads 的两个单 epoch 分支；
`lr=1e-7/3e-7` 全 rollout KL 分别为 0.000363/0.000974。随后使用 16 个未训练 fresh
seed、双座位、同一冻结对手日程筛选：incumbent 为 9/2/21、score rate 31.25%；两个
候选分别为 8/0/24（25.00%）和 9/0/23（28.125%）。相对 incumbent 的 score gain
分别为 -6.25pp、-3.125pp，seed-block 95% CI 分别为 `[-18.75,+6.25]pp`、
`[-12.5,+6.25]pp`，均未通过 pooled 非退化门。

`lr=3e-7` 的分差增益为 +8,537.6，CI `[+2,928.1,+14,746.9]`，但自身金币增益仅
+2,333.8，CI `[-1,366.2,+6,035.2]`，且得分率下降；约 73% 的分差改善来自对手金币
下降，不得解释成能力晋级。两个候选均记为 `REJECT_SCREEN`，不进入 Gold-Dev，
不写入 Self-play incumbent。下一轮必须缩小可训练范围，优先只学习新增历史输入的残差
能力，禁止再次用全 shared-worker 更新扰动已验证生产能力。

### 13.5 Stage 28 历史条件残差 PPO 预注册

Stage 28 只允许更新 `own_global_dense/kernel` 最后 32 个历史输入行；原 60 个环境输入行、
所有 decoder、expert projection、Router、value head 和 embedding 必须逐字节不变。该模式
禁用 AdamW weight decay，并在每步更新前对梯度做行级掩码；训练结束必须自动输出参数
差分审计，任何越界变化立即失败，不生成可评测候选。

第 2 轮训练 seed 固定为 11330000–11330063，仍使用 64 seed × 双座位混合联赛；根据首轮
incumbent 逐对手数据更新 PFSP，训练配额和 V76 9.375% 上限保持不变。预注册两个单 epoch、
zero-value-loss 分支：`lr=1e-5` 与 `lr=3e-5`。训练前不查看筛选集；筛选使用新的
11331000–11331015，候选必须同时满足 pooled score 不低于 incumbent、Gold-Train score
不退化、灾难率不增加，才可进入 Gold-Dev。点估计分差改善但自身金币 CI 跨 0，仍按
“压低双方经济”否决。

Stage 28 已完成。第 2 轮 64 fresh seed × 双座位共 128 局，得到 92,032 transitions，
Gold/PPO History/Self-play/Exploiter/Anchor 配额仍严格为 52/38/18/14/6，V76 为 9.375%，
零异常。两个 checkpoint 的参数作用域审计均通过：只改变最后 32 个历史输入行，原 60 行
和其他参数逐字节不变。

独立 16-seed screen 中，incumbent 为 7/0/25、score rate 21.875%。`lr=1e-5` 为
8/0/24、25.00%，自身金币配对增益 +1,567.8，seed-block 95% CI
`[+132.3,+3,377.5]`，按预注册门进入 Gold-Dev；但分差增益为 −4,250.5，CI
`[-13,090.9,+1,670.7]`。`lr=3e-5` 虽为 10/0/22，却将灾难率从 12.5% 提高到
18.75%，按门控直接 `REJECT_SCREEN`。

`lr=1e-5` 随后对 Gold-Dev 的 V54 使用 64 个新 seed、双座位，基线和候选各 128 局。
两者均为 0/0/128；候选平均自身金币 7,923.6，低于基线 8,334.2，配对增益 −410.6，
CI `[-1,386.7,+622.0]`；分差增益 −340.8，CI `[-2,623.6,+1,911.3]`。候选灾难率
22.66% 虽低于基线 28.91%，但没有实际胜局，也没有稳定自身金币或分差增益，最终
`REJECT_GOLD_DEV`。不登记专项专家、不更新 incumbent、不消费 Gold-Blind。

### 13.6 下一独立 PPO expert 的边界

Stage 28 证明仅靠历史输入残差不能形成稳定金牌职责。下一轮不得继续扩大该 checkpoint
学习率或围绕其打补丁；应新建独立的现金安全 expert 或共享市场冲击 expert。训练目标以
相对金币差为主，加入自身金币低于 3,000 的灾难约束，并保留自身经济作为 guardrail；仍
使用冻结混合对手联赛、每层 advantage 标准化和 fresh-seed 门控。至少两个职责不同的
PPO experts 分别通过 screen 与 Gold-Dev 后，才允许训练 option-level Router。

### 13.7 Stage 29 现金安全市场 expert 预注册

Stage 29 不继承 Stage 28 checkpoint。从与 Stage20 incumbent 闭环等价的 Stage27 初始化
checkpoint 出发，将 market expert 2 克隆到独立 slot 5；初始化 SHA256 为
`e49f084b1bc5e754006ed38901e2d83086da4c7488c2b5bb7b0f255bf2a9765c`。在 4 个新 seed、
双座位、同一混合对手日程上，slot 2 与 slot 5 的 8 局金币、分差、胜负和动作计数逐项
一致，确认克隆没有引入行为漂移。

职责固定为“现金安全市场动作”：unit expert 固定为 3，market expert 固定为 5；只允许
`market_expert_projection` 的 slot 5 切片更新，其余参数与其余 expert slot 必须逐字节
不变。奖励使用 `cash-safety-relative`：相对公开企业价值 + 现金储备效用 − 低于 3,000
金币的短缺惩罚；终局以 100,000 为尺度优化金币差，并附加 0.75 倍现金灾难惩罚。

训练集固定为 11340000–11340063，64 fresh seed × 双座位；混合池配额、PFSP、同 seed
双座位同对手和分层 advantage 标准化保持不变。预注册单 epoch 分支 `lr=1e-5/3e-5`，
不得事后追加。screen 固定为 11341000–11341015；除 pooled、Gold-Train、最差金牌和
灾难率非退化外，现金安全职责还要求灾难率严格下降，且自身金币或分差的 seed-block
CI 下界大于 0。通过后才可访问 V54 Gold-Dev（11342000 起）；Gold-Blind 继续隔离。

Stage 29 已按预注册协议完成。训练集为 64 fresh seed × 双座位，共 128 局、92,032
transitions，零异常；配额严格为 52/38/18/14/6，V76 占 9.375%，各层 advantage
独立标准化。两个分支的参数审计均通过，仅 `market_expert_projection` slot 5 改变。

16-seed screen 中，基线为 10/2/20、score rate 34.375%、灾难率 21.875%。`lr=1e-5`
为 9/0/23、28.125%，灾难率虽降至 6.25%，但 pooled score 退化；自身金币增益
+1,593.7，CI `[-950.6,+4,742.6]`，分差增益 −2,017.0，CI
`[-6,431.9,+2,925.6]`。`lr=3e-5` 为 14/0/18、43.75%，灾难率降至 18.75%，但
自身金币增益 +2,647.5，CI `[-2,341.3,+9,740.5]`，分差增益 +395.9，CI
`[-7,981.9,+9,583.8]`；同时 Gold-Train 平均金币差退化 −2,616.7。两者均未满足
“灾难率严格下降且经济增益 CI 下界大于 0”的现金安全职责门，最终
`REJECT_SCREEN`。不访问 Gold-Dev/Gold-Blind，不登记专项 expert，不更新 incumbent。

### 13.8 下一独立 expert

Stage 30 不继续调 Stage 29 的学习率或奖励权重。下一条独立谱系定位为“共享市场冲击
响应”：以可观察的对手商店队列、商品库存变化、双方公开现金与最近市场成交为状态，
只训练新的市场动作 expert；目标是同时保全自身经济并减少被抢购/挤兑后的无效采购。
仍使用冻结混合对手联赛和全新训练/screen seed。完成预注册与克隆等价烟测前不得训练；
至少通过 screen 与 Gold-Dev，才可登记为第二个独立职责 expert。两个职责 expert 均通过
后才允许进入 option-level Router。

### 13.9 Stage 30 共享市场冲击 expert 预注册

Stage 30 从 Stage20 等价 history 初始化独立分叉，不继承 Stage29。将 market slot 2 克隆
到 slot 4，初始化 SHA256 为
`0c34871fbe5bf3e6a560d5bd6eaa299b28beb23b79d980089449bfbee16a234d`；在 seed
11349000–11349003、双座位、同一混合对手日程的 8 局中，slot 2/4 的金币、分差、胜负、
状态和动作计数逐项一致。

职责固定为“共享市场冲击响应”：unit expert 固定 3、market expert 固定 4，只允许
`market_expert_projection` slot 4 更新。势函数为相对公开企业价值，加上“市场库存低于
10,000 时的己方可变现库存价值”和“稀缺期现金缓冲”；权重固定为 0.35/0.15，终局仍
优化 100,000 尺度金币差，并加入 0.25 倍灾难惩罚。该信号与 Stage29 的固定现金下限
职责不同，目标是识别商品级共享库存冲击并调整采购/出售。

训练 seed 固定为 11350000–11350063，64 fresh seed × 双座位，联赛协议不变；分支预注册
为单 epoch `lr=1e-5/2e-5`，不得事后追加。screen 固定为 11351000–11351015；除 pooled、
Gold-Train、最差金牌和灾难率非退化外，还要求 Exploiter 层非退化，且自身金币或分差的
seed-block CI 下界大于 0。通过后才访问 V54 Gold-Dev（11352000 起）；Gold-Blind 隔离。

Stage 30 已完成：64 fresh seed × 双座位=128 局、92,032 transitions、零异常，配额
52/38/18/14/6，V76 占 9.375%，两个分支均只改变 market slot 4。16-seed screen 基线
为 11/0/21、score rate 34.375%、灾难率 25%。`lr=1e-5` 为 10/0/22、31.25%，自身
金币配对增益 +2,267.3，CI `[+125.9,+5,002.5]`，灾难率降至 6.25%，但 pooled score
明确退化，`REJECT_SCREEN`。`lr=2e-5` 为 13/0/19、40.625%，但灾难率升至 31.25%；
自身金币增益 +667.1，CI `[-2,799.5,+4,526.7]`，分差增益 +2,509.1，CI
`[-2,130.0,+7,154.4]`，同样 `REJECT_SCREEN`。不访问 Gold-Dev/Blind，不登记 expert。

### 13.10 下一独立 expert 的状态边界

Stage 30 的模型只看到当前市场库存/价格以及己方动作历史，不能区分“本来就稀缺”和
“对手刚刚造成的共享市场冲击”。下一轮不得调整 Stage30 权重；应建立独立的市场状态
记忆，显式记录上一观测的逐商品库存与价格变化，再从 Stage20 等价初始化训练新的冲击
响应 market expert。先证明新增状态的零初始化闭环等价，再用 fresh-seed 混合联赛训练。
这属于新的状态契约与动作专家，不是 Stage30 checkpoint 补丁。

### 13.11 Stage 31 市场状态记忆 expert 预注册

Stage 31 从 Stage20 等价 history checkpoint 独立分叉，market slot 2 克隆到 slot 4；新增
36 维 observation-only 市场记忆：上一时点逐商品库存、库存变化、上一价格和价格变化。
新记忆只进入零初始化的 `market_memory_dense`，随后仅接入 market Router/Expert，单位分支
不读取这 36 维状态。初始化 SHA256 为
`8de3b486c5442478db0206a1bcf746b74773912966f31c62c660ef4c9353bc99`。seed
11359000–11359003、双座位 8 局中，与旧 market slot 2 的金币、分差、胜负、状态、动作
计数和非 PASS 单位动作逐项一致。

为隔离状态契约的贡献，奖励和超参数固定沿用 Stage30：`shared-market-shock-relative`，
库存基准/尺度 10,000/1,000，库存与现金权重 0.35/0.15，终局 margin scale 100,000，
灾难惩罚 0.25；只训练 `market_memory_dense` 与 market projection slot 4，其余参数逐位
冻结。训练 seed 11360000–11360063，64 fresh seed × 双座位；分支固定单 epoch
`lr=1e-5/2e-5`。screen 为 11361000–11361015，门控与 Stage30 相同；通过后才访问
V54 Gold-Dev（11362000 起），Gold-Blind 隔离。

Stage 31 screen 中，基线 8/0/24、score rate 25%、自身金币 16,211、灾难率 15.625%；
`lr=1e-5` 为 12/0/20、37.5%、自身金币 22,878、灾难率 6.25%，配对自身金币增益
+6,667，CI `[+1,234,+12,478]`，通过 screen；`lr=2e-5` 因经济 CI 跨 0 淘汰。

进入 V54 Gold-Dev 后，64 fresh seed × 双座位中基线和候选均 0/0/128。候选自身金币
由 9,297.2 提高到 10,060.2，灾难率由 27.34% 降至 25%，但配对自身金币增益 +763.0，
CI `[-918.6,+2,419.4]`；分差增益 +916.8，CI `[-2,950.2,+4,692.2]`。没有实际金牌
胜局，也没有稳定经济 CI，最终 `REJECT_GOLD_DEV`；不登记 expert、不更新 incumbent、
不访问 Gold-Blind。

### 13.12 下一独立完整动作 expert

Stage31 证明市场状态记忆能改善混合池 screen，但 market-only 动作无法跨越 V54 的终局
单位返仓、DROP 与 SELL 协同优势。下一轮不得继续调整市场记忆或奖励权重；应从独立
初始化训练“终局兑现协调”完整动作 expert，让同一 slot 的 unit 与 market projection
共同更新，市场记忆仍只供市场侧使用，安全执行器继续负责合法性。训练仍面对完整混合
池，V54 只在 Gold-Dev 使用，避免把专家训练成 V54 专项 exploit。

### 13.13 Stage 32 终局兑现协调完整动作 expert 预注册

Stage32 从 Stage20 等价 history checkpoint 独立分叉：将 unit expert 3 与 market expert 2
分别克隆到同一新 slot 5，再添加与 Stage31 相同的零初始化 36 维市场记忆。初始化
SHA256 为 `e9f90be063c5998c310c78177c557d3da0a94ad7814daf5d073e2fd25d9cf1c7`；
seed 11369000–11369003、双座位 8 局中，新 slot 5 与旧 unit3/market2 的全部结果和动作
计数逐项一致。

训练只允许 `market_memory_dense`、unit projection slot 5、market projection slot 5 更新；
共享 trunk、两个 decoder、Router、value 与其他 slots 逐位冻结。为隔离联合动作范围的贡献，
奖励继续沿用 Stage31，不调整势函数。训练 seed 11370000–11370063，分支固定单 epoch
`lr=5e-6/1e-5`；screen 为 11371000–11371015。只有通过混合池门控后才访问 V54
Gold-Dev（11372000 起），Gold-Blind 继续隔离。

Stage32 screen 基线为 9/0/23、score rate 28.125%、灾难率 9.375%。`lr=5e-6` 为
7/0/25、21.875%，自身金币增益 −3,124.7，CI `[-7,127.4,+794.2]`，分差增益
−9,860.9，CI `[-19,165.5,-1,645.0]`；`lr=1e-5` 为 8/0/24、25%，自身金币增益
−3,347.1，CI `[-8,649.8,+2,275.8]`，灾难率升至 21.875%。两条分支均
`REJECT_SCREEN`，不访问 Gold-Dev/Blind。

### 13.14 下一独立终局 option 的边界

Stage32 说明整场 720 步的终局回报无法稳定归因到 unit+market 联合动作。下一轮不得
继续缩小学习率或重复整场 PPO；应创建独立终局 option，仅对最后 48 步（672–719）
计算 PPO 更新，并把最终金币差、灾难惩罚和自身兑现结果显式加入该 phase 的最后回报。
训练仍使用完整混合对手池，V54 不进入训练。该 option 必须先独立通过 mixed screen 和
V54 Gold-Dev，才可登记专家或与其他 option 训练 Router。

### 13.15 Stage 33 终局 48 步 option 预注册

Stage33 从 Stage20 等价 history checkpoint 独立分叉，不继承 Stage31/32 的训练参数；把
unit expert 3 与 market expert 2 克隆到 slot 5，并添加零初始化 36 维市场记忆。初始化
SHA256 为 `e9f90be063c5998c310c78177c557d3da0a94ad7814daf5d073e2fd25d9cf1c7`；
seed 11379000–11379003、双座位 8 局中，旧 unit3/market2 与新 unit5/market5 的结果、
动作计数和非 PASS 单位指令逐项一致。

训练固定使用 mixed league iteration 7，64 fresh seed（11380000–11380063）× 双座位；
只保留环境步 672–719，共应产生 6,144 条 transition。同一 seed 的两个座位面对同一
对手，配额固定为 Gold/History/Self-play/Exploiter/Anchor = 52/38/18/14/6 局，按层
标准化 advantage。V54 不进入训练。

奖励预注册为 `shared-market-shock-relative`：opponent impact 1.0、市场库存参考 10,000、
尺度 1,000、流动性权重 0.35、现金权重 0.15；phase 最后一条 transition 显式加入
`tanh(金币差/100000) + 0.25*log1p(自身金币/3000) - 0.25*现金灾难缺口`。只允许
market memory、unit slot 5 与 market slot 5 更新；其余参数逐位冻结。训练分支预注册为
2 epoch、`lr=1e-5/3e-5`，不作事后调参。

screen 固定为 11381000–11381015，使用完整 720 步游戏比较初始化与两条候选；必须同时
通过 pooled、Gold、最差 Gold、Exploiter、灾难率和正向经济 CI 门控。通过者才访问
V54 Gold-Dev（11382000 起，64 seed × 双座位）；Gold-Blind 继续隔离，禁止 Kaggle 提交。

Stage33 原 screen 错误地把 slot 5 强制部署到全局 719 次决策。`lr=1e-5` 虽将 pooled
score rate 从 31.25% 提高到 37.5%、自身金币提高 3,545.7、灾难率从 21.875% 降到
9.375%，但经济 CI 下界仍为负，且对 Gold-Train 仍为 0/0/12；`lr=3e-5` 退化到
21.875%。两者在该“全局部署”合同下均 `REJECT_SCREEN`，不得访问 Dev/Blind。

### 13.16 Stage 34 终局 option 部署合同修正预注册

Stage33 的训练 transition 覆盖人类计数的决策轮 672–719，对应引擎观测 step 671–718；
终局 option 的正确部署必须是 unit `0:3,671:5`、market `0:2,671:5`，而不是整局
强制 slot 5。Stage34 不新增训练、不调整 checkpoint 或阈值，只修正 option 的生效范围。
为防止使用已经观察过的结果选模型，重新固定全新 screen seed 11383000–11383015，
同时评估初始化、`lr=1e-5`、`lr=3e-5`，沿用 Stage33 全部门控。通过者才访问新的 V54
Gold-Dev seed（11384000 起）；原 11381000 screen 不得再用于选择。

Stage34 的调度审计通过：三模型各 32 局，每局 unit expert 3/5 使用 671/48 次，market
expert 2/5 使用 671/48 次。基线为 8/0/24、25%；`lr=1e-5` 为 7/0/25、21.875%，
自身金币 −313.6；`lr=3e-5` 为 9/0/23、28.125%，自身金币 +330.9，CI
`[-1,151.1,+1,934.2]`，分差 −63.3，CI `[-3,738.1,+3,614.3]`。两分支对
Gold-Train 仍为 0/0/12，均未通过正向经济 CI，最终 `REJECT_SCREEN`；不访问 Dev/Blind。

### 13.17 下一主线：多教师动作预训练，而非继续局部 option

Stage29–34 已证明，从弱 incumbent 出发用局部市场/终局 PPO 无法跨越对 Gold-Train
约 12.8 万的整局分差。下一轮停止围绕 slot 5 调时点、学习率或奖励；应从 Gold-Train
行为去重代表采集合法的完整动作序列，训练一个不含规则调用的多教师 BC 动作模型，再把
该 checkpoint 放入同一混合联赛做 PPO。教师标签只提供动作监督，不作为在线 Router；
Gold-Dev/Blind 继续隔离。先用按教师留一验证证明模型学习了跨谱系共同动作能力，再进行
64 fresh seed × 双座位 PPO，避免重新退化为 V76 单教师过拟合。

### 13.18 Stage 35 行为家族均衡多教师动作 BC 预注册

Stage35 不继承任何 PPO/BC checkpoint，从零初始化 timed autoregressive full-action HMoE。
教师只来自 registry 中 `gold_split=train` 的三个行为家族：production-route-router
（V19/V21共享家族配额）、demand-timing-preemption（V32）、procurement-slot-ordering
（V76）。registry SHA256 固定为
`fd8f47b2b06e6ec297b3ca77da350e4e3788464bcaf62341cba34b0f4c034968`；V54 Dev 与
V66 Blind 不得进入数据、epoch 选择或调参。

教师必须从 step 0 开始完整闭环执行，逐局重新加载模块；禁止使用候选状态上的 DAgger
oracle。训练标签使用当前状态下 `normalise → encode → decode` 的 canonical 动作，原始
动作仍真实送入官方引擎以保持教师状态分布。报告必须包含 raw→canonical 修改率、未知
token、DONE/DONE、教师/家族/阶段覆盖和固定 SHA。数据 seed 从 11391000 开始，每个行为
家族固定 8 个 seed group、双座位，共 24 seed group、48 局、预期 34,512 行；对手在
Starter、V21、V32、V76 之间固定轮换，保持 mirror/cross-family/anchor 触发覆盖。

专家标签不包含教师身份，只由 canonical 动作和公开 step 决定：unit slots 0/1/2/4/5
分别负责作物、动物、物流、空闲规划、最后 48 次决策；market slots 3/4/5 分别负责出售、
采购/STOP、最后 48 次决策。教师 ID/家族仅用于分组和审计，禁止进入模型输入。

先并行训练三个 leave-one-family-out fold：8 epoch、batch 128、`lr=3e-4`、value coef 0、
router coef 0.35、action-frequency exponent 0.25；checkpoint 只由剩余家族内部按 seed 分组
的 25% validation 选择，held-out 家族只在训练结束后读取一次。随后用全部三个家族同参数
训练最终 BC。LOFO 只是防单教师过拟合诊断；最终模型仍需在 fresh-seed Starter 闭环和
混合联赛 screen 中证明经济能力，之后才允许进入 64-seed mixed PPO。Gold-Dev/Blind
保持隔离，禁止 Kaggle 提交。

### 13.19 Stage 35 结果：可用初始化，但未通过混合门控

正式采集得到 48/48 个 DONE/DONE 对局、34,512 行；三个行为家族各 11,504 行，
V19/V21 各占生产路线家族的一半。数据 SHA256 为
`501a0d60bf37953a8087d8fe841f9c2be75d469170fccac4c46e67a5b2eccbe3`，raw 与
canonical 均无未知 token，raw→canonical 修改率 20.8565%。独立官方状态等价审计又在
三个家族代表、双座位的 4,314 个 transition 上验证：947 次 canonical 修改后，完整
官方状态 hash 分歧为 0，数据转移合同通过。

三个 leave-one-family-out fold 的 held-out loss 分别为 1.9234（production）、1.8364
（demand）、2.0232（procurement），但 fresh-seed 闭环对留出金牌均为 0 胜，说明离线
动作泛化不能代替策略泛化。全家族 BC checkpoint SHA256 为
`9ae3c948c721839a3bcad19eb639a6d96f8f873d600a6ce67f5cebac3eb2bd55`。

首次闭环发现部署协议错误：逐步 functional expert 标签却继承了 24 步 Router 缓存。
同 checkpoint 对 Starter 在 `router_period=24` 时为 0/0/16、平均金币 14.7；改为逐步
路由后为 16/0/0、平均金币 9,959.1、平均分差 +6,334.3。SequenceAction 的默认部署已
改为 `router_period=1`，旧 factorized/option 模型仍保留 24。严格单专家消融只有
8/0/8、平均金币 3,757.5，证明多专家切换对基础闭环有效。

16 fresh seed × 双座位混合 screen 中，incumbent 与 Stage35 均为 8/0/24、score rate
25%；但 Stage35 平均金币仅 7,841.2，对 incumbent 的配对金币增益 −23,629.8，
seed-block CI `[-54,489.3,-1,061.5]`，灾难率由 12.5% 升至 31.25%，Gold-Train 仍
0/0/12，最终 `REJECT_SCREEN`。不进入 PPO，不访问 Gold-Dev/Blind，不更新 incumbent。

候选状态教师一致性审计定位出状态漂移边界：joint exact 在 step 0–30 为 67.74%，
31–71 为 53.66%，72–215 降至 3.47%，216 以后为 0。下一轮不能调 BC epoch 或 Router
权重；必须补 candidate-state DAgger 数据，重点覆盖 step 72 之后的恢复行为。

### 13.20 Stage 36 候选状态多教师 DAgger 预注册

Stage36 固定以 Stage35 全家族 BC 为 candidate，部署 `router_period=1`。candidate 在官方
环境执行自身动作；每局按 Gold-Train 行为家族等权选择一个状态连续的 shadow teacher，
教师只对 candidate observation 生成 canonical 标签，绝不进入执行动作。V19/V21 继续
平分生产路线家族配额；同一 seed 双座位面对同一 teacher/opponent，每局重载所有模块。

正式 DAgger seed 从 11397000 开始，每家族 8 个 seed group，共 24 seed group、48 局；
对手固定轮换 Starter、V21、V32、V76。收集完整 0–718 步，报告必须同时给出逐阶段动作
一致率、未知 token、DONE、金币与固定 SHA。训练只设一个预注册分支：原教师轨迹与
DAgger 轨迹等权合并，从 Stage35 checkpoint 初始化，4 epoch、batch 128、`lr=1e-4`、
value coef 0、router coef 0.35、action-frequency exponent 0.25、day-start repeat 1；
checkpoint 仍只由合并训练集内部 fresh seed-group validation 选择。

Stage36 screen 固定为 11398000–11398015，沿用完整混合池与 Stage20 incumbent 的同
seed/seat/对手配对门控。必须同时满足 pooled/Gold/最差 Gold/Exploiter 非退化、灾难率
不升、且自身金币或分差 CI 下界大于 0，才允许进入 64-seed mixed PPO。V54 Dev 与
V66 Blind 继续隔离，禁止 Kaggle 提交。

### 13.21 Stage 36 结果：DAgger 闭环退化，基础门否决

两个并行 shard 共完成 48/48 个 DONE/DONE 对局、34,512 行，24 个 seed group 无重叠；
三个家族各 11,504 行，candidate 与 teacher 的 raw/canonical unknown token 均为 0。
DAgger 数据 SHA256 分别为
`c58fcc9126accc11361e4a0ea8b805fa599b20bc5481e9270a8c64292df5b586` 与
`fbedce3369ed4ff5bb1f2b75e357d6ec707348f21c384e4fa9c6522e376fb74b`。

按唯一预注册分支合并 69,024 行训练 4 epoch，checkpoint SHA256 为
`fa2373d069dd19a45553f7b8fbd2be0e07df90a15a3fbe8e0fdbfc9c86fcf206`。同一组 8 fresh
seed × 双座位 Starter 对照中，Stage35 为 16/0/0、平均金币 12,564.1；Stage36 为
11/0/5、平均金币 4,586.5。按 functional contract 增加“终局前禁用 slot 5、最后 48 步
强制 slot 5”的职责安全 mask 后仍只有 9/0/7、平均金币 4,338.7，说明问题不是单一
Router 越界，而是 teacher-forced DAgger 更新破坏了闭环动作分布。

Stage36 最终 `REJECT_BASIC_GATE`，不运行 11398000 mixed screen，不进入 Gold-Dev/Blind，
不更新 incumbent。职责安全 mask 仅对带 `router_granularity=step` 元数据的新 checkpoint
生效，旧 sequence/option checkpoint 不受影响。

### 13.22 Stage 37 多职责 expert 的混合池 on-policy PPO 预注册

停止继续调 DAgger；回到能稳定完成基础经济循环的 Stage35 checkpoint，仅作为训练初始化，
不把它登记为 incumbent 或 gold。Router head、共享 trunk 与 autoregressive decoder 全部冻结，
只训练全部 unit/market expert projection；每条 transition 只更新当时实际路由到的职责
expert，从而让作物、动物、物流、出售、采购等低层动作在 on-policy 状态上分别适应。

训练固定为 mixed league iteration 11，64 fresh seed 11399000–11399063 × 双座位；全局
配额仍为 Gold/History/Self-play/Exploiter/Anchor = 52/38/18/14/6 局，V76 总占比控制在
8%–10%，同 seed 双座位面对同一对手，按层独立标准化 advantage。四个 rollout shard
必须共享一个 64-seed 全局 schedule，不能各自重采样。

奖励固定为 `relative-public-enterprise`，`gamma=0.995`、GAE lambda 0.95、terminal
smooth margin scale 100,000、现金灾难阈值 3,000、灾难惩罚 0.25、自身金币 log 奖励
0.25；BC value 未训练，因此首次 PPO 固定忽略旧 value baseline。只设一个更新分支：
1 epoch、batch 256、`lr=3e-6`、clip 0.1、target KL 0.01、value coef 0、worker
temperature 0.2、joint ratio；不得看到结果后追加学习率。

screen 固定为 11401000–11401015，与 Stage20 incumbent 使用同 seed/seat/对手比较；
必须通过 pooled、Gold、最差 Gold、Exploiter、灾难率和正向经济 CI 门控。通过前不得访问
Gold-Dev/Blind，也不得提交 Kaggle。

### 13.23 Stage 37 实际结果与用户停止指令

四个 shard 最终按同一全局 schedule 完成 64 fresh seed × 双座位，共 128 局、92,032
transition，全部 `DONE/DONE`。实际配额严格为 Gold-Train/PPO History/Self-play/
Exploiter/Anchor=`52/38/18/14/6`，V76 为 12 局、占 9.375%；各层 advantage 分别标准化。

但温度 0.2 的 on-policy 轨迹已经发生全面经济坍塌：4胜6平118负，score rate 5.46875%，
平均自身金币 26.40，平均金币差 −115,065.31，128/128 局终局金币均低于 3,000。由这些
轨迹执行唯一预注册更新后，checkpoint SHA256 为
`18b17040ee73e2e06ab95fa0a7f7f31b527265ffb4ecef7a74ed3d69ab2fc665`；近似 KL
0.000201、clip fraction 0.00497。叶子级参数审计确认只修改 unit/market expert
projection 的 kernel 与 bias 共 4 个参数叶，其余 70 个参数叶逐位一致。

2026-08-30 用户在 fresh-seed Starter 诊断完成 6/8 seed block 时要求停止当前目标和所有
后台任务。该诊断被中断，没有最终 JSON，不作为正式门控证据；预注册的 11401000 mixed
screen 未运行，Gold-Dev/Blind 未访问，incumbent 未更新，也未提交 Kaggle。当前研究状态
为 `STOPPED_BY_USER / NOT_GOLD`，最强已验证 checkpoint 仍为 Stage20。

完整复盘和下一版 PPO 的第一性原理重构建议见 `OVERNIGHT_TRAINING_SUMMARY_20260830.md`。
