"""r38g 败局明细:对手/人群/命中/商店;现金差时间线;各产品卖量与均价;买畜;反事实(其他版本开环)。"""
import json, glob, csv, collections, sys
from concurrent.futures import ProcessPoolExecutor
from official_eval import sim
from review_fp import cls
PR=("WHEAT","CARROT","TOMATO","STRAWBERRY","MELON","EGG","MILK","WOOL","FERTILIZER")
if __name__=="__main__":
    LB={}
    for f in glob.glob(sys.argv[1]+"/*.csv"):
        for r in csv.DictReader(open(f,encoding="utf-8-sig")): LB[r["TeamName"]]=float(r["Score"])
    G=json.load(open("online_games.json"))
    L=sorted([(e,v) for e,v in G.items() if v["ver"]=="r38g" and v["d"]<0],key=lambda ev:ev[1]["end"])
    ns={}; exec(open("agents/v54r38g_main.py").read(),ns); K42=1042.0
    def hit(c,sh):
        t=lambda n: sh in ns[n]
        if c=="新版人群": return t("_R36_MILK") or t("_R32_NEWGEN") or t("_R33_NEWGEN_LATE")
        if c=="cha谱系": return t("_R38_CHA") or sh in ns["_R23_CHA"][(K42,9989)]
        if c=="rescue7系": return t("_R28_MILK39") or t("_R21_MIR") or t("_R20_SPLICE")
        return False
    VV=["v54r38f","v54r38e","v54r34"]
    jobs=[(a,"rlive3",e,v["seat"],()) for e,v in L for a in VV]
    with ProcessPoolExecutor(8) as ex: X={(j[0],j[2]):(x or {}).get("d") for j,x in ex.map(sim,jobs,chunksize=1)}
    tot=sum(1 for v in G.values() if v["ver"]=="r38g"); print(f"r38g 线上 {tot} 局,败 {len(L)} 局\n")
    for e,v in L:
        r=json.load(open(f"rlive3/{e}.json")); p=v["seat"]; o=1-p; M=r["money"]
        c=cls(float(round(v["key"][0])),v["lin"]); sh=tuple(v["shops"])
        print(f"■ {v['end'][5:16]} 对手 {v['opp_team'][:20]}(榜 {LB.get(v['opp_team'],0):.0f}) 键 {round(v['key'][0])}/{v['key'][1]} 谱系信号 {v['lin']} → {c} | 商店 {'|'.join(sh)} | 针对格命中 {'是' if hit(c,sh) else '否'} | 线上差 {v['d']:.0f}")
        print("   现金差(我-对):"+" ".join(f"t{t}:{(M[t][p]-M[t][o]) if M[t] else 0:+.0f}" for t in (144,288,432,504,576,648,700)))
        q=[collections.Counter(),collections.Counter()]; pr=[collections.Counter(),collections.Counter()]; an=[collections.Counter(),collections.Counter()]
        for t in range(1,len(r["acts"])):
            for i,side in ((0,p),(1,o)):
                for x in ((r["acts"][t][side] or {}).get("market") or []):
                    if not x: continue
                    try: n=int(x[2]) if len(x)>2 else 1
                    except Exception: n=1
                    if x[0]=="SELL": q[i][x[1]]+=n
                    elif x[0]=="BUY_ANIMAL": an[i][x[1]]+=n
                    elif x[0]=="BUY_LAND": an[i]["LAND"]+=1
        print("   卖出件数(我/对): "+"  ".join(f"{x[:4]} {q[0][x]}/{q[1][x]}" for x in PR if q[0][x] or q[1][x]))
        print(f"   买畜/地(我/对): 羊 {an[0]['SHEEP']}/{an[1]['SHEEP']} 牛 {an[0]['COW']}/{an[1]['COW']} 鹅 {an[0]['GOOSE']}/{an[1]['GOOSE']} 地 {an[0]['LAND']}/{an[1]['LAND']}")
        print("   反事实(同种子同席位,对手实录):"+"  ".join(f"{a[3:]} {X.get((a,e)) or 0:+.0f}" for a in VV))
        print()
