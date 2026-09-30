# Runner V2：代理配置隐藏真实 seed

`run_match_v2.py` 修复了原 runner 在 `backend=fast` 且未启用 parity 时向代理配置注入真实环境 seed 的问题。原 `run_match.py`、既有对局和冻结机制分析器未修改。V2不新增策略行为、评测种子或完整对局。

- 原 runner SHA：`3a32e264d2df6d3fa419f15aa43d06eaaebb300c5ea864e1e5778a733fcde945`。
- V2 runner SHA：`04d0e5ff740c469264561d43e76ef55bc231770e9c190c026173a07fd160002f`。
- 冻结机制分析器 SHA：`cc4d5c01a482034b55b93422e90b332e7058d6a73a096250dad39cc8eae74963`，保持不变。

## 修复范围

原快路径用 `manifest['configuration'] | {'seed': seed}` 构造代理配置。完整官方解释器的初始化则调用 `resolve_episode_seed`，将真实seed保存在引擎内部 `env.info`，并将 `configuration.seed` 清成 `None`。因此原快路径比官方代理多获得一个隐藏信息。

V2新增 `agent_configuration`：对选定配置深复制，统一把 `seed` 设为 `None`，保留其余字段与值。official 与 parity 路径仍取初始化后的官方配置；纯fast路径取冻结manifest中的官方默认配置模板。真实seed只用于初始化引擎与本地实验登记，不再写入代理配置。输出schema升为 `v125-natural-rng-match-v2`，manifest注明配置可见范围。

官方源码依据：

- `kaggle_environments/utils.py:199`：`resolve_episode_seed`读取、清空、保存seed。
- `kaggle_environments/envs/kaggriculture/kaggriculture.py:249`：初始化时调用该方法。
- `kaggle_environments/envs/kaggriculture/kaggriculture.json`：seed字段说明必须清空。
- `kaggle_environments/agent.py:160`：官方 callable 代理接收环境configuration。

源文件绝对路径与SHA记录在 `fix_manifest.json`，不依赖未经验证的在线版本推断。

## 实际验证

全部8项测试通过，其中一项覆盖8条后端、parity与候选席位组合：

| 后端 | parity | 候选席位 | 物理步数/探针 | 结果 |
|---|---|---|---:|---|
| official | 关 | 0、1 | 1 | 双方代理均见seed=None，观测递归无seed |
| fast | 关 | 0、1 | 1 | 同上，其他配置完全一致 |
| official | 开 | 0、1 | 1 | 同上，初始与下一状态parity一致 |
| fast | 开 | 0、1 | 1 | 同上，初始与下一状态parity一致 |

每条探针在step0由双方测试代理检查配置并返回PASS，step1再次检查后主动抛出 `INTENTIONAL_ONE_STEP_PROBE_STOP`。runner将其捕获为ERROR是预期测试停止，不是一次比赛失败；这些结果只写测试报告，没有写入任何正式 `games.jsonl`。新增完整比赛0，生产候选调用0。

另外验证：

1. 通过官方 `kaggle_environments.agent.Agent` 实际调用函数代理，直接捕获双方可见配置。共15个配置字段：seed为None，其余14个字段与V2逐项相同。
2. 原runner纯fast路径在执行第一个物理步骤前触发“configuration seed leaked”断言，复现原缺陷。
3. 深复制保留全部非seed字段，修改返回的嵌套配置不改变原manifest。
4. 旧三项回归原样绑定到V2执行并通过：同一模块及本地依赖跨席位/新局独立；代理内部TypeError只调用一次；官方structify之后的审计钩子识别建牧场、真实采购/雇工及无效动作。

首轮测试脚手架出现了两处错误：将 `make` 作为类属性后被实例自动绑定，以及向官方 `Agent.act` 传入普通dict而非官方观测Struct。修正只涉及测试脚手架，runner代码未因这些失败改变。原失败日志、报告和测试源码保存在 `initial_test_fixture_failure/`，随后8项全部通过。

## 配置口径的边界

15个字段为：`seed`、`episodeSteps`、`actTimeout`、`runTimeout`、`boardSize`、`startingMoney`、`maxMarketOrdersPerTurn`、`turnsPerDay`、`shedCapacity`、`weedSpawnChance`、`townShopUnlockInterval`、`townShopSellInterval`、`townCenterSellInterval`、`farmHandCostMult`、`marketParams`。

官方“原始Python文件”加载适配器会额外注入 `__raw_path__`（`agent.py:150`），用于表示被加载文件/源码。V125 runner直接加载命名入口 `agent`，没有模拟该文件适配器；这属于已存在的入口加载差异，不是本次seed修复新增的可见比赛信息。本次验证对齐官方callable代理的环境配置值，不宣称已完成Kaggle原始包加载器、Struct属性访问、执行沙箱或overage时间预算的完整仿真。

## 现有结果与机制分析器

只读清点了40条已有V125完整结果：均为 `backend=official` 且 `parity_pass=true`。它们使用已初始化并清空seed的官方配置，因此本次发现的纯fast分支缺陷不影响这40条已保存结果。逐条来源与key已记录在 `fix_manifest.json`；没有重写或重跑这些比赛。

冻结 `analyze_trace.py` 从来源manifest的 `harness.path` 动态导入runner，并用到 `Engine`、`import_engines`、`snapshot`、`first_difference` 四个接口。V2保留四项接口和来源字段。测试按V2 manifest路径动态导入，以R0已保存动作带的前2条动作分别通过V1/V2官方Engine重放，双方完整观测及snapshot完全一致，候选调用0。此项验证的是接口及短片段兼容，没有新建完整V2对局，也没有修改旧manifest来伪装V2来源。

后续使用V2时指定新的evaluation输出目录，由V2在首场前登记自身路径与SHA。旧目录的manifest与既有数据继续保留V1，不能原地升级。

```bash
.venv/bin/python kaggle_Kaggriculture/model/v125_closed_loop_economy/evaluation/test_harness_v2.py

# 后续已授权比赛沿用原CLI，只替换入口文件名并选择新的输出目录。
.venv/bin/python kaggle_Kaggriculture/model/v125_closed_loop_economy/evaluation/run_match_v2.py --help
```

可核对的产物：`test_log.txt`、`validation_report.json`、`fix_manifest.json`。本修复仅提高配置保密一致性，不增加策略强度或金牌证据。
