# V116 RC8 参数化候选

这是一个自包含的 ParamSpec 驱动 Hierarchical MoE 候选生成器。本阶段只完成
参数接口、冻结器和机制验证，没有运行大评测。

## 冻结接口

```python
from candidate import DEFAULT_PARAMS, build_executor, freeze_candidate

executor = build_executor(DEFAULT_PARAMS, mode="router")
action = executor.act(obs)

params_hash = freeze_candidate(DEFAULT_PARAMS, "main.py")
```

`mode` 支持 `router`、专家名和 `fixed_<expert>`。冻结后的 `main.py` 仅使用
Python 标准库，不依赖 RC3–RC7、父 agent 或历史模型。

## 参数空间

五个专家为 `wool / dairy_berry / tomato_market / root / grain_egg`。每个专家
只有四个聚合参数：`focus2 / focus3 / donor_template / animal_suffix`。compiler
固定生成 30 日目标，并强制：

- opening 为 WHEAT 8 + MELON 7 + SHEEP 4；
- 三个作物块大小为 15 / 19 / 25，最终作物总数 59；
- 所有专家 WHEAT>=18；
- root CARROT>=8；dairy STRAWBERRY>=12 且 COW>=4；
- tomato TOMATO>=6；wool SHEEP>=5；grain WHEAT>=24 且 GOOSE>=2。

auction 与 market 各 6 维，完整离散集合见 `param_spec.json`。Router 只读取
首次公开 shop：YARN→wool，SMOOTHIE/ICE→dairy，PIZZA/FARMERS→tomato，
PET→root，BAKERY/BRUNCH/unknown→grain。

## 哈希与验证

参数先递归排序，再使用紧凑 UTF-8 JSON；SHA256 域前缀为
`v116-rc8-param-spec-v1\0`。默认参数哈希：

`5db3c00c86e5e86f288ec2be54beb9560bce8ebde427bbb9aa81dc1aa4650e36`

验证结果：

- `candidate.py` 与冻结 `main.py` 均通过 py_compile；
- 13 项参数/compiler/Router/auction/market 机制检查通过；
- 3 项冻结器检查通过；
- cppsim 1.32.7 单步 action schema 检查通过；
- 静态原创性审计通过：仅标准库、无禁止导入或动作表；
- 未运行批量回归、fresh 或金牌 arena。
