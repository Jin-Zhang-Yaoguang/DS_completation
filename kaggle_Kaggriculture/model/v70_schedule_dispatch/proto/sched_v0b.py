"""v0b:BFS 寻路,可通行格=带子录制中任何单位站过的格(按天累积),并在线学习撞墙格。"""
import sys, collections, statistics
from concurrent.futures import ProcessPoolExecutor
import sched_proto as sp

def record_with_cells(me, opp, seed, seat):
    rec = sp.record(me, opp, seed, seat)
    # 重跑一次拿每步所有单位位置(record 未保存位置,只存事件)
    m = sp.fidelity.make_agent(me); o = sp.fidelity.make_agent(opp)
    k = sp.engine.load_kagsim(); g = k.Game(seed=seed); oo = 1 - seat
    walk = collections.defaultdict(set); t = 0
    while not sp.engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = m(obs[seat]); a[oo] = o(obs[oo])
        f = obs[seat]["farms"][seat]
        for u in [f["farmer"]] + f["hands"]: walk[t // 24].add(tuple(u))
        g.step(a[0], a[1]); t += 1
    rec["walk"] = {d: sorted(v) for d, v in walk.items()}
    return rec

class ExecBFS(sp.Executor):
    def __init__(self, rec, slack=0):
        super().__init__(rec, slack)
        self.walk_upto = {}
        acc = set()
        for d in sorted(rec["walk"]):
            acc |= set(rec["walk"][d]); self.walk_upto[d] = set(acc)
        self.last = {}; self.blocked = set()
    def step_to(self, day, src, dst):
        W = self.walk_upto.get(day, set()) - self.blocked
        W = W | {src, dst}
        prev = {src: None}; dq = collections.deque([src])
        while dq:
            c = dq.popleft()
            if c == dst: break
            for name, (dx, dy) in sp.MOVES.items():
                n = (c[0]+dx, c[1]+dy)
                if n in W and n not in prev and 0 <= n[0] < 10 and 0 <= n[1] < 10:
                    prev[n] = (c, name); dq.append(n)
        if dst not in prev:
            return None
        c = dst; mv = None
        while prev[c] is not None:
            c, mv = prev[c]
        return [mv]
    def __call__(self, obs):
        t = int(obs.get("step", 0)); day = t // 24
        p = int(obs.get("player", 0)); f = obs["farms"][p]
        units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        # 学习撞墙:上一步发了移动但位置没变
        for i, (pos, mv) in self.last.items():
            if i < len(units) and units[i] == pos and t % 24 != 0:
                dx, dy = sp.MOVES[mv]; self.blocked.add((pos[0]+dx, pos[1]+dy)); self.stats["bump"] += 1
        self.last = {}
        cmds = []
        for i, (ux, uy) in enumerate(units):
            q = self.q[(day, i)]; cmd = ["PASS"]
            if q:
                et, x, y, c = q[0]
                if (ux, uy) == (x, y):
                    if t >= et - self.slack:
                        cmd = list(c); q.popleft(); self.stats["work"] += 1; self.stats["late"] += (t > et)
                    else:
                        self.stats["wait"] += 1
                else:
                    mv = self.step_to(day, (ux, uy), (x, y))
                    if mv is None:
                        mv = (["EAST"] if x > ux else ["WEST"]) if ux != x else (["SOUTH"] if y > uy else ["NORTH"])
                        self.stats["nopath"] += 1
                    cmd = mv; self.last[i] = ((ux, uy), mv[0]); self.stats["move"] += 1
            else:
                self.stats["idle"] += 1
            cmds.append(cmd)
        mk = self.rec["market"][t] if t < len(self.rec["market"]) else []
        return {"farmer": cmds[0], "hands": cmds[1:], "market": [list(x) for x in mk]}

def one(job):
    seed, seat, opp = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_with_cells(me, op_spec, seed, seat)
    ex = ExecBFS(rec, 0); op = sp.fidelity.make_agent(op_spec)
    k = sp.engine.load_kagsim(); g = k.Game(seed=seed); o = 1 - seat
    while not sp.engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = ex(obs[seat]); a[o] = op(obs[o]); g.step(a[0], a[1])
    b0, b1 = float(g.reward(seat)), float(g.reward(o))
    return seed, seat, opp, rec["bank"][0], rec["bank"][0]-rec["bank"][1], b0, b0-b1, ex.stats.get("late",0), ex.leftover(), ex.stats.get("bump",0), ex.stats.get("nopath",0)

if __name__ == "__main__":
    jobs = [(s, s % 2, o) for s in range(1100, 1108) for o in ("y68s2", "y68r2")]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for r in res: print(f"seed{r[0]} vs {r[2]:6s} 带子 {r[3]:7.0f} 分差 {r[4]:+7.0f} | BFS {r[5]:7.0f} ({r[5]/r[3]:.1%}) 分差 {r[6]:+7.0f} 迟到 {r[7]} 剩余 {r[8]} 撞墙 {r[9]} 无路 {r[10]}")
    ratio = [r[5]/r[3] for r in res]
    print(f"银行比 中位 {statistics.median(ratio):.1%} 最低 {min(ratio):.1%};带子胜 {sum(r[4]>0 for r in res)}/16,BFS 执行器胜 {sum(r[6]>0 for r in res)}/16;分差变化中位 {statistics.median(r[6]-r[4] for r in res):+.0f};迟到中位 {statistics.median(r[7] for r in res)}")
