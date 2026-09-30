# V124 蒸馏执行与门控报告

## 结论

V124 已完成启动、训练和预注册的前两级本地验证，最终结论为：

`STOPPED_AT_GATE2 / NOT_GOLD / NOT_AUTHORIZED`

离线多教师合同模型具有稳定预测增量，但独立执行器没有把预算合同兑现成有效的现金、生产和终局闭环。
Gate 2 对 V120 与合并后的 V21/V29/V76 已知家族均为 `0/32`，差距远超可接受的局部回归。因此不再
根据已观察对局补规则，不冻结候选，不消耗 Gate 3 的未触碰对手与 seed，也不提交 Kaggle。

## 1. 数据与泄露审计

- 训练数据仅来自 `top20_cli_training_auxiliary`：255 个唯一 Replay、320 条教师轨迹、20 位教师、
  9,600 个日级样本。
- 255/255 个训练 Replay SHA 校验通过；84/84 个预留在线面板 Replay SHA 校验通过。
- 正式在线面板进入训练的样本数为 0；训练面板与预留面板的 `episode_id + replay_sha256` 交集为 0。
- 每个嵌套验证 fold 都按完整 episode 清除，Inner 与 Outer 的训练/验证 episode 交集均为 0。
- 运行时使用 97 个当前或历史观测特征；教师、seat、seed、episode、Replay SHA、未来动作均未进入
  运行时特征。
- 没有导出逐步动作 tape，目标只保留无顺序的日级预算合同。
- V124 不导入或调用 V76、V120、V123 等父 agent；`strategy_parent=null`，独立性审计通过。

本轮没有发现样本泄露。唯一不能消除的限制是 320 条训练轨迹的实际采集日期都为 2026-09-02，
训练集内部无法形成真正的时间前推盲区。该限制已明确标记为 `TIME_BLIND_DEFERRED`，没有用随机切分
伪装成时间验证；由于 Gate 2 已失败，未来在线时间盲区也没有被打开。

## 2. 行为分族

普通 K-Means 会把教师切成 `18 + 1 + 1` 的退化结构，不满足共享专家至少 3 位教师的预注册门槛，
因此被拒绝，没有降低支持度阈值。随后使用不含收益结果字段的闭环动作指纹做谱聚类：

| 轴 | 家族数 | 轨迹支持 |
|---|---:|---|
| 教师行为家族 | 3 | 96 / 80 / 144 |
| 对手行为家族 | 4 | 60 / 43 / 71 / 146 |

共有 39 个 Replay 同时包含不同教师家族。嵌套验证在持出任一家族时，会从训练侧清除这些 Replay 的
全部样本，避免共享局面泄露。

## 3. HMoE 训练结果

最终模型包含六个独立语义专家：`crop_flow`、`livestock_cycle`、`market_liquidity`、
`land_labor_capacity`、`recovery`、`terminal_liquidation`。每个专家均由 20 位教师和 255 个 Replay
共同支持，超过“至少 3 位教师、8 个 episode”的门槛。

外层验证采用留一教师行为家族，内层选择采用留一对手行为家族；所有超参数只看 Inner Dev，
Outer 分数不参与最终超参数选择。对照基线是按精确经营日给出训练集平均合同的 `BestFixed`。

| 外层教师族 | HMoE 相对 BestFixed 改善 | Router 首选专家数 |
|---|---:|---:|
| `teacher_family_00` | 12.17% | 6 |
| `teacher_family_01` | 8.86% | 6 |
| `teacher_family_02` | 23.86% | 6 |

三组均为正，最低改善 8.86%，中位改善 12.17%，六个专家在每个外层 fold 都实际成为过 Router
首选。Gate 1 因此为 `PASS_TIME_BLIND_DEFERRED`。这些只是离线研究信号，不是金牌证据。

## 4. Gate 2 闭环结果

Gate 2 在查看结果前固定 16 个新 Development seed，每个对手家族双席位共 32 场；验收条件为零错误、
全部 719 次调用、且每个家族纯胜率至少 50%。

| 已知家族 | 胜/平/负 | 纯胜率 | 候选均分 | 对手均分 | 平均分差 |
|---|---:|---:|---:|---:|---:|
| V120 回归门 | 0/0/32 | 0% | 6,180.16 | 157,722.91 | -151,542.75 |
| V21/V29/V76 合并家族 | 0/0/32 | 0% | 14,295.06 | 164,235.28 | -149,940.22 |

64/64 场均完成 719 次调用，运行错误为 0。候选单局得分范围为 201–22,361，中位数 11,511.5。
因此失败不是席位偏差、运行崩溃或少数坏 seed，而是稳定的闭环能力不足。

## 5. 根因判断

本轮证据支持以下区分：

1. HMoE 学会了“在给定状态下，优秀教师下一日大致分配多少作物、牲畜、市场和劳动预算”；
2. 它没有学会“如何在 719 个连续回合里，以正确的空间路径、任务依赖、日内交付和市场顺序兑现预算”；
3. 独立执行器的状态分布很快偏离教师分布，离线合同 MAE 的改善没有转化成闭环收益；
4. 继续针对 V120 或 V21 的失败局增加规则，会把研究重新带回 V123 的已知对手过拟合路径。

所以 V124 验证了“多教师聚合合同可预测”，同时否定了“仅靠日级无顺序合同即可安全蒸馏出金牌闭环策略”。

## 6. 最终门控状态

| 门控 | 状态 | 说明 |
|---|---|---|
| Gate 0 | `PASS_TIME_BLIND_DEFERRED` | 来源、SHA、episode 清除、特征和独立性通过；时间盲区待未来数据 |
| Gate 1 | `PASS_TIME_BLIND_DEFERRED` | 三个教师族均优于 BestFixed，六专家均实际路由 |
| Gate 2 | `FAIL` | 两个已知家族均 0/32 |
| Gate 3 | `NOT_OPENED` | 避免浪费未触碰对手与 seed |
| Gate 4 | `NOT_STARTED_NOT_AUTHORIZED` | 未获 Kaggle 提交授权 |
| Gate 5 | `NOT_STARTED` | 主面板未开始，确认面板保持独立 |

## 7. 后续建议

停止当前 V124-R0 候选，但不终止蒸馏研究计划。后续按
[可持续蒸馏迭代协议](ITERATIVE_DISTILLATION_PROTOCOL.md) 进入 R1：把学习目标从日级总量推进到
“状态—可执行 Option—依赖—短时域结果”的层级，并为每代候选分配全新的 Development 确认块。
R1 只有先证明闭环机制和父子增量，再达到已知家族绝对强度线，才允许进入 512 场金牌门控。

## 8. 证据索引

- [Gate 0 审计](gate0_audit.json)
- [数据清单](dataset_manifest.json)
- [切分清单](split_manifest.json)
- [教师家族登记](teacher_family_registry.json)
- [对手家族登记](opponent_family_registry.json)
- [运行时特征合同](feature_contract.json)
- [专家支持度](expert_support_report.json)
- [训练报告](training_report.json)
- [外层验证报告](outer_validation_report.json)
- [Gate 2 开发报告](development_report.json)
- [候选冻结状态](candidate_freeze_manifest.json)
- [Gate 3 状态](local_generalization_gate.json)
- [线上主面板状态](online_primary_report.json)
- [官方确认面板状态](official_confirmation_report.json)
- [最终决策](decision.json)
- [后续迭代协议](ITERATIVE_DISTILLATION_PROTOCOL.md)
- [候选与面板迭代账本](iteration_registry.json)
