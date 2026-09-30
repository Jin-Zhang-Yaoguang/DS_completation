#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
V10=$W/model/v10_rule_distill/dist/main.py; V76=$W/model/v76_adjacent_safe_buy_lead/main.py
for team in Crop_Dusta tetsuya yukino Driz_Lo MtN; do
  echo "== 树 $team vs V76 / V10：M6(fixed) =="
  V5_TEAM=$team $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v76=$V76 v10=$V10 --scenarios scenarios_64.json --workers 10 --out ../../v12_crop_dusta/eval_m6fixed_tree_${team}.json 2>&1 | tail -2
done
echo TREES_DONE
