"""v55 分支筛选:① 逐组合基线(v55b);② 对最弱 K 个 + 缺失组合,候选=同第1家商店的全部 Arjun 对局;选择集 idx20,21,验证集 idx16,17;只采纳两集都更好的。"""
import json, collections, os, sys
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
OPPS=["me2965_28","engineV3","v54r38g"]
def run(jobs):
    with ProcessPoolExecutor(8) as ex: return dict(ex.map(be.one,jobs,chunksize=2))
def score(R,prefix):
    d=[v for k,v in R.items() if k.startswith(prefix) and v is not None]; return sum(x>0 for x in d),len(d),sum(d)
if __name__=="__main__":
    K=int(sys.argv[1]) if len(sys.argv)>1 else 16
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    ALL=json.load(open("agents/arjun_all_eps.json")); D=json.load(open("agents/afrep_arjun.json"))
    jobs=[("v55b",o,IDX[c][i],st,f"{c}|{o}|{i}|{st}",()) for c in cells for o in OPPS for i in (20,21) for st in (0,1)]
    B=run(jobs); base={c:score(B,c+"|") for c in cells}
    json.dump({c:list(v) for c,v in base.items()},open("v55_cellbase.json","w"))
    tot=sum(v[0] for v in base.values()); print(f"v55b 基线 {tot}/{sum(v[1] for v in base.values())}",flush=True)
    miss=[c for c in cells if c not in D["by_shops"]]
    weak=sorted([c for c in cells if c not in miss],key=lambda c:(base[c][0],base[c][2]))[:K]
    print("缺失:",[(c,base[c][0]) for c in miss],flush=True); print("最弱:",[(c,base[c][0]) for c in weak],flush=True)
    picks={}
    for c in miss+weak:
        f=c.split("|")[0]
        cands=[e for e,v in ALL.items() if v["shops"] and v["shops"][0]==f]
        cur=D["by_shops"].get(c,{}).get("eid")
        cands=[e for e in cands if str(e)!=str(cur)]
        if not cands: continue
        jobs=[("v55x",o,IDX[c][i],st,f"{e}|{o}|{i}|{st}",(f"KAG_V55_OVR={c}={e}",)) for e in cands for o in OPPS for i in (20,21) for st in (0,1)]
        R=run(jobs); sc={e:score(R,f"{e}|") for e in cands}
        best=max(cands,key=lambda e:(sc[e][0],sc[e][2]))
        line=f"{c:32s} 现 {base[c][0]}/{base[c][1]}({base[c][2]/max(1,base[c][1]):6.0f}) 候选{len(cands)} 最佳 {best}: {sc[best][0]}/{sc[best][1]}({sc[best][2]/max(1,sc[best][1]):6.0f})"
        if sc[best][0]>base[c][0] or (sc[best][0]==base[c][0] and sc[best][2]>base[c][2]+2000*base[c][1]/12):
            vj=[("v55x" if a=="n" else "v55b",o,IDX[c][i],st,f"{a}|{o}|{i}|{st}",((f"KAG_V55_OVR={c}={best}",) if a=="n" else ())) for a in ("n","b") for o in OPPS for i in (16,17) for st in (0,1)]
            V=run(vj); vn=score(V,"n|"); vb=score(V,"b|")
            line+=f" | 验证 新 {vn[0]}/{vn[1]}({vn[2]/max(1,vn[1]):6.0f}) 现 {vb[0]}/{vb[1]}({vb[2]/max(1,vb[1]):6.0f})"
            if vn[0]>vb[0] or (vn[0]==vb[0] and vn[2]>vb[2]): picks[c]=best; line+=" ✔采纳"
            else: line+=" ✘验证未过"
        print(line,flush=True)
        json.dump(picks,open("v55_picks.json","w"))
    print("采纳",len(picks),picks)
