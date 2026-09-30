#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
V120=$W/model/v120_hierarchical_top5_distillation/main.py
until grep -q MATRIX_DONE $W/model/eval_m6_fixed/matrix.log 2>/dev/null; do sleep 10; done
for cfg in "0 0" "1 0" "0 1" "1 1"; do
  set -- $cfg
  echo "== V9 fert=$1 hedge=$2 vs V120：M6(fixed) =="
  V9_FERT=$1 V9_HEDGE=$2 $PY arena.py --candidate ../../v9_v120_pass_fill/main.py --opponents v120=$V120 --scenarios scenarios_64.json --workers 10 --out ../../v9_v120_pass_fill/eval_m6_f$1_h$2.json 2>&1 | tail -1
done
echo V9_DONE
