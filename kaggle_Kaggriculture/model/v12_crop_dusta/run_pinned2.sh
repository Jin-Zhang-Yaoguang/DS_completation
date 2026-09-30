#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
V10=$W/model/v10_rule_distill/dist/main.py; OUT=$W/model/v12_crop_dusta
for pair in $($PY -c "import json; d=json.load(open('$OUT/base_candidates.json')); print(' '.join(f'{k}={v}' for k,v in d.items()))"); do
  r=${pair%%=*}; ep=${pair##*=}
  echo "== 固定轨迹(守卫修复后) $r ($ep) vs V10：M6(fixed) =="
  V5_PARAMS=$OUT/params_pin_$r.json V5_TEAM=Crop_Dusta $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v10=$V10 --scenarios scenarios_64.json --workers 10 --out $OUT/eval_pin2_$r.json 2>&1 | tail -1
done
echo PINNED2_DONE
