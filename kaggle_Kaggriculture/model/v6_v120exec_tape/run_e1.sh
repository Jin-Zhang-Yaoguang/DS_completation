#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
V120=$W/model/v120_hierarchical_top5_distillation/main.py
echo "== E4 对照：V6(tape=v120) vs V120，M6 =="
V6_TAPE=v120 $PY arena.py --candidate ../../v6_v120exec_tape/main.py --opponents v120=$V120 --scenarios scenarios_64.json --workers 10 --out ../../v6_v120exec_tape/eval_m6_ctrl_v120tape.json 2>&1 | tail -1
echo "== E1：V6(tape=102549659) vs V120，M6 =="
V6_TAPE=102549659 $PY arena.py --candidate ../../v6_v120exec_tape/main.py --opponents v120=$V120 --scenarios scenarios_64.json --workers 10 --out ../../v6_v120exec_tape/eval_m6_vs_v120.json 2>&1 | tail -1
echo "== E2：V6(tape=102549659) vs V76/V20，M6 =="
V6_TAPE=102549659 $PY arena.py --candidate ../../v6_v120exec_tape/main.py --opponents v76=$W/model/v76_adjacent_safe_buy_lead/main.py v20=$W/model/v20_demand_timing_moe/main.py --scenarios scenarios_64.json --workers 10 --out ../../v6_v120exec_tape/eval_m6_vs_bench.json 2>&1 | tail -2
echo E1_DONE
