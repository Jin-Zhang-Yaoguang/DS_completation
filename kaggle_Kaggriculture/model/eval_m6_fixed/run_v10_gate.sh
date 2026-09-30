#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
OUT=$W/model/eval_m6_fixed; V10=$W/model/v10_gate/main.py; S=scenarios_64.json
echo "== V5(OceanMix) vs V10 =="; V5_TEAM=OceanMix $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v10=$V10 --scenarios $S --workers 8 --out $OUT/v5_vs_v10.json 2>&1 | tail -1
echo "== V120 vs V10 =="; $PY arena.py --candidate $W/model/v120_hierarchical_top5_distillation/main.py --opponents v10=$V10 --scenarios $S --workers 8 --out $OUT/v120_vs_v10.json 2>&1 | tail -1
echo "== V8(skip7) vs V10 =="; V8_SKIP_FROM_DAY=7 $PY arena.py --candidate ../../v8_v120_yarn_hedge/main.py --opponents v10=$V10 --scenarios $S --workers 8 --out $OUT/v8_vs_v10.json 2>&1 | tail -1
echo "== V10 vs V76/V20 =="; $PY arena.py --candidate $V10 --opponents v76=$W/model/v76_adjacent_safe_buy_lead/main.py v20=$W/model/v20_demand_timing_moe/main.py --scenarios $S --workers 8 --out $OUT/v10_vs_bench.json 2>&1 | tail -2
echo V10GATE_DONE
