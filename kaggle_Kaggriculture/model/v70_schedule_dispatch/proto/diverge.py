import collections, json
import sched_proto as sp
SEED, SEAT = 1101, 0
me = f"sub:{sp.S}/y68x3b13_main.py"; opp = f"sub:{sp.S}/y68s2_main.py"
def trace(agent_factory):
    ag = agent_factory(); op = sp.fidelity.make_agent(opp)
    k = sp.engine.load_kagsim(); g = k.Game(seed=SEED); tr = []
    while not sp.engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        a0 = ag(obs[0]); a1 = op(obs[1])
        f = obs[0]["farms"][0]
        tr.append(([tuple(f["farmer"])] + [tuple(h) for h in f["hands"]], [a0.get("farmer") or ["PASS"]] + list(a0.get("hands") or []), [list(x) for x in (a0.get("market") or [])]))
        g.step(a0, a1)
    return tr
rec = sp.record(me, opp, SEED, SEAT)
T = trace(lambda: sp.fidelity.make_agent(me))
E = trace(lambda: sp.Executor(rec, 0))
first = {}; kinds = collections.Counter(); examples = []
for t in range(min(len(T), len(E))):
    tu, tc, _ = T[t]; eu, ec, _ = E[t]
    if len(tu) != len(eu):
        kinds["单位数不同"] += 1
        if len(examples) < 3: examples.append(("单位数", t, len(tu), len(eu)))
        continue
    for i in range(len(tu)):
        if tu[i] != eu[i] and (t // 24, i) not in first:
            first[(t // 24, i)] = t
            # 回看上一步双方指令
            pt, pe = T[t-1][1][i] if i < len(T[t-1][1]) else None, E[t-1][1][i] if i < len(E[t-1][1]) else None
            key = f"带子:{pt[0] if pt else None} / 执行器:{pe[0] if pe else None}"
            kinds[key] += 1
            if len(examples) < 14: examples.append((t, i, "上一步位置", T[t-1][0][i] if i < len(T[t-1][0]) else None, E[t-1][0][i] if i < len(E[t-1][0]) else None, "带子指令", pt, "执行器指令", pe, "现位置", tu[i], eu[i]))
print("首次走岔的原因分布:", kinds.most_common(12))
for x in examples: print(" ", x)
