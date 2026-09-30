"""任意棋盘集的代表搜索:实际版本 vs 候选,胜负一致率。用法: python rep_any.py <棋盘json> <候选,...>"""
import sys, json
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
if __name__=="__main__":
    B=json.load(open(sys.argv[1])); cands=sys.argv[2].split(",")
    print("棋盘",len(B),"线上我方胜",sum(x["d"]>0 for x in B),flush=True)
    for c in cands:
        jobs=[(f"v54{x['ver']}",c,x["seed"],x["seat"],x["eid"],()) for x in B]
        with ProcessPoolExecutor(2) as ex: res=dict(ex.map(be.one,jobs))
        ok=sum(1 for x in B if res.get(x["eid"]) is not None and (res[x["eid"]]>0)==(x["d"]>0))
        print(f"  {c:12s} 一致 {ok}/{len(B)}",flush=True)
