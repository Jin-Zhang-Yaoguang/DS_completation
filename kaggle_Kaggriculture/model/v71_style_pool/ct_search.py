"""刀1:求 V52/V53/V54镜像 的 t2 rkey;对每个对手 × 反制模板跑 8 seed 双席位,选正模板。"""
import sys, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
# 模板:{名: [(step, slot, order), ...]}
TPL = {
    "base": [],
    "跟买跟卖10": [(2, 0, ("BUY_PRODUCT", "WHEAT", 10)), (3, 1, ("SELL", "WHEAT", 10))],
    "抢卖5": [(3, 0, ("SELL", "WHEAT", 5))],
    "前置对冲20": [(2, 0, ("BUY_PRODUCT", "WHEAT", 20)), (4, 0, ("SELL", "WHEAT", 20))],
    "跟买跟卖20": [(2, 0, ("BUY_PRODUCT", "WHEAT", 20)), (3, 1, ("SELL", "WHEAT", 20))],
}
def make_me(plan):
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity
    base = fidelity.make_agent(f"sub:{HERE}/agents/v54_main.py")
    if not plan: return base, None
    def me(obs):
        a = base(obs); step = int(obs.get("step", 0))
        items = sorted((slot, list(o)) for t, slot, o in plan if t == step)
        if items:
            mk = [list(x) for x in (a.get("market") or [])]
            for slot, o in items:
                while len(mk) < slot: mk.append(["SELL", "WHEAT", 0])
                mk.insert(slot, o)
            a = dict(a); a["market"] = mk[:10]
        return a
    return me, None
def one(job):
    opp, tpl, seed, seat = job
    sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
    import fidelity, engine
    me, _ = make_me(TPL[tpl])
    op = fidelity.make_agent(f"sub:{HERE}/agents/{opp}_main.py")
    k = engine.load_kagsim(); g = k.Game(seed=seed); o = 1 - seat; t = 0; rkey = None
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        if t == 2:
            rv = obs[seat]["farms"][o]
            rkey = (round(float(rv["money"]), 3), int(obs[seat]["market"]["inventory"]["WHEAT"]))
        a = [None, None]; a[seat] = me(obs[seat]); a[o] = op(obs[o]); g.step(a[0], a[1]); t += 1
    return opp, tpl, seed, seat, float(g.reward(seat) - g.reward(o)), rkey
if __name__ == "__main__":
    jobs = [(o2, tp, s, st) for o2 in ("v52", "v53", "v54") for tp in TPL for s in range(9000, 9008) for st in (0, 1)]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs, chunksize=2))
    json.dump([list(r) for r in res], open(HERE/"ct_search.json", "w"), ensure_ascii=False)
    keys = collections.Counter((r[0], r[5] and tuple(r[5])) for r in res)
    print("rkey(对手, t2指纹):", dict(collections.Counter((r[0], str(r[5])) for r in res if r[1] == "base")))
    import statistics as st2
    for o2 in ("v52", "v53", "v54"):
        print(f"\n== vs {o2}")
        for tp in TPL:
            v = [r for r in res if r[0] == o2 and r[1] == tp]
            w = sum(1 for r in v if r[4] > 0)
            print(f"  {tp:10s} {w:2d}/{len(v)} 中位 {st2.median(r[4] for r in v):+8.0f}")
