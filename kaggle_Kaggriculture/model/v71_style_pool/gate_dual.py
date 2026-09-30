"""双席位回归门控:同一种子我方分别坐 P0/P1。A 大种子 64 组合×8 最强代表×2 席位(r34 vs r38c);C r38c vs r34 同种子双席位;统计席位翻转率。"""
import json, collections, os
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
VERS=["v54r34","v54r38c"]
OPPS=["me2965_28","guru28","harvest88","engineV3","rescue7","metav4","v52","fieldcraft29"]
W=int(os.environ.get("KAG_WORKERS","8"))
if __name__=="__main__":
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    jobs=[(v,o,IDX[c][2],st,f"{v}|{o}|{c}|{st}",()) for v in VERS for o in OPPS for c in cells for st in (0,1)]
    with ProcessPoolExecutor(W) as ex: R=dict(ex.map(be.one,jobs,chunksize=4))
    print("[A 双席位 大种子 vs 本地最强代表] 每格:胜/128(席位0胜+席位1胜) 均差 | 席位翻转率",flush=True)
    tot=collections.Counter(); flipc=collections.Counter(); nc=collections.Counter()
    for o in OPPS:
        line=f"   {o:12s}"
        for v in VERS:
            d0=[R.get(f"{v}|{o}|{c}|0") for c in cells]; d1=[R.get(f"{v}|{o}|{c}|1") for c in cells]
            P=[(a,b) for a,b in zip(d0,d1) if a is not None and b is not None]
            w0=sum(a>0 for a,_ in P); w1=sum(b>0 for _,b in P); fl=sum((a>0)!=(b>0) for a,b in P)
            tot[v]+=w0+w1; flipc[v]+=fl; nc[v]+=len(P)
            line+=f"   {v[3:]}: {w0+w1:3d}/{2*len(P)} ({w0}+{w1}) 均{(sum(a for a,_ in P)+sum(b for _,b in P))/max(1,2*len(P)):6.0f} 翻{fl:2d}"
        print(line,flush=True)
    for v in VERS: print(f"   合计 {v[3:]}: {tot[v]}/{2*nc[v]}  席位翻转 {flipc[v]}/{nc[v]} ({flipc[v]/max(1,nc[v]):.0%})",flush=True)
    import pub_splice
    jobs=[("v54r38c","v54r34",IDX[c][i],st,f"{c}|{i}|{st}",()) for c in cells for i in (0,1) for st in (0,1)]
    with ProcessPoolExecutor(W) as ex: Y=dict(ex.map(be.one,jobs,chunksize=2))
    d=[x for x in Y.values() if x is not None]
    fl=sum(1 for c in cells for i in (0,1) if Y.get(f"{c}|{i}|0") is not None and Y.get(f"{c}|{i}|1") is not None and (Y[f"{c}|{i}|0"]>0)!=(Y[f"{c}|{i}|1"]>0))
    print(f"\n[C 双席位直接对打] r38c vs r34 {len(d)} 局: 胜 {sum(x>0 for x in d)} 平 {sum(x==0 for x in d)} 负 {sum(x<0 for x in d)} 均差 {sum(d)/max(1,len(d)):.0f}  同种子换席位胜负不同 {fl}/128",flush=True)
