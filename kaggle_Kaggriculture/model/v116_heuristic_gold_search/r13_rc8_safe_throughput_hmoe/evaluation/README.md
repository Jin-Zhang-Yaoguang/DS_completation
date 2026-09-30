# R13 P2/P3 专用评测器

本目录只评测 `r13_rc8_safe_throughput_hmoe/main.py`。它不读取 Replay，不导入历史
候选作为父策略，也不会修改候选、gold 模型或注册文件。每一局都通过
`build_executor(params=None, mode=...)` 创建新的候选实例，并在冻结的
`kagsim 1.32.7` 中进行双座位实时对局。

## 固定面板

- 六种 mode：`router`、`fixed_wool`、`fixed_dairy_berry`、
  `fixed_tomato_market`、`fixed_root`、`fixed_grain_egg`；
- P2：6 seeds × 6 modes × 双座位 × idle，共 72 局；
- P3：18 gold × 2 seeds × 6 modes × 双座位，共 432 局；
- workers 必须在 `[1,8]`；ERROR、缺局、非 719 calls 均按非胜并使机械门失败；
- 对手 action schema 只作诊断，候选 schema violation 会直接否决。

P2 seeds 固定为：

```text
7100, 7101, 7102, 7103, 1641819451, 915926955
```

P3 seeds 固定为：

```text
1641819451, 915926955
```

## 门槛

P2 必须同时满足：五个 fixed mode 的 mean bank 各不低于 90,000；router mean
bank 不低于 100,000，lower CVaR25 不低于 80,000；全部 72 局的末局实际生产
资产最小值不低于 58；无 ERROR、候选 schema violation，且每局均为 719 calls。

P3 必须同时满足：每个 fixed 专家至少 2 个独占胜局；best fixed 纯胜率不低于
35%；五专家 outcome oracle 纯胜率不低于 80%；router 纯胜率不低于 70%、mean
bank 不低于 110,000；至少 12/18 个对手的 router 中位 margin 为正；router 纯
胜率严格超过 best fixed，且至少存在一个 router 相对 best fixed 的正翻转。

Outcome oracle 仅在同一个 `opponent + seed + seat` 上询问五个 fixed 专家中是否
至少一个获胜，是专家集合诊断，不是可部署策略成绩。

## 只读 dry-run

dry-run 会校验候选语法、自包含契约、六种 mode 接口、engine 版本、对手文件、
任务数和全部来源哈希，但不会创建输出目录或启动任何一局：

```bash
python \
  kaggle_Kaggriculture/model/v116_heuristic_gold_search/r13_rc8_safe_throughput_hmoe/evaluation/evaluate.py \
  --panel p2 \
  --workers 8 \
  --output-dir /absolute/path/to/not-created-dry-run \
  --dry-run
```

运行单测：

```bash
.venv/bin/python -m unittest -v \
  kaggle_Kaggriculture/model/v116_heuristic_gold_search/r13_rc8_safe_throughput_hmoe/evaluation/test_evaluation.py
```

## 正式运行接口

删除 `--dry-run` 才会启动正式面板。输出目录必须不存在，评测器拒绝覆盖。每次
正式运行产生：

- `run_manifest.json`：候选、评测源码、engine、agent factory、全部对手、任务
  计划及门槛的完整 hash；
- `games.jsonl`：逐局原始证据；
- `summary.json`：整体、mode、座位、对手和 P3 专项统计；
- `decision.json`：逐项判定，P2/P3 通过也不是最终金牌证据；
- `artifact_manifest.json`：上述四个结果工件的 SHA-256 与 evidence-set hash。

只有 P2 通过后才应运行 P3；只有 P2/P3 都通过后，才可在独立冻结的 Replay 协议
下打开开发面板。本评测器永不授权 `golden_model.md` 注册。
