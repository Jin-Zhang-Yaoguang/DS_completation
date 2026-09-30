#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
V10=$W/model/v10_rule_distill/dist/main.py
OUT=$W/model/v12_crop_dusta
until grep -q TREES_DONE $OUT/trees.log 2>/dev/null; do sleep 15; done
run() { tag=$1; shift; echo "$@" > $OUT/params_$tag.json; echo "== 路由 $tag vs V10：M6(fixed) =="; V5_PARAMS=$OUT/params_$tag.json V5_TEAM=Crop_Dusta $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v10=$V10 --scenarios scenarios_64.json --workers 10 --out $OUT/eval_router_$tag.json 2>&1 | tail -1; }
run latest_lock6   '{"team": "Crop_Dusta", "version_prefix": "fdca8962", "lock_after_day": 6}'
run latest_lock6_bank '{"team": "Crop_Dusta", "version_prefix": "fdca8962", "lock_after_day": 6, "bank_weight": 1.0}'
run latest_lock8_bank '{"team": "Crop_Dusta", "version_prefix": "fdca8962", "lock_after_day": 8, "bank_weight": 1.0}'
run latest_lock5_bank '{"team": "Crop_Dusta", "version_prefix": "fdca8962", "lock_after_day": 5, "bank_weight": 1.0}'
run all_lock6_bank   '{"team": "Crop_Dusta", "lock_after_day": 6, "bank_weight": 1.0}'
run latest_nolock_bank '{"team": "Crop_Dusta", "version_prefix": "fdca8962", "bank_weight": 1.0}'
echo ROUTER_DONE
