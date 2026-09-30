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
    A=("v54r38","v54r38c","v54r36")
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(one,[(e,a) for e,_,_ in B for a in A]))
    S=collections.defaultdict(lambda:collections.Counter())
    for e,v,k in B:
        if any(R.get((e,a)) is None for a in A): continue
        grp=("簇460-650" if 460<=k[0]<=650 else "其他")+("≥2000" if v["opp"]["initialScore"]>=2000 else "<2000")
        for g in (grp,"合计≥2000" if v["opp"]["initialScore"]>=2000 else "合计<2000"):
            S[g]["n"]+=1
            for a in A: S[g][a]+=R[(e,a)]>0; S[g][a+"$"]+=R[(e,a)]
    for g,s in sorted(S.items()):
        print(f"  {g:12s} n={s['n']:3d}  "+"  ".join(f"{a[3:]}: 胜{s[a]:3d} 均{s[a+'$']/s['n']:7.0f}" for a in A))
