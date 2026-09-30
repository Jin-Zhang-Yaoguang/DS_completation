#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
until grep -q V10GATE_DONE $W/model/eval_m6_fixed/v10_gate.log 2>/dev/null; do sleep 10; done
OUT=$W/model/v11_distill_top20/lib; S=scenarios_64.json
V120=$W/model/v120_hierarchical_top5_distillation/main.py; V76=$W/model/v76_adjacent_safe_buy_lead/main.py; V20=$W/model/v20_demand_timing_moe/main.py
for team in Driz_Lo yukino Milan_Leonard tetsuya OceanMix Crop_Dusta; do
  echo "== 树路由 $team vs V76/V20 =="
  V5_TEAM=$team $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v76=$V76 v20=$V20 --scenarios $S --workers 10 --out $OUT/tree_${team}_vs_bench.json 2>&1 | tail -2
  echo "== 树路由 $team vs V120 =="
  V5_TEAM=$team $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v120=$V120 --scenarios $S --workers 10 --out $OUT/tree_${team}_vs_v120.json 2>&1 | tail -1
done
echo TREES_DONE
