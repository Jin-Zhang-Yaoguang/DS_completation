"""逐盘代理分配:每盘取与线上吻合最久的代理变体;测胜负一致率,并可评估候选版本。
用法: python assign_eval.py <diverge json> <棋盘json> <out assign json> [候选版本,...]"""
import sys, json, collections
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
if __name__=="__main__":
    dv,bf,out=sys.argv[1:4]; vers=sys.argv[4].split(",") if len(sys.argv)>4 else []
    best={}
    for e,c,t,info in json.load(open(dv)):
        if t is None: continue
        if e not in best or t>best[e][1]: best[e]=(c,t)
    json.dump({e:c for e,(c,t) in best.items()},open(out,"w"))
    B=[x for x in json.load(open(bf)) if x["eid"] in best]
    print("代理分配:",collections.Counter(c for c,t in best.values()))
    jobs=[(f"v54{x['ver']}",best[x["eid"]][0],x["seed"],x["seat"],x["eid"],()) for x in B]
    with ProcessPoolExecutor(7) as ex: res=dict(ex.map(be.one,jobs,chunksize=2))
    agree=sum(1 for x in B if res.get(x["eid"]) is not None and (res[x["eid"]]>0)==(x["d"]>0))
    print(f"实际版本 vs 逐盘代理:与线上一致 {agree}/{len(B)} ({agree/len(B):.0%});线上我方胜 {sum(x['d']>0 for x in B)}/{len(B)}")
    for v in vers:
        jobs=[(v if v.startswith("v54") or v.startswith("r30") else f"v54{v}",best[x["eid"]][0],x["seed"],x["seat"],x["eid"],()) for x in B]
        with ProcessPoolExecutor(7) as ex: r=dict(ex.map(be.one,jobs,chunksize=2))
        print(f"  {v} vs 逐盘代理: {sum(1 for d in r.values() if d is not None and d>0)}/{len(B)}")
        json.dump(r,open(f"assign_{v}_{out}","w"))
