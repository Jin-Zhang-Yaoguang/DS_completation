"""可行性:从市场库存增量推断对手卖量(高价品),与对手真实 SELL 对比。按 step%4 区分是否有城镇消耗。"""
import sys, json, collections
M="/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model"
sys.path.insert(0,M+"/v4_demand_race/harness"); import engine
PREM=("CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL","FERTILIZER")
def load(p,fn):
    ns={"__name__":"m"}; exec(open(p).read(),ns); return ns[fn]
A=load("agents/v54r38g_main.py","_lead_final"); B=load("agents/me2965_28_main.py","agent")
stats=collections.defaultdict(lambda:[0,0,0])   # step%4 -> [步数, 推断=真实, 真实>0 的步数]
exact=collections.Counter(); tot=collections.Counter()
for seed in (1500000017,1700000033):
    k=engine.load_kagsim(); g=k.Game(seed=seed); prev=None; t=0
    while not engine._val(g.done):
        o0=g.observe(0); o1=g.observe(1); a0=A(o0); a1=B(o1)
        inv=dict(o0["market"]["inventory"])
        if prev is not None:
            pinv,pa0,pa1=prev
            for it in PREM:
                ours=sum(int(x[2]) for x in (pa0.get("market") or []) if x and x[0]=="SELL" and x[1]==it and len(x)>2)
                theirs=sum(int(x[2]) for x in (pa1.get("market") or []) if x and x[0]=="SELL" and x[1]==it and len(x)>2)
                buys=sum(int(x[2]) for p in (pa0,pa1) for x in (p.get("market") or []) if x and x[0]=="BUY_PRODUCT" and x[1]==it and len(x)>2)
                inferred=inv[it]-pinv[it]-ours+buys
                ph=(t-1)%4
                s=stats[ph]; s[0]+=1; s[1]+=inferred==theirs; s[2]+=theirs>0
                if theirs>0: tot[ph]+=1; exact[ph]+=inferred==theirs
        prev=(inv,a0 or {},a1 or {})
        g.step(a0,a1); t+=1
for ph in sorted(stats):
    s=stats[ph]; print(f"上一步 step%4={ph}: 品项-步 {s[0]} 推断完全正确 {s[1]/s[0]:.1%} | 对手真有卖出的 {tot[ph]} 次中推断正确 {exact[ph]/max(1,tot[ph]):.1%}")
