"""对手行为特征(官方回放 + 我方线上,最近 5 天):按时间点累计的小麦买卖、买畜、买地、种子、卖出、雇工;开局键与 t92 信号。输出 style_feats.json。"""
import json, glob, collections, os
from concurrent.futures import ThreadPoolExecutor
CK=(24,48,96,144,216,288,432,720)
def feats(acts,o,money):
    F={}; c=collections.Counter(); first_animal=None; first_land=None
    ck=list(CK)
    for t in range(1,len(acts)):
        for x in ((acts[t][o] or {}).get("market") or []):
            if not x: continue
            try: n=int(x[2]) if len(x)>2 else 1
            except Exception: n=1
            k=x[0]; it=str(x[1]) if len(x)>1 else ""
            if k=="SELL": c["sell_"+it]+=n
            elif k=="BUY_PRODUCT": c["buy_"+it]+=n
            elif k=="BUY_ANIMAL": c["ani_"+it]+=n; first_animal=first_animal or t
            elif k=="BUY_SEED": c["seed_"+it]+=n
            elif k=="BUY_LAND": c["land"]+=1; first_land=first_land or t
            elif k=="HIRE": c["hire"]+=1
        if ck and t>=ck[0]-1:
            F[ck.pop(0)]=dict(c)
    F["first_animal"]=first_animal; F["first_land"]=first_land
    return F
def one(item):
    src,f,o,meta=item
    try:
        r=json.load(open(f)); M=r["money"]
        lin="cha" if (M[92] and M[91] and M[92][o]-M[91][o]>50) else "main"
        return dict(src=src,eid=r["eid"],opp_seat=o,feats=feats(r["acts"],o,M),lin=lin,shops=(r.get("shops") or [])[:2],**meta)
    except Exception as ex: return None
if __name__=="__main__":
    items=[]
    for r in json.load(open("official_rows.json")):
        items.append(("官方",f"roff/{r['eid']}.json",1-r["seat"],dict(team=r["team"],key=r["key"],cls=r["cls"],d=r["d"])))
    for e,v in json.load(open("online_games.json")).items():
        if v.get("key"): items.append(("线上",f"rlive3/{e}.json",1-v["seat"],dict(team=v["opp_team"],key=v["key"],cls=None,d=v["d"],ver=v["ver"],end=v["end"])))
    with ThreadPoolExecutor(8) as ex: out=[x for x in ex.map(one,items) if x]
    json.dump(out,open("style_feats.json","w"),ensure_ascii=False)
    print("对手棋盘",len(out),collections.Counter(x["src"] for x in out))
