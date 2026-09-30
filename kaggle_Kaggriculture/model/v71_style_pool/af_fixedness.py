"""动物优先顶队是否"按上下文查表的固定带":同队 × 同对手类型 × 同前两家商店 的对局之间,动作序列公共前缀长度(步)。
对照:同队不同商店;同队不同对手类型。"""
import json, glob, collections, statistics as st
from review_fp import cls
TEAMS=["Luca","Aaweg","Planned Economy","Arjun Vinod","high frequency farming","Alan C52","daulettoibazar","pangzi233","DeeperNet","Vlas Veles","tine.sh agent"]
FIXED={"新版人群","cha谱系","rescue7系","metav4","K52"}
G=collections.defaultdict(list)
for f in glob.glob("roff_af/*.json"):
    r=json.load(open(f)); nm=r["names"]; M=r["money"]
    for p,n in enumerate(nm):
        if n not in TEAMS: continue
        o=1-p; sk=r["key2"][o]
        if not (sk[1] in (9990,9991,9992) and sk[0]<900): continue
        k=r["key2"][p]; lin="cha" if (M[92] and M[91] and M[92][o]-M[91][o]>50) else "main"
        oc=cls(float(round(k[0])),lin); kind="固定路线型" if oc in FIXED else ("动物优先" if (k[1] in (9990,9991,9992) and k[0]<900) else "其他")
        seq=[json.dumps(r["acts"][t][p],sort_keys=True) for t in range(1,len(r["acts"]))]
        mk=[json.dumps((r["acts"][t][p] or {}).get("market") or [],sort_keys=True) for t in range(1,len(r["acts"]))]
        G[n].append(dict(kind=kind,shops=tuple((r["shops"] or [])[:2]),seq=seq,mk=mk,eid=r["eid"]))
def lcp(a,b):
    n=0
    for x,y in zip(a,b):
        if x!=y: break
        n+=1
    return n
print(f"{'队伍':22s} 局 | 同对手类型+同前两商店: 全动作前缀 / 仅市场动作前缀 (中位,步) | 同对手类型不同商店 | 不同对手类型")
for team,L in sorted(G.items(),key=lambda kv:-len(kv[1])):
    same=[];samem=[];diffshop=[];diffkind=[]
    for i in range(len(L)):
        for j in range(i+1,len(L)):
            a,b=L[i],L[j]
            if a["kind"]==b["kind"] and a["shops"]==b["shops"]: same.append(lcp(a["seq"],b["seq"])); samem.append(lcp(a["mk"],b["mk"]))
            elif a["kind"]==b["kind"]: diffshop.append(lcp(a["seq"],b["seq"]))
            else: diffkind.append(lcp(a["seq"],b["seq"]))
    med=lambda x: f"{st.median(x):.0f}(n={len(x)})" if x else "-"
    print(f"{team[:22]:22s} {len(L):3d} | {med(same)} / {med(samem)} | {med(diffshop)} | {med(diffkind)}")
