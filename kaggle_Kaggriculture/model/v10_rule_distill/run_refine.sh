#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
V120=$W/model/v120_hierarchical_top5_distillation/main.py
OUT=$W/model/v10_rule_distill/lib
SEEDS=$($PY -c "import random; random.seed(20260902); print(','.join(str(random.randrange(1,2**31)) for _ in range(40)))")
# cfg: R1 R1_DAY R2 R2_DAY R2_MAX
for cfg in "0 8 1 6 1" "0 8 1 7 1" "0 8 1 8 0" "0 8 1 7 0" "0 8 1 6 0" "1 8 1 7 1" "1 10 1 8 1" "1 10 1 7 1" "1 6 1 7 1"; do
  set -- $cfg
  tag="r1_${1}d${2}_r2_${3}d${4}m${5}"
  echo "== $tag vs V120：M6(fixed) =="
  V10_R1=$1 V10_R1_DAY=$2 V10_R2=$3 V10_R2_DAY=$4 V10_R2_MAX=$5 V10_R3=0 $PY arena.py --candidate ../../v10_rule_distill/main.py --opponents v120=$V120 --scenarios scenarios_64.json --workers 10 --out $OUT/m6_${tag}.json 2>&1 | tail -1
  echo "== $tag vs V120：新 40 seed =="
  V10_R1=$1 V10_R1_DAY=$2 V10_R2=$3 V10_R2_DAY=$4 V10_R2_MAX=$5 V10_R3=0 $PY arena.py --candidate ../../v10_rule_distill/main.py --opponents v120=$V120 --seeds $SEEDS --workers 10 --out $OUT/fresh40_${tag}.json 2>&1 | tail -1
done
echo REFINE_DONE
