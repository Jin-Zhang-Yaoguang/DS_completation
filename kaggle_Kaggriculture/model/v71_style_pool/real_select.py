"""真实棋盘选带(cha 谱系):A 半选、B 半验。对手 engineV3,保留线上席位。"""
import sys, os, json, hashlib, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE=Path(__file__).resolve().parent
M=Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
from pub_splice import OPP
def one(job):
    tag,seed,seat,eid,cut,rid=job
    for k in list(os.environ):
        if k.startswith("KAG_CUT"): os.environ.pop(k,None)
    if cut: os.environ[f"KAG_CUT{cut}"]=str(rid)
    sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness")); sys.path.insert(0,str(Path(OPP["engineV3"]).parent))
    import fidelity, engine
    try:
        me=fidelity.make_agent(f"sub:{HERE}/agents/{os.environ.get('RS_PROBE','v54r29cut')}_main.py"); op=fidelity.make_agent(f"sub:{OPP['engineV3']}")
        k=engine.load_kagsim(); g=k.Game(seed=seed); o=1-seat
        while not engine._val(g.done):
            obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
        return tag,eid,cut,rid,float(g.reward(seat)-g.reward(o))
    except Exception: return tag,eid,cut,rid,None
def half(eid): return "A" if int(hashlib.md5(str(eid).encode()).hexdigest(),16)%2==0 else "B"
if __name__=="__main__":
    comp={}
    import glob
    for f in glob.glob(str(HERE/"rlive3/*.json")):
        r=json.load(open(f)); comp[str(r["eid"])]=r
    rows=[x for x in json.load(open(HERE/os.environ.get("RS_BOARDS","scan_live_rows.json"))) if (x["key"],x["lin"])==("1042.0","cha") and x.get("seed") is not None]
    for x in rows: x["combo"]="|".join((comp[x["eid"]].get("shops") or [])[:2]); x["half"]=half(x["eid"])
    base=json.load(open(HERE/os.environ["RS_BASE"])) if os.environ.get("RS_BASE") else {e:d for v,e,d in json.load(open(HERE/"board_eval_r29.json"))}
    # 候选臂:本地选带 top5 + 旧表值 + 当前值
    res=json.load(open(HERE/"lin_select_cha1042_r26.json")); agg=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.0]))
    for c,o,s,cut,rid,m in res:
        if m is None or cut is None: continue
        a=agg[c][(cut,rid)]; a[0]+=m>0; a[1]+=m
    old=json.load(open(HERE/"cha1042_stage2.json")); cur=json.load(open(HERE/"cha1042_r27.json")); cur.update({"BRUNCH_SPOT|PET_CAFE":[432,120],"ICE_CREAM_SHOP|SMOOTHIE_SHOP":[432,124],"ICE_CREAM_SHOP|PIZZA_SHOP":[144,107]})
    arms={}
    for c in {x["combo"] for x in rows}:
        top=[k for k,_ in sorted(agg[c].items(),key=lambda kv:(-kv[1][0],-kv[1][1]))[:5]]
        cand=set(top)|({tuple(old[c])} if c in old else set())
        cand.discard(tuple(cur[c]) if c in cur else None)
        arms[c]=sorted(cand)
    stage=sys.argv[1]
    if stage=="A":
        jobs=[("A",x["seed"],x["seat"],x["eid"],cut,rid) for x in rows if x["half"]=="A" for cut,rid in arms[x["combo"]]]
        print("A 半棋盘",sum(x["half"]=="A" for x in rows),"任务",len(jobs),flush=True)
        with ProcessPoolExecutor(7) as ex: out=list(ex.map(one,jobs,chunksize=2))
        json.dump(out,open(HERE/f"real_select_A{os.environ.get('RS_TAG','')}.json","w"))
        S=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0.0,0]))
        B0=collections.defaultdict(lambda:[0,0.0,0])
        for x in rows:
            if x["half"]=="A" and base.get(x["eid"]) is not None: b=B0[x["combo"]]; b[0]+=base[x["eid"]]>0; b[1]+=base[x["eid"]]; b[2]+=1
        for tag,e,cut,rid,d in out:
            if d is None: continue
            c=next(x["combo"] for x in rows if x["eid"]==e); a=S[c][(cut,rid)]; a[0]+=d>0; a[1]+=d; a[2]+=1
        pick={}
        for c in S:
            b=B0[c]; k,v=max(S[c].items(),key=lambda kv:(kv[1][0],kv[1][1]))
            if v[0]>b[0]:
                pick[c]=list(k); print(f"  [改] {c:32s} 当前 {b[0]}/{b[2]} → {k} {v[0]}/{v[2]}")
        json.dump(pick,open(HERE/f"real_pick_cha{os.environ.get('RS_TAG','')}.json","w")); print("A 半改格",len(pick))
    else:
        pick=json.load(open(HERE/f"real_pick_cha{os.environ.get('RS_TAG','')}.json"))
        jobs=[("B",x["seed"],x["seat"],x["eid"],*pick[x["combo"]]) for x in rows if x["half"]=="B" and x["combo"] in pick]
        print("B 半受影响棋盘",len(jobs),flush=True)
        with ProcessPoolExecutor(7) as ex: out=list(ex.map(one,jobs,chunksize=1))
        json.dump(out,open(HERE/f"real_select_B{os.environ.get('RS_TAG','')}.json","w"))
        w0=sum(base[e]>0 for _,e,_,_,_ in out); w1=sum((d or 0)>0 for *_,d in out)
        up=sum(1 for _,e,_,_,d in out if d is not None and base[e]<=0<d); dn=sum(1 for _,e,_,_,d in out if d is not None and d<=0<base[e])
        print(f"B 半:当前 {w0}/{len(out)} → 新值 {w1}/{len(out)}  翻盘 {up} 被翻 {dn}")
