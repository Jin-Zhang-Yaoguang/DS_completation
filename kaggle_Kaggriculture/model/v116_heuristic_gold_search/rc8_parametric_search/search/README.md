# R8参数化启发式搜索骨架

结论：这是研究基础设施，不是金牌证据。它不会修改候选、协议或历史模型，也不使用Island-GA compiler/evaluator、Replay动作流、逐步位置流或父代理。

## 候选接口

候选模块必须提供：

```python
def build_executor(params: dict, mode: str):
    # 每局返回一个全新对象；对象必须有 act(observation) 方法。
    ...
```

候选的全部farmer、hands、market动作必须由当前observation和自身在线状态生成。`params`只能表达阈值、日级聚合目标、reserve、优先级等参数，不能表达逐回合动作、逐步位置或等价开环蓝图。

搜索器会哈希候选目录内全部`.py`，因此改动任一候选源码都会使旧缓存失效。

## 参数空间

`space.example.json`使用确定性的shifted-Halton低差异设计，默认生成128个唯一配置。支持：

- `float`、`log_float`：`low/high`
- `int`：含端点的`low/high`
- `choice`：`values`
- `bool`
- `fixed`：`value`

示例文件以候选的字面量`DEFAULT_PARAMS`为完整基底，并通过点路径覆盖拍卖和市场参数；参数hash使用冻结域`v116-rc8-param-spec-v1`。

## 四阶段

- R1 idle race：128进32，8 seeds，双座位。
- R2 idle confirm：32进12，24个全新seeds，双座位。
- R3 gold scout：12进4，2个全新seeds，对18个行为版本金牌，双座位。
- R4 gold confirm：4进1，8个全新seeds，对18个行为版本金牌，双座位。

每个阶段内所有配置使用完全相同的`seed × opponent × seat`任务网格。晋级只在完整CRN块完成后发生。Futility只淘汰失败配置，任何阶段都不会输出“已达金牌”；R4 survivor也只是研究候选，仍须独立运行冻结协议的Development和Confirmation。

默认直接读取同级`protocol/seed_manifest.json`中的冻结`r1/r2/r3/r4` split，并核对8/24/2/8的数量和跨轮不重复。禁止按首店选seed、补样或改变分母；首店只在全部对战完成后按实际observation后验报告。结果按首店、对手和座位分别汇总。

R2执行idle纯胜100%、mean bank不低于70,000、CVaR25不低于55,000的硬门。R3要求纯胜至少65%且至少10个金牌对手的median margin为正；R4要求纯胜至少72%、单侧95% Wilson LCB至少68%，且至少12个对手的median margin为正。轮内排序遵循冻结协议；本实现不做轮内提前成功判定。

## 评测和缓存语义

- 单层`ProcessPoolExecutor`，`workers`强制为1–8，不嵌套进程池。
- 缓存键覆盖`param_hash / executor_hash / evaluator_hash / opponent_hash / seed / seat / mode`。
- 只缓存`DONE`；ERROR会在下次运行重试。
- 每一计划局都写入`games.jsonl`；worker异常和缺失结果生成ERROR行。
- 纯胜率使用`wins / planned_games`，平局和ERROR均非胜。
- Idle层报告`mean bank`、下尾25% CVaR及两者等权目标；金牌层报告单侧Wilson LCB、median margin、下尾10% CVaR margin，同时保留纯胜、719调用和schema违规。
- 缓存命中也重新写入本次原始JSONL，并标记`cache_hit=true`。

## 使用

只检查计划，不启动引擎、不写文件：

```bash
python search.py \
  --candidate ../candidate/candidate.py \
  --space space.example.json \
  --configs 128 --workers 8 --dry-run
```

机制测试：

```bash
python test_synthetic.py
```

实际研究会创建一个全新输出目录，已有目录拒绝覆盖：

```bash
python search.py \
  --candidate ../candidate/candidate.py \
  --space candidate_space.json \
  --seed-manifest ../protocol/seed_manifest.json \
  --cache runs/shared_cache.jsonl \
  --output-dir runs/r8_search_001 \
  --workers 8
```

输出包括`run_manifest.json`、`configs.json`、逐局`games.jsonl`、各阶段summary和最终`summary.json`。Development 64 seeds和Confirmation 128 seeds不属于search runner，必须由正式冻结评测器另行执行；上述产物仍不等于正式金牌证据。
