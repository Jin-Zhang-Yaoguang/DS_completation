# V127a：神经日计划＋状态反馈执行器

V127 神经网络谱系的第一个字母版本。2026-09-15 将 `v127_neural_daily_tasks` 的运行代码和第 26 轮权重原样冻结为 V127a，没有改变策略行为，也没有重新训练。原目录保留此前实验。

后续版本使用 **V127b、V127c……**。纯规则、固定 tape、固定日计划对照不作为 V127 谱系候选；对照可以用于归因。当前尚未实现 b/c。

## 模型堆栈

| 层 | 实现 | 职责 |
|---|---|---|
| 状态编码 | `plan_features.py` | 当前可见商店、市场、双方公开农场、自有库存和时刻；不输入 seed、对手身份或未来信息 |
| 神经网络 | `network.py`、`weights.npz` | 日序嵌入 32 维＋两层 192 维隐藏层＋三输出头，共 658,905 参数 |
| 日任务输出 | `main.py` | 每日一次输出 100 格生产类型、工人数、土地规模 |
| 反馈执行 | `executor.py` | 每步重建任务，喂养/浇水优先，分配工人、预留资源、执行市场单 |
| 合法动作与规则 | `action_space.py`、`rules.py` | 官方规则投影和合法性约束 |

训练使用 JAX/Flax，推理只依赖 NumPy。这里只有一个神经网络，不是多个模型投票；没有调用 y68、其他父策略或教师 tape 生成动作。执行器仍含明确的工程规则，不把整个程序称为端到端神经网络。

## y68 家族门控

- [门控结果](gate_y68_20260915/REPORT.md)
- [冻结清单](gate_y68_20260915/freeze.json)：25 个模型、各 16 seed × 双席位，共 800 局。
- 本地驱动不强制 Kaggle 容器超时；耗时另存逐局记录，胜负仅代表本地动态对战。
- 引擎：本机 `kaggle-environments 1.32.7` 官方 Python interpreter；双方完整策略动态执行。
- seed：1100–1115，沿用 Claude 的历史 gate16 基准，并非新的未见 holdout。
- 每模型必须 32/32 严格胜出才通过；平局不计胜。该阈值沿用 Claude 的全胜门控。
- 所有对手按官方 `get_last_callable` 加载；每局创建新策略实例，异常不替换为 PASS。
- 轨迹主指标：同对手、同席位、不同 seed，同一步整队 farmer+hands 动作完全相同的比例；240 个轨迹对取算术平均。
- 另报市场订单、全部动作、物理位置、逐工人动作和每日计划一致性。

1 表示本面板中轨迹完全相同，0 表示没有同一步的整队动作完全相同。低值不代表每个工人的动作都不同，更不能单凭该值判断是否深度学习；1 也不能证明源码中使用了 tape。

## 复现

从仓库根目录执行：

```bash
.venv/bin/python kaggle_Kaggriculture/model/v127a_neural_daily_tasks/test_tasks.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python kaggle_Kaggriculture/model/v127a_neural_daily_tasks/gate_y68_20260915/evaluate.py --workers 8
.venv/bin/python kaggle_Kaggriculture/model/v127a_neural_daily_tasks/gate_y68_20260915/summarize.py
```

驱动只补齐不存在的对局文件，逐局原子保存。已完成对局作为冻结证据保留；需要重跑时另建结果目录，不覆盖历史。`v127a_policy_bundle.zip` 仅含运行代码和神经权重，本轮没有提交 Kaggle。
