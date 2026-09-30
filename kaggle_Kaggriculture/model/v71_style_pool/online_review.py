"""线上复盘:r38f/r38g(对照 r38c 同局数段):分数轨迹、分段胜率、人群×命中胜率、败局明细与同棋盘反事实。"""
import json, glob, csv, collections, sys
from concurrent.futures import ProcessPoolExecutor
from official_eval import sim
from review_fp import cls
if __name__=="__main__":
    LB={}
    for f in glob.glob(sys.argv[1]+"/*.csv"):
        for r in csv.DictReader(open(f,encoding="utf-8-sig")): LB[r["TeamName"]]=float(r["Score"])
    sc=sorted(LB.values(),reverse=True); N=len(sc); me=LB.get("datatuu",0)
    print(f"[排行榜] {N} 队 我们 {me} 第 {1+sum(1 for x in sc if x>me)} 名 | 金(前30) {sc[29]:.0f} 银(前5%) {sc[int(N*.05)-1]:.0f} 铜(前10%) {sc[int(N*.1)-1]:.0f}")
    G=json.load(open("online_games.json"))
    ns={}; exec(open("agents/v54r38g_main.py").read(),ns); K42=1042.0
    def hit(c,sh):
        t=lambda n: sh in ns[n]
        if c=="新版人群": return t("_R36_MILK") or t("_R32_NEWGEN") or t("_R33_NEWGEN_LATE") or sh in ns["_V54R3_HS"]
        if c=="cha谱系": return t("_R38_CHA") or sh in ns["_R23_CHA"][(K42,9989)]
        if c=="rescue7系": return t("_R28_MILK39") or t("_R21_MIR") or t("_R20_SPLICE") or sh in ns["_V54R3_MIR"]
        if c=="K52": return t("_R21_K52") or t("_V54R3_K52")
        if c=="metav4": return t("_R22_MV4")
        return False
    band=lambda s:"<1500" if s<1500 else "1500-2000" if s<2000 else "2000-2200" if s<2200 else "2200-2400" if s<2400 else "≥2400"
    for ver in ("r38g","r38f","r38c"):
        L=sorted([(e,v) for e,v in G.items() if v["ver"]==ver],key=lambda ev:ev[1]["end"])
        if ver=="r38c": L=L[:70]
        W=sum(v["d"]>0 for _,v in L)
        B=collections.defaultdict(lambda:[0,0])
        for _,v in L: b=band(LB.get(v["opp_team"],0)); B[b][0]+=1; B[b][1]+=v["d"]>0
        print(f"\n=== {ver}{'(前70局对照)' if ver=='r38c' else ''}: {len(L)} 局 胜 {W} ({W/max(1,len(L)):.0%})  "+"  ".join(f"{b} {B[b][1]}/{B[b][0]}" for b in ("<1500","1500-2000","2000-2200","2200-2400","≥2400") if B[b][0]))
        C=collections.defaultdict(collections.Counter)
        for e,v in L:
            if not v.get("key"): continue
            c=cls(float(round(v["key"][0])),v["lin"]); h=hit(c,tuple(v["shops"])); w=v["d"]>0
            a=C[c]; a["n"]+=1; a["w"]+=w; a["h"]+=h; a["hw"]+=h and w
        for c,a in sorted(C.items(),key=lambda kv:-kv[1]["n"]):
            print(f"   {c:10s} {a['n']:3d} 局 胜 {a['w']}/{a['n']} | 命中 {a['h']} 命中胜 {a['hw']}/{a['h']} 未命中胜 {a['w']-a['hw']}/{a['n']-a['h']}")
    # r38f/g 败局 + 同棋盘反事实
    for ver in ("r38g","r38f"):
        L=sorted([(e,v) for e,v in G.items() if v["ver"]==ver and v["d"]<0],key=lambda ev:ev[1]["end"])
        alt="v54r38f" if ver=="r38g" else "v54r38g"
        jobs=[(a,"rlive3",e,v["seat"],()) for e,v in L for a in (alt,"v54r38e")]
        with ProcessPoolExecutor(8) as ex: X={(j[0],j[2]):(x or {}).get("d") for j,x in ex.map(sim,jobs,chunksize=1)}
        print(f"\n[{ver} 败局 {len(L)}] 时间 对手(榜分) 人群 命中 线上差 | 换 {alt[3:]} / r38e")
        for e,v in L:
            c=cls(float(round(v["key"][0])),v["lin"]) if v.get("key") else "?"
            print(f"   {v['end'][11:16]} {v['opp_team'][:16]:16s}({LB.get(v['opp_team'],0):5.0f}) {c:8s} {'Y' if hit(c,tuple(v['shops'])) else 'N'} {v['d']:7.0f} | {X.get((alt,e)) or 0:+7.0f} / {X.get(('v54r38e',e)) or 0:+7.0f}")
