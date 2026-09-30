"""线上版本表现 + 对手指纹覆盖:识别键 / t92 谱系 / 针对格是否触发。用法: python coverage_live.py r25 r26"""
import sys, json, glob, collections
from pathlib import Path
HERE=Path(__file__).resolve().parent
ns={}; exec((HERE/"agents/v54r26_main.py").read_text(), ns)
K39,K42,K51,K49=(1039.0,9989),(1042.0,9989),(151.0,9959),(1049.0,9989)
def cells(key,lin,shops):
    hit=[]
    if key in (K39,K42):
        for n in ("_V54R3_MIR","_R8_FREE","_R8_GATED","_R20_SPLICE","_R21_MIR"):
            if shops in ns[n]: hit.append(n)
    if key==K42 and shops in ns["_V54R3_HS"]: hit.append("_V54R3_HS")
    if key==K51:
        for n in ("_V54R3_K52","_R21_K52"):
            if shops in ns[n]: hit.append(n)
    if key==K49 and shops in ns["_R22_MV4"]: hit.append("_R22_MV4")
    if lin=="cha" and shops in ns["_R23_CHA"].get(key,{}): hit.append("_R23_CHA")
    if "YARN_STORE" in shops and key in ns["_V93_ROUTE_BY_RIVAL"]: hit.append("_V93")
    return hit
m=json.load(open(HERE/"meta_live.json")); H=json.load(open(HERE/"rkey_head.json"))
comp={}
for f in glob.glob(str(HERE/"rlive3/*.json")):
    r=json.load(open(f)); comp[str(r["eid"])]=r
for ver in sys.argv[1:]:
    R=[(e,v) for e,v in m.items() if v["ver"]==ver and v.get("opp") and v["opp"].get("reward") is not None and v["me"].get("reward") is not None]
    R.sort(key=lambda x:x[1]["end"] or "")
    w=sum(v["me"]["reward"]>v["opp"]["reward"] for e,v in R)
    print(f"\n===== {ver}: {len(R)} 局 胜 {w} ({w/max(1,len(R)):.0%})  当前分 {R[-1][1]['me']['updatedScore']:.1f}  最高 {max(v['me']['updatedScore'] for e,v in R):.1f}")
    band=collections.defaultdict(lambda:[0,0,0.0]); lvl=collections.defaultdict(lambda:[0,0,0.0]); tabs=collections.Counter()
    for e,v in R:
        s=v["opp"]["initialScore"]; d=v["me"]["reward"]-v["opp"]["reward"]
        b=("<2000" if s<2000 else "2000-2200" if s<2200 else "2200-2400" if s<2400 else "≥2400")
        a=band[b]; a[0]+=d>0; a[1]+=1; a[2]+=d
        key=tuple(H.get(e,{}).get("rkey") or ()); r=comp.get(e)
        lin="?"; shops=()
        if r:
            p=r["seat"]; o=1-p; M=r["money"]
            if M[92] and M[91]: lin="cha" if M[92][o]-M[91][o]>50 else "main"
            shops=tuple((r.get("shops") or [])[:2])
        known=key in (K39,K42,K51,K49)
        hit=cells(key,lin,shops) if known and shops else []
        for h in hit: tabs[h]+=1
        L=("A 未识别键" if not known else "B 识别键·无针对格" if not hit else "C 识别键·针对格触发")
        if s>=2200: L2=L+"(对手≥2200)"
        for k in (L,)+((L2,) if s>=2200 else ()):
            a=lvl[k]; a[0]+=d>0; a[1]+=1; a[2]+=d
    print("  分段:", "  ".join(f"{b} {a[0]}/{a[1]}({a[2]/a[1]:+.0f})" for b,a in sorted(band.items())))
    for k in sorted(lvl): a=lvl[k]; print(f"  {k:28s} {a[1]:3d}局 胜{a[0]:3d} ({a[0]/a[1]:4.0%}) 均差{a[2]/a[1]:+7.0f}")
    print("  触发表:",dict(tabs))
    miss=collections.Counter(str(tuple(H.get(e,{}).get("rkey") or ())) for e,v in R if tuple(H.get(e,{}).get("rkey") or ()) not in (K39,K42,K51,K49))
    print("  未识别键分布:",dict(miss.most_common(8)))
