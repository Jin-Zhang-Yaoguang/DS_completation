import collections
import sched_proto as sp
rec = sp.record(f"sub:{sp.S}/y68x3b13_main.py", f"sub:{sp.S}/y68s2_main.py", 1101, 0)
# 带子里每个单位每步的位置,用于和执行器对比
ex = sp.Executor(rec, 0); op = sp.fidelity.make_agent(f"sub:{sp.S}/y68s2_main.py")
k = sp.engine.load_kagsim(); g = k.Game(seed=1101)
late = collections.Counter(); late_cmd = collections.Counter(); lag = collections.Counter(); first = []
orig = {}
for t, i, x, y, c in rec["events"]: orig[(t, i)] = (x, y, c[0])
t = 0
while not sp.engine._val(g.done):
    obs = [g.observe(0), g.observe(1)]
    f = obs[0]["farms"][0]; units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
    before = {k2: list(v) for k2, v in ex.q.items() if k2[0] == t // 24}
    a0 = ex(obs[0]); a1 = op(obs[1])
    cmds = [a0["farmer"]] + a0["hands"]
    for i, c in enumerate(cmds):
        q = before.get((t // 24, i)) or []
        if q and c and c[0] not in sp.MOVES and c[0] != "PASS":
            et = q[0][0]
            if t > et:
                late[t % 24] += 1; late_cmd[c[0]] += 1; lag[min(t - et, 9)] += 1
                if len(first) < 8: first.append((t, i, units[i], (q[0][1], q[0][2]), c[0], t - et))
    g.step(a0, a1); t += 1
print("迟到按小时:", sorted(late.items()))
print("迟到按动作:", late_cmd.most_common())
print("迟到步数分布:", sorted(lag.items()))
print("前几例 (step, 单位, 当前位, 目标格, 动作, 迟到):", first)
