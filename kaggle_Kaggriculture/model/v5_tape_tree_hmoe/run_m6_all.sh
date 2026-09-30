#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
for team in "$@"; do
  tag=$(echo "$team" | tr ' ' '_')
  V5_TEAM="$team" $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py \
    --opponents v76=$W/model/v76_adjacent_safe_buy_lead/main.py v20=$W/model/v20_demand_timing_moe/main.py \
    --scenarios scenarios_64.json --workers 10 --out ../../v5_tape_tree_hmoe/eval_m6_$tag.json 2>&1 | tail -2 | sed "s/^/[$tag] /"
done
echo ALL_DONE
