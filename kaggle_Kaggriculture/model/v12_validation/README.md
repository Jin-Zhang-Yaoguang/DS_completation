# V12 frozen_v5 本地验证协议

这里仅负责最终候选的独立本地验证，不修改 V11 状态、不访问 test、不写
`experiments.md`，也不提交 Kaggle。旧 `frozen_v3/v4` 与 `runs_v3/v4` 只保留为
开发证据，不能 resume 到 v5。

## 固定假设

- 主检验：`v12_incumbent_r002`，父策略 `learned_router`。
- 次检验：`v12a2_no_shop_gate`，父策略为策略等价的独立包
  `v12_incumbent_r002`。
- 共同对手固定 7 类：`baseline_v1`、`baseline_v5`、`baseline_v8`、
  `rule_router`、`v5_topdays`、`v8_topdays`、`v8_conservative`。
- 固定顺序：主检验全部过门后，A2 才能作确认性解释；否则 A2 只作探索展示。

正式只运行统计实际消费的 23 个无序 pair：每个候选 1 个 direct-parent arm，
候选及其父策略各自对 7 个共同对手；重复的 incumbent-control arms 去重。
每 pair 使用相同 100 source、双席位，共 4,600 局。

## 正式 panel 与泄漏保护

正式 panel 沿用最初冻结的 100 source，日期配额为 34/33/33，records SHA256
固定为：

`02d8d87151a525bd3977889153192d73d7729cf25f9528d530115522a6be49d7`

构建器不会重新抽样。若新增暴露 seed 与这 100 个 source 碰撞，会直接失败，
而不是替换 source。当前排除清单覆盖 Router-fit 200、Round 1/2/3、候选两边
package QA/submission clean match、A2 README 中的关键失败 seed，以及 A2 设计时
看过的完整 v3/v4 screen panel。只允许 train/validation，test 数量恒为 0。

两位候选都从 `submission.tar.gz` 的干净解包目录加载。preflight 会重新打开
archive，逐项核对安全相对路径、成员唯一性、size/SHA、submission manifest 与
closure；同时把 incumbent 的 `source_serving_sha256` 与 V11 原 r002 的实时
`model_fingerprint` 三方对齐。combined registry、外部父 registry、评测器实现、
协议脚本和所有冻结资产均有 SHA 封存。

## 统计门

- direct-parent 得分率点估计 `>= 50%`；日期分层 source-cluster bootstrap 95% CI
  下界 `>= 50%`。
- 面对 7 个共同对手的 paired score uplift 点估计 `> 0`，95% CI 下界 `> 0`。
- 任一共同对手的 paired uplift 点估计 `>= -2pp`；其 CI 只报告、不作门槛。
- 4,600 行必须严格匹配冻结 task set，全部 `DONE/DONE`、零 error。

审计粒度是 `registered ordered pair × official source × model_a seat`。fingerprint、
task ID、pair ID、模型方向、`seat_models`、完整 source、奖励、分差和 score 都从
冻结协议独立重建。bootstrap 以 source 为 cluster，并在日期内保持 34/33/33 分层。

## 命令

```bash
cd /Users/a1-6/Desktop/PycharmProjects/DS_completation

# 生成/复核资产，不运行游戏
bash kaggle_Kaggriculture/model/v12_validation/run_validation.sh build
bash kaggle_Kaggriculture/model/v12_validation/run_validation.sh preflight

# 独立红队通过后才可显式解锁；省略 flag 会在任务构造前失败
bash kaggle_Kaggriculture/model/v12_validation/run_validation.sh formal --execute-formal

# formal 完整收集后只读审计
bash kaggle_Kaggriculture/model/v12_validation/run_validation.sh audit
```

当前协议不依赖任何旧 A/B screen marker。正式 panel 只能在 serving closure、对手集、
pair set、阈值和代码全部冻结后打开一次；不得根据正式结果修改参数后重复使用。
