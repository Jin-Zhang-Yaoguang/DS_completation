#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v11_distill_top20 && $PY extract_ctx.py "Crop Dusta" tetsuya "Milan Leonard" 2>&1 | tail -3
# 校验对齐：与正确库逐步相同
$PY - <<'PYEOF'
import gzip, json, pathlib
LIB = pathlib.Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v11_distill_top20/lib")
a = {g["ep"]: g for g in json.load(gzip.open(LIB / "Crop_Dusta.json.gz", "rt"))["games"]}
b = {g["ep"]: g for g in json.load(gzip.open(LIB / "Crop_Dusta_ctx.json.gz", "rt"))["games"]}
ep = "95572923"; A, B = a[ep]["actions"], b[ep]["actions"]
print("ALIGN_CHECK 逐步相同:", sum(1 for x, y in zip(A, B) if json.dumps(x, sort_keys=True) == json.dumps(y, sort_keys=True)), "/ 720")
PYEOF
for t in Crop_Dusta tetsuya Milan_Leonard; do cp $W/model/v11_distill_top20/lib/${t}_ctx.json.gz $W/model/v5_tape_tree_hmoe/lib/; done
rm -rf $W/model/v5_tape_tree_hmoe/lib/cache
cd $W/model/v4_demand_race/harness
OUT=$W/model/v11_distill_top20/lib; S=scenarios_64.json
V120=$W/model/v120_hierarchical_top5_distillation/main.py; V76=$W/model/v76_adjacent_safe_buy_lead/main.py; V20=$W/model/v20_demand_timing_moe/main.py
run () { PF=$OUT/params_$2.json; echo "$3" > $PF
  echo "== $2 vs V76/V20 =="; V5_PARAMS=$PF V5_TEAM=$1 $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v76=$V76 v20=$V20 --scenarios $S --workers 10 --out $OUT/tree3_$2_vs_bench.json 2>&1 | tail -2
  echo "== $2 vs V120 =="; V5_PARAMS=$PF V5_TEAM=$1 $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v120=$V120 --scenarios $S --workers 10 --out $OUT/tree3_$2_vs_v120.json 2>&1 | tail -1; }
run Milan_Leonard_ctx Milan_oppsig    '{"team":"Milan_Leonard_ctx","route_key":"shop_seq","oppsig_filter":1}'
run Crop_Dusta_ctx   CropDusta_oppsig '{"team":"Crop_Dusta_ctx","route_key":"shop_seq","oppsig_filter":1}'
run tetsuya_ctx      tetsuya_oppsig   '{"team":"tetsuya_ctx","route_key":"shop_seq","oppsig_filter":1}'
echo TREES3_DONE
