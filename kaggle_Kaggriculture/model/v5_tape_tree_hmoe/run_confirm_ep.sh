#!/bin/bash
# 用法: run_confirm_ep.sh <team> <ep>   —— 固定跟随该 tape（pin），新 40 seed vs V120 + M6 vs V76/V20
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
TEAM=$1; EP=$2
cd $W/model/v4_demand_race/harness
V120=$W/model/v120_hierarchical_top5_distillation/main.py
PF=$W/model/v5_tape_tree_hmoe/lib/confirm_${TEAM}_${EP}.json
echo "{\"team\": \"$TEAM\", \"prefer_ep\": \"$EP\", \"pin\": 1}" > $PF
SEEDS=$($PY -c "import random; random.seed(20260902); print(','.join(str(random.randrange(1,2**31)) for _ in range(40)))")
echo "== $TEAM/$EP vs V120：新 40 seed × 双席位（out-of-sample）=="
V5_PARAMS=$PF V5_TEAM=$TEAM $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v120=$V120 --seeds $SEEDS --workers 10 --out ../../v5_tape_tree_hmoe/eval_fresh40_${TEAM}_${EP}_vs_v120.json 2>&1 | tail -1
echo "== $TEAM/$EP vs V76/V20：M6 =="
V5_PARAMS=$PF V5_TEAM=$TEAM $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v76=$W/model/v76_adjacent_safe_buy_lead/main.py v20=$W/model/v20_demand_timing_moe/main.py --scenarios scenarios_64.json --workers 10 --out ../../v5_tape_tree_hmoe/eval_m6_${TEAM}_${EP}_vs_bench.json 2>&1 | tail -2
echo CONFIRM_EP_DONE
