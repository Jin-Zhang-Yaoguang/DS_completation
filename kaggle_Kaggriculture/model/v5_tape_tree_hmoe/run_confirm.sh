#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
SEEDS=$($PY -c "import random; random.seed(20260902); print(','.join(str(random.randrange(1,2**31)) for _ in range(40)))")
echo "== A) OceanMix 树：40 个全新随机 seed × 双席位 vs V76/V20 =="
V5_TEAM=OceanMix $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v76=$W/model/v76_adjacent_safe_buy_lead/main.py v20=$W/model/v20_demand_timing_moe/main.py --seeds $SEEDS --workers 10 --out ../../v5_tape_tree_hmoe/eval_fresh40_OceanMix.json 2>&1 | tail -2
echo "== B) OceanMix 树：M6 vs v1am / V4H =="
V5_TEAM=OceanMix $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v1am=$W/model/v1_adaptive_market/main.py v4h=$W/model/v4h_demand_race_hybrid/main.py --scenarios scenarios_64.json --workers 10 --out ../../v5_tape_tree_hmoe/eval_m6_OceanMix_extra.json 2>&1 | tail -2
echo "== C) 消融：修正后裸 tape（无守卫/前移/终局）M6 vs V76/V20 =="
$PY arena.py --candidate ../../v4h_tape_ledger_hybrid/raw_tape_agent.py --opponents v76=$W/model/v76_adjacent_safe_buy_lead/main.py v20=$W/model/v20_demand_timing_moe/main.py --scenarios scenarios_64.json --workers 10 --out ../../v5_tape_tree_hmoe/eval_m6_rawtape_fixed.json 2>&1 | tail -2
echo "== D) 方案 A（修正 tape 后）M6 vs V76/V20 =="
$PY arena.py --candidate ../../v4h_tape_ledger_hybrid/main.py --opponents v76=$W/model/v76_adjacent_safe_buy_lead/main.py v20=$W/model/v20_demand_timing_moe/main.py --scenarios scenarios_64.json --workers 10 --out ../../v4h_tape_ledger_hybrid/eval_m6_v4h_tape_fixed.json 2>&1 | tail -2
echo CONFIRM_DONE
