#!/bin/bash
W=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture
PY=/Users/a1-6/Desktop/PycharmProjects/DS_completation/.venv/bin/python
cd $W/model/v4_demand_race/harness
until grep -q TREES_DONE $W/model/v11_distill_top20/lib/trees.log 2>/dev/null; do sleep 15; done
OUT=$W/model/v11_distill_top20/lib; S=scenarios_64.json
V120=$W/model/v120_hierarchical_top5_distillation/main.py; V76=$W/model/v76_adjacent_safe_buy_lead/main.py; V20=$W/model/v20_demand_timing_moe/main.py
run () { # $1=team $2=tag $3=params-json
  PF=$OUT/params_$2.json; echo "$3" > $PF
  echo "== $2 vs V76/V20 =="; V5_PARAMS=$PF V5_TEAM=$1 $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v76=$V76 v20=$V20 --scenarios $S --workers 10 --out $OUT/tree2_$2_vs_bench.json 2>&1 | tail -2
  echo "== $2 vs V120 =="; V5_PARAMS=$PF V5_TEAM=$1 $PY arena.py --candidate ../../v5_tape_tree_hmoe/main.py --opponents v120=$V120 --scenarios $S --workers 10 --out $OUT/tree2_$2_vs_v120.json 2>&1 | tail -1
}
run Driz_Lo          DrizLo_shopseq   '{"team":"Driz_Lo","route_key":"shop_seq"}'
run yukino           yukino_shopseq   '{"team":"yukino","route_key":"shop_seq"}'
run Milan_Leonard_ctx Milan_oppsig    '{"team":"Milan_Leonard_ctx","route_key":"shop_seq","oppsig_filter":1}'
run Crop_Dusta_ctx   CropDusta_oppsig '{"team":"Crop_Dusta_ctx","route_key":"shop_seq","oppsig_filter":1}'
run tetsuya_ctx      tetsuya_oppsig   '{"team":"tetsuya_ctx","route_key":"shop_seq","oppsig_filter":1}'
run OceanMix         OceanMix_shopseq '{"team":"OceanMix","route_key":"shop_seq"}'
echo TREES2_DONE
