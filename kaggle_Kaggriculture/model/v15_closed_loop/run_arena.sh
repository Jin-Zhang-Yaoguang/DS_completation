#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
D=$W/model/v15_closed_loop
cd $W/model/v4_demand_race/harness
V10=$W/model/v10_rule_distill/dist/main.py
echo "== V15 全闭环 vs V10：M6(fixed) 64x2 =="
V15_PARAMS=$D/params/hw3.json $PY arena.py --candidate $D/main.py --opponents v10=$V10 --scenarios scenarios_64.json --workers 10 --out $D/eval_v15_full_vs_v10.json 2>&1 | tail -1
echo "== V15 混合(tape<20) vs V10：M6(fixed) 64x2 =="
V15_PARAMS=$D/params/tape20_hw3.json $PY arena.py --candidate $D/main.py --opponents v10=$V10 --scenarios scenarios_64.json --workers 10 --out $D/eval_v15_tape20_vs_v10.json 2>&1 | tail -1
echo ARENA_DONE
