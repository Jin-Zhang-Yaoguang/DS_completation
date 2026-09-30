"""线上报告(不依赖限流接口):SDK 列对局 + 回放取指纹/商店 + 排行榜分数近似对手分。"""
import json, glob, subprocess, collections, sys, csv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from kaggle.api.kaggle_api_extended import KaggleApi
HERE=Path(__file__).resolve().parent
from review_fp import cls
LB={}
for f in glob.glob(sys.argv[1]+"/*.csv"):
    for r in csv.DictReader(open(f,encoding="utf-8-sig")): LB[r["TeamName"]]=float(r["Score"])
VERS={"r38c":56670130,"r38原":56663930,"r38b":56665280}
api=KaggleApi(); api.authenticate()
CACHE=HERE/"live2_cache.json"; C=json.load(open(CACHE)) if CACHE.exists() else {}
def fetch(eid):
    if eid in C: return eid,C[eid]
    raw=subprocess.run(["curl","-sL","--compressed","-m","300",f"https://www.kaggleusercontent.com/episodes/{eid}.json"],capture_output=True).stdout
    try:
        r=json.loads(raw); nm=r["info"]["TeamNames"]; p=nm.index("datatuu"); o=1-p; s=r["steps"]
        ob=s[2][p]["observation"]; key=(float(ob["farms"][o]["money"]),int(ob["market"]["inventory"]["WHEAT"]))
        m91=s[91][p]["observation"]["farms"][o]["money"]; m92=s[92][p]["observation"]["farms"][o]["money"]
        shops=None
        for t in range(len(s)):
            tw=(s[t][p].get("observation") or {}).get("town")
            if tw: shops=tw.get("unlocked_shops")
        return eid,{"key":key,"lin":"cha" if m92-m91>50 else "main","shops":(shops or [])[:2],"opp":nm[o],"rew":r["rewards"],"p":p}
    except Exception as ex: return eid,None
nsd={}
for v in ("v54r38c","v54r38"):
    ns={}; exec(open(f"agents/{v}_main.py").read(),ns); nsd[v]=ns
K42=1042.0
def hit(ns,c,shops,key):
    t=lambda n: shops in ns[n]
    if c=="新版人群": return t("_R36_MILK") or t("_R32_NEWGEN") or t("_R33_NEWGEN_LATE")
    if c=="cha谱系": return t("_R38_CHA") or shops in ns["_R23_CHA"][(K42,9989)] or t("_R33_CHA_LATE")
    if c=="rescue7系": return t("_R28_MILK39") or t("_R21_MIR") or t("_R20_SPLICE")
    if c=="K52": return t("_R21_K52") or t("_V54R3_K52")
    if c=="metav4": return t("_R22_MV4")
    if c=="Majkel簇": return True
    if c=="其他低现金": return "r38c" not in ns.get("__file__","") and ns is nsd["v54r38"]
    return False
band=lambda s: "<1500" if s<1500 else "1500-2000" if s<2000 else "2000-2200" if s<2200 else "2200-2400" if s<2400 else "≥2400"
for name,sub in VERS.items():
    eps=[e for e in api.competition_list_episodes(sub) if str(getattr(e,"state","")).endswith("COMPLETED") and "PUBLIC" in str(getattr(e,"type",""))]
    with ThreadPoolExecutor(4) as ex: R=dict(ex.map(fetch,[str(e.id) for e in eps]))
    C.update({k:v for k,v in R.items() if v}); json.dump(C,open(CACHE,"w"))
    ns=nsd["v54r38c" if name=="r38c" else "v54r38"]
    rows=[]
    for e in eps:
        x=R.get(str(e.id))
        if not x: continue
        c=cls(float(round(x["key"][0])),x["lin"]); win=x["rew"][x["p"]]>x["rew"][1-x["p"]]
        rows.append(dict(c=c,win=win,d=x["rew"][x["p"]]-x["rew"][1-x["p"]],h=hit(ns,c,tuple(x["shops"]),x["key"]),s=LB.get(x["opp"],0),opp=x["opp"],key=x["key"],end=str(e.end_time)))
    W=sum(r["win"] for r in rows)
    print(f"\n=== {name}: {len(rows)} 局 胜 {W} ({W/max(1,len(rows)):.0%})  对手分段(排行榜现分): "+"  ".join(f"{b} {sum(r['win'] for r in rows if band(r['s'])==b)}/{sum(1 for r in rows if band(r['s'])==b)}" for b in ("<1500","1500-2000","2000-2200","2200-2400","≥2400") if any(band(r['s'])==b for r in rows)))
    S=collections.defaultdict(lambda:collections.Counter())
    for r in rows:
        a=S[r["c"]]; a["n"]+=1; a["w"]+=r["win"]; a["h"]+=r["h"]; a["hw"]+=r["h"] and r["win"]; a["d"]+=r["d"]
    print(f"   {'类别':10s} {'局':>3s} {'胜':>8s} {'命中':>6s} {'命中胜':>8s} {'未命中胜':>8s} {'均差':>7s}")
    for c,a in sorted(S.items(),key=lambda kv:-kv[1]["n"]):
        n=a["n"]; f=lambda x,y:f"{x}/{y}" if y else "-"
        print(f"   {c:10s} {n:3d} {f(a['w'],n):>8s} {f(a['h'],n):>6s} {f(a['hw'],a['h']):>8s} {f(a['w']-a['hw'],n-a['h']):>8s} {a['d']/n:7.0f}")
    L=[r for r in rows if not r["win"]]
    print("   败局明细:"); 
    for r in sorted(L,key=lambda r:r["end"]): print(f"     {r['end'][11:16]} {r['c']:8s} 命中{'Y' if r['h'] else 'N'} 对手 {r['opp'][:18]:18s} 榜分 {r['s']:6.0f} 键 {round(r['key'][0])}/{r['key'][1]} 差 {r['d']:7.0f}")
