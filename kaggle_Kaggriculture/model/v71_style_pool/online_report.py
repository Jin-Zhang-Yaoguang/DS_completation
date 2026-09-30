"""线上成绩汇报(最近 5 天):分数/胜率/分段胜率/指纹类别命中与命中胜率。"""
import json, glob, collections, datetime, sys
m=json.load(open("meta_live.json")); H=json.load(open("rkey_head.json"))
comp={}
for f in glob.glob("rlive3/*.json"):
    r=json.load(open(f)); comp[str(r["eid"])]=r
SINCE=(datetime.datetime.utcnow()-datetime.timedelta(days=5)).strftime("%Y-%m-%dT%H")
VERS=sys.argv[1:] or ["r34","r36","r38","r38b"]
NS={}
for v in set(x if x!="r38b" else "r38" for x in VERS):
    ns={}; exec(open(f"agents/v54{v}_main.py").read(),ns); NS[v]=ns
K42=1042.0
def cls(key,lin):
    if key==K42 and lin=="cha": return "cha谱系"
    if key==K42: return "新版人群"
    if key in (1039.0,1041.0,1043.0): return "rescue7系"
    if key==151.0: return "K52"
    if key==1049.0: return "metav4"
    if 460<=key<=650: return "Majkel簇"
    if key<900: return "其他低现金"
    return "其他键"
def hit(ver,c,key,shops):
    ns=NS["r38" if ver=="r38b" else ver]; t=lambda n: n in ns and shops in ns[n]
    if c=="cha谱系": return t("_R38_CHA") or shops in ns.get("_R23_CHA",{}).get((K42,9989),{}) or t("_R33_CHA_LATE")
    if c=="新版人群": return t("_R36_MILK") or t("_R32_NEWGEN") or t("_R33_NEWGEN_LATE")
    if c=="rescue7系": return t("_R28_MILK39") or t("_R21_MIR") or t("_R20_SPLICE")
    if c=="K52": return t("_R21_K52")
    if c=="metav4": return t("_R22_MV4")
    if c in ("Majkel簇","其他低现金"): return "_R37_MAJKEL_ROUTE" in ns and key not in (151.0,7.0)
    return False
print(f"窗口:{SINCE} 之后(最近 5 天)")
for ver in VERS:
    G=sorted([(v["end"],e,v) for e,v in m.items() if v["ver"]==ver and v.get("opp") and v["opp"].get("reward") is not None and v["me"].get("reward") is not None and (v.get("end") or "")>=SINCE])
    if not G: continue
    w=sum(v["me"]["reward"]>v["opp"]["reward"] for _,_,v in G); last=G[-1][2]["me"]["updatedScore"]
    bands=collections.defaultdict(lambda:[0,0])
    for _,e,v in G:
        s=v["opp"]["initialScore"]; b="<1500" if s<1500 else "1500-2000" if s<2000 else "2000-2200" if s<2200 else "≥2200"
        bands[b][0]+=1; bands[b][1]+=v["me"]["reward"]>v["opp"]["reward"]
    print(f"\n=== {ver}: {len(G)} 局 胜 {w} ({w/len(G):.0%}) 当前分 {last:.1f}  分段: "+"  ".join(f"{b} {bands[b][1]}/{bands[b][0]}" for b in ("<1500","1500-2000","2000-2200","≥2200") if bands[b][0]))
    S=collections.defaultdict(lambda:collections.Counter()); miss=0
    for _,e,v in G:
        r=comp.get(e); hk=(H.get(e) or {}).get("rkey")
        if not r or not hk: miss+=1; continue
        o=1-r["seat"]; M=r["money"]; lin="cha" if (M[92] and M[91] and M[92][o]-M[91][o]>50) else "main"
        shops=tuple((r.get("shops") or [])[:2]); key=float(hk[0]); c=cls(key,lin); h=hit(ver,c,key,shops); win=v["me"]["reward"]>v["opp"]["reward"]
        a=S[c]; a["n"]+=1; a["w"]+=win; a["h"]+=h; a["hw"]+=win and h; a["d"]+=v["me"]["reward"]-v["opp"]["reward"]; a["hi"]+=v["opp"]["initialScore"]>=2000; a["hiw"]+=win and v["opp"]["initialScore"]>=2000
    print(f"   {'类别':10s} {'局':>4s} {'胜率':>10s} {'命中':>9s} {'命中胜':>10s} {'未命中胜':>10s} {'≥2000胜':>9s} {'均差':>7s}")
    for c,a in sorted(S.items(),key=lambda kv:-kv[1]["n"]):
        n=a["n"]; mn=n-a["h"]; mw=a["w"]-a["hw"]
        f=lambda x,y: f"{x}/{y}" if y else "-"
        print(f"   {c:10s} {n:4d} {f(a['w'],n)+f' {a[chr(119)]/n:.0%}':>10s} {f(a['h'],n):>9s} {f(a['hw'],a['h']):>10s} {f(mw,mn):>10s} {f(a['hiw'],a['hi']):>9s} {a['d']/n:7.0f}")
    if miss: print(f"   (无回放/无指纹 {miss} 局)")
