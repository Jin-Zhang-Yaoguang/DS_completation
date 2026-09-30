#!/bin/bash
# 按产品的前移扫描：每次只对一个产品前移 1 回合（两种模式），vs V120 M6
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
V120=$W/model/v120_hierarchical_top5_distillation/main.py
until grep -q V7_DONE $W/model/v7_v120_mirror_lead/v7.log 2>/dev/null; do sleep 15; done
for item in WOOL MILK STRAWBERRY MELON CARROT; do
  for mode in no_tick always; do
    echo "== V7 item=$item mode=$mode k=1 vs V120：M6 =="
    V7_LEAD_K=1 V7_MODE=$mode V7_ITEMS=$item $PY arena.py --candidate ../../v7_v120_mirror_lead/main.py --opponents v120=$V120 --scenarios scenarios_64.json --workers 10 --out ../../v7_v120_mirror_lead/eval_m6_${item}_${mode}.json 2>&1 | tail -1
  done
done
echo SWEEP_DONE
