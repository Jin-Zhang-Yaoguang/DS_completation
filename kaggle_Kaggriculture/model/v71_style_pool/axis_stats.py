"""四轴三指标:按对手人群统计 占比/胜率/均差(方向0)、r38 针对格覆盖(方向1)、命中与未命中胜率(方向3);保真另由 fid_recent.py 给出(方向2)。"""
import json, glob, collections, os
m=json.load(open("meta_live.json")); H=json.load(open("rkey_head.json"))
comp={}
for f in glob.glob("rlive3/*.json"):
    r=json.load(open(f)); comp[str(r["eid"])]=r
ns={}; exec(open("agents/v54r38_main.py").read(), ns)
K39,K42,K51,K49=1039.0,1042.0,151.0,1049.0
def cls(key,lin):
    if key==K42 and lin=="cha": return "cha谱系"
    if key==K42: return "新版人群"
    if key in (K39,1041.0,1043.0): return "rescue7系"
    if key==K51: return "K52"
    if key==K49: return "metav4"
    if key<900 and key!=7.0: return "Majkel式(<900)"
    return "未识别键"
def cover(c,shops):
    """r38 在该盘会触发的专属针对(不含通用底盘表)。"""
    rows=[]
    if c=="cha谱系":
        if shops in ns["_R38_CHA"]: rows.append("R38_CHA")
        elif shops in ns["_R23_CHA"].get((K42,9989),{}): rows.append("R23_CHA")
        if shops in ns["_R33_CHA_LATE"]: rows.append("R33_CHA_LATE")
    if c=="新版人群":
        if shops in ns["_R36_MILK"]: rows.append("R36_MILK")
        if shops in ns["_R32_NEWGEN"]: rows.append("R32_NEWGEN")
        if shops in ns["_R33_NEWGEN_LATE"]: rows.append("R33_LATE")
    if c=="rescue7系":
        for n in ("_R28_MILK39","_R21_MIR","_R20_SPLICE"):
            if shops in ns[n]: rows.append(n[1:])
    if c=="K52":
        for n in ("_R21_K52",):
            if shops in ns[n]: rows.append(n[1:])
    if c=="metav4" and shops in ns["_R22_MV4"]: rows.append("R22_MV4")
    if c=="Majkel式(<900)": rows.append("R37_MAJKEL")
    return rows
MIN=float(os.environ.get("FP_MIN","2000")); SINCE=os.environ.get("SINCE","2026-09-27T12")
VERS=os.environ.get("VERS","r32,r33,r34,r36").split(",")
S=collections.defaultdict(lambda: collections.Counter()); CL=[]; nall=0
for e,v in m.items():
    if v["ver"] not in VERS or not v.get("opp") or v["opp"].get("reward") is None or v["me"].get("reward") is None: continue
    if (v["opp"].get("initialScore") or 0)<MIN or (v.get("end") or "")<SINCE: continue
    nall+=1
    r=comp.get(e); hk=H.get(e,{}).get("rkey")
    if not r or not hk: S["(缺回放)"]["n"]+=1; continue
    o=1-r["seat"]; M=r["money"]
    lin="cha" if (M[92] and M[91] and M[92][o]-M[91][o]>50) else "main"
    shops=tuple((r.get("shops") or [])[:2]); key=float(hk[0]); c=cls(key,lin)
    d=v["me"]["reward"]-v["opp"]["reward"]; win=d>0; rows=cover(c,shops)
    for kk in (c,"全部"):
        a=S[kk]; a["n"]+=1; a["w"]+=win; a["d"]+=d
        a["hn"]+=bool(rows); a["hw"]+=win and bool(rows)
        a[f"n_{v['ver']}"]+=1; a[f"w_{v['ver']}"]+=win
    milk=any(s in ("ICE_CREAM_SHOP","SMOOTHIE_SHOP","YARN_STORE") for s in shops)  # 奶/毛类世界(粗)
    CL.append(dict(eid=e,ver=v["ver"],cls=c,seed=r["seed"],seat=r["seat"],d=d,shops=list(shops),hit=rows,end=v["end"],opp=v["opp"]["initialScore"],team=v.get("opp_team")))
json.dump(CL,open("axis_rows.json","w"))
pct=lambda w,n: f"{w}/{n} {w/n:.0%}" if n else "-"
print(f"对手分≥{MIN:.0f}  时间≥{SINCE}  版本{VERS}  有效 {nall} 局")
print(f"{'人群':14s} {'占比':>5s} {'胜率':>12s} {'均差':>7s} {'r38覆盖':>8s} {'命中胜':>11s} {'未命中胜':>11s} {'败局':>4s} | 分版本")
for c in sorted(S,key=lambda c:-S[c]["n"]):
    a=S[c]; n=a["n"]
    if c=="(缺回放)": print(c,n); continue
    mw=a["w"]-a["hw"]; mn=n-a["hn"]
    per="  ".join(f"{v}:{pct(a[f'w_{v}'],a[f'n_{v}'])}" for v in VERS if a[f"n_{v}"])
    print(f"{c:14s} {n/S['全部']['n']:5.0%} {pct(a['w'],n):>12s} {a['d']/n:7.0f} {a['hn']/n:8.0%} {pct(a['hw'],a['hn']):>11s} {pct(mw,mn):>11s} {n-a['w']:4d} | {per}")
