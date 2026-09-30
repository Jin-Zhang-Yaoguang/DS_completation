# V18 两个 P0 的独立 confirm 合同

本目录只评测冻结包，不修改候选、不调参、不提交。

## 冻结对象

父策略是 V17 RC1：archive SHA256 `0c1b9b...2ba6`，`main.py` SHA256 `b52e62...a4b1`。评测器先重新计算两者；任一不符立即退出。

开发与 confirm 直接数据完全隔离：开发只允许直接使用 `2026-08-25` 回放和 seed `50000–50999`；confirm 固定使用 `2026-08-20–24` 的十个行为去重谱系和 seed `61000–61039`，每个 seed 双席。日期列表和 seed 集合都必须零交集，不做静默交集。

十个对手是完整生产路线，经冻结的 v1 live-repair executor 闭环执行。它们按生产结构、购买/种植、土地、雇工、动物照料和前 72 步精确哈希去重；每个 family 局数相同，因此总体就是谱系等权。

## 晋级门

所有门同时成立才是 `PASS`：

- 相对 V17 paired score uplift 至少 `+2pp`，按 seed 聚类 bootstrap 的 95% CI 下界严格大于 0；
- 每个行为 family 的 score uplift 不低于 `-1pp`；
- margin P10 和 CVaR10 均不低于 V17；
- 两个 P0 的单位动作前置条件失败都必须为 0；市场 MPC 的全部市场/资源成交失败必须为 0；任务 DAG 的市场/资源失败必须逐局且总量均不高于同局 V17；最终组合包必须恢复绝对 0；
- raw-loader 最后 callable 必须是 `agent`，无 stdout/stderr；
- Cppsim 与官方 `kaggle-environments==1.32.7` 双席奖励逐局完全相同，双方各 719 次调用且 `DONE/DONE`。

两个候选独立过门，不允许挑最好结果后合并成一项声明。confirm 一旦运行，不得再根据结果修改并重跑同名候选；修改后必须作为新版本并重新预注册。

## 外部冻结锁

- `contract.json`: 见 `LOCK.json` 的 v18-p0-confirm-2 冻结值。
- `evaluate_confirm.py`: 见 `LOCK.json` 的 v18-p0-confirm-2 冻结值。
- `candidate_manifest.schema.json`: 见 `LOCK.json` 的 v18-p0-confirm-2 冻结值。

评测器启动时会自行核对 `LOCK.json`；不匹配则在读取候选结果前退出。锁定之后不得修改 evaluator 或 contract。若必须修改，应升级 `contract_version`，且不能沿用已查看过的 confirm panel。

## 运行

候选先提供符合 `candidate_manifest.schema.json` 的冻结 manifest，然后：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v16_gold_strategy_research/next_gold/v18_eval_contract/evaluate_confirm.py \
  --candidate-manifest /absolute/path/to/candidate_manifest.json \
  --output /absolute/path/to/confirm_result.json
```

快速自检可增加 `--seed-limit 2 --family-limit 1 --bootstrap-reps 200`；快速结果永远标记 `SMOKE_ONLY`，不能用于晋级。
