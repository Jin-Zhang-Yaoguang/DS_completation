"""对手指纹线上统计:类别 × 版本 → 场次/胜率/专属格命中/命中与未命中胜率。"""
import json, glob, collections, os, sys
m=json.load(open("meta_live.json")); H=json.load(open("rkey_head.json"))
comp={}
for f in glob.glob("rlive3/*.json"):
    r=json.load(open(f)); comp[str(r["eid"])]=r
VERS=["r20","r22","r25","r26","r28","r30","r32","r33","r34","r36"]
NS={}
for v in VERS:
    ns={}; exec(open(f"agents/v54{v}_main.py").read(), ns); NS[v]=ns
K39,K42,K51,K49=1039.0,1042.0,151.0,1049.0
def hit(v,key,lin,shops):
    ns=NS[v]; km=ns.get("_KEYMAP",{}) or {}
    k=km.get(key,key); rows=[]
    def has(n,cond=True):
        if cond and n in ns and shops in ns[n]: rows.append(n)
    if k in (K39,K42):
        for n in ("_V54R3_MIR","_R8_FREE","_R8_GATED","_R20_SPLICE","_R21_MIR"): has(n)
    if k==K42: has("_V54R3_HS")
    if k==K51: has("_V54R3_K52"); has("_R21_K52")
    if k==K49: has("_R22_MV4")
    if "_R23_CHA" in ns and lin=="cha" and shops in ns["_R23_CHA"].get((k,9989),{}): rows.append("_R23_CHA")
    if k==K39 and lin!="cha": has("_R28_MILK39")
    if k==K42 and lin!="cha": has("_R32_NEWGEN")
    return k,rows
def cls(key,lin,end):
    if key==K42 and lin=="cha": return "cha谱系(1042+t92)"
    if key==K42: return "新版人群(1042无t92,09-27后)" if end>="2026-09-27T12" else "老herdsafe(1042无t92,09-27前)"
    if key in (K39,1041.0,1043.0): return "rescue7系(1039/1041/1043)"
    if key==K51: return "K52(151)"
    if key==K49: return "metav4(1049)"
    return "未识别键"
MIN=float(os.environ.get("FP_MIN","2000"))
S=collections.defaultdict(lambda:[0,0,0,0,0,0])   # 场次 胜 命中 命中胜 未命中 未命中胜
rowc=collections.defaultdict(collections.Counter); CL=[]
for e,v in m.items():
    ver=v["ver"]
    if ver not in VERS or not v.get("opp") or v["opp"].get("reward") is None or v["me"].get("reward") is None: continue
    if (v["opp"].get("initialScore") or 0)<MIN: continue
    r=comp.get(e); hk=H.get(e,{}).get("rkey")
    if not r or not hk: continue
    p=r["seat"]; o=1-p; M=r["money"]
    lin="cha" if (M[92] and M[91] and M[92][o]-M[91][o]>50) else "main"
    shops=tuple((r.get("shops") or [])[:2]); key=float(hk[0])
    c=cls(key,lin,v.get("end") or ""); k2,rows=hit(ver,key,lin,shops)
    win=v["me"]["reward"]>v["opp"]["reward"]
    CL.append(dict(eid=e,ver=ver,cls=c,seed=r["seed"],seat=r["seat"],d=v["me"]["reward"]-v["opp"]["reward"],key=str(key),lin=lin,hit=bool(rows)))
    for kk in ((c,ver),(c,"全部")):
        a=S[kk]; a[0]+=1; a[1]+=win
        if rows: a[2]+=1; a[3]+=win
        else: a[4]+=1; a[5]+=win
    for rw in rows: rowc[c][rw]+=1
pct=lambda w,n: f"{w}/{n}({w/n:.0%})" if n else "-"
print(f"对手分 ≥{MIN:.0f}")
for c in sorted({k[0] for k in S},key=lambda c:-S[(c,"全部")][0]):
    a=S[(c,"全部")]
    print(f"\n【{c}】 共 {a[0]} 局 胜 {pct(a[1],a[0])} | 专属格命中 {a[2]} 局({a[2]/a[0]:.0%}) 命中胜 {pct(a[3],a[2])} | 未命中胜 {pct(a[5],a[4])}")
    print("   命中的表:",dict(rowc[c].most_common(6)))
    print("   分版本: "+"  ".join(f"{v}:{pct(S[(c,v)][1],S[(c,v)][0])}(命中{S[(c,v)][2]})" for v in VERS if S[(c,v)][0]))

json.dump(CL,open('fp_class_rows.json','w'))
