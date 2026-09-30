# dd 家族实验记录

目标：3 个独立通过全 y68 家族门控与新种子确认的模型。当前没有模型通过。

对手池：33 个源码哈希不同的 y68，官方引擎 1.32.7。开发结果不能代替门控。

| 版本 | 技术变化 | 开发面板 | 胜/局 | 平均胜差 | 状态 |
|---|---|---|---:|---:|---|
| dda | state-conditioned joint-action prototype behavior cloning | dev02 / 4 seeds | 8/32 | -10,533.16 | DEVELOPMENT_FAILED |
| ddb | Outcome-weighted prototype behavior cloning | dev01 / 4 seeds | 0/32 | -34,651.16 | DEVELOPMENT_FAILED |
| ddc | Compatibility-constrained outcome distillation | dev01 / 4 seeds | 0/32 | -20,525.94 | DEVELOPMENT_FAILED |
| ddd | Actual-inventory liquidation ablation | dev01 / 4 seeds | 4/32 | -7,075.19 | DEVELOPMENT_FAILED |
| dde | New-teacher-only joint-action behavioral cloning | dev01 / 4 seeds | 0/32 | -56,108.25 | DEVELOPMENT_FAILED |
| ddf | Hierarchical local-action distillation | dev01 / 1 seeds | 0/8 | -118,108.62 | DEVELOPMENT_FAILED |
| ddg | Daily ordered-task distillation with resource feedback | dev01 / 1 seeds | 0/8 | -92,828.00 | DEVELOPMENT_FAILED |
| ddh | Release-time constrained task distillation | dev01 / 1 seeds | 0/8 | -124,335.00 | DEVELOPMENT_FAILED |
| ddi | Whole-trajectory distillation control | dev01 / 4 seeds | 0/32 | -61,836.88 | DEVELOPMENT_FAILED |
| ddj | Autoregressive decision-tree policy distillation | dev01 / 1 seeds | 0/8 | -136,862.25 | DEVELOPMENT_FAILED |
| ddk | Daily plan distillation with spatial task bundles | dev01 / 1 seeds | 0/8 | -96,252.00 | DEVELOPMENT_FAILED |
| ddl | Task-bundle distillation with committed-animal feed | dev01 / 1 seeds | 0/8 | -71,610.25 | DEVELOPMENT_FAILED |
| ddm | Single-team joint-action distillation: M & M & P & Q | dev01 / 1 seeds | 0/8 | -17,758.62 | DEVELOPMENT_FAILED |
| ddn | Simulator-ranked trajectory distillation | dev01 / 4 seeds | 24/32 | 5,306.38 | DEVELOPMENT_BASELINE |
| ddo | Single-team joint-action distillation: Artem The Farmer 🍅 | dev01 / 1 seeds | 0/8 | -4,217.62 | DEVELOPMENT_FAILED |
| ddp | Inventory-transition distillation | dev01 / 4 seeds | 18/32 | -1,198.28 | DEVELOPMENT_FAILED |
| ddq | Distilled plan with demand-safe sale preemption | fresh01 / 8 seeds | 24/64 | -5,264.56 | DEVELOPMENT_BASELINE_NOT_ROBUST |
| ddr | Distilled plan with maintenance-safe fertilizer conversion | dev01 / 4 seeds | 24/32 | 5,044.47 | DEVELOPMENT_FAILED |
| dds | Production-substitution trajectory distillation | dev01 / 4 seeds | 0/32 | -34,605.47 | DEVELOPMENT_FAILED |
| ddt | Task-preserving local residual distillation | dev01 / 4 seeds | 18/32 | 1,682.06 | DEVELOPMENT_FAILED |
| ddu | Counterexample-selected trajectory distillation | combined01 / 12 seeds | 56/96 | 1,355.00 | DEVELOPMENT_FAILED |
| ddv | New-teacher simulator-guided trajectory distillation | — | — | — | DEVELOPMENT_FAILED |
| ddw | Hierarchical animal-allocation distillation | broad01 / 8 seeds | 48/64 | 1,754.41 | DEVELOPMENT_BASELINE_NOT_ROBUST |
| ddx | Animal-inventory liquidation ablation | broad01 / 8 seeds | 40/64 | -2,581.53 | ABLATION_COMPLETE |
| ddy | Seed-separated hierarchical animal allocation | combined01 / 12 seeds | 72/96 | 2,853.28 | DEVELOPMENT_BASELINE_NOT_ROBUST |
| ddz | Batch-resolved portfolio animal distillation | dev01 / 4 seeds | 0/32 | -42,126.81 | DEVELOPMENT_FAILED |
| ddaa | Counterfactual advantage distillation for animal allocation | value_dev01 / 20 seeds | 25/40 | -169.38 | DEVELOPMENT_FAILED |
| ddab | Harvest-compatible crop substitution in distilled tasks | dev01 / 4 seeds | 24/32 | 4,991.78 | DEVELOPMENT_FAILED |
| ddac | Slack-bounded recovery of distilled planting tasks | dev01 / 4 seeds | 24/32 | 5,075.16 | DEVELOPMENT_BASELINE_NOT_ROBUST |
| ddad | Committed-seed deficit recovery after settlement | broad01 / 16 seeds | 70/128 | -381.99 | DEVELOPMENT_BASELINE_NOT_ROBUST |
| ddae | Cash-causal market ordering for distilled commitments | broad01 / 16 seeds | 18/32 | -201.16 | DEVELOPMENT_BASELINE_NOT_ROBUST |
| ddaf | Re-ranked hierarchical trajectory distillation | — | — | — | SEARCH_COMPLETE_NO_PROMOTION |
| ddag | Demand-window market planning over a distilled production policy | broad01 / 16 seeds | 18/32 | 306.38 | DEVELOPMENT_BASELINE_NOT_ROBUST |
| ddah | New-teacher distillation with cash and seed recovery | — | — | — | SEARCH_COMPLETE_NO_PROMOTION |
| ddai | Replay-schedule animal value planning | broad01 / 16 seeds | 14/32 | 447.59 | DEVELOPMENT_FAILED |
| ddaj | Distilled labor-window crop rescheduling | broad01 / 20 seeds | 24/40 | 1,897.65 | ABLATION_INACTIVE |
| ddak | Replay-completion residual labor dispatch | broad01 / 20 seeds | 24/40 | 2,034.80 | DEVELOPMENT_BASELINE_NOT_ROBUST |
| ddal | Mature-farm daily task distillation with reactive dispatch | dev02 / 4 seeds | 0/8 | -56,534.50 | DEVELOPMENT_FAILED |
| ddam | Cash-feasible joint animal distillation | broad01 / 20 seeds | 24/40 | 2,104.50 | DEVELOPMENT_BASELINE_NOT_ROBUST |
| ddan | Day-horizon procurement reserve for distilled upgrades | broad01 / 20 seeds | 24/40 | 1,371.38 | DEVELOPMENT_FAILED |
| ddao | Budgeted partial-opening portfolio distillation | — | — | — | DEVELOPMENT_FAILED |
| ddap | Joint-intent faithful trajectory distillation | — | — | — | DEVELOPMENT_FAILED |
| ddaq | Executed-event hierarchical new-teacher distillation | — | — | — | DEVELOPMENT_FAILED |
| ddar | Joint procurement composition regression distillation | expand01 / 16 seeds | 18/32 | 51.09 | DEVELOPMENT_FAILED |
| ddas | Executed joint procurement composition distillation | broad01 / 20 seeds | 24/40 | 1,991.15 | DEVELOPMENT_FAILED |
| ddat | Executed inventory-sale policy distillation | expand01 / 16 seeds | 14/32 | -1,402.97 | DEVELOPMENT_FAILED |
| ddau | Replay-distilled market-flow value control | expand01 / 16 seeds | 15/32 | -415.44 | DEVELOPMENT_FAILED |
| ddav | Distilled opponent-flow competitive sale control | broad01 / 20 seeds | 20/40 | 1,323.50 | DEVELOPMENT_FAILED |
| ddaw | Joint replay-production genome search | — | — | — | DEVELOPMENT_SEARCH_FAILED |

## 已确认的边界

- dda/ddb/ddc/ddd/dde/ddf 是非参数原型模仿或执行对照，不是神经网络权重蒸馏。
- ddg/ddh 是从回放提取任务顺序的原型；简单时序压缩与补资源尚未成功。
- ddi 是固定整局动作计划的研究对照，明确不计入三个独立模型。
- ddj 学习决策树条件策略，运行时不读取示范状态和动作表。
- ddn 对 M & M & P & Q 的 146 条完整教师计划进行了 868 局开发筛选，选出原型 35。
- ddq 在该计划上提前出售部分已有库存；原 4 seed 开发集 24/32 胜，不能称为稳定胜出。
- 每版开发面板的 seed 数见表，实际 seed/席位/对手见 runs/<run>/plan.json；同名 broad01 在不同版本不一定采用相同面板。
- 旧教师训练 271 局、新教师训练 121 局的源文件 SHA 和抽样时间对齐均已审计。
- 旧教师训练/验证/测试：271/57/53；新教师 193 局已重新切分，不能再称为 dd 的版本外推测试。
- 所有开发 seed 已用于研发；只有冻结候选后的独占新种子面板可作为门控和确认。
- 无 Kaggle 提交；没有把保存文件、完成训练或通过接口检查算作实战成功。

稳定标准与版本说明见 [家族说明](README.md)，冻结对手和种子协议见 [protocol.json](protocol.json)。
逐局现金、动作轨迹、推理计时和源码数据哈希位于每版 runs/<run>/。

更新：2026-09-19T19:56:14.605327+00:00
