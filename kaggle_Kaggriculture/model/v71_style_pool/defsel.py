"""第3步 默认表重选:弱格 × 候选路线;选择集 = 代表(5)×种子idx0,1×双席位 + 官方回放 A 半;验证集 = 代表×种子idx3,4×双席位 + 官方回放 B 半。"""
import json, os, hashlib, collections, sys
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
from official_eval import sim
W=int(os.environ.get("KAG_WORKERS","8"))
REPS=["me2965_28","guru28","engineV3","rescue7","fieldcraft29"]
def half(eid): return "A" if int(hashlib.md5(str(eid).encode()).hexdigest(),16)%2==0 else "B"
def cands(cell,cur):
    base=[0,1,103,107,110,124,126] if "YARN_STORE" in cell else [100,103,105,107,110,112,124]
    return [cur]+[r for r in base if r!=cur]
def evaluate(cell,routes,seed_idx,part,IDX,rows):
    jobs=[]
    for r in routes:
        env=(f"KAG_DEFCELL={cell}",f"KAG_DEFROUTE={r}")
        for o in REPS:
            for i in seed_idx:
                for st in (0,1): jobs.append(("rep",r,("r38def",o,IDX[cell][i],st,f"{r}|{o}|{i}|{st}",env)))
        for x in rows:
            if tuple(x["shops"])==tuple(cell.split("|")) and half(x["eid"])==part:
                jobs.append(("off",r,("r38def","roff",x["eid"],x["seat"],env)))
    return jobs
def run(jobs):
    rep=[j for j in jobs if j[0]=="rep"]; off=[j for j in jobs if j[0]=="off"]
    with ProcessPoolExecutor(W) as ex:
        a=list(ex.map(be.one,[j[2] for j in rep],chunksize=2)); b=list(ex.map(sim,[j[2] for j in off],chunksize=2))
    S=collections.defaultdict(lambda:[0,0,0.0,0,0])   # route -> [rep胜, rep局, 均差和, off胜, off局]
    for j,(_,d) in zip(rep,a):
        if d is None: continue
        s=S[j[1]]; s[0]+=d>0; s[1]+=1; s[2]+=d
    for j,(_,x) in zip(off,b):
        if not x: continue
        s=S[j[1]]; s[3]+=x["d"]>0; s[4]+=1; s[2]+=x["d"]
    return S
if __name__=="__main__":
    IDX=json.load(open("combo_big.json"))["v54"]; rows=json.load(open("official_rows.json"))
    ns={}; exec(open("agents/v54r38e_main.py").read(),ns)
    def default(sh):
        r=ns["_R108_SHOP_ROUTES"].get(sh,100) if sh.count("YARN_STORE")<=0 else ns["_R110_OLD_SHOPS"].get(sh,0); return ns["_V92_TABLE"].get(sh,r)
    cells=json.load(open("weak_cells.json")); picks={}
    for cell in cells:
        cur=default(tuple(cell.split("|"))); R=cands(cell,cur)
        S=run(evaluate(cell,R,(0,1),"A",IDX,rows))
        score=lambda s:(s[0]+s[3])/max(1,s[1]+s[4])
        best=max(R,key=lambda r:(score(S[r]),S[r][2]))
        line=f"{cell:32s} 当前 {cur}: {S[cur][0]}/{S[cur][1]}+{S[cur][3]}/{S[cur][4]}"
        if best!=cur and (S[best][0]+S[best][3])-(S[cur][0]+S[cur][3])>=3:
            V=run(evaluate(cell,[cur,best],(3,4),"B",IDX,rows))
            dv=(V[best][0]+V[best][3])-(V[cur][0]+V[cur][3])
            line+=f" → 选 {best}: {S[best][0]}/{S[best][1]}+{S[best][3]}/{S[best][4]} | 验证 当前 {V[cur][0]}/{V[cur][1]}+{V[cur][3]}/{V[cur][4]} 新 {V[best][0]}/{V[best][1]}+{V[best][3]}/{V[best][4]} 差 {dv:+d}"
            if dv>0: picks[cell]=best; line+=" ✔采纳"
            else: line+=" ✘验证未过"
        else: line+=f" (最佳 {best} 增益不足)"
        print(line,flush=True)
        json.dump(picks,open("defsel_picks.json","w"))
    print("采纳",len(picks),picks)
