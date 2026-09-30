"""按人群选分支(轴1识别 × 轴3针对 × 轴2保真):
人群按对手第2步现金划分:P=公开底盘(1030-1060) A=动物流头部(560-600,Arjun/Alan/Vlas/Luca/hff/Aaweg) L=低现金(<560,DeeperNet/Planned/花光型)。
每个人群、每个前两店组合:评估集 = 该人群对手的开环回放(官方 roff/roff_af + 我方线上 rlive3,近5天,按组合分组,偶数位选择/奇数位验证,各≤CAP)
 + 该人群本地闭环代表(combo_big 选择 idx20,21 / 验证 idx16,17,双席位)。
候选 = v55d 当前分支(基线) + arjun100 中同第1家商店的全部对局(探针 v55y + KAG_V55_OVR)。选择集更优且验证集不差才采纳。
用法: python sel_cls.py P|A|L [CAP]   输出 sel_cls_<人群>.json"""
import json, os, sys, glob, random, collections
from concurrent.futures import ProcessPoolExecutor
from official_eval import sim
import board_eval2 as be
CUT=113065923
REPS={"P":["me2965_28","engineV3","v54r38g"],"A":["afrep_arjun","v55b"],"L":["afrep_deepernet","afrep_planned"]}
RANGE={"P":(1030,1060),"A":(560,600),"L":(-1,560)}
def job(j):
    kind=j[0]; os.environ.pop("KAG_V55_OVR",None)
    if kind=="open":
        _,ag,src,eid,seat,env,tag=j; r=sim((ag,src,eid,seat,env))[1]; return tag,(r or {}).get("d")
    _,ag,opp,seed,seat,env,tag=j; return tag,be.one((ag,opp,seed,seat,tag,env))[1]
def boards(cls):
    lo,hi=RANGE[cls]; out=collections.defaultdict(list)
    for src in ("roff","roff_af","rlive3"):
        for f in glob.glob(f"{src}/*.json"):
            eid=os.path.basename(f)[:-5]
            if int(eid)<CUT: continue
            try: r=json.load(open(f))
            except Exception: continue
            M=r.get("money"); sh=r.get("shops") or []
            if not M or len(M)<3 or not M[2] or len(sh)<2: continue
            seats=[r["seat"]] if src=="rlive3" else [s for s in (0,1) if r["names"][1-s]!="datatuu"]
            for s in seats:
                c=M[2][1-s]
                if lo<=c<hi: out["|".join(sh[:2])].append((src,eid,s))
    return out
def run(jobs):
    with ProcessPoolExecutor(8) as ex: return dict(ex.map(job,jobs,chunksize=4))
def stat(R,pre):
    d=[v for k,v in R.items() if k.startswith(pre) and v is not None]; return sum(x>0 for x in d),len(d),sum(d)
if __name__=="__main__":
    cls=sys.argv[1]; CAP=int(sys.argv[2]) if len(sys.argv)>2 else 40
    IDX=json.load(open("combo_big.json"))["v54"]; LIB=json.load(open("agents/arjun100.json"))
    B=boards(cls); rnd=random.Random(1001)
    outf=f"sel_cls_{cls}.json"; picks=json.load(open(outf)) if os.path.exists(outf) else {}
    print(f"人群{cls}: 组合 {len(B)} 板 {sum(len(v) for v in B.values())}",flush=True)
    for c in sorted(IDX):
        if c in picks: continue
        L=sorted(B.get(c,[])); rnd.shuffle(L); SEL=L[0::2][:CAP]; VAL=L[1::2][:CAP]
        cands=[e for e,v in LIB.items() if v["shops"][0]==c.split("|")[0]]
        def jobs(ag_env_tag,units,idxs):
            J=[]
            for tag,env in ag_env_tag:
                J+=[("open","v55y",src,eid,s,env,f"{tag}|o|{src}|{eid}|{s}") for src,eid,s in units]
                J+=[("closed","v55y",o,IDX[c][i],st,env,f"{tag}|c|{o}|{i}|{st}") for o in REPS[cls] for i in idxs for st in (0,1)]
            return J
        arms=[("base",())]+[(e,(f"KAG_V55_OVR={c}={e}",)) for e in cands]
        R=run(jobs(arms,SEL,(20,21)))
        sc={t:stat(R,t+"|") for t,_ in arms}; b=sc["base"]
        best=max(cands,key=lambda e:(sc[e][0],sc[e][2])) if cands else None
        line=f"{c:30s} 板{len(SEL)}+{len(VAL)} 基线 {b[0]}/{b[1]} 均{b[2]/max(1,b[1]):7.0f}"
        rec={"pick":None,"sel":{t:list(v) for t,v in sc.items()}}
        if best and (sc[best][0]>b[0] or (sc[best][0]==b[0] and (sc[best][2]-b[2])/max(1,b[1])>1000)):
            line+=f" | 最佳 {best} {sc[best][0]}/{sc[best][1]} 均{sc[best][2]/max(1,sc[best][1]):7.0f}"
            V=run(jobs([("n",(f"KAG_V55_OVR={c}={best}",)),("b",())],VAL,(16,17))); vn=stat(V,"n|"); vb=stat(V,"b|")
            line+=f" | 验证 新 {vn[0]}/{vn[1]}({vn[2]/max(1,vn[1]):7.0f}) 基 {vb[0]}/{vb[1]}({vb[2]/max(1,vb[1]):7.0f})"
            rec["val"]=[list(vn),list(vb)]
            if vn[0]>=vb[0] and vn[2]>vb[2]: rec["pick"]=best; line+=" ✔"
            else: line+=" ✘"
        print(line,flush=True); picks[c]=rec; json.dump(picks,open(outf,"w"))
    print("采纳",{c:v["pick"] for c,v in picks.items() if v["pick"]})
