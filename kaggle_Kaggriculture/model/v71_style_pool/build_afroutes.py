"""把固定带型动物优先队伍(DeeperNet / Planned Economy / Arjun Vinod)的对局整理成路线表:
每队:按前两家商店分组,每组选一局(优先对手为固定路线型、该队赢的局)作为该商店组合的整局动作带;另存一局作默认。输出 afroutes.json。"""
import json, glob, collections
from review_fp import cls
FIXED={"新版人群","cha谱系","rescue7系","metav4","K52"}
TEAMS=["DeeperNet","Planned Economy","Arjun Vinod"]
out={t:{"by_shops":{},"first_shop":{},"default":None,"n":0} for t in TEAMS}
cand=collections.defaultdict(list)
for f in glob.glob("roff_af/*.json"):
    r=json.load(open(f)); nm=r["names"]; M=r["money"]
    for p,n in enumerate(nm):
        if n not in TEAMS: continue
        o=1-p; sk=r["key2"][o]
        if not (sk[1] in (9990,9991,9992) and sk[0]<900): continue
        k=r["key2"][p]; lin="cha" if (M[92] and M[91] and M[92][o]-M[91][o]>50) else "main"
        oc=cls(float(round(k[0])),lin); won=(r["rewards"][p] or 0)>(r["rewards"][o] or 0)
        tape=[(r["acts"][t+1][p] or {"farmer":["PASS"],"hands":[],"market":[]}) for t in range(len(r["acts"])-1)]
        cand[n].append(dict(shops=tuple((r["shops"] or [])[:2]),vs_fixed=oc in FIXED,won=won,tape=tape,eid=r["eid"],margin=(r["rewards"][p] or 0)-(r["rewards"][o] or 0)))
for t,L in cand.items():
    out[t]["n"]=len(L)
    g=collections.defaultdict(list)
    for x in L: g["|".join(x["shops"])].append(x)
    for sh,xs in g.items():
        xs.sort(key=lambda x:(x["vs_fixed"],x["won"],x["margin"]),reverse=True)
        out[t]["by_shops"][sh]={"eid":xs[0]["eid"],"tape":xs[0]["tape"]}
    g1=collections.defaultdict(list)
    for x in L: g1[x["shops"][0] if x["shops"] else ""].append(x)
    for s1,xs in g1.items():
        xs.sort(key=lambda x:(x["vs_fixed"],x["won"],x["margin"]),reverse=True)
        out[t]["first_shop"][s1]={"eid":xs[0]["eid"],"tape":xs[0]["tape"]}
    L.sort(key=lambda x:(x["vs_fixed"],x["won"],x["margin"]),reverse=True)
    out[t]["default"]={"eid":L[0]["eid"],"tape":L[0]["tape"]}
    print(f"{t}: 局 {len(L)} 覆盖前两商店组合 {len(out[t]['by_shops'])}/64 覆盖第1家商店 {len(out[t]['first_shop'])}/8")
json.dump(out,open("afroutes.json","w"))
