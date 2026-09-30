#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
V120=$W/model/v120_hierarchical_top5_distillation/main.py
for cfg in "1 no_tick" "1 always" "2 no_tick"; do
  set -- $cfg
  echo "== V7 lead_k=$1 mode=$2 vs V120：M6 =="
  V7_LEAD_K=$1 V7_MODE=$2 $PY arena.py --candidate ../../v7_v120_mirror_lead/main.py --opponents v120=$V120 --scenarios scenarios_64.json --workers 10 --out ../../v7_v120_mirror_lead/eval_m6_k$1_$2.json 2>&1 | tail -1
done
echo V7_DONE
