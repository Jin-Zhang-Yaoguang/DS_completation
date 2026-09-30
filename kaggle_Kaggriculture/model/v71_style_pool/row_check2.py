"""全部 <900 键开环棋盘:r38(行开) vs r36(无行),按 Majkel 簇(560-650 & 9990)/其他分组。"""
import json, collections
from concurrent.futures import ProcessPoolExecutor
from row_check import one, HERE
if __name__=="__main__":
    m=json.load(open("meta_live.json")); H=json.load(open("rkey_head.json"))
    B=[]
    for e,v in m.items():
        k=(H.get(e) or {}).get("rkey")
        if not k or k[0]>=900 or k[0] in (151.0,7.0) or not (HERE/f"rlive3/{e}.json").exists() or not v.get("opp"): continue
        if (v.get("end") or "")<"2026-09-26": continue
        B.append((e,v,k))
    print("棋盘",len(B))
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(one,[(e,a) for e,_,_ in B for a in ("v54r38","v54r36")]))
    S=collections.defaultdict(lambda:[0,0,0,0.0])
    for e,v,k in B:
        a,b=R.get((e,"v54r38")),R.get((e,"v54r36"))
        if a is None or b is None: continue
        grp=("簇" if 560<=k[0]<=650 and k[1]==9990 else "其他")+("≥2000" if v["opp"]["initialScore"]>=2000 else "<2000")
        s=S[grp]; s[0]+=1; s[1]+=a>0; s[2]+=b>0; s[3]+=a-b
    for g,s in sorted(S.items()): print(f"  {g:10s} n={s[0]:3d}  r38(行) 胜 {s[1]}  r36(无行) 胜 {s[2]}  平均差(r38-r36) {s[3]/s[0]:8.0f}")
