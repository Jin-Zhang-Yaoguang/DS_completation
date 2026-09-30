"""FM 组合路线搜索(y68v 开局下):每组合 4 seed(座位交替)× 候选路线,对手反应式 V43;含 y68v 基线。"""
import sys, json, statistics, inspect
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
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
def build(rids):
    base = (S / "y68v_main.py").read_text()
    for rid in rids:
        p = S / f"fr_{rid}_main.py"
        p.write_text(base + TAIL.replace("{rid}", str(rid)))
    ns = {}; exec((S / f"fr_{rids[0]}_main.py").read_text(), ns)
    last = [k for k, v in ns.items() if callable(v) and not inspect.isclass(v) and not k.startswith("__")][-1]
    assert last == "_YZ_ENTRY", last
    assert rids[0] in ns["_IMPL"].chassis.routes
def one(job):
    combo, sd, seat, ver = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    me = fidelity.make_agent(f"sub:{S}/{ver}_main.py"); op = fidelity.make_agent(f"sub:{S}/kernels_0915/v43_agent.py")
    k = engine.load_kagsim(); g = k.Game(seed=sd); t = 0; real = None
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[1 - seat] = op(obs[1 - seat])
        g.step(acts[0], acts[1]); t += 1
        if t == 146: real = "|".join(((g.observe(0).get("town") or {}).get("unlocked_shops") or [])[:2])
    return combo, sd, seat, ver, real, g.reward(seat) - g.reward(1 - seat)
if __name__ == "__main__":
    pack = json.load(open(S / "v42_router_pack.json"))
    tab = pack["shop_routes"]
    ns38 = {}; exec((S / "kernels_0913" / "v38_main.py").read_text(), ns38)
    router = ns38["_router"]
    by = json.load(open(S / "combo_seeds_y68v.json"))
    fm = {c: v for c, v in by.items() if "FARMERS_MARKET" in c.split("|")}
    plan = {}
    for c, sds in fm.items():
        shops = c.split("|")
        cands = {0, 2, router({"town": {"unlocked_shops": shops}}, 144, {})}
        if c in tab: cands.add(int(tab[c]))
        if "YARN_STORE" in shops: cands.add(5); cands.add(1)
        plan[c] = (sorted(cands), sds[:4])
    rids = sorted({r for cs, _ in plan.values() for r in cs})
    build(rids)
    print("候选路线全集:", rids, flush=True)
    jobs = []
    for c, (cs, sds) in plan.items():
        for i, sd in enumerate(sds):
            jobs.append((c, sd, i % 2, "y68v"))
            for r in cs: jobs.append((c, sd, i % 2, f"fr_{r}"))
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=2))
    json.dump(res, open(S / "fm_route_search.json", "w"), ensure_ascii=False)
    print(f"{'组合':32s} {'y68v 基线':>14s}  各候选路线(胜/局 均margin)")
    summary = []
    for c, (cs, sds) in sorted(plan.items()):
        def stat(ver):
            v = [m for cc, sd, st, vv, real, m in res if cc == c and vv == ver]
            return sum(x > 0 for x in v), len(v), statistics.mean(v) if v else 0
        bw, bn, bm = stat("y68v")
        cells = []; best = ("y68v", bw, bm)
        for r in cs:
            w, n, mm = stat(f"fr_{r}")
            cells.append(f"r{r}:{w}/{n} {mm:+.0f}")
            if (w, mm) > (best[1], best[2]): best = (f"r{r}", w, mm)
        mism = sum(1 for cc, sd, st, vv, real, m in res if cc == c and vv == "y68v" and real != c)
        print(f"{c:32s} {bw}/{bn} {bm:+8.0f}   " + "  ".join(cells) + f"   → 最佳 {best[0]}{'  (组合漂移'+str(mism)+')' if mism else ''}")
        summary.append((c, bw, bn, best))
    print(f"\ny68v 基线 FM 局合计 {sum(s[1] for s in summary)}/{sum(s[2] for s in summary)};逐组合取最佳后 {sum(s[3][1] for s in summary)}/{sum(s[2] for s in summary)}")
