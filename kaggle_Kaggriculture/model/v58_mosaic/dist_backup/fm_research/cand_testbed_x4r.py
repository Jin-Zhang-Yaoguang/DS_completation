"""线上 seed 测试床:y68r2 / y68s / y68t。组 A=36 局 V41/V42 潮(原版反应式);组 B=3 个 FM|FM 大崩(对手 tape);组 C=5 局 B10(对手 V43+B10 开局)。"""
import sys, json
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent
VERS = ["y68x4r"]
def one(job):
    grp, eid, opp, ver = job
    sys.path.insert(0, str(M / "v16_online_fidelity")); sys.path.insert(0, str(M / "v4_demand_race" / "harness"))
    import fidelity, engine
    rep = json.load(open(S / f"live_replays3/episode-{eid}-replay.json"))
    nm = rep["info"]["TeamNames"]; seat = nm.index("datatuu"); o = 1 - seat; st = rep["steps"]
    me = fidelity.make_agent(f"sub:{S}/{ver}_main.py")
    if opp == "tape":
        op = fidelity.tape_agent([st[t + 1][o].get("action") or {} for t in range(len(st) - 1)])
    else:
        op = fidelity.make_agent(f"sub:{S}/" + {"v41": "kernels_0914/v41_agent.py", "v42": "kernels_0914/v42_agent.py", "v43b10": "kernels_0915/v43b10_agent.py"}[opp])
    k = engine.load_kagsim(); g = k.Game(seed=rep["info"]["seed"])
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        acts = [None, None]; acts[seat] = me(obs[seat]); acts[o] = op(obs[o])
        g.step(acts[0], acts[1])
    return grp, eid, str(nm[o]), ver, g.reward(seat) - g.reward(o)
if __name__ == "__main__":
    games = [("A:V41/42潮", r[0], r[1]) for r in json.load(open(S / "opp_identity.json"))]
    games += [("B:FM|FM大崩", e, "tape") for e in (109138184, 109090129, 109173872)]
    ids = json.load(open(S / "ep_ids8.json")); b10 = set()
    for tag in ids:
        for eid in ids[tag]:
            p = S / f"live_replays3/episode-{eid}-replay.json"
            if not p.exists(): continue
            rep = json.load(open(p)); nm = rep["info"]["TeamNames"]
            if nm.count("datatuu") != 1: continue
            o = 1 - nm.index("datatuu"); m1 = (rep["steps"][1][o].get("action") or {}).get("market") or []
            if sum(int(x[2]) for x in m1 if x and x[0] == "BUY_PRODUCT" and len(x) > 2) == 10: b10.add(eid)
    games += [("C:B10家族", e, "v43b10") for e in sorted(b10)]
    jobs = [(g, e, o, v) for g, e, o in games for v in VERS]
    with ProcessPoolExecutor(8) as ex:
        res = list(ex.map(one, jobs, chunksize=2))
    json.dump(res, open(S / "cand_testbed_x4r.json", "w"), ensure_ascii=False)
    tab = {}
    for grp, eid, opp, ver, m in res:
        tab.setdefault((grp, eid, opp), {})[ver] = m
    print(f"{'组':12s} {'对手':16s} " + " ".join(f"{v:>8s}" for v in VERS))
    for (grp, eid, opp), d in sorted(tab.items(), key=lambda kv: (kv[0][0], kv[1]["y68x4r"])):
        print(f"{grp:12s} {opp[:16]:16s} " + " ".join(f"{d[v]:+8.0f}" for v in VERS))
    print("\n汇总(胜局/局数, 总 margin):")
    for grp in sorted({k[0] for k in tab}):
        rows = [d for k, d in tab.items() if k[0] == grp]
        print(f"  {grp}: " + " | ".join(f"{v} {sum(d[v]>0 for d in rows)}/{len(rows)} {sum(d[v] for d in rows):+.0f}" for v in VERS))
    allr = list(tab.values())
    print(f"  全部 {len(allr)} 局: " + " | ".join(f"{v} {sum(d[v]>0 for d in allr)}/{len(allr)} {sum(d[v] for d in allr):+.0f}" for v in VERS))
