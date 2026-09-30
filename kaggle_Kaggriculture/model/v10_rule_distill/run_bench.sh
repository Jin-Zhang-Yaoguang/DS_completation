#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
OUT=$W/model/v10_rule_distill/lib
until grep -q REFINE2_DONE $OUT/refine2.log 2>/dev/null; do sleep 15; done
echo "== R1(d10)+R2(d8,≤1) vs V76/V20：M6(fixed) =="
V10_R1=1 V10_R1_DAY=10 V10_R2=1 V10_R2_DAY=8 V10_R2_MAX=1 V10_R3=0 $PY arena.py --candidate ../../v10_rule_distill/main.py --opponents v76=$W/model/v76_adjacent_safe_buy_lead/main.py v20=$W/model/v20_demand_timing_moe/main.py --scenarios scenarios_64.json --workers 10 --out $OUT/m6_best_vs_bench.json 2>&1 | tail -2
echo BENCH_DONE
