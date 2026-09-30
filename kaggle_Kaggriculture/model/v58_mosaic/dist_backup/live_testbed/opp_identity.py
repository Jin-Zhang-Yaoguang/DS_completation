"""线上 B15/S60 对手是否=原版 V41/V42:线上 seed、线上席位,本地 V41/V42 反应式对手 vs y68j,
比对对手模拟动作与线上对手动作,并对比 margin。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
def norm(a):
    a = a or {}
    return json.dumps({"f": a.get("farmer") or ["PASS"], "h": a.get("hands") or [], "m": a.get("market") or []}, sort_keys=True)
def one(job):
    eid, ver = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    rep = json.load(open(S / f"live_replays3/episode-{eid}-replay.json"))
    names = rep["info"]["TeamNames"]; seat = names.index("datatuu"); o = 1 - seat
    steps = rep["steps"]; seed = rep["info"]["seed"]
    live_op = [steps[t + 1][o].get("action") or {} for t in range(len(steps) - 1)]
    me = fidelity.make_agent(f"sub:{S}/y68j_main.py")
    op = fidelity.make_agent(f"sub:{S}/kernels_0914/{ver}_agent.py")
    k = engine.load_kagsim(); g = k.Game(seed=seed)
    t = 0; first = None; mis = 0
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        a_me = me(obs[seat]); a_op = op(obs[o])
        if t < len(live_op) and norm(a_op) != norm(live_op[t]):
            mis += 1
            if first is None: first = t
        acts = [None, None]; acts[seat] = a_me; acts[o] = a_op
        g.step(acts[0], acts[1]); t += 1
    shops = tuple(((steps[150][0]["observation"].get("town") or {}).get("unlocked_shops") or [])[:2])
    return eid, ver, str(names[o]), "Y" if "YARN_STORE" in shops else "N", first, mis, t, g.reward(seat) - g.reward(o), rep["rewards"][seat] - rep["rewards"][o]
if __name__ == "__main__":
    ids = json.load(open(S / "ep_ids7.json"))
    pick = []
    for eid in ids["y68j"]:
        p = S / f"live_replays3/episode-{eid}-replay.json"
        if not p.exists(): continue
        rep = json.load(open(p)); nm = rep["info"]["TeamNames"]
        if nm.count("datatuu") != 1: continue
        o = 1 - nm.index("datatuu")
        m1 = (rep["steps"][1][o].get("action") or {}).get("market") or []
        if (sum(int(x[2]) for x in m1 if x and x[0] == "BUY_PRODUCT" and len(x) > 2),
            sum(int(x[2]) for x in m1 if x and x[0] == "SELL" and len(x) > 2)) == (15, 60):
            pick.append(eid)
    jobs = [(e, v) for e in pick for v in ("v41", "v42")]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=2))
    best = {}
    for r in res:
        if r[0] not in best or r[5] < best[r[0]][5]:
            best[r[0]] = r
    exact = [r for r in best.values() if r[5] == 0]
    print(f"B15/S60 对手 {len(best)} 局:与原版 V41/V42 动作完全一致 {len(exact)} 局")
    print(f"{'ep':>10s} {'版本':4s} {'对手':16s} YARN {'首不一致':>8s} {'不一致步':>8s} {'本地margin':>10s} {'线上margin':>10s}")
    for r in sorted(best.values(), key=lambda r: (r[5] > 0, r[8])):
        print(f"{r[0]:>10d} {r[1]:4s} {r[2][:16]:16s}  {r[3]}   {str(r[4]):>8s} {r[5]:>5d}/{r[6]} {r[7]:+10.0f} {r[8]:+10.0f}")
    lw = [r for r in best.values() if r[5] == 0]
    if lw:
        print(f"\n完全一致局中:线上胜 {sum(r[8]>0 for r in lw)}/{len(lw)},本地复算胜 {sum(r[7]>0 for r in lw)}/{len(lw)}")
    json.dump([list(r) for r in best.values()], open(S / "opp_identity.json", "w"), ensure_ascii=False)
