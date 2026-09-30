"""Arjun 固定带:逐商店组合表现(样本外 idx20,21 双席位 × me2965/engineV3/r38g),标出缺失组合(用第1家商店对局代替)。"""
import json, collections
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
if __name__=="__main__":
    D=json.load(open("agents/afrep_arjun.json")); have=set(D["by_shops"])
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    OP=["me2965_28","engineV3","v54r38g"]
    jobs=[("afrep_arjun",o,IDX[c][i],st,f"{c}|{o}|{i}|{st}",()) for c in cells for o in OP for i in (20,21) for st in (0,1)]
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(be.one,jobs,chunksize=4))
    S={}
    for c in cells:
        d=[v for k,v in R.items() if k.startswith(c+"|") and v is not None]
        S[c]=(sum(x>0 for x in d),len(d),sum(d)/max(1,len(d)))
    json.dump({c:list(v) for c,v in S.items()},open("v55_cells.json","w"))
    miss=[c for c in cells if c not in have]
    print(f"缺失组合 {len(miss)}:")
    for c in miss: print(f"   {c:32s} 胜 {S[c][0]}/{S[c][1]} 均{S[c][2]:7.0f}")
    hv=[S[c] for c in cells if c in have]; mv=[S[c] for c in miss]
    print(f"有对局的组合合计 胜 {sum(x[0] for x in hv)}/{sum(x[1] for x in hv)}  缺失组合合计 胜 {sum(x[0] for x in mv)}/{sum(x[1] for x in mv)}")
    print("最弱的 10 个组合:",[(c,S[c][0],S[c][1]) for c in sorted(cells,key=lambda c:S[c][0]/max(1,S[c][1]))[:10]])
