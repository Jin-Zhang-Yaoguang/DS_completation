# Kaggriculture V11 迭代联赛预注册协议

## 目标

以 V10 的 14 个模型为初始池。每轮使用 2026-08-18 至 2026-08-20 的官方环境 seed 进行闭环联赛，由策略优化 agent 基于本轮证据提出一个新完整模型。模型池最多保留 16 个，直到最终池恰有 16 个模型，且 `baseline_v1`、`baseline_v2`、`baseline_v5`、`baseline_v8` 均被真实积分淘汰。

“淘汰 baseline”不能通过改名、复制或人为保护新模型实现。候选必须产生可测动作差异，淘汰只由同轮公共面板上的比赛结果决定。

## 数据边界

- 数据源：三日官方 Episode manifest；历史 Replay 只提供日期、episode、seed 和 provenance。
- 原始开发池：manifest 的 `train` 与 `validation`，合计 1,880 个唯一 seed。
- V10 learned/rule Router 最终拟合使用的 200 个 seed 通过 metadata-only exclusion 文件永久排除；联赛不读取这些 grid 的 reward、score、feature 或动作，首个联赛 cycle 剩余 1,680 个 seed。
- 最终复核池：未参与训练、策略设计或联赛的 clean `test` seed；不参与逐轮淘汰。
- 每轮在当前 cycle 开发池中按日期分层、不放回抽取 100 个 seed。三日配额轮换为 `34/33/33`，避免某一天长期多一个样本。
- 同一轮所有模型对使用完全相同的 100 seed；首个 cycle 固定 16 轮、cycle 内不得复用 seed。
- 若 16 轮后仍未达到终止条件，开启下一 cycle。跨 cycle 允许复用 seed，但每个日期内必须先选择全局使用次数最少的 seed，同使用次数内才由本轮 salt 随机；cycle 内仍不放回，且任何完整 100-seed panel 不得与历史 panel 完全相同。每轮显式记录 `cycle`、`cycle_round`、`reused_seed_count`、逐 seed 复用次数及全局/分日期 min-max reuse。
- 首次激活 pending 候选时，新面板必须与其设计轮面板零 seed 交集；该约束跨 cycle 生效，不能因 cycle 计数重置而失效。
- 面板必须在本轮首场比赛前写入 JSON 并记录 SHA256。看到结果后不得重抽。

## 一轮迭代

每轮包含四个阶段：

1. **激活待评候选**：把上一轮生成的一个 `pending` 候选加入本轮 active pool。第一轮没有待评候选，从 14 个 V10 模型直接开始。
2. **完整联赛**：active pool 内任意两个模型使用本轮全新的公共 100-seed 面板闭环对战；每个 seed 交换先后手，共 200 场。
3. **排名与淘汰**：输出完整积分榜和矩阵。如果 active pool 大于 16，淘汰本轮排名最后一名。然后检查终止条件。
4. **策略优化**：若尚未达到终止条件，策略优化 agent 读取本轮结果和代表性败局，提出并实现一个新完整模型，登记为下一轮的唯一 `pending` 候选。

因此，每轮最终报告中的每个 active 模型都与其余模型在同一公共面板上完成 200 场。新候选不会用其据以设计的同一轮数据立即证明自己；它必须等到下一轮，在与设计轮零交集的 100-seed 面板上首次接受评测。`pending` 候选没有分数，不参与当轮淘汰，也不计入 active pool 的 16 模型上限。

## 计分与排名

- 单场获胜：1 分。
- 单场平局：0.5 分。
- 单场失败：0 分。
- 模型总分：对全部其他模型的 200 场积分之和。
- 主要排序：总分降序。
- 同分 tie-break 依次为：
  1. 同分模型之间的直接对战积分；
  2. 全部比赛平均金币差；
  3. 最差单一对手的得分率；
  4. 运行错误更少；
  5. `model_id` 字典序，确保完全确定性。
- 运行错误或非 `DONE/DONE` 每个 task 跨进程、跨 resume 累计最多三次，不会因重启恢复预算；观察到第 4 条尝试（即使之后出现成功行）立即整轮 hard-fail。仍未成功时输出 `failure_audit.json`，不得把技术失败擅自归因为任何模型的负场，也不得进入淘汰。
- 相同 `task_id` 的完全一致成功重试可以去重；成功结果的语义摘要冲突时整轮 hard-fail。
- 每条计分行都要从冻结 task 重算并核验 schema、官方 closed-loop engine、source、seat、pair、task_id、`DONE/DONE`、reward、margin 与 score；Router 及其任意候选后代必须恰有一个完整健康的递归 Router diagnostics，所选专家必须属于 `selection_eligible`。任一异常整轮 hard-fail。

## 策略优化 agent

策略优化 agent 每轮必须生成以下证据：

1. 当前积分榜、对手分层、日期分层、席位分层和金币差分布。
2. 最低分模型与领先模型的差距来源。
3. 至少三类代表性败局：惨败、窄负、特定谱系反复失败。
4. 对代表性 seed 的动作级重放分析，覆盖：
   - 固定开局和首次路线分叉；
   - 土地、工人、动物和商店路线；
   - 市场出售时机、数量、slot 顺序与价格冲击；
   - 牲畜死亡、库存溢出、终局未清仓等安全事件；
   - 对手行为变化后策略是否仍闭环响应。
5. 一项可证伪的改进假设，只生成一个新模型；明确直接父版本、变更范围、预期改善的失败簇和可能副作用。

### 新模型准入

- 是完整可调用 agent，不是动作片段或固定 TraceAgent。
- `py_compile` 通过。
- 直接父版本必须仍 active 且是设计轮积分榜 leader；proposal、registry entry、runtime `parent_registry` 与 serving 指纹必须一致。
- 仅接受冻结的 `candidate_agent.py` + `mutation_catalog.py` 市场残差 wrapper、`create_agent` factory 和完整 factory kwargs；换模块、陈旧 parent registry 或同名替换一律拒绝。
- optimizer smoke 必须绑定报告绝对路径与 SHA、设计轮 panel 的 6 个 train/validation 来源、候选/父模型 serving 指纹及 registry SHA。`add-candidate` 不信任其中的布尔值，会用同 6 个明确来源、双席位独立重跑候选和父版本各 12 局，共 24 局；全部 720 回合 `DONE/DONE`、零 stderr 才能准入。
- 相对直接父版本存在真实动作差异；逐局等价的改名模型拒绝入池。
- 每代 candidate registry 必须原样继承 Fast/V10 的 manifest、fit exclusion、equivalence、fresh challenge、serving fingerprint 与 pre-test seals；不可变 metadata 变化即拒绝。
- 不读取用户名、episode 结果、test 标签或对手隐藏状态做决策；允许使用比赛接口合法提供给自己的 `obs.private`（例如自己的 shed 库存）。
- 不得修改已经完成比赛的旧模型源码；新版本使用新的 `model_id` 和代码哈希。

## 日志格式

每轮生成 `round_XX/report.md`，结构固定为：

```markdown
# 第 N 轮迭代

## 模型及得分（降序排列）

| 排名 | 模型 | 总分 | 胜/平/负 | 平均金币差 | 最差对手得分率 | 状态 |
| ---: | --- | ---: | --- | ---: | ---: | --- |

## N×N 对战矩阵

| 行模型 \\ 列模型 | model_a | model_b |
| --- | --- | --- |
| model_a | — | W-D-L / 积分 |
| model_b | W-D-L / 积分 | — |

## 策略优化 agent 结论

## 新增模型与准入证据

## 淘汰结果
```

矩阵每个非对角单元格以行模型视角记录 `胜-平-负 / 积分`；对称单元格必须互为胜负反转。

## 终止条件

仅当以下条件同时满足才结束：

1. 活跃模型池恰好 16 个；
2. 四个原始 baseline 均不在活跃池；
3. 最后一轮完整矩阵所有模型对均有 200 场、双席位平衡；
4. 原始 JSONL、面板、registry、积分榜、矩阵和淘汰记录均通过独立验收；
5. 最终 clean test 复核完成，且明确区分“联赛淘汰结论”和“独立泛化结果”。

未满足上述全部条件时，实验保持进行中，不得把部分轮次称为完成目标。
