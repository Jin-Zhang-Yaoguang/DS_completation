# opponent_pool_v1:进化线 fitness 分层对手池(2026-09-13,收编线会话供给)

## 目的
GA/FunSearch 的 fitness 若只打固定弱对手或 solo,进化方向会偏离线上生态。
本池按 09-10~12 线上生态分布分层,8 对手 ≈ 当前对手池的代表性切面。

## 口径(fidelity.play spec)
- 引擎:model/v4_demand_race/harness/engine.py(kagsim,0.3s/局)
- 评测:model/v16_online_fidelity/fidelity.py
  - `tape:<json>` 带重放;`sub:<main.py>` 完整包(exec 取 ns 中 dict 序最后 callable,
    与 Kaggle get_last_callable 一致——层叠包注意 `_ENTRY = agent` 显式入口)
- packs/yhay81_0908_extract/v57_main.py 必须 cwd 在该目录跑(读同目录 json)

## 分层清单(建议 fitness 权重)
| 层 | 对手 | spec | 线上占比近似 |
|---|---|---|---|
| 自适应切片 | tapes/ymg_slice0/1.json, nl_SpaTaro*.json, nl_Otter_Vibe*.json | tape: | NEW 家族,当前最强势 ~35% |
| t955 进化切片 | tapes/fta_slice0/1.json | tape: | feel the agi 常态 |
| 我方旗舰 | packs/y67_main.py, y66_main.py | sub: | 2300+ 水平锚点 |
| 公开包 | packs/p955_main.py, v58_rebuild.py, yhay81_0908_extract/v57_main.py | sub: | 老家族大众水平 |
| 抄带者 | tapes/ult_normal.json | tape: | ult 家族(裸抄,弱) |

## 警示(实验实锤,勿踩)
1. 自适应者切片(ymg/SpaTaro/Otter)只是其一局演绎,作"考官"合格、作"弹药"无效;
2. 8-seed 评估与我们门控口径的桥:上线前过包级门控(最近六提交,2 seed 对×双席位全胜),
   工具 model/v58_mosaic/gate_v59.py 可改包表直接用;
3. 商店解锁内生(seed×双方行为),换对手=换商店时序,fitness 波动的一部分来自此。
