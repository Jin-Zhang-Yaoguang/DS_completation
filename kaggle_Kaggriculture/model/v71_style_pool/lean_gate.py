"""精简门控:候选 vs 基线,配对样本分批跑,缓存结果,按翻转局单侧符号检验提前停止。
用法: python lean_gate.py <候选agent> <基线agent> [候选env,..] [--max 960] [--batch 160]
样本单元:大种子 idx20,21 × 5 代表 × 双席位 + 官方回放按类分层(每类≤80),随机混合。"""
import json, os, sys, random, hashlib, collections, math
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
from official_eval import sim
OPPS=["me2965_28","guru28","engineV3","rescue7","fieldcraft29"]
CACHE="lean_cache.json"
def fp(agent,env): return hashlib.md5(open(f"agents/{agent}_main.py","rb").read()+"|".join(env).encode()).hexdigest()[:12]
def run_unit(args):
    agent,env,u=args
    if u[0]=="rep":
        _,o,seed,st=u; _,d=be.one((agent,o,seed,st,"x",tuple(env))); return d
    _,eid,seat=u; _,x=sim((agent,"roff",eid,seat,tuple(env))); return (x or {}).get("d")
def binom_p(k,n):   # P(X>=k), X~Bin(n,0.5)
    return sum(math.comb(n,i) for i in range(k,n+1))/2**n if n else 1.0
if __name__=="__main__":
    cand,base=sys.argv[1],sys.argv[2]; cenv=[x for x in (sys.argv[3].split(";") if len(sys.argv)>3 and not sys.argv[3].startswith("--") else []) if x]
    MAX=int(sys.argv[sys.argv.index("--max")+1]) if "--max" in sys.argv else 960
    B=int(sys.argv[sys.argv.index("--batch")+1]) if "--batch" in sys.argv else 160
    IDX=json.load(open("combo_big.json"))["v54"]; cells=sorted(IDX)
    SEEDI=[int(x) for x in sys.argv[sys.argv.index("--idx")+1].split(",")] if "--idx" in sys.argv else [20,21]
    units=[("rep",o,IDX[c][i],st) for o in OPPS for c in cells for i in SEEDI for st in (0,1)]
    rows=json.load(open("official_rows.json")); byc=collections.defaultdict(list)
    for r in rows: byc[r["cls"]].append(r)
    rnd=random.Random(20260930)
    if "--nooff" not in sys.argv:
        for c,L in byc.items(): rnd.shuffle(L); units+=[("off",r["eid"],r["seat"]) for r in L[:80]]
    rnd.shuffle(units); units=units[:MAX]
    cache=json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    fc,fb=fp(cand,cenv),fp(base,[])
    key=lambda f,u: f+"|"+"|".join(map(str,u))
    plus=minus=same=0; done=0; per=collections.Counter(); verdict="无显著差异"
    for s in range(0,len(units),B):
        batch=units[s:s+B]; todo=[]
        for u in batch:
            for ag,env,f in ((cand,cenv,fc),(base,[],fb)):
                if key(f,u) not in cache: todo.append((ag,env,f,u))
        if todo:
            with ProcessPoolExecutor(8) as ex: res=list(ex.map(run_unit,[(a,e,u) for a,e,f,u in todo],chunksize=2))
            for (a,e,f,u),d in zip(todo,res): cache[key(f,u)]=d
            json.dump(cache,open(CACHE,"w"))
        for u in batch:
            a,b=cache.get(key(fc,u)),cache.get(key(fb,u))
            if a is None or b is None: continue
            done+=1
            if a>0>=b: plus+=1; per[("+",u[0] if u[0]=="off" else u[1])]+=1
            elif b>0>=a: minus+=1; per[("-",u[0] if u[0]=="off" else u[1])]+=1
            else: same+=1
        n=plus+minus; pu=binom_p(plus,n); pd=binom_p(minus,n)
        print(f"  已评 {done} 配对:翻转 +{plus} / −{minus}(其余 {same} 同胜负)  p(更好)={pu:.3f} p(更差)={pd:.3f}",flush=True)
        if n>=8 and pu<0.05: verdict="通过(显著更好)"; break
        if n>=8 and pd<0.05: verdict="失败(显著更差)"; break
    print(f"结论:{cand}{'('+','.join(cenv)+')' if cenv else ''} vs {base}:{verdict};翻转分布 {dict(per)}")
