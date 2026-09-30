#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
V10=$W/model/v10_rule_distill/dist/main.py
OUT=$W/model/v13_route_library
for R in 10C4S_3Q 8C6S_3Q 6C8S_3Q 6C12S_4Q_FIRST_YARN 6C12S_4Q_SECOND_YARN; do
  echo "== route $R vs V10：M6(fixed) =="
  V13_ROUTE=$R $PY arena.py --candidate $OUT/main.py --opponents v10=$V10 --scenarios scenarios_64.json --workers 10 --out $OUT/eval_route_${R}_vs_v10.json 2>&1 | tail -1
done
echo "== tetsutani 原版（自带选择器）vs V10：M6(fixed) =="
$PY arena.py --candidate $OUT/tetsutani_main.py --opponents v10=$V10 --scenarios scenarios_64.json --workers 10 --out $OUT/eval_tetsutani_vs_v10.json 2>&1 | tail -1
echo ROUTES_DONE
