# R17 evaluator-only accounting engine

本目录从冻结的 `kaggriculture-cppsim` 1.32.7 源码确定性复制并 patch，构建独立模块
`kagsim_accounting`。原源码、原 `.so` 和 R17 候选均不修改。

## 信息边界

- `Game.observe(player)` 与原 1.32.7 完全一致，不含 accounting 字段。
- `Game.accounting(player)` 只能由 evaluator 在 agent 返回 action 之后调用。
- requested 数量由 evaluator 从 action 统计；本 API 只返回真实成功累计量。
- 模块不能被候选 `main.py` 导入，也不能进入 Kaggle 提交包。

真值字段至少包括：

- `produced`
- `sold_units`
- `sell_revenue`
- `total_spend`
- `discarded`
- `successful_hires`
- `bought_units` / `consumed_units`
- `discarded_explicit` / `discarded_end_of_day`
- 独立种子命名空间 `bought_seed_units` / `planted_seed_units`
- `shed` / `carried` / `total_inventory`

## 可复现命令

使用与原 kagsim 构建兼容的 CPython 3.12。若共享环境没有 pybind11，固定版本只安装到
本目录，不修改共享环境：

```bash
python3.12 -m pip install --target _deps pybind11==2.13.6
python build_accounting_engine.py
python verify_accounting_engine.py
```

构建脚本会：

1. 校验 `sim.hpp`、`pyrandom.hpp`、`kagsim.cpp` 的冻结 SHA256；
2. 把源码复制到本目录 `_generated/src/`；
3. 对每个补丁要求唯一精确匹配，任何漂移都 fail closed；
4. 单编译进程输出到 `_module/`；
5. 写出 `build_manifest.json`。

验证脚本写出 `verification_report.json`。测试覆盖：

- 固定合法动作流下，原引擎与 instrumentation 完整719步 observation/reward 相等；
- `accounting` 不进入 observation；
- SELL 请求不等于成交；
- 资金耗尽后的 HIRE 请求不等于成功 HIRE；
- bought/consumed 只在真实成功结算时增加；
- 显式 DROP 与日终自动 DROP 的 shed 溢出拆分及逐商品守恒。

这些测试不是 P2、金牌对战或 Replay 证据。
