# V10 三日官方数据预注册评测协议

## 数据边界

- 来源：Kaggle 官方 `Kaggriculture Episodes Index` 的 `2026-08-18`、`2026-08-19`、`2026-08-20` 三日数据。
- 历史 Replay 只提供日期、官方环境 seed 和动作谱系 provenance；候选之间全部在本地 Kaggle 环境中重新闭环运行，不使用固定 `TraceAgent`。
- 数据按 episode/seed 成组后确定性拆分为 train/validation/test=`1670/210/210`，任何 seed 或 episode 不跨 split。
- test 在专家、规则、特征、超参数和 Router 权重全部冻结前不得读取；最终 14 模型矩阵是 test 的唯一一次开启，结果不再用于调参。

## 预注册模型

- 四个生产根谱系：`baseline_v1`、`baseline_v2`、`baseline_v5`、`baseline_v8`。
- 八个完整变体：`v1_topdays`、`v2_topdays`、`v5_topdays`、`v8_topdays`、`v5_price_slot`、`v8_lead1`、`v8_no_preempt`、`v8_conservative`。
- 两个 Router：`rule_router`、`learned_router`。二者从 step 0 同步影子执行四个完整根专家，只在 step 72 选择一次，之后整季不再切换。
- 所有 14 个模型在正式 test 前冻结。新增模型不得补入同一次 test 矩阵。

## Router 训练与 LOLO

- train、validation 各固定抽取 100 个三日分层 seed。
- 每个 `(seed, seat, opponent root lineage)` 上，对四个候选执行同前缀潜在结果网格；候选必须具有相同 step72 特征和完全一致的 step 0–71 动作。
- LOLO 的留出单位是**对手根谱系**：每折从训练对手中完整移除 V1/V2/V5/V8 之一，但四个可选候选始终保留，避免把“陌生对手泛化”与“缩小动作空间”混为一谈。
- 学习 Router 为 NumPy 线性 ridge value heads，只使用 step72 公开特征；不使用用户名、episode ID、官方历史终局、`private` 字段或 test 数据。
- validation 必须报告最佳固定专家、规则 Router、学习 Router 的得分率、平均金币差、按官方 seed 聚类的 bootstrap 95% CI、选择分布和规则触发原因。
- 单一选择占比过高不自动证明无效，但若 Router 只选择一个专家且没有相对该专家的闭环提升，则按“固定专家伪装成 Router”拒绝。

## 最终 test 矩阵

- 从 test 的 210 个唯一 seed 中按三天分层、固定盐随机选择 100 个。
- 14 个模型任意两个不同模型组成 `C(14,2)=91` 对；每对使用同一 100 seed 并交换席位，恰好 200 场，共 18,200 场。
- 每对报告胜/平/负、得分率、平均金币差、100 个 paired-seed cluster bootstrap 95% CI、三日分项、错误与 `DONE/DONE`。
- 汇总同时报告：四根专家中的最佳固定专家、全部 12 个固定模型中的最佳模型、规则 Router、学习 Router、宏平均得分率、最差对手得分率和选择分布。
- 金币差仅作诊断，不替代胜负得分；Router 的选择不读取对手 ID。

## `tag` 判定规则

- `保留基线`：V1/V2/V5/V8 等仍承担比较、回退或独立生产谱系作用的方案。
- `候选`：相对预注册参照的 paired-score 95% CI 下界高于 50%，且零运行/安全错误；Router 还必须不是单专家退化。
- `研究`：方向有机制价值，但 200 场证据不确定、只在部分谱系有效，或作为必要因果消融保留。
- `无价值`：出现运行/安全失败；或相对直接父版本的 paired-score CI 上界不高于 50% 且平均金币差不为正；或与父版本逐局等价、没有新行为；或学习/规则层退化为单一专家且无可测增益。
- `无价值` 表示不再作为竞争候选继续投入，不删除其失败证据。

