"""样本外门控:combo_big 种子 idx 16,17(从未用于选格),双席位,5 代表;r34 / r38e / r38e 关 cha 格。"""
import json, collections
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
ARMS=[("r34","v54r34",()),("r38e","v54r38e",()),("r38e关cha","r38eabl",("KAG_CUTOFF=CHA",))]
OPPS=["me2965_28","guru28","engineV3","rescue7","fieldcraft29"]
if __name__=="__main__":
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    jobs=[(ag,o,IDX[c][i],st,f"{nm}|{o}|{c}|{i}|{st}",env) for nm,ag,env in ARMS for o in OPPS for c in cells for i in (16,17) for st in (0,1)]
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(be.one,jobs,chunksize=4))
    print("[样本外 双席位 idx16-17] 胜/256 (均差)")
    tot=collections.Counter()
    for o in OPPS:
        line=f"   {o:12s}"
        for nm,_,_ in ARMS:
            d=[v for k,v in R.items() if k.startswith(f"{nm}|{o}|") and v is not None]; tot[nm]+=sum(x>0 for x in d)
            line+=f"  {nm}: {sum(x>0 for x in d):3d} ({sum(d)/max(1,len(d)):5.0f})"
        print(line,flush=True)
    print("   合计 "+"  ".join(f"{nm}: {tot[nm]}/1280" for nm,_,_ in ARMS))
