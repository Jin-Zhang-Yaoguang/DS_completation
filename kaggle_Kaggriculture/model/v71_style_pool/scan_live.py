"""r25/r26/r28 在 ≥2200 对手上的分解:键×谱系、世界、开局动作、败局分化时点。"""
import json,glob,collections,statistics as st,os
VERS=tuple(os.environ.get("SCAN_VERS","r25,r26,r28").split(","))
MIN=float(os.environ.get("SCAN_MIN","2200"))
m=json.load(open("meta_live.json")); H=json.load(open("rkey_head.json"))
comp={}
for f in glob.glob("rlive3/*.json"):
    r=json.load(open(f)); comp[str(r["eid"])]=r
MILK={"PIZZA_SHOP","ICE_CREAM_SHOP","SMOOTHIE_SHOP"}
def lin_of(r):
    p=r["seat"]; o=1-p; M=r["money"]
    if not (M[92] and M[91]): return "?"
    if M[92][o]-M[91][o]>50: return "cha"
    if M[58] and M[57] and M[58][o]-M[57][o]>30: return "t58"
    return "main"
def world(sh):
    n=len([x for x in sh if x in MILK]); return "奶" if n else ("羊毛" if "YARN_STORE" in sh else "其他")
rows=[]
for e,v in m.items():
    if v["ver"] not in VERS or not v.get("opp") or v["opp"].get("reward") is None or v["me"].get("reward") is None: continue
    s=v["opp"]["initialScore"]
    if s<MIN: continue
    r=comp.get(e); key=str((H.get(e,{}).get("rkey") or ["?"])[0])
    d=v["me"]["reward"]-v["opp"]["reward"]
    lin=lin_of(r) if r else "?"; w=world((r.get("shops") or [])[:2]) if r else "?"
    div=None
    if r and d<0:
        p=r["seat"]; o=1-p; M=r["money"]
        for t in range(144,720,24):
            if M[t] and M[t][p]-M[t][o]<-500: div=t; break
    rows.append(dict(eid=e,seed=(r or {}).get("seed"),seat=(r or {}).get("seat"),ver=v["ver"],key=key,lin=lin,world=w,d=d,s=s,div=div,team=v.get("opp_team"),end=v.get("end")))
def tab(f,title):
    A=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0]))
    for x in rows: a=A[f(x)][x["ver"]]; a[0]+=x["d"]>0; a[1]+=1
    print(f"\n== {title}")
    for k in sorted(A,key=lambda k:-sum(a[1] for a in A[k].values())):
        print(f"  {str(k):22s} "+"  ".join(f"{v}:{A[k][v][0]}/{A[k][v][1]}" for v in VERS if A[k][v][1]))
tab(lambda x:"合计","合计(对手≥2200)")
tab(lambda x:(x["key"],x["lin"]),"键×谱系")
tab(lambda x:x["world"],"世界")
tab(lambda x:"2200-2300" if x["s"]<2300 else "2300-2400" if x["s"]<2400 else "≥2400","对手分段")
dv=collections.defaultdict(list)
for x in rows:
    if x["div"] is not None: dv[x["ver"]].append(x["div"])
print("\n== 败局现金差首次 < −500 的时点中位:",{k:(st.median(v),len(v)) for k,v in dv.items()})
json.dump(rows,open(os.environ.get("SCAN_OUT","scan_live_rows.json"),"w"))
