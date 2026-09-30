"""新池矩阵:候选尾部(graft 带)× newpool top-N 对手 × seed 双席位。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
TAPES = HERE.parent / "v16_online_fidelity" / "tapes"
_cache = {}
def tape_agent(path):
    if path not in _cache:
        _cache[path] = json.load(open(path))["actions"]
    actions = _cache[path]
    def agent(obs):
        t = int(obs.get("day",0))*24 + int(obs.get("hour",0))
        a = actions[t] if t < len(actions) else {}
        return {"farmer": list(a.get("farmer") or ["PASS"]),
                "hands": [list(h) for h in (a.get("hands") or [])],
                "market": [list(o) for o in (a.get("market") or [])]}
    return agent
def one(job):
    cand_path, cand, opp_path, opp, seed, seat = job
    import engine
    k = engine.load_kagsim(); g = k.Game(seed=seed)
    a=[None,None]
    if cand_path.startswith("sub:"):
        import sys as _s; _s.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
        import fidelity
        a[seat]=fidelity.make_agent(cand_path)
    else:
        a[seat]=tape_agent(cand_path)
    a[1-seat]=tape_agent(opp_path)
    fs=None; step=0
    while not engine._val(g.done):
        obs=[g.observe(0),g.observe(1)]
        if fs is None and step>=73:
            cur=(obs[0].get("town") or {}).get("unlocked_shops") or []
            if cur:
                s=cur[0]; fs=s if isinstance(s,str) else s.get("name")
        acts=[]
        for p in (0,1):
            try: acts.append(a[p](obs[p]))
            except Exception: acts.append({"farmer":["PASS"],"hands":[],"market":[]})
        g.step(acts[0],acts[1]); step+=1
    bank=[float(g.reward(0)),float(g.reward(1))]
    return {"cand":cand,"opp":opp,"seed":seed,"seat":seat,"my":bank[seat],"their":bank[1-seat],"first_shop":fs}
if __name__ == "__main__":
    out=Path(sys.argv[1])
    cands=[]  # (path, name)
    for spec in sys.argv[2].split(","):
        name, path = spec.split("=")
        cands.append((path, name))
    pool=sorted(Path("newpool").glob("op_*.json"), key=lambda p:-json.load(open(p))["bank"])[:int(sys.argv[3])]
    seeds=[int(x) for x in sys.argv[4].split(",")] if len(sys.argv)>4 else list(range(7000,7008))
    jobs=[(cp,cn,str(op),op.stem,sd,seat) for cp,cn in cands for op in pool for sd in seeds for seat in (0,1)]
    print(f"{len(jobs)} games ...", flush=True)
    done=0
    with out.open("w") as f, ProcessPoolExecutor(8) as ex:
        for r in ex.map(one, jobs, chunksize=8):
            f.write(json.dumps(r)+"\n"); done+=1
            if done%500==0: print(f"  {done}/{len(jobs)}", flush=True)
    print("done ->", out)
