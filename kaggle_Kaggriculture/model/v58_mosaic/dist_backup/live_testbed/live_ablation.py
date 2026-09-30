"""线上 seed 测试床(36 局,原版反应式 V41/V42 对手,线上席位)上的 y68j 变体消融。"""
import sys, json, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
def build():
    base = (S / "y68j_main.py").read_text()
    out = {}
    specs = {
        "nofert": ("if value<1.1*cost+50", "if value<99*cost+50"),
        "nofr": ('_IMPL.chassis.cfg["front_run"] = True', '_IMPL.chassis.cfg["front_run"] = False'),
        "norg": ('_IMPL.chassis.cfg["room_guard"] = True', '_IMPL.chassis.cfg["room_guard"] = False'),
    }
    for name, (old, new) in specs.items():
        if old in base:
            (S / f"abl_{name}_main.py").write_text(base.replace(old, new)); out[name] = f"abl_{name}_main.py"
        else:
            print(f"[跳过] {name}: 未找到锚点 {old!r}", flush=True)
    out["y68r2"] = "y68r2_main.py"; out["y68k"] = "y68k_main.py"
    return out
def one(job):
    eid, ver, vname, vfile = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    rep = json.load(open(S / f"live_replays3/episode-{eid}-replay.json"))
    names = rep["info"]["TeamNames"]; seat = names.index("datatuu"); o = 1 - seat
    me = fidelity.make_agent(f"sub:{S}/{vfile}")
    op = fidelity.make_agent(f"sub:{S}/kernels_0914/{ver}_agent.py")
    k = engine.load_kagsim(); g = k.Game(seed=rep["info"]["seed"])
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[o] = op(obs[o])
        g.step(acts[0], acts[1])
    return eid, vname, g.reward(seat) - g.reward(o)
if __name__ == "__main__":
    variants = build()
    ident = json.load(open(S / "opp_identity.json"))
    base = {r[0]: r[7] for r in ident}; vers = {r[0]: r[1] for r in ident}; opps = {r[0]: r[2] for r in ident}; yarn = {r[0]: r[3] for r in ident}
    jobs = [(e, vers[e], vn, vf) for e in base for vn, vf in variants.items()]
    res = {}
    with ProcessPoolExecutor(8) as ex:
        for eid, vn, m in ex.map(one, jobs, chunksize=3):
            res.setdefault(vn, {})[eid] = m
    names = list(variants)
    print(f"{'对手':14s} Y  {'y68j':>7s} " + " ".join(f"{n:>7s}" for n in names))
    for e in sorted(base, key=lambda e: base[e]):
        print(f"{opps[e][:14]:14s} {yarn[e]}  {base[e]:+7.0f} " + " ".join(f"{res[n][e]:+7.0f}" for n in names))
    print("\n汇总(胜/36, 总margin, 基线输局上的变化):")
    losers = [e for e in base if base[e] <= 0]
    print(f"  y68j   {sum(v>0 for v in base.values()):2d}/36  总{sum(base.values()):+8.0f}")
    for n in names:
        v = res[n]
        print(f"  {n:6s} {sum(x>0 for x in v.values()):2d}/36  总{sum(v.values()):+8.0f}  输局{len(losers)}上 胜{sum(v[e]>0 for e in losers)} 和基线差{sum(v[e]-base[e] for e in losers):+7.0f}  赢局上差{sum(v[e]-base[e] for e in base if base[e]>0):+7.0f}")
