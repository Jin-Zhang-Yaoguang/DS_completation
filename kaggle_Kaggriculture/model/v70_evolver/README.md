# v70_evolver — 调度器参数进化框架

启发式调度器(vendored `scheduler.py`,v55 谱系)+ 遗传算法参数搜索。
「机器搜数值、人改结构」双层循环中的机器层。

## 模块

| 文件 | 职责 |
|---|---|
| `space.py` | 参数空间(32 维)与遗传算子(mutate/crossover/clamp) |
| `arena.py` | 评分器:配置 × 对手池 × seed → 对战 margin(进程安全 worker) |
| `evolve.py` | 主程序:种群循环、精英保留、断点续跑、历史留档 |
| `plot.py` | 评估曲线 history.jsonl → evolution_curve.png |
| `scheduler.py` | 被优化的调度器本体(优先级贪心;改结构在这里) |
| `opponents.json` | (可选)对手池 spec 列表,缺省用 arena.default_opponents |

## 用法

```bash
cd v70_evolver
python evolve.py --generations 10                # 首跑;再次运行自动从断点续
python evolve.py --generations 100 --run big     # 独立实验互不干扰
python plot.py                                   # 出评估曲线
```

产物在 `runs/<run>/`:`best_cfg.json`(历史最优,供接管层/带生成消费)、
`history.jsonl`(曲线数据)、`state.json`(断点)。

## 约定

- 评分口径 = 全程调度器对战 margin(候选上线仍须过六包门控,门控在 v58_mosaic/gate_*)。
- 对手池换血(加入新强带/新包)后,历史分数不可比,请换 `--run` 名。
- 改 `scheduler.py` 结构后同理:换 run 名重跑,防止旧断点里的种群搭错车。
- 参数加减:改 `space.py` 的 SPACE 即可,`clamp` 会为旧配置补缺省值。

## 已知基线(2026-09-10)

- v55 手工调参:best_cfg_58k(solo 稳态 58k;对强池 margin ≈ -85k)
- 首轮 10 代(pop32, seeds 901/902, 对手池含 y63/P955):-85,377 → -73,590,未收敛。
