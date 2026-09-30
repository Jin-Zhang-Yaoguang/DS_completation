"""线上 seed 精确复算:我方 y68j(sub) vs 对手线上动作带(tape),逐步比对我方模拟动作与线上动作。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
TARGETS = ["Arda Ceylan", "HayatoFujihara", "bpbpbpbpb", "tech-Mira"]
def norm(a):
    a = a or {}
    return json.dumps({"f": a.get("farmer") or ["PASS"], "h": a.get("hands") or [], "m": a.get("market") or []}, sort_keys=True)
def one(eid):
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    rep = json.load(open(S / f"live_replays3/episode-{eid}-replay.json"))
    names = rep["info"]["TeamNames"]; seat = names.index("datatuu"); o = 1 - seat
    steps = rep["steps"]; seed = rep["info"]["seed"]
    opp_tape = [steps[t + 1][o].get("action") or {} for t in range(len(steps) - 1)]
    live_me = [steps[t + 1][seat].get("action") or {} for t in range(len(steps) - 1)]
    me = fidelity.make_agent(f"sub:{S}/y68j_main.py"); op = fidelity.tape_agent(opp_tape)
    k = engine.load_kagsim(); g = k.Game(seed=seed)
    first_mis = None; mis = 0; t = 0; mis_detail = None
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        a_me = me(obs[seat]); a_op = op(obs[o])
        if t < len(live_me) and norm(a_me) != norm(live_me[t]):
            mis += 1
            if first_mis is None:
                first_mis = t
                mis_detail = (norm(a_me)[:260], norm(live_me[t])[:260])
        acts = [None, None]; acts[seat] = a_me; acts[o] = a_op
        g.step(acts[0], acts[1]); t += 1
    sim = (g.reward(seat), g.reward(o)); live = (rep["rewards"][seat], rep["rewards"][o])
    return eid, names[o], seed, first_mis, mis, t, sim, live, mis_detail
if __name__ == "__main__":
    ids = json.load(open(S / "ep_ids7.json"))
    pick = []
    for eid in ids["y68j"]:
        p = S / f"live_replays3/episode-{eid}-replay.json"
        if not p.exists(): continue
        nm = json.load(open(p))["info"]["TeamNames"]
        if any(x in nm for x in TARGETS) and nm.count("datatuu") == 1:
            pick.append(eid)
    with ProcessPoolExecutor(4) as ex:
        for eid, opp, seed, fm, mis, n, sim, live, det in ex.map(one, pick):
            print(f"ep{eid} vs {opp} seed={seed}")
            print(f"   我方动作逐步一致: 不一致 {mis}/{n} 步, 首次不一致 t{fm}")
            print(f"   bank 模拟 我{sim[0]:.0f}/彼{sim[1]:.0f} (margin {sim[0]-sim[1]:+.0f}) | 线上 我{live[0]:.0f}/彼{live[1]:.0f} (margin {live[0]-live[1]:+.0f})")
            if det:
                print(f"   首分叉 模拟: {det[0]}")
                print(f"   首分叉 线上: {det[1]}")
