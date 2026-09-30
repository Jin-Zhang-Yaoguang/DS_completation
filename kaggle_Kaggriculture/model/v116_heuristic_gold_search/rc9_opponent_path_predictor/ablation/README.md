# RC9 对手路径预测 2×2 消融

这是已暴露 R3 两个 seed 上的机制诊断工具，不是 fresh 验证，也不是金牌晋级证据。它只复用 RC8 `search.py` 的引擎、动作 schema、18 金牌池与 agent 加载逻辑，不修改候选、历史结果或其他目录。

## 冻结设计

- 候选接口：`build_executor(params, mode) -> executor`；executor 必须有 `act(obs)` 和 `diagnostics()`。
- 四个基础模式：`base`、`target_only`、`market_only`、`full`。
- 可选固定路径：`fixed_collision`、`fixed_scarcity`、`fixed_liquidator`；三者和 `full`
  一样同时启用生产与市场 overlay，只把浅树叶固定，用于检验 Router 是否优于固定叶。
- 基础分母：4 模式 × 18 金牌 × 2 seed × 双座位 = **288 局**。
- 加固定路径：7 模式 × 18 金牌 × 2 seed × 双座位 = **504 局**。
- seed 必须精确等于 R3 的 `1641819451, 915926955`；不读取 dev/confirm。
- workers 范围 1–8，默认 8。
- p0064 必须仍是 R3 唯一、首名配置，参数 canonical hash 必须匹配 R3 记录。

`diagnostics()` 至少建议返回：

```python
{
    "base_expert": "root",
    "path_leaf": "collision",
    "path_candidate": "collision",
    "stage_commits": {"5": {"path": "collision"}},
    "market_policy_counts": {"collision_withhold": 12},
}
```

评测会保存 diagnostics 状态变化轨迹；路径覆盖表按上述三个字段及首次商店统计。缺少 `diagnostics()` 会在预注册前失败。

## 两阶段运行

先 dry-run，只校验并打印计划，不写文件、不运行对战：

```bash
.venv/bin/python \
  kaggle_Kaggriculture/model/v116_heuristic_gold_search/rc9_opponent_path_predictor/ablation/ablation.py \
  plan --candidate /absolute/path/to/rc9_candidate.py \
  --output-dir /absolute/path/to/new_run --workers 8 --dry-run
```

确认后预注册。目录必须不存在，防止覆盖：

```bash
.venv/bin/python \
  kaggle_Kaggriculture/model/v116_heuristic_gold_search/rc9_opponent_path_predictor/ablation/ablation.py \
  plan --candidate /absolute/path/to/rc9_candidate.py \
  --output-dir /absolute/path/to/new_run --workers 8
```

如需额外三个固定路径，在 `plan` 增加 `--include-fixed`。正式运行只能使用已冻结 manifest：

```bash
.venv/bin/python \
  kaggle_Kaggriculture/model/v116_heuristic_gold_search/rc9_opponent_path_predictor/ablation/ablation.py \
  run --manifest /absolute/path/to/new_run/preregistered_manifest.json --workers 8
```

runner 会重新计算候选、评测器、引擎、18 个对手、R3 输入和 variant hash；任一漂移即停止。已存在正式结果也拒绝覆盖。

## 输出与口径

预注册文件：

- `preregistered_manifest.json`：完整参数、variant hash、source hash、精确 seed、冻结分母。
- `tasks.json`：逐局 task/cache key；variant 必须进入 cache identity。
- `preregistered_manifest.sha256`：manifest 文件 hash。

正式结果：

- `games.jsonl`：逐局 719 调用、双方 schema、终局 bank/margin、首次商店、diagnostics 轨迹、双方 action trace hash；异常保留为 `ERROR` 且按非胜计入冻结分母。
- `paired_results.json`：每个非 BASE 模式对同 opponent/seed/seat BASE 的 bank、opponent bank、margin、score 配对差。
- `synergy.json`：`FULL - TARGET_ONLY - MARKET_ONLY + BASE` 的协同项。
- `path_coverage.json`：首次商店与 target/market/fixed 路径覆盖。
- `summary.json`：逐模式和总体结果、719/schema 完整性、输出文件 hash、action/diagnostic trace 清单 hash。

即使 mechanics 全部通过，decision 仍固定为 `ABLATION_MECHANISM_DIAGNOSTIC_ONLY`，不得据此注册或宣称金牌。

## 本轮验证边界

`test_synthetic.py` 只做合成与 dry-run：检查 288/504 分母、精确 R3 seed、18 金牌、variant/cache 唯一性、manifest 往返校验、BASE 配对、协同公式、路径覆盖，以及 ERROR 仍留在 planned denominator。它执行 **0 局正式对战**。`synthetic_contract_fixture.py` 仅是接口测试夹具，禁止用于对战。
