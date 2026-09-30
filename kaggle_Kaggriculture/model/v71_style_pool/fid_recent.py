"""方向2:近期真实棋盘上各人群代表的保真(模拟胜负与线上一致率)。"""
import json, os
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
REPS={"新版人群":["me2965_28","guru28","harvest29","guru29"],"cha谱系":["engineV3","me2965_28"],
      "rescue7系":["rescue7","me2965_28","harvest29"],"未识别键":["me2965_28","harvest29","multiroute29"]}
if __name__=="__main__":
    CL=[x for x in json.load(open("axis_rows.json")) if x["end"]>=os.environ.get("SINCE2","2026-09-28T12")]
    W=int(os.environ.get("KAG_WORKERS","8"))
    for c,reps in REPS.items():
        B=[x for x in CL if x["cls"]==c][:40]
        if not B: continue
        for rep in reps:
            jobs=[(f"v54{x['ver']}",rep,x["seed"],x["seat"],x["eid"],()) for x in B]
            with ProcessPoolExecutor(W) as ex: res=dict(ex.map(be.one,jobs,chunksize=1))
            ok=sum(1 for x in B if res.get(x["eid"]) is not None and (res[x["eid"]]>0)==(x["d"]>0))
            lw=sum(1 for x in B if x["d"]<0 and res.get(x["eid"]) is not None and res[x["eid"]]<0)
            print(f"{c:10s} 代表 {rep:12s} 一致 {ok}/{len(B)} ({ok/len(B):.0%})  线上败局复现 {lw}/{sum(x['d']<0 for x in B)}",flush=True)
