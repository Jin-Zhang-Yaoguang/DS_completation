"""阶段1:从 y68x3b13 带子蒸馏日程表(雇工/买入/布局),并检验固定程度。"""
import sys, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "proto"))
FIELD = {"PLANT", "BUILD_PASTURE", "BUILD_COOP", "PLACE", "DIG"}

def one(job):
    seed, opp = job
    import sched_proto as sp
    seat = seed % 2
    me = sp.fidelity.make_agent(f"sub:{sp.S}/y68x3b13_main.py"); op = sp.fidelity.make_agent(f"sub:{sp.S}/{opp}_main.py")
    k = sp.engine.load_kagsim(); g = k.Game(seed=seed); o = 1 - seat
    hires = collections.Counter(); units = {}; money = {}; omoney = {}; prices = {}; shed = {}; buys = []; field = []; t = 0; shops = None
    while not sp.engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = me(obs[seat]); a[o] = op(obs[o])
        f = obs[seat]["farms"][seat]; us = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        units[t] = len(us); money[t] = f["money"]; omoney[t] = obs[seat]["farms"][o]["money"]
        if t in (150, 196, 217, 265, 433, 648, 649, 650): prices[t] = obs[seat]["market"]["prices"]; shed[t] = (obs[seat].get("private") or {}).get("shed")
        if t == 146: shops = tuple((obs[seat].get("town") or {}).get("unlocked_shops") or [])[:2]
        for x in (a[seat].get("market") or []):
            if not x: continue
            if x[0] == "HIRE": hires[t] += 1
            elif x[0] != "SELL": buys.append([t] + list(x))
        cmds = [a[seat].get("farmer") or ["PASS"]] + list(a[seat].get("hands") or [])
        for i, c in enumerate(cmds[:len(us)]):
            if c and c[0] in FIELD: field.append([t, us[i][0], us[i][1]] + list(c))
        g.step(a[0], a[1]); t += 1
    return dict(seed=seed, opp=opp, seat=seat, shops=list(shops or []), hires=dict(hires), units=units, buys=buys, field=field,
                money=money, omoney=omoney, prices=prices, shed=shed, bank=float(g.reward(seat)), margin=float(g.reward(seat) - g.reward(o)))

if __name__ == "__main__":
    jobs = [(s, "y68s2") for s in range(2000, 2024)]
    with ProcessPoolExecutor(7) as ex: R = list(ex.map(one, jobs))
    json.dump(R, open(HERE / "distill_raw.json", "w"))
    print("局数", len(R), "商店组合", collections.Counter("|".join(r["shops"]) for r in R).most_common())
