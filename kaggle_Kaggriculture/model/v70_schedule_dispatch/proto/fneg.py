import collections, json
import sched_proto as sp
from sched_v0d import record_full
from sched_f import ExecF
from sched_v import done_ok
SEED, SEAT = 1101, 0
me = f"sub:{sp.S}/y68x3b13_main.py"; opp = f"sub:{sp.S}/y68s2_main.py"
rec = record_full(me, opp, SEED, SEAT)
ex = ExecF(rec, 0, "xy", "spawn"); op = sp.fidelity.make_agent(opp)
k = sp.engine.load_kagsim(); g = k.Game(seed=SEED)
cnt = collections.Counter(); ex_ = collections.defaultdict(list); t = 0
while not sp.engine._val(g.done):
    obs = [g.observe(0), g.observe(1)]; f = obs[0]["farms"][0]
    units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
    a = ex(obs[0]); cmds = [a["farmer"]] + a["hands"]
    tiles0 = f["tiles"]; g.step(a, op(obs[1])); tiles1 = g.observe(0)["farms"][0]["tiles"]
    for i, c in enumerate(cmds):
        if c and c[0] in ("WATER", "FEED", "CARE", "COLLECT_FERTILIZER", "HARVEST") and i < len(units):
            x, y = units[i]; b = tiles0[y][x]; af = tiles1[y][x]
            ok = done_ok(c, b, af); cnt[(c[0], ok)] += 1
            if not ok and len(ex_[c[0]]) < 2:
                ex_[c[0]].append((t, c, {k2: b.get(k2) for k2 in ("kind","crop","animal","watered_today","fed_today","cared_today","fertilizer_available","yield_units")} if isinstance(b, dict) else b,
                                  {k2: af.get(k2) for k2 in ("kind","crop","animal","watered_today","fed_today","cared_today","fertilizer_available","yield_units")} if isinstance(af, dict) else af))
    t += 1
print("无扰动局 (动作, 判定成功):", sorted(cnt.items()))
for k2, v in ex_.items():
    for e in v: print(" 误判例", k2, e)
