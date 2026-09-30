"""④ 未知高频键扩行安全验证:对某键的线上局,tape 重放 v54r3(表不含该键) vs v54r3x(表扩入该键)。
用法: python key_extend_tape.py 988.0 9989   —— 会自动生成 v54r3x 临时代理。"""
import sys, json, glob, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
KEY=(float(sys.argv[1]), int(sys.argv[2]))
ROW=sys.argv[3] if len(sys.argv)>3 else "mir"
rows=json.load(open(HERE/"rival_freq.json"))
eps={x["ep"]:x["dir"] for x in rows if tuple(x["rkey"])==KEY}
# 生成扩键代理:把 KEY 并入镜像行触发
base=(HERE/"agents/v54r3w48_main.py").read_text()
old=("        if state.get('rkey')==(1042.0, 9989) and shops in _V54R3_MIR:" if ROW=="mir" else "        if state.get('rkey')==(154.0, 9959) and shops in _V54R3_K52:")
assert base.count(old)==1
tabname="_V54R3_MIR" if ROW=="mir" else "_V54R3_K52"
basekey="(1042.0, 9989)" if ROW=="mir" else "(154.0, 9959)"
xt=base.replace(old, f"        if state.get('rkey') in ({basekey}, {KEY!r}) and shops in {tabname}:")
(HERE/"agents/w48x_main.py").write_text(xt)
def one(job):
    fn, ver = job
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    r=json.load(open(fn)); nm=r["info"]["TeamNames"]; s=r["steps"]
    seat=nm.index("datatuu"); o=1-seat
    op=fidelity.tape_agent([s[t+1][o].get("action") or {} for t in range(len(s)-1)])
    me=fidelity.make_agent(f"sub:{HERE}/agents/{ver}_main.py")
    k=engine.load_kagsim(); g=k.Game(seed=r["info"]["seed"])
    while not engine._val(g.done):
        obs=[g.observe(0),g.observe(1)]; a=[None,None]; a[seat]=me(obs[seat]); a[o]=op(obs[o]); g.step(a[0],a[1])
    return Path(fn).name, ver, float(g.reward(seat)-g.reward(o))
if __name__=="__main__":
    fns=[]
    for ep,d in eps.items():
        p=HERE/d/f"episode-{ep}-replay.json"
        if p.exists(): fns.append(str(p))
    print(f"键 {KEY} 局数 {len(fns)}", flush=True)
    jobs=[(f,v) for f in fns for v in ("v54r3w48","w48x")]
    with ProcessPoolExecutor(7) as ex: res=list(ex.map(one,jobs,chunksize=2))
    tab=collections.defaultdict(dict)
    for n,v,m in res: tab[n][v]=m
    a=sum(1 for v in tab.values() if v.get("v54r3w48",0)>0); b=sum(1 for v in tab.values() if v.get("w48x",0)>0)
    ch=[(n,round(v["w48x"]-v["v54r3w48"])) for n,v in tab.items() if abs(v.get("w48x",0)-v.get("v54r3w48",0))>1]
    print(f"{len(tab)} 局: 不扩键 {a} 胜 | 扩键 {b} 胜 | 触发变化局 {len(ch)}")
    for n,d in sorted(ch,key=lambda x:x[1])[:12]: print(" ",n,d)
