import sys, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE / "proto"))
def one(seed):
    import sched_proto as sp
    seat = seed % 2; o = 1 - seat
    me = sp.fidelity.make_agent(f"sub:{sp.S}/y68x3b13_main.py"); op = sp.fidelity.make_agent(f"sub:{sp.S}/y68s2_main.py")
    k = sp.engine.load_kagsim(); g = k.Game(seed=seed); t = 0; snap = {}; dec = {}
    while t <= 440:
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = me(obs[seat]); a[o] = op(obs[o])
        if t in (217, 433): snap[t] = list((obs[seat].get("town") or {}).get("unlocked_shops") or [])
        if t == 217: dec[217] = [x[1] for x in (a[seat].get("market") or []) if x and x[0] == "BUY_ANIMAL"]
        if t == 433: dec[433] = any(x and x[0] == "BUY_LAND" for x in (a[seat].get("market") or []))
        g.step(a[0], a[1]); t += 1
    return seed, snap, dec
if __name__ == "__main__":
    with ProcessPoolExecutor(7) as ex: R = list(ex.map(one, range(2000, 2024)))
    print("step217 决策 vs 第3家商店:")
    c = collections.defaultdict(collections.Counter)
    for s, snap, dec in R: c[snap[217][2] if len(snap[217]) > 2 else None][tuple(dec[217])] += 1
    for k, v in c.items(): print("  ", k, dict(v))
    print("step433 买地 vs 第6家商店 / 已解锁序列:")
    c2 = collections.defaultdict(collections.Counter)
    for s, snap, dec in R:
        c2[snap[433][5] if len(snap[433]) > 5 else None][dec[433]] += 1
        if dec[433]: print("   买地局 seed", s, snap[433])
    for k, v in c2.items(): print("  ", k, dict(v))
