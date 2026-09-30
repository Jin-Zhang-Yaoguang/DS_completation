"""lead-N 样本外:combo_big idx16,17 双席位 × 5 代表;基线 r38e=1009/1280(gate_oos)。"""
import json, collections, sys
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
OPPS=["me2965_28","guru28","engineV3","rescue7","fieldcraft29"]
if __name__=="__main__":
    NS=[int(x) for x in sys.argv[1].split(",")]
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    jobs=[("r38lead",o,IDX[c][i],st,f"{n}|{o}|{c}|{i}|{st}",(f"KAG_LEADN={n}",)) for n in NS for o in OPPS for c in cells for i in (16,17) for st in (0,1)]
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(be.one,jobs,chunksize=4))
    print("[lead-N 样本外 idx16-17 双席位] 胜/256 (均差)   基线 r38e: me2965 171 guru 183 engineV3 230 rescue7 216 fieldcraft 209 = 1009")
    for n in NS:
        tot=0; line=f"   N={n:3d}"
        for o in OPPS:
            d=[v for k,v in R.items() if k.startswith(f"{n}|{o}|") and v is not None]; tot+=sum(x>0 for x in d)
            line+=f"  {o[:9]}: {sum(x>0 for x in d):3d} ({sum(d)/max(1,len(d)):5.0f})"
        print(line+f"  合计 {tot}/1280",flush=True)
