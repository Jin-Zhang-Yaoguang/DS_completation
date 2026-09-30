# V14 A2 Shadow 校准报告

## 结论先行

`复制我方 private` 不能作为 A2 shadow 的部署依据；在闭环换序后，它会把候选自己的库存偏移误当成对手库存。合并两个已暴露面板后，方法 A 的 queue exact 只有 **94.006%**，product shed exact 只有 **71.733%**，真实队列可执行量判断 exact 为 **88.734%**。

从初始零 private 出发、用预测动作和当前公开状态按官方引擎前推的方法 C，以及在此基础上增加上一回合公开 market-flow 纠偏的方法 B，在本次校准的 **13,581** 个候选侧可重排机会中均达到：

- current A2 queue exact：13,581 / 13,581；
- SELL multiset exact：13,581 / 13,581；
- 每商品 SELL quantity exact：13,581 / 13,581；
- product shed exact：13,581 / 13,581；
- 按真实 A2 queue 计算的可执行 SELL cap exact：13,581 / 13,581。

推荐预注册实现为 **B / flow-corrected tracker + flow_history conformance gate**。在 shadow 当前队列为 SELL-only 的可执行子集上，它覆盖 **12,583 / 13,581 = 92.651%**，观察到 **0 次 queue false positive**，queue exact 的 Wilson 95% 下界为 **99.969%**。

这仍然只是“对手确实运行封存 A2 字节”条件下的校准，不是未知 Kaggle 对手识别器，也不是未见面板验证结果。

## 数据边界与复现

只使用了此前已经暴露的两套轨迹：

| 轨迹 | 候选 parent | source | 双席游戏 | 候选可重排机会 |
|---|---|---:|---:|---:|
| V13 screen36 strict oracle | A2 | 36 | 72 | 3,645 |
| V13 confirm100 strict oracle | V13C | 100 | 200 | 9,936 |
| 合计 | — | 136 | 272 | 13,581 |

日期只含 `2026-08-18`、`2026-08-19`、`2026-08-20`；split 只含 train / validation，未读取 test outcome。272 / 272 条闭环轨迹的 `margin + eligible_steps + triggered_steps` 均与既有 oracle 日志完全一致。

校准目标固定为封存 A2：

- model id：`v12a2_no_shop_gate`；
- source archive SHA256：`e4c8e07fc607ccff3d9592c5774cbd866a11de096a7b12a7c3c642eda76adbf8`；
- clean submission closure SHA256：`ba82131cbe582e228f16822602b47d670d391fab6b96a3972aed84b3ea9b3830`。

候选侧“可重排机会”在看对手真值前定义：`step >= 96`、候选 market queue 全为 SELL、2–7 个订单、至少两个不同商品、候选 worker 当回合无 DROP / PICKUP / PLACE。

每一步先完成三种 shadow action 与 private estimate，再读取真实 A2 current action/private 作为离线标签。机会表不含 final outcome、margin 或 reward；门控选择没有使用最终胜负。

## 三种 private 输入

### A：own_private_copy

把候选当前 `private` 原样复制给 opposite-seat A2 shadow。它在未干预对称状态下看似合理，但换序改变候选与对手的现金和库存路径后，复制关系不再成立。

### B：flow_corrected

从公开初始零 private 开始：

1. 用候选已提交动作、shadow 预测动作、当前公开 farms / market / town；
2. 调用官方单位动作、市场锁步和日末落仓语义，推进对手 private 点估计；
3. 下一回合用公开 market inventory 的实际值减预测值；
4. 将该残差反向校正到对手 product shed 点估计。

本次 exact-A2 轨迹上，模型前推本身已经精确，B 与 C 没有发生可观测分歧。因此“B 的纠偏比 C 更有效”没有被本实验因果证明；选择 B 是工程上的失配保险，而不是统计优胜。

### C：forward_model

同样从零 private 开始，仅用预测动作与公开状态按官方引擎前推，不做 market-flow 校正。本次结果与 B 完全一致。

## 总体结果

| 方法 | Queue exact | SELL qty exact | Shed exact | Exec-cap exact | Shed L1 均值 |
|---|---:|---:|---:|---:|---:|
| A 复制我方 private | 94.006% | 94.389% | 71.733% | 88.734% | 2.144 |
| B flow-corrected | 100.000% | 100.000% | 100.000% | 100.000% | 0.000 |
| C forward-model | 100.000% | 100.000% | 100.000% | 100.000% | 0.000 |

A 的失效不是均匀噪声，而是结构性错误：

| 候选分支 / A2 分支 | 机会数 | A queue exact | A shed exact | A exec-cap exact |
|---|---:|---:|---:|---:|
| V5 / V5 | 1,870 | 100.000% | 99.893% | 99.893% |
| V5 / V8 | 1,057 | 84.295% | 8.988% | 50.710% |
| V8 / V5 | 1,083 | 78.670% | 7.941% | 59.741% |
| V8 / V8 | 9,571 | 95.643% | 80.378% | 94.034% |

A 的 shed 误差主要集中在 WOOL、WHEAT、STRAWBERRY 和 FERTILIZER；其中 WOOL shed exact 仅 79.685%，WHEAT 为 86.680%。这与 V13C 的 WOOL 路径和换序后的库存分化相符。

B 在三个日期、两个席位和四种候选/A2分支组合上均为 100% queue / shed / exec-cap exact；各分组明细见 `segment_metrics.csv`。

## 覆盖率—精度曲线与预注册门

全部门控特征都只依赖提交前可获得的信息：当前公开状态、我方计划动作、shadow 预测，以及上一回合预测状态与本回合公开状态的残差。禁用特征包括真实对手当前动作、真实对手 private、终局 margin 和终局 outcome。

方法 B 的主要门：

| 门 | 选择数 | 覆盖率 | Queue false positive | Queue precision |
|---|---:|---:|---:|---:|
| base：当前 shadow queue 为 SELL-only | 12,583 | 92.651% | 0 | 100.000% |
| flow_history | 12,583 | 92.651% | 0 | 100.000% |
| history_consensus：再要求 A/B/C queue 一致 | 11,909 | 87.689% | 0 | 100.000% |
| own_shadow：再要求我方与 shadow 的生产动作、market multiset、branch 一致 | 10,688 | 78.698% | 0 | 100.000% |
| mirror_now：再要求双方公开生产状态完全镜像 | 6,740 | 49.628% | 0 | 100.000% |

预注册 `flow_history` 的判定顺序：

1. opponent tracker 从 step 0 连续运行，不允许中途新建；
2. shadow 当前 queue 必须非空且全部为 SELL，worker 无 shed transfer；
3. 上一回合预测 market inventory 与本回合公开 market inventory 完全相等；
4. 上一回合预测的对手公开 farm 与本回合公开 farm 完全相等；
5. 上一回合预测的对手 money 与本回合公开 money 完全相等；
6. 任一条件失败，本回合不干预，回退 parent；生产动作和 SELL 数量始终不得被 queue solver 修改。

部署时建议进一步采用 fail-closed latch：首次 conformance residual 后，本局永久停止 queue 干预。该 latch 比本报告的逐回合曲线更保守，不能用本报告声称覆盖率不变，必须在精确 submission package 上单独复测。

## 不能外推的部分

1. 这是 exposed calibration，不是新 screen / confirm，更不是 Kaggle online 证明。
2. B/C 的 100% 来自“真实对手就是同一份 deterministic A2”这一条件；它不证明能够识别未知对手。
3. conformance 只能在动作执行后的下一回合发现失配，无法撤销第一次错误干预。一般 Kaggle 提交若面对混合对手，仍需对手身份先验、零影响探针或更严格 fail-closed 设计。
4. B 的 market-flow 纠偏无法从 shared inventory 识别 `$1` 价格下不增加 market supply 的成交；若未来面板触发该边界，应直接停用干预或增加独立可识别证据。
5. 本报告只校准 shadow action/private；它不证明 queue permutation 自身能达到 65% 纯胜率，也不授权跳过全新冻结面板。

## 产物

- `calibrate_shadow.py`：逐步复放、三种 shadow、真值标签与分组统计；
- `combine_existing.py`：合并两个已暴露 shard；
- `combined_summary.json`：主结果与门控曲线；
- `combined_games.jsonl`：272 局复现审计；
- `combined_opportunities.jsonl`：13,581 个逐步离线标签；
- `coverage_precision.csv`：门控覆盖率—精度；
- `segment_metrics.csv`：panel / date / seat / branch 分组结果。

主数据 SHA256：

- `combined_games.jsonl`：`c7587ab493d519507a5fe5c019ada2cb2ea4fbac803afb5d5d7c01520df34f8b`；
- `combined_opportunities.jsonl`：`7c5b18c3815fa23e28b93ec2c2fae1da8c1d006b99ce9d377bb5d4eedff96332`；
- `combined_summary.json`：`57c6417854435afc0919c8c3ad232e9f99661a69ba97d79d2226511b075e3819`。
