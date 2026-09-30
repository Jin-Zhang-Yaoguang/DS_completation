#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
V120=$W/model/v120_hierarchical_top5_distillation/main.py; V76=$W/model/v76_adjacent_safe_buy_lead/main.py; V20=$W/model/v20_demand_timing_moe/main.py
OUT=$W/model/v10_rule_distill/lib
SEEDS=$($PY -c "import random; random.seed(20260902); print(','.join(str(random.randrange(1,2**31)) for _ in range(40)))")
for cfg in "1 0 0" "1 1 0" "1 1 1" "0 1 0"; do
  set -- $cfg
  echo "== V10 R1=$1 R2=$2 R3=$3 vs V120：M6(fixed) =="
  V10_R1=$1 V10_R2=$2 V10_R3=$3 $PY arena.py --candidate ../../v10_rule_distill/main.py --opponents v120=$V120 --scenarios scenarios_64.json --workers 10 --out $OUT/m6_r$1$2$3_vs_v120.json 2>&1 | tail -1
  echo "== V10 R1=$1 R2=$2 R3=$3 vs V120：新 40 seed =="
  V10_R1=$1 V10_R2=$2 V10_R3=$3 $PY arena.py --candidate ../../v10_rule_distill/main.py --opponents v120=$V120 --seeds $SEEDS --workers 10 --out $OUT/fresh40_r$1$2$3_vs_v120.json 2>&1 | tail -1
done
echo "== V10 R1=1 R2=1 R3=0 vs V76/V20：M6(fixed) =="
V10_R1=1 V10_R2=1 V10_R3=0 $PY arena.py --candidate ../../v10_rule_distill/main.py --opponents v76=$V76 v20=$V20 --scenarios scenarios_64.json --workers 10 --out $OUT/m6_r110_vs_bench.json 2>&1 | tail -2
echo GATE_DONE
