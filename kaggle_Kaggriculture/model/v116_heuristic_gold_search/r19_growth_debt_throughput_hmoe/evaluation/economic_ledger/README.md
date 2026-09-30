# R19 evaluator-only exact economic ledger

本目录只做 R17/R18/R19 的经济根因诊断。固定条件：

- engine `1.32.7`
- accounting module SHA256
  `cfc6708a693b04cd34fcb3b8d60c90d54c5c6b8d64bc6b9be1eb900ad5dd8ba2`
- seed `7100`
- 双座位
- router 对 idle
- 单进程、共6局

这不是 P2、Replay 或金牌证据。

## 信息边界

候选先从标准 observation 生成 action，之后 evaluator 才调用
`Game.accounting(player)`。每一步递归检查 observation 不含 `accounting`；三个候选源码也
fail-closed 检查禁止引用 `kagsim_accounting`、`Game.accounting` 或 `sys.modules`。

## 指标

- 精确 `sell_revenue`、`total_spend`
- 逐商品 `produced`、`sold_units`、`discarded`
- 成功 HIRE、成功 BUY_SEED、成功 BUY_ANIMAL
- unit action 和 market request 计数
- 30个日初资产/现金/累计经济快照
- 商品、种子和现金守恒残差

## 可复现命令

```bash
/opt/anaconda3/envs/quant_d1_2026/bin/python3.12 evaluate_economy.py
/opt/anaconda3/envs/quant_d1_2026/bin/python3.12 verify_economic_ledger.py
```

输出：`games.jsonl`、`summary.json`、`run_manifest.json`、`decision.json`、
`test_results.json` 和源码级 `root_cause_report.md`。
