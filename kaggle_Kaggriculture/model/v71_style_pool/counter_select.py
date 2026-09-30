"""新版人群反制选带:1042 主干真实棋盘种子,A 半对 me2965_28 选 t144 带,B 半对 guru28+me2965_28 验证。"""
import sys, os, json, glob, hashlib, collections
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
SHORT=[0,100,101,103,107,110,112,115,118,120,123,124,126]
def half(e): return "A" if int(hashlib.md5(("cs"+str(e)).encode()).hexdigest(),16)%2==0 else "B"
if __name__=="__main__":
    comp={}
    for f in glob.glob("rlive3/*.json"):
        r=json.load(open(f)); comp[str(r["eid"])]=r
    seen=set(); B=[]
    for fn in ("boards_recent.json","boards_all.json"):
        for x in json.load(open(fn)):
            if x.get("seed") is None or (x["key"],x["lin"])!=("1042.0","main") or x["eid"] in seen or x["eid"] not in comp: continue
            seen.add(x["eid"]); x["combo"]="|".join((comp[x["eid"]].get("shops") or [])[:2]); x["half"]=half(x["eid"]); B.append(x)
    A=[x for x in B if x["half"]=="A"]; H=[x for x in B if x["half"]=="B"]
    print("棋盘",len(B),"A",len(A),"B",len(H),flush=True)
    stage=sys.argv[1]
    if stage=="A":
        res={"default":be.run(A,"r31probe","me2965_28",[])}
        for r in SHORT: res[r]=be.run(A,"r31probe","me2965_28",[f"KAG_CUT144={r}"])
        json.dump({str(k):v for k,v in res.items()},open("counter_A.json","w"))
        S=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.0,0]))
        for arm,rr in res.items():
            for x in A:
                d=rr.get(x["eid"])
                if d is None: continue
                a=S[x["combo"]][arm]; a[0]+=d>0; a[1]+=d; a[2]+=1
        pick={}
        tot0=sum(S[c]["default"][0] for c in S); tot1=0
        for c in S:
            b=S[c]["default"]; k,v=max(((k,v) for k,v in S[c].items() if k!="default"),key=lambda kv:(kv[1][0],kv[1][1]))
            if v[0]>b[0]: pick[c]=[144,k]; tot1+=v[0]; print(f"  [改] {c:32s} 默认 {b[0]}/{b[2]} → 带{k} {v[0]}/{v[2]}")
            else: tot1+=b[0]
        print(f"A 半:默认 {tot0}/{len(A)} → 选带 {tot1}/{len(A)},改格 {len(pick)}")
        json.dump(pick,open("counter_pick.json","w"))
    else:
        pick=json.load(open("counter_pick.json"))
        T=[x for x in H if x["combo"] in pick]
        print("B 半受影响",len(T),flush=True)
        for opp in ("guru28","me2965_28"):
            d0=be.run(T,"v54r31",opp,[])
            by=collections.defaultdict(list)
            for x in T: by[pick[x["combo"]][1]].append(x)
            d1={}
            for r,xs in by.items(): d1.update(be.run(xs,"r31probe",opp,[f"KAG_CUT144={r}"]))
            w0=sum(1 for x in T if (d0.get(x["eid"]) or 0)>0); w1=sum(1 for x in T if (d1.get(x["eid"]) or 0)>0)
            print(f"  B 半 vs {opp}: 默认 {w0}/{len(T)} → 反制表 {w1}/{len(T)}",flush=True)
