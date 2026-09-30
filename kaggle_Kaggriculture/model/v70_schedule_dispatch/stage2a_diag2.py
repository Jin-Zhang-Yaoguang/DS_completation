import sys, collections, json
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE / "proto"))
import sched_proto as sp
from sched_v0d import record_full
from stage2a import Stage2A
SEED, SEAT = 1101, 1
me = f"sub:{sp.S}/y68x3b13_main.py"; opp = f"sub:{sp.S}/y68s2_main.py"
rec = record_full(me, opp, SEED, SEAT)
ag = Stage2A(rec, me); op = sp.fidelity.make_agent(opp); k = sp.engine.load_kagsim(); g = k.Game(seed=SEED); o = 1 - SEAT
t = 0
while t < 96:
    obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[SEAT] = ag(obs[SEAT]); a[o] = op(obs[o])
    f = obs[SEAT]["farms"][SEAT]; pr = obs[SEAT]["private"]
    units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
    cmds = [a[SEAT].get("farmer")] + list(a[SEAT].get("hands") or [])
    before = json.dumps([f["tiles"], pr.get("inventories"), pr.get("shed"), pr.get("seeds")], sort_keys=True)
    inv0 = [dict(x) for x in (pr.get("inventories") or [])]; shed0 = dict(pr.get("shed") or {})
    g.step(a[0], a[1])
    o2 = g.observe(SEAT); f2 = o2["farms"][SEAT]; pr2 = o2["private"]
    if t >= 40:
        for i, c in enumerate(cmds):
            if not c or c[0] in ("NORTH", "SOUTH", "EAST", "WEST", "PASS", "WATER", "CARE", "COLLECT_FERTILIZER"): continue
            x, y = units[i]
            tb = f["tiles"][y][x]; ta = f2["tiles"][y][x]
            ib = inv0[i] if i < len(inv0) else {}; ia = (pr2.get("inventories") or [{}]*20)[i] if i < len(pr2.get("inventories") or []) else {}
            changed = (json.dumps(tb, sort_keys=True) != json.dumps(ta, sort_keys=True)) or ib != ia
            if not changed:
                print(f"t{t} 单位{i}@{(x,y)} {c} 无效  格前={ (tb or {}).get('kind') if isinstance(tb,dict) else tb} 动物={(tb or {}).get('animal') if isinstance(tb,dict) else None} 背包={ib} 仓库小麦={shed0.get('WHEAT')} 仓库牛={shed0.get('COW')}")
        for x in (a[SEAT].get("market") or []):
            if x and x[0] == "SELL" and len(x) > 2:
                have = shed0.get(x[1], 0) + sum(v.get(x[1], 0) for v in inv0)
                if have < x[2] and x[2] < 1000: print(f"t{t} 卖单 {x} 可卖 {have}")
    t += 1
