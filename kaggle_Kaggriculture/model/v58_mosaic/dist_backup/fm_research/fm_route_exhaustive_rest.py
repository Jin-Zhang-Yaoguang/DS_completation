"""弱 FM 组合全路线穷举:41 条路线 × 每组合最多 10 seed(座位交替),对手反应式 V43。"""
import sys, json, statistics, inspect
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
_ALL = json.load(open(Path(__file__).resolve().parent / "combo_seeds_y68v.json"))
_W6 = {"FARMERS_MARKET|FARMERS_MARKET", "FARMERS_MARKET|YARN_STORE", "BRUNCH_SPOT|FARMERS_MARKET", "BAKERY|FARMERS_MARKET", "PET_CAFE|FARMERS_MARKET", "YARN_STORE|FARMERS_MARKET"}
WEAK = sorted(c for c in _ALL if "FARMERS_MARKET" in c.split("|") and c not in _W6)
TAIL = '''

# ==== 路线搜索专用:强制走 route {rid},t648 起切 route2 ====
def _yz_force_router(observation, step, state):
    if step >= 144 and not state.get("day6"):
        state["route"] = {rid}
        state["day6"] = True
    if step >= 648 and not state.get("day27"):
        state["route"] = 2
        state["day27"] = True
    return state.get("route", 0)

_IMPL.chassis.router = _yz_force_router
_YZ_ENTRY = _Y68U_ENTRY
'''
def one(job):
    combo, sd, seat, ver = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{S}/{ver}_main.py"); op = fidelity.make_agent(f"sub:{S}/kernels_0915/v43_agent.py")
    k = engine.load_kagsim(); g = k.Game(seed=sd)
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[1 - seat] = op(obs[1 - seat])
        g.step(acts[0], acts[1])
    return combo, sd, seat, ver, g.reward(seat) - g.reward(1 - seat)
if __name__ == "__main__":
    base = (S / "y68v_main.py").read_text()
    ns = {}; exec(base, ns)
    rids = sorted(ns["_IMPL"].chassis.routes)
    for rid in rids:
        p = S / f"fr_{rid}_main.py"
        if not p.exists(): p.write_text(base + TAIL.replace("{rid}", str(rid)))
    chk = {}; exec((S / f"fr_{rids[-1]}_main.py").read_text(), chk)
    assert [k for k, v in chk.items() if callable(v) and not inspect.isclass(v) and not k.startswith("__")][-1] == "_YZ_ENTRY"
    by = json.load(open(S / "combo_seeds_y68v.json"))
    jobs = []
    for c in WEAK:
        for i, sd in enumerate(by[c][:10]):
            jobs.append((c, sd, i % 2, "y68v"))
            for rid in rids: jobs.append((c, sd, i % 2, f"fr_{rid}"))
    print(f"路线 {len(rids)} 条,任务 {len(jobs)} 局", flush=True)
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=8))
    json.dump(res, open(S / "fm_route_exhaustive_rest.json", "w"), ensure_ascii=False)
    for c in WEAK:
        def stat(ver):
            v = [m for cc, sd, st, vv, m in res if cc == c and vv == ver]
            return sum(x > 0 for x in v), len(v), statistics.mean(v), min(v)
        bw, bn, bm, bmin = stat("y68v")
        ranked = sorted(((stat(f"fr_{r}"), r) for r in rids), key=lambda x: (x[0][0], x[0][2]), reverse=True)
        print(f"\n{c}(y68v 基线 {bw}/{bn} 均{bm:+.0f} 最差{bmin:+.0f})")
        for (w, n, mm, mn), r in ranked[:6]:
            print(f"   route{r:<4d} {w}/{n} 均{mm:+7.0f} 最差{mn:+7.0f}")
