# K1 内核重写规格（KERNEL_SPEC.md，2026-09-15）

来源：`kernel_audit.py` 对 Majkel1337 16 局原始 replay 的逐步「观测→单位动作」还原，
同口径对比 K1 自跑 6 局。所有规格均为实测，不含推测。

## 实测对照

| 规格 | Majkel | K1（重写前） |
|---|---|---|
| 全天 WORK / MOVE / PASS | 51.8% / 47.2% / 0.9% | 28.3% / 68.5% / 3.2% |
| 移动/工作比 | 0.91 | 2.42 |
| 连续工作格距 0（同格连做） | 50% | 24% |
| 连续工作格距 1 | 34% | 43% |
| 移动目标 = 全局最近任务 | 84% | 71% |
| 离仓单位持麦 | 46%（均 3.3） | 22%（均 4.5） |
| PICKUP 小麦 | 180 次/局 × 2.8 | 45 次/局 × 7.5 |
| PICKUP 肥料 | 0 次/局 | 26 次/局 × 7.2 |
| 动物格首动作 | FEED 58% / COLLECT 21% / HARVEST 14% / CARE 7% | FEED 39% / CARE 32% / COLLECT 19% / HARVEST 11% |
| h20 工作率 | 45% | 14% |

## 内核规则（按实测翻译）

- **M1 同格清空**：单位所在格有可做任务时继续做完，不离开。
- **M2 格内次序**：动物格 FEED → COLLECT_FERTILIZER → HARVEST → CARE；
  作物格 HARVEST → WATER → FERTILIZE。
- **M3 纯就近派活**：非生存任务不分优先级桶，全局按（距离, 次序）贪心匹配；
  目标按「格」占用（一格一人），避免多人奔同一格。
- **M4 生存任务先行**：濒死喂养/濒枯浇水仍先于就近匹配（保零饿死红线）。
- **M5 小批高频领麦**：途经仓库且持麦 < 2 时领 3 个；不做大批补给。
- **M6 肥料不进仓**：施肥只由随身携带者执行，肥料来自收肥动作；不从仓库领肥。

## 布局模板（d12 各格众数，Majkel 16 局）

```
STR MEL STR WHE STR STR STR STR STR STR
STR STR STR STR STR STR STR STR STR STR
STR WHE MEL WHE PAS PAS PAS STR STR WHE
STR WHE WHE WHE PAS PAS PAS STR STR STR
STR WHE PAS PAS PAS PAS PAS PAS STR STR
WHE WHE WHE PAS PAS LOC LOC LOC LOC LOC
WHE WHE WHE WHE PAS LOC LOC LOC LOC LOC
WHE WHE WHE WHE PAS LOC LOC LOC LOC LOC
WHE WHE WHE WHE EMP LOC LOC LOC LOC LOC
WHE WHE WHE WHE EMP LOC LOC LOC LOC LOC
```

牧场环绕仓库集中于中心；草莓占北侧两行与 NE 象限；小麦占 SW 象限；SE 从不解锁。
布局对齐列为内核第二阶段（先对齐执行规则 M1-M6，再对齐空间模板）。

## 验收口径

新内核以 `scheduler_mode="majkel"` 接入，重跑 `kernel_audit.py` 逐项对比上表，
再跑 `eval_vs_y68.py`（胜率 + 重合度）与 `gate_k.py`。
