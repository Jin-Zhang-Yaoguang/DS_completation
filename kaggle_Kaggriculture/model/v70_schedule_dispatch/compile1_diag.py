import sys, collections
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE / "proto"))
import sched_proto as sp
from sched_v0d import record_full
from compile1 import Compile1
SEED, SEAT = 1101, 1
me = f"sub:{sp.S}/y68x3b13_main.py"; opp = f"sub:{sp.S}/y68s2_main.py"
rec = record_full(me, opp, SEED, SEAT)
def run(ag):
    op = sp.fidelity.make_agent(opp); k = sp.engine.load_kagsim(); g = k.Game(seed=SEED); o = 1 - SEAT
    daily = collections.defaultdict(collections.Counter); t = 0; endstate = {}
    while not sp.engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[SEAT] = ag(obs[SEAT]); a[o] = op(obs[o])
        f = obs[SEAT]["farms"][SEAT]; day = t // 24
        for c in [a[SEAT].get("farmer")] + list(a[SEAT].get("hands") or []):
            if c: daily[day][c[0] if c[0] not in ("NORTH","SOUTH","EAST","WEST") else "MOVE"] += 1
        if t % 24 == 23:
            tl = [c for row in f["tiles"] for c in row if isinstance(c, dict)]
            endstate[day] = dict(crops=sum(c.get("kind")=="PLANT" for c in tl), unwater=sum(c.get("kind")=="PLANT" and not c.get("watered_today") for c in tl),
                                 weeds=sum(c.get("kind")=="WEED" for c in tl), animals=sum(bool(c.get("animal")) for c in tl),
                                 uncared=sum(bool(c.get("animal")) and not c.get("cared_today") for c in tl), unfed=sum(bool(c.get("animal")) and not c.get("fed_today") for c in tl), money=f["money"])
        g.step(a[0], a[1]); t += 1
    return daily, endstate, g.reward(SEAT)
tape = sp.fidelity.make_agent(me)
d0, e0, b0 = run(tape); d1, e1, b1 = run(Compile1(rec, me, water_at=0))
print("银行 带子", b0, "阶段2a", b1)
for day in range(8):
    k0 = d0[day]; k1 = d1[day]
    print(f"第{day}天 带子 浇{k0['WATER']} 照{k0['CARE']} 收肥{k0['COLLECT_FERTILIZER']} 收{k0['HARVEST']} 种{k0['PLANT']} 喂{k0['FEED']} 取{k0['PICKUP']} 移{k0['MOVE']} 闲{k0['PASS']} | 2a 浇{k1['WATER']} 照{k1['CARE']} 收肥{k1['COLLECT_FERTILIZER']} 收{k1['HARVEST']} 种{k1['PLANT']} 喂{k1['FEED']} 取{k1['PICKUP']} 移{k1['MOVE']} 闲{k1['PASS']}")
    print(f"      日终 带子 {e0.get(day)}\n      日终 2a   {e1.get(day)}")
