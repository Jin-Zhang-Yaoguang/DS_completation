#!/bin/bash
# 按表路由（BR 模式）评测：in-sample M6 + out-of-sample 新 40 seed，vs V120；再 vs V76/V20 保底
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
V120=$W/model/v120_hierarchical_top5_distillation/main.py
PF=$W/model/v5_tape_tree_hmoe/lib/br_params.json
cat > $PF <<JSON
{"team": "OceanMix+V120tape", "br_table": "lib/br_table.json", "br_scen": "$W/model/v4_demand_race/harness/scenarios_64.json", "br_tau": ${BR_TAU:-0.25}}
JSON
SEEDS=$($PY -c "import random; random.seed(20260902); print(','.join(str(random.randrange(1,2**31)) for _ in range(40)))")
echo "== BR 路由 vs V120：M6（in-sample）=="
V5_PARAMS=$PF V5_TEAM=OceanMix+V120tape $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v120=$V120 --scenarios scenarios_64.json --workers 10 --out ../../v5_tape_tree_hmoe/eval_br_m6_vs_v120.json 2>&1 | tail -1
echo "== BR 路由 vs V120：新 40 seed（out-of-sample）=="
V5_PARAMS=$PF V5_TEAM=OceanMix+V120tape $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v120=$V120 --seeds $SEEDS --workers 10 --out ../../v5_tape_tree_hmoe/eval_br_fresh40_vs_v120.json 2>&1 | tail -1
echo "== BR 路由 vs V76/V20：M6 =="
V5_PARAMS=$PF V5_TEAM=OceanMix+V120tape $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v76=$W/model/v76_adjacent_safe_buy_lead/main.py v20=$W/model/v20_demand_timing_moe/main.py --scenarios scenarios_64.json --workers 10 --out ../../v5_tape_tree_hmoe/eval_br_m6_vs_bench.json 2>&1 | tail -2
echo BR_EVAL_DONE
