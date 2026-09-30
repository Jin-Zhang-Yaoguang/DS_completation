"""照抄带上限测试:动物优先开局顶队(榜分≥2600)的整局实录,在其原种子原席位上开环重放,
对 本地代表 / r38c;与 r38c 在同种子同席位对同代表对照。"""
import sys, os, json, glob, csv, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from pub_splice import OPP
def one(job):
    who,opp,eid,seat=job   # who: "CLONE" 或 agent 名;seat=我方(克隆或 r38c)所在席位
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    try:
        r=json.load(open(HERE/f"roff/{eid}.json")); o=1-seat
        if who=="CLONE": me=fidelity.tape_agent([r["acts"][t+1][seat] for t in range(len(r["acts"])-1)])
        else: me=fidelity.make_agent(f"sub:{HERE}/agents/{who}_main.py")
        sys.path.insert(0,str(Path(OPP[opp]).parent)); op=fidelity.make_agent(f"sub:{OPP[opp]}")
        k=engine.load_kagsim(); g=k.Game(seed=r["seed"])
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
        return job,float(g.reward(seat)-g.reward(o))
    except Exception as ex: return job,None
if __name__=="__main__":
    LB={}
    for f in glob.glob(sys.argv[1]+"/*.csv"):
        for r in csv.DictReader(open(f,encoding="utf-8-sig")): LB[r["TeamName"]]=float(r["Score"])
    rows=[r for r in json.load(open("official_rows.json")) if r["cls"]=="Majkel簇" and LB.get(r["team"],0)>=2600]
    print("动物优先顶队(≥2600)实录局:",len(rows),"队伍",len({r['team'] for r in rows}),flush=True)
    OPPS=["me2965_28","guru28","engineV3","rescue7","v54r38c"]
    jobs=[(w,o,r["eid"],1-r["seat"]) for r in rows for o in OPPS for w in ("CLONE","v54r38c") if not (w=="v54r38c" and o=="v54r38c")]
    with ProcessPoolExecutor(8) as ex: R=dict(ex.map(one,jobs,chunksize=2))
    for o in OPPS:
        for w in ("CLONE","v54r38c"):
            if w=="v54r38c" and o=="v54r38c": continue
            d=[R.get((w,o,r["eid"],1-r["seat"])) for r in rows]; d=[x for x in d if x is not None]
            print(f"   {'照抄带' if w=='CLONE' else 'r38c  '} vs {o:10s} 胜 {sum(x>0 for x in d):3d}/{len(d)} ({sum(x>0 for x in d)/max(1,len(d)):.0%}) 均差 {sum(d)/max(1,len(d)):7.0f}",flush=True)
    # 原局中该顶队的实际战绩(对真实对手)作参照
    act=[r for r in rows]; 
    print(f"   参照:这些局里顶队对真实对手的实际胜率 {sum(1 for r in rows if r['opp_won'])}/{len(rows)}")
