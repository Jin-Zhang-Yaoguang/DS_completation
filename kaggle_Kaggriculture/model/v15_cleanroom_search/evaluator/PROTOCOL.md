# V15 黑盒评测协议

## 目标与边界

本协议只回答一个问题：一个完全独立生成、未读取历史模型构造和败局信息的候选，是否同时优于固定锚点、去重后的历史强模型池和冻结父模型。

生成器只收到 `cleanroom/score_only_feedback.schema.json` 定义的匿名聚合比例。原始对局、source、seed、对手身份、谱系映射、动作、margin、败因和 hidden 结果都留在 evaluator-private 路径。本协议是当前共享文件系统上的程序性隔离，不是 OS 权限隔离；真正的恶意隔离仍需要独立用户、容器或 VM。

协议建设阶段只运行了单测和非消费式 dry-run；此后 `attempt_001` development 已完成真实评测并产生匿名聚合反馈，hidden 尚未运行。这里不公开个局、source、seed、对手身份、margin 或其他 evaluator-private 细节。

## 模型池盘点与去重

2026-08-24 22:00:30（Asia/Taipei）使用官方 Kaggle CLI 获取完整提交快照。严格筛选 `publicScore > 2000`：

- 12 条合格提交记录；
- V1 的两次提交为相同版本，合并后是 11 个本地可核验归档；
- 以 canonical serving fingerprint 去除完全相同的可达运行字节，并用归档 SHA、Python code fingerprint 留证；
- 去重后 11 个版本全部进入 hidden 池，不因属于同一行为谱系而删除；
- 11 个版本事前归入 7 个行为谱系；谱系权重固定各 `1/7`，谱系内部版本等权；
- development 只使用每个谱系历史峰值 publicScore 最高的一个冻结代表，共 7 个；hidden 覆盖全部 11 个版本。

谱系和真实模型映射只保存在 `lineage_seal.private.json`。generator 端只看到匿名 pool，不接触该文件。

父模型 `P0` 的 evaluator-private 映射固定为 A2 冻结归档：

- 目录版本：`v12a2_no_shop_gate`；
- Submission：`55713355`；
- 历史 publicScore：`2429.0`；
- 归档 SHA256：`e4c8e07fc607ccff3d9592c5774cbd866a11de096a7b12a7c3c642eda76adbf8`。

primary anchor 与 `P0` 是同一冻结策略的独立进程实例；secondary anchor 固定为 r002 冻结归档。锚点身份不进入 generator feedback。

## 两阶段矩阵

每个候选先经过 clean-room firewall，归档运行时只能包含一个无 import 的自包含 `main.py`。evaluator 严格绑定 firewall candidate seal、归档 SHA、serving SHA 和 policy SHA。

### Development

- 100 个从未暴露的 source；
- 7 个 development 行为谱系，每谱系一个冻结代表；
- candidate 与 `P0` 都在完全相同的 source、席位、对手上运行；
- `100 source × 7 model × 2 seat × 2 policy = 2800` 局；
- 两个直接锚点均在这 7 个代表中，所以 candidate 对 A2、r002 各恰好 200 局；
- 只输出固定 schema 的匿名聚合比例。

### Hidden

- 另 100 个从未暴露、且与 development 不相交的 source；
- 全部 11 个非重复模型、覆盖全部 7 个行为谱系；
- `100 source × 11 model × 2 seat × 2 policy = 4400` 局；
- 两个直接锚点仍各恰好 200 局；
- 只有 development 全门通过且候选字节完全不变时才能预约；
- 预约即消费，运行中断不能重试；
- 同一 serving fingerprint 不能换 attempt 再抽一次 hidden；
- hidden 结果只供 evaluator/orchestrator 作最终裁决，不反馈给下一名 generator。

## 指标定义

单局比赛得分：胜 `1`、平 `0.5`、负 `0`。纯胜率中平局仍在分母，但不计胜。

令：

- `s` 为 source cluster；
- `l` 为行为谱系；
- `m∈l` 为谱系内版本；
- `a∈{0,1}` 为候选席位；
- `C(s,m,a)` 为 candidate 对版本 `m` 的得分；
- `P(s,m,a)` 为冻结父模型 `P0` 在相同 source、席位、对手版本上的得分。

先在 source、版本内合并双席位，再在谱系内对版本等权：

```text
C_sm = mean_a C(s,m,a)
P_sm = mean_a P(s,m,a)
C_sl = mean_(m in l) C_sm
P_sl = mean_(m in l) P_sm
```

再对谱系等权，不按提交数或同族版本数加权：

```text
C_s = mean_l C_sl
P_s = mean_l P_sl
```

模型池得分率与 paired uplift：

```text
pool_score = mean_s C_s
paired_uplift = mean_s (C_s - P_s)
```

因此 paired uplift 的底层每个差值严格绑定同一 source、同一候选席位和同一冻结对手版本；它不是两个不配对总体胜率的差。版本数较多的谱系不会获得更大总权重。

## Source-cluster bootstrap

- 抽样单位是完整 source cluster，不是单场；双席位始终绑定；
- 每个 source 内依次完成双席、谱系内版本平均、7 谱系等权；
- 按 source 日期 `2026-08-18/19/20` 分层；
- 每层有放回抽取与原层相同数量的 source；
- 10,000 次确定性 bootstrap；
- 报告 2.5% 分位数作为 95% CI 下界；
- pool score 与 paired uplift 分别 bootstrap。

## 硬门

候选必须同时满足：

- primary anchor（A2）纯胜率 `>= 65%`；
- 谱系等权 pool score rate `>= 65%`；
- pool source-cluster 95% CI 下界 `>= 60%`；
- 相对 `P0` 的 paired uplift 95% CI 下界严格 `> 10` 个百分点；
- secondary anchor（r002）必须闭合 200 局并报告纯胜率，但用户没有为它设置独立数值硬门；
- 所有任务必须严格闭合、`DONE/DONE`、零 error，且 firewall integrity 为真。

每条原始行必须逐字段匹配预生成 sealed task 的 `task_id/run_fingerprint/pair_id/model_a/model_b/model_a_seat/source`，并固定使用 `kaggriculture-v10-pairwise-closed-loop-1` schema 与 `kaggle_environments.make(kaggriculture)` engine。`reward_a/reward_b/margin_a/score_a` 必须能由双席 rewards 精确重算。JSON 重复 key、重复物理行、外来 task、错误或未完成行一律 fail closed。development resume 仅接受当前 task 矩阵的干净无重复子集；hidden 不允许 resume。

## Fresh source 与 attempt 状态机

只读取官方 source identity metadata；`test` 永久禁止。历史 exposure inventory、panel 和 seed manifest 共同构成已暴露集合，任何历史暴露 source 均不可再分配。

当前审计结果：

- 官方记录 2090；
- 允许的 train/validation 记录 1880；
- 清除历史暴露后初始剩余 956；`attempt_001` development 已预约 100，当前剩余 856；
- 每个完整 attempt 消耗 development 100 + hidden 100；
- 当前最多支持 4 个完全 fresh 的完整 attempt，剩余容量不能冒充第五轮完整验证。

每个 panel 使用独占文件预约，原始记录保存在 `state/private/`。同一 attempt 的重复调用只能得到同一预约；不同 attempt 的已预约 source 必须完全不相交。若容量耗尽，协议必须阻断，不能退回 test、旧 source 或同一 hidden panel。

## 失败后的循环

1. development 未通过：当前 candidate 结束；新建 `fork_turns="none"` generator 和新 attempt，分配新的 development source。
2. development 通过：候选字节冻结，单次消费 fresh hidden。
3. hidden 未通过：当前 attempt 永久结束；不得向后续 generator 提供 hidden 细节或进行同候选调参；回到新的独立 generator。
4. hidden 通过：才具备本地候选资格；是否提交 Kaggle 仍是独立授权动作。
