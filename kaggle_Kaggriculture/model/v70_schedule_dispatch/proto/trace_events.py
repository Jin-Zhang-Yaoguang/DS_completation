"""单局逐事件追踪:v0d 执行器,seed1101 vs y68s2,无扰动 vs 每天卡1步×2。"""
import collections, json
import sched_proto as sp
from sched_v0d import record_full, ExecD
from perturb import make_plan
SEED, SEAT = 1101, 0
me = f"sub:{sp.S}/y68x3b13_main.py"; opp = f"sub:{sp.S}/y68s2_main.py"
rec = record_full(me, opp, SEED, SEAT)
CRIT = {"WATER": "watered_today", "FEED": "fed_today", "CARE": "cared_today"}

def run(plan):
    ex = ExecD(rec, 0, "xy", "spawn"); op = sp.fidelity.make_agent(opp)
    k = sp.engine.load_kagsim(); g = k.Game(seed=SEED)
    log = []; eff = set(); t = 0
    while not sp.engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; f = obs[0]["farms"][0]
        units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        day = t // 24
        heads = {i: (list(ex.q[(day, ex.map.get(i, i))])[:3] if i in ex.map else None) for i in range(len(units))}
        a = ex(obs[0]); cmds = [a["farmer"]] + a["hands"]
        orig = [list(c) for c in cmds]
        for (tt, i) in plan.get(t, []):
            if i < len(cmds): cmds[i] = ["PASS"]
        tp = rec["pos"][t] if t < len(rec["pos"]) else []
        tiles0 = f["tiles"]
        g.step({"farmer": cmds[0], "hands": cmds[1:], "market": a["market"]}, op(obs[1]))
        tiles1 = g.observe(0)["farms"][0]["tiles"]
        for i, c in enumerate(cmds):
            if c and c[0] in CRIT and i < len(units):
                x, y = units[i]; b = tiles0[y][x]; af = tiles1[y][x]
                if isinstance(af, dict) and af.get(CRIT[c[0]]) and not (isinstance(b, dict) and b.get(CRIT[c[0]])):
                    eff.add((day, x, y, c[0]))
        log.append(dict(t=t, units=units, tp=[tp[ex.map.get(i, i)] if ex.map.get(i, i) < len(tp) else None for i in range(len(units))],
                        orig=orig, sent=[list(c) for c in cmds], heads=heads, pert=[i for (_, i) in plan.get(t, [])]))
        t += 1
    return eff, log, float(g.reward(0))

e0, L0, b0 = run({})
plan = make_plan(SEED, 1, 2)
e1, L1, b1 = run(plan)
print(f"银行 无扰动 {b0:.0f} 扰动 {b1:.0f}")
miss = sorted(e0 - e1); extra = sorted(e1 - e0)
byday = collections.Counter(d for d, *_ in miss)
print(f"扰动局丢失的关键动作 {len(miss)} 个(多出 {len(extra)} 个);按天 {sorted(byday.items())[:12]}")
print("按类型:", collections.Counter(m[3] for m in miss))
# 前几天丢失事件的叙述
pert_steps = sorted(plan)
for m in miss[:6]:
    day, x, y, op_ = m
    # 找无扰动局中是谁、哪一步做的
    who = None
    for row in L0[day*24:(day+1)*24]:
        for i, c in enumerate(row["sent"]):
            if c and c[0] == op_ and i < len(row["units"]) and row["units"][i] == (x, y): who = (row["t"], i); break
        if who: break
    print(f"\n### 丢失 day{day} {op_}@({x},{y}),无扰动局由 单位{who[1] if who else '?'} 在 step{who[0] if who else '?'} 完成")
    if not who: continue
    ti, ui = who
    for row in L1[day*24:(day+1)*24]:
        tt = row["t"]
        if ui >= len(row["units"]): continue
        mark = " <扰动>" if ui in row["pert"] else ""
        h = row["heads"].get(ui)
        hs = [(e[0], e[1], e[2], e[3][0]) for e in h] if h else h
        print(f"  t{tt:3d} 位置{row['units'][ui]} 带子位置{row['tp'][ui]} 执行器发{row['orig'][ui]} 实际{row['sent'][ui]}{mark} 队首{hs}")
