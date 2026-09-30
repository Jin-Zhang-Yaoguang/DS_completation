#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
SEEDS=$($PY -c "import random; random.seed(20260902); print(','.join(str(random.randrange(1,2**31)) for _ in range(40)))")
V120=$W/model/v120_hierarchical_top5_distillation/main.py
echo "== 1) V5(OceanMix) vs V120：M6 64 场景 × 双席位 =="
V5_TEAM=OceanMix $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v120=$V120 --scenarios scenarios_64.json --workers 10 --out ../../v5_tape_tree_hmoe/eval_m6_vs_v120.json 2>&1 | tail -1
echo "== 2) V5(OceanMix) vs V120：新 40 seed × 双席位 =="
V5_TEAM=OceanMix $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v120=$V120 --seeds $SEEDS --workers 10 --out ../../v5_tape_tree_hmoe/eval_fresh40_vs_v120.json 2>&1 | tail -1
echo "== 3) V120 vs V76/V20：M6 64 场景 × 双席位 =="
$PY arena.py --candidate $V120 --opponents v76=$W/model/v76_adjacent_safe_buy_lead/main.py v20=$W/model/v20_demand_timing_moe/main.py --scenarios scenarios_64.json --workers 10 --out ../../v5_tape_tree_hmoe/eval_m6_v120_vs_bench.json 2>&1 | tail -2
echo "== 4) V120 vs V76/V20：同一新 40 seed × 双席位 =="
$PY arena.py --candidate $V120 --opponents v76=$W/model/v76_adjacent_safe_buy_lead/main.py v20=$W/model/v20_demand_timing_moe/main.py --seeds $SEEDS --workers 10 --out ../../v5_tape_tree_hmoe/eval_fresh40_v120_vs_bench.json 2>&1 | tail -2
echo GATE_DONE
