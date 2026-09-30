import json, os
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
if __name__=="__main__":
    B=[x for x in json.load(open("axis_rows.json")) if x["cls"]=="cha谱系"]
    print("cha 棋盘",len(B),"其中 09-28T12 后",sum(x["end"]>="2026-09-28T12" for x in B))
    for rep in ("engineV3","chahyb"):
        jobs=[(f"v54{x['ver']}",rep,x["seed"],x["seat"],x["eid"],()) for x in B]
        with ProcessPoolExecutor(8) as ex: res=dict(ex.map(be.one,jobs,chunksize=1))
        for nm,S in (("全部",B),("近期",[x for x in B if x["end"]>="2026-09-28T12"])):
            ok=sum(1 for x in S if res.get(x["eid"]) is not None and (res[x["eid"]]>0)==(x["d"]>0))
            lw=sum(1 for x in S if x["d"]<0 and res.get(x["eid"]) is not None and res[x["eid"]]<0)
            print(f"  {rep:9s} {nm}: 一致 {ok}/{len(S)} ({ok/max(1,len(S)):.0%}) 败局复现 {lw}/{sum(x['d']<0 for x in S)}",flush=True)
