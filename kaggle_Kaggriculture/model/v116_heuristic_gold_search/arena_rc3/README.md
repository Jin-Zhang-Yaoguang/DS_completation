# V116 Arena RC3

通用、只读的候选对战评测器。它不会修改或注册候选模型，也不会写
`golden_model.md`。V29/V30 已知为 V21 行为别名，不进入 18 版本权重；实际运行还会按
同 seed、同座位下的完整对手动作轨迹再次聚类。

## 快速使用

仅校验环境、文件、哈希、seed 和任务规模，不运行对局、不写文件：

```bash
/path/to/python3.12 arena.py --candidate /absolute/path/to/main.py --profile smoke --dry-run
```

小型锚点烟测（2 seed × 6 对手 × 双座位，共 24 个 Router 对局）：

```bash
/path/to/python3.12 arena.py --candidate /absolute/path/to/main.py \
  --profile smoke --workers 4 --output-dir /new/path/arena-smoke-001
```

Development 默认为 64 seed × 18 版本 × 双座位 = 2,304 个 Router 对局；
Confirmation 默认为 128 × 18 × 2 = 4,608 局。`workers` 强制限制在 1–4。
当前本地 `kagsim` 是 CPython 3.12 扩展，因此实际运行须使用匹配的 Python 3.12；
解释器不匹配时会在 preflight 明确失败，不会开始对局。

## 固定专家与 Router 贡献

可重复传入独立固定专家文件：

```bash
--fixed-expert wool=/path/fixed_wool.py --fixed-expert dairy=/path/fixed_dairy.py
```

也可在候选源码顶层提供不执行即可读取的字面量：

```python
ARENA_FIXED_EXPERTS = {"wool": "fixed_wool.py", "dairy": "fixed_dairy.py"}
```

评测器按完全相同的 `(opponent, seed, candidate_seat)` 汇总 Router 相对每个固定专家的
纯胜率 BEU、正 flip、负 flip 和净 flip。没有固定专家时，Router 贡献门记为未知，不会
误判为通过。

## 输出与口径

新运行目录包含：

- `run_manifest.json`：候选、固定专家、18 个对手、评测器、适配器和 C++ 模拟器哈希；
- `seeds.json`：冻结 seed；
- `games.jsonl`：每局状态、719 calls、schema、收益、margin 和动作哈希；
- `summary.json`：按版本、运行时行为簇、座位和候选模式汇总。

主指标固定为 `wins / planned_games`。平局、ERROR、worker 丢失结果都不是胜局；不会从
分母删除。结果目录存在时直接拒绝覆盖。

该工具只提供本地对战证据。即使 Confirmation 面板达到 75%，也不能单独证明原创性、
提交包一致性、官方 Python 复算一致性或金牌资格，更不能替代 `gold_protocol.md` 的其余门。
