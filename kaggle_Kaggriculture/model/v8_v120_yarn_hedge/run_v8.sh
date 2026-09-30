#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
V120=$W/model/v120_hierarchical_top5_distillation/main.py
for d in 9 7 12; do
  echo "== V8 skip_from_day=$d vs V120：M6 =="
  V8_SKIP_FROM_DAY=$d $PY arena.py --candidate ../../v8_v120_yarn_hedge/main.py --opponents v120=$V120 --scenarios scenarios_64.json --workers 10 --out ../../v8_v120_yarn_hedge/eval_m6_skip$d.json 2>&1 | tail -1
done
echo V8_DONE
cd $W/model/v5_tape_tree_hmoe && $PY screen_teams_vs_v120.py
