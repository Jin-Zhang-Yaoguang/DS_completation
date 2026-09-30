# 940 单次内部经济函数 profile

此目录只归因已打开的人工 `48_strawberries_day8_funded_s0` 状态。原型源码 SHA 为 `940a7438f57d10978ef93ee2eb4168a04e644f0fa8531180f1c960719f5471f0`；默认参数逐项锁在 `config.json`，不改配置或源码。

输入包含完整 `fixtures_v1_snapshot.json`、逐字段相同的 `fixture_case.json` 和原始单文件快照 `prototype_940.py`。这是 day8/h0/step192/seat0、48 株已到位草莓、现金100000的人工条件，未证明自然可达。

运行必须取得根针对 `freeze_manifest.json` SHA 的 release。仅定义加载一次、`new_state(obs)` 一次、`economic_plan_prefix(obs, st)` 一次；完整 agent、引擎、新比赛调用均为0。前两项在 profiler 之外。脚本本身不调用官方解释器，不读取其他样本。

`run_once/` 的原子创建充当一次执行锁；无论成功、中断或异常，都不删除该目录、不自动重试。内部经济函数有30秒 SIGALRM 保护；触发时先停 profiler，保存当时 Python 堆栈，再抛异常。finally 优先保存原始 `raw.pstats`，随后生成 `function_stats.json` 和按累计/自身时间排序的文本。无法导出会另存错误，不补跑。

每类 self 时间按互斥分类求和；cumulative 时间包含子调用，不能相加或当作独占百分比。外部 copy/json 按文件分组；内联源码按冻结 AST 顶层函数/类的行号区间归属模块，包括嵌套函数、方法和推导式。类别是函数归档口径，`json` 的 C 内部工作可能记在 Python 调用者内；原始逐函数 pstats 才是复核依据。中断画像只说明已执行前缀，不代表整个计划占比。带 profile 的耗时不能充当无 profile 性能门，也不证明唯一热点。

运行后保存原/后输入 SHA 核对、实际尝试计数、状态字段摘要、是否返回计划、异常、保护堆栈及部分 pstats。即使路线函数在中断前返回过可行证书，也不代表整体计划、新增许可或实际生产完成。

根放行文件格式如下（此示例不是授权）：

```json
{
  "schema": "r10-performance-940-release-v1",
  "root_execution_release": true,
  "freeze_sha256": "根复核后的 freeze_manifest.json SHA256",
  "run_id": "day8_funded_s0_single_internal_profile"
}
```

根核验后唯一执行命令：

```text
.venv/bin/python kaggle_Kaggriculture/model/v125_closed_loop_economy/research/r10_service_calendar/stage_b/performance_940/profile_once.py --release <根签发的release路径>
```

准备阶段只做 AST/语法检查，没有定义加载或任何候选、solver、checker、官方函数调用。源和输入冻结后不再修改；优化另立实现与等价控制。
