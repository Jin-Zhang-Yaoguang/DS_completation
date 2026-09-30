"""各指纹类别的识别准确率:实际参赛版本 vs 候选代表,真实棋盘胜负与线上一致率。"""
import json, collections
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
REPS={"cha谱系(1042+t92)":["engineV3","me2965_28"],"新版人群(1042无t92,09-27后)":["me2965_28","guru28"],
      "老herdsafe(1042无t92,09-27前)":["herdsafe","engineV3","me2965_28"],"rescue7系(1039/1041/1043)":["rescue7","hybrid2965","me2965_28"],
      "metav4(1049)":["metav4","me2965_28"],"未识别键":["me2965_28","engineV3"]}
if __name__=="__main__":
    CL=json.load(open("fp_class_rows.json"))
    for c,reps in REPS.items():
        B=[x for x in CL if x["cls"]==c]
        best=None
        for rep in reps:
            jobs=[(f"v54{x['ver']}",rep,x["seed"],x["seat"],x["eid"],()) for x in B]
            with ProcessPoolExecutor(7) as ex: res=dict(ex.map(be.one,jobs,chunksize=2))
            ok=sum(1 for x in B if res.get(x["eid"]) is not None and (res[x["eid"]]>0)==(x["d"]>0))
            print(f"  {c:28s} 代表 {rep:10s} 一致 {ok}/{len(B)} ({ok/max(1,len(B)):.0%})",flush=True)
