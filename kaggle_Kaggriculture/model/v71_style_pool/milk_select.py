"""奶类世界后半程换带:奶类组合 × {默认, t360/t432 × 13 带} × 面板 × 1 种子(combo_index6 指定序号)。
用法: PROBE=r26cut PUB_INDEX=combo_index6.json python milk_select.py <tag> <opp,opp> <种子序号>"""
import sys, os, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
from pub_splice import one, IDX, SHORT
MILK={"PIZZA_SHOP","ICE_CREAM_SHOP","SMOOTHIE_SHOP"}
ARMS=[(None,-1)]+[(c,r) for c in (360,432) for r in SHORT]
if __name__=="__main__":
    tag=sys.argv[1]; opps=sys.argv[2].split(","); si=int(sys.argv[3])
    cells=[c for c in sorted(IDX) if MILK & set(c.split("|"))]
    jobs=[(c,o,IDX[c][si],cut,rid) for c in cells for o in opps for cut,rid in ARMS]
    print("任务",len(jobs),"奶类组合",len(cells),flush=True)
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=4))
    json.dump([list(r) for r in res],open(HERE/f"lin_select_{tag}.json","w")); print("完成")
