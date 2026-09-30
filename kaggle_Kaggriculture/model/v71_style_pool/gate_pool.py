"""新门控第二部分:同一对手池(官方回放 1798 开环 + 我方线上对局反事实)上,候选与三个基线的胜率。结果缓存到 pool_cache.json。"""
import json, os, sys, collections
from concurrent.futures import ProcessPoolExecutor
from official_eval import sim
from review_fp import cls
if __name__=="__main__":
    AG=sys.argv[1].split(",")
    cache=json.load(open("pool_cache.json")) if os.path.exists("pool_cache.json") else {}
    rows=json.load(open("official_rows.json")); G=json.load(open("online_games.json"))
    import random
    rnd=random.Random(930); byc=collections.defaultdict(list)
    for r in rows: byc[r["cls"]].append(r)
    units=[]
    for c,L in byc.items(): rnd.shuffle(L); units+=[("roff",r["eid"],r["seat"],r["cls"]) for r in L[:80]]
    on=[("rlive3",e,v["seat"],cls(float(round(v["key"][0])),v["lin"]) if v.get("key") else "?") for e,v in G.items()]
    rnd.shuffle(on); units+=on[:300]
    jobs=[(a,src,e,s,()) for a in AG for src,e,s,_ in units if f"{a}|{src}|{e}|{s}" not in cache]
    print("待算",len(jobs),flush=True)
    if jobs:
        with ProcessPoolExecutor(8) as ex:
            for j,x in ex.map(sim,jobs,chunksize=4): cache[f"{j[0]}|{j[1]}|{j[2]}|{j[3]}"]=(x or {}).get("d")
        json.dump(cache,open("pool_cache.json","w"))
    for src,title in (("roff","官方回放 分层抽样(每类≤80,开环)"),("rlive3","我方线上对局 抽样300(反事实)")):
        print(f"\n[{title}]")
        T=collections.defaultdict(lambda:collections.defaultdict(list))
        for s_,e,s,c in units:
            if s_!=src: continue
            for a in AG:
                d=cache.get(f"{a}|{src}|{e}|{s}")
                if d is not None: T[c][a].append(d); T["合计"][a].append(d)
        for c,t in sorted(T.items(),key=lambda kv:(kv[0]!="合计",-len(kv[1][AG[0]]))):
            print(f"   {c:10s} n={len(t[AG[0]]):4d} "+"  ".join(f"{a}: {sum(x>0 for x in t[a])/max(1,len(t[a])):4.0%}({sum(t[a])/max(1,len(t[a])):6.0f})" for a in AG))
