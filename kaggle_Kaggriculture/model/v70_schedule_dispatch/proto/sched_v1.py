"""v1:在 v0 基础上加执行校验——动作后若 目标格/该单位背包/仓库 均无变化,则任务放回队首重试。"""
import sys, json, collections
from sched_proto import record, fidelity, engine, MOVES, S

def sig(obs, i, x, y):
    p = int(obs.get("player", 0)); f = obs["farms"][p]
    tile = f["tiles"][y][x] if 0 <= y < len(f["tiles"]) and 0 <= x < len(f["tiles"][y]) else None
    pr = obs.get("private") or {}
    inv = (pr.get("inventories") or [])
    return json.dumps([tile, inv[i] if i < len(inv) else None, pr.get("shed"), pr.get("seeds")], sort_keys=True)

class ExecV1:
    def __init__(self, rec, slack=0, axis="xy", max_retry=6):
        self.rec = rec; self.slack = slack; self.axis = axis; self.max_retry = max_retry
        self.q = collections.defaultdict(collections.deque)
        for t, i, x, y, c in rec["events"]:
            self.q[(t // 24, i)].append([t, x, y, c, 0])
        self.pending = {}; self.stats = collections.Counter()
    def __call__(self, obs):
        t = int(obs.get("step", 0)); day = t // 24
        p = int(obs.get("player", 0)); f = obs["farms"][p]
        units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        # 校验上一步的工作
        for i, (ev, pre, d) in list(self.pending.items()):
            if d == day and i < len(units) and sig(obs, i, ev[1], ev[2]) == pre:
                ev[4] += 1
                if ev[4] <= self.max_retry:
                    self.q[(d, i)].appendleft(ev); self.stats["retry"] += 1
                else:
                    self.stats["drop"] += 1
            else:
                self.stats["ok"] += 1
        self.pending = {}
        cmds = []
        for i, (ux, uy) in enumerate(units):
            q = self.q[(day, i)]; cmd = ["PASS"]
            if q:
                et, x, y, c, r = q[0]
                if (ux, uy) == (x, y):
                    if t >= et - self.slack:
                        ev = q.popleft(); cmd = list(c)
                        self.pending[i] = (ev, sig(obs, i, x, y), day)
                        self.stats["early"] += (t < et); self.stats["late"] += (t > et)
                    else:
                        self.stats["wait"] += 1
                else:
                    if self.axis == "xy":
                        cmd = (["EAST"] if x > ux else ["WEST"]) if ux != x else (["SOUTH"] if y > uy else ["NORTH"])
                    else:
                        cmd = (["SOUTH"] if y > uy else ["NORTH"]) if uy != y else (["EAST"] if x > ux else ["WEST"])
                    self.stats["move"] += 1
            else:
                self.stats["idle"] += 1
            cmds.append(cmd)
        mk = self.rec["market"][t] if t < len(self.rec["market"]) else []
        return {"farmer": cmds[0], "hands": cmds[1:], "market": [list(x) for x in mk]}
    def leftover(self):
        return sum(len(v) for v in self.q.values())

def run(rec, opp_spec, seed, seat, **kw):
    ex = ExecV1(rec, **kw); op = fidelity.make_agent(opp_spec)
    k = engine.load_kagsim(); g = k.Game(seed=seed); o = 1 - seat
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = ex(obs[seat]); a[o] = op(obs[o]); g.step(a[0], a[1])
    return float(g.reward(seat)), float(g.reward(o)), dict(ex.stats), ex.leftover()

if __name__ == "__main__":
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1101; seat = 0
    opp = f"sub:{S}/y68s2_main.py"; me = f"sub:{S}/y68x3b13_main.py"
    rec = record(me, opp, seed, seat)
    print(f"带子: 我 {rec['bank'][0]:.0f} 分差 {rec['bank'][0]-rec['bank'][1]:+.0f}")
    for axis in ("xy", "yx"):
        for slack in (0, 2, 6, 24):
            b0, b1, st, left = run(rec, opp, seed, seat, slack=slack, axis=axis)
            print(f"v1 axis={axis} slack={slack:2d}: 我 {b0:.0f} 银行比 {b0/rec['bank'][0]:.1%} 分差 {b0-b1:+.0f} 剩余 {left} ok {st.get('ok',0)} retry {st.get('retry',0)} drop {st.get('drop',0)} early {st.get('early',0)} late {st.get('late',0)} idle {st.get('idle',0)}")
