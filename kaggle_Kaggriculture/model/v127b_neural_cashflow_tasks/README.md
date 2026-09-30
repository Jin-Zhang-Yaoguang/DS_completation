# V127b：神经日计划＋跨日资金与任务可行性执行器

V127b 沿用 V127a 的 658,905 参数网络、状态编码及权重。网络继续每天输出生产格子、工人数和土地目标；本版修改资金约束、采购顺序、增长任务期限和实际成交反馈。**没有重新训练网络，执行器带来的改善不算作网络训练收益。**

## 改动

1. **跨日预算**：根据已持有和待放置的动物、已有作物成熟时间及网络目标估算到下一次回款的资金需求。为未来重雇和饲料预留现金，购买新增牲畜时立即计入其维护负债。饲料按当前市场和自身边际需求报价，再加 25% 工程压力系数。
2. **收入确认**：未实现的未来产出不提前抵作现金。出售当前仓库产出后，优先当日饲料与雇工，再推进网络要求的短周期作物、动物、长周期作物和土地。
3. **劳力准入**：按实际工人数估算日维护工作量，为任务和路程留缓冲。它是近似检查，不是对完整路线可行性的数学保证。
4. **增长期限**：新增播种留出浇水时间；新增动物留出喂养所需的时间。存量维护仍由原优先级任务调度执行。
5. **失败反馈**：对比上一步投影成交与当前实际工人数、仓库和种子，记录缺口；每步按实际状态重新计算未完成目标、可用预算与延期原因。日内反馈作用于执行器，网络仍每天更新一次；没有宣称模型已学会读取这些新增原因码。

网络目标保持不变，执行器可以延期不可行的新增任务。纯固定日计划只作研究对照，不作为 V127 家族候选。V127a 原文件与门控记录保留。

## 对照与门控

- 开发：2 个开发 seed × 双席位 × y68a/y68v × 4 组，共 32 局。
- 四组为原版、只加跨日预算、完整 V127b、固定日计划配完整执行器。固定日计划来自此前训练集按日众数，未使用本次结果制作。
- 完整门控：25 个与 V127a 相同的冻结 y68 模型 × seed1100–1115 × 双席位，共 800 局。每个对手 32/32 严格胜出才通过。
- 新 seed 确认：16 个不同于开发/历史门控的 seed × 双席位 × y68a/y68v × 原版/V127b/固定日计划，共 192 局；此面板不用于调参。
- 全部使用官方 Python 1.32.7 动态对战，未强制 Kaggle 容器超时。对手按官方最后 callable 入口加载，每局状态独立，异常不替换成 PASS。
- 完整动作、市场单、实际位置、日计划和反馈存于 `research/*/games/*.json.gz`。轨迹一致性沿用 V127a 同席位、跨 seed、整队动作逐步相等的口径。

研究结果见 [RESULTS.md](RESULTS.md)。细分表见 [门控报告](research/REPORT.md)。

## 文件

| 文件 | 用途 |
|---|---|
| `main.py`、`weights.npz` | 原样保留的神经日计划推理 |
| `budget.py` | 维护负债、跨日现金需求和劳力近似检查 |
| `executor.py` | 完整 V127b 执行器；reserve_only 开关仅作开发归因 |
| `research/plan.json` | 预先登记的面板和候选 |
| `research/candidate_freeze.json` | 门控前冻结代码、权重及对照哈希 |
| `research/development_source/` | 开发时实现快照 |
| `executor_a.py`、`time_plan.npz` | 仅作评估对照，不在部署包内 |
| `v127b_policy_bundle.zip` | NumPy 运行代码和神经权重，无评估对手 |

## 复现

在仓库根目录运行：

```bash
OPENBLAS_NUM_THREADS=1 .venv/bin/python kaggle_Kaggriculture/model/v127b_neural_cashflow_tasks/test_tasks.py
OPENBLAS_NUM_THREADS=1 .venv/bin/python kaggle_Kaggriculture/model/v127b_neural_cashflow_tasks/test_budget.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python kaggle_Kaggriculture/model/v127b_neural_cashflow_tasks/research/evaluate.py --panel gate --workers 6
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python kaggle_Kaggriculture/model/v127b_neural_cashflow_tasks/research/evaluate.py --panel fresh --workers 2
```

对局驱动逐局原子保存并跳过已有记录。开发结果不得伪装成新确认；改模型需另立版本、重新冻结。这里没有任何 Kaggle 提交。
