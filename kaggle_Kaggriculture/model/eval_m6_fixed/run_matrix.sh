#!/bin/bash
# 修复 harness（逐步揭示商店）后的 M6 核心矩阵重跑
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
OUT=$W/model/eval_m6_fixed
V120=$W/model/v120_hierarchical_top5_distillation/main.py
V76=$W/model/v76_adjacent_safe_buy_lead/main.py
V20=$W/model/v20_demand_timing_moe/main.py
S=scenarios_64.json
echo "== a) V5(OceanMix) vs V76/V20 =="
V5_TEAM=OceanMix $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v76=$V76 v20=$V20 --scenarios $S --workers 10 --out $OUT/v5_vs_bench.json 2>&1 | tail -2
echo "== b) V120 vs V76/V20 =="
$PY arena.py --candidate $V120 --opponents v76=$V76 v20=$V20 --scenarios $S --workers 10 --out $OUT/v120_vs_bench.json 2>&1 | tail -2
echo "== c) V5(OceanMix) vs V120 =="
V5_TEAM=OceanMix $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v120=$V120 --scenarios $S --workers 10 --out $OUT/v5_vs_v120.json 2>&1 | tail -1
echo "== d) V8(skip7) vs V120 =="
V8_SKIP_FROM_DAY=7 $PY arena.py --candidate ../../v8_v120_yarn_hedge/main.py --opponents v120=$V120 --scenarios $S --workers 10 --out $OUT/v8skip7_vs_v120.json 2>&1 | tail -1
echo "== e) tetsuya 103951199(pin) vs V120 =="
PF=$OUT/pin_tetsuya.json; echo '{"team": "tetsuya", "prefer_ep": "103951199", "pin": 1}' > $PF
V5_PARAMS=$PF V5_TEAM=tetsuya $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v120=$V120 --scenarios $S --workers 10 --out $OUT/tetsuya103951199_vs_v120.json 2>&1 | tail -1
echo "== f) V4H(v1am 底盘) vs V76/V20 =="
$PY arena.py --candidate ../../v4h_demand_race_hybrid/main.py --opponents v76=$V76 v20=$V20 --scenarios $S --workers 10 --out $OUT/v4h_vs_bench.json 2>&1 | tail -2
echo "== g) 裸 OceanMix tape vs V76/V20 =="
$PY arena.py --candidate ../../v4h_tape_ledger_hybrid/raw_tape_agent.py --opponents v76=$V76 v20=$V20 --scenarios $S --workers 10 --out $OUT/rawtape_vs_bench.json 2>&1 | tail -2
echo MATRIX_DONE
