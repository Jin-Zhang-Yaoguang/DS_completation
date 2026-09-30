#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
OUT=$W/model/v10_rule_distill/lib
V120=$W/model/v120_hierarchical_top5_distillation/main.py
until grep -q BENCH_DONE $OUT/refine2.log 2>/dev/null; do sleep 15; done
export V10_R1=1 V10_R1_DAY=10 V10_R2=1 V10_R2_DAY=9 V10_R2_MAX=1 V10_R3=0
SEEDS=$($PY -c "import random; random.seed(20260903); print(','.join(str(random.randrange(1,2**31)) for _ in range(100)))")
echo "== FINAL best(d10/d9) vs V120：全新 100 seed × 双席位（从未接触）=="
$PY arena.py --candidate ../../v10_rule_distill/main.py --opponents v120=$V120 --seeds $SEEDS --workers 10 --out $OUT/final100_best_vs_v120.json 2>&1 | tail -1
echo "== FINAL best(d10/d9) vs V76/V20：M6(fixed) =="
$PY arena.py --candidate ../../v10_rule_distill/main.py --opponents v76=$W/model/v76_adjacent_safe_buy_lead/main.py v20=$W/model/v20_demand_timing_moe/main.py --scenarios scenarios_64.json --workers 10 --out $OUT/m6_best_d10d9_vs_bench.json 2>&1 | tail -2
echo "== FINAL best(d10/d9) vs V76/V20：全新 100 seed =="
$PY arena.py --candidate ../../v10_rule_distill/main.py --opponents v76=$W/model/v76_adjacent_safe_buy_lead/main.py v20=$W/model/v20_demand_timing_moe/main.py --seeds $SEEDS --workers 10 --out $OUT/final100_best_vs_bench.json 2>&1 | tail -2
echo FINAL_DONE
