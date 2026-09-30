"""田间战略改动基准:第 D 天起,按格子奇偶把一部分 PLANT WHEAT 改为 PLANT CARROT,BUY_SEED 同比例换。底座:原带子 / v0f。"""
import statistics
from concurrent.futures import ProcessPoolExecutor
import sched_proto as sp
from sched_v0d import record_full
from sched_f import ExecF
from perturb import play

def swap(agent, frac=0.5, start_day=10, to="CARROT"):
    def pick(x, y):
        return ((x * 7 + y * 3) % 4) < round(frac * 4)
    def f(obs):
        a = agent(obs); t = int(obs.get("step", 0))
        if t // 24 < start_day: return a
        p = int(obs.get("player", 0)); fm = obs["farms"][p]
        units = [tuple(fm["farmer"])] + [tuple(h) for h in fm["hands"]]
        cmds = [list(a.get("farmer") or ["PASS"])] + [list(c) for c in (a.get("hands") or [])]
        for i, c in enumerate(cmds):
            if c[:2] == ["PLANT", "WHEAT"] and i < len(units) and pick(*units[i]):
                cmds[i] = ["PLANT", to] + c[2:]
        mk = []
        for x in (a.get("market") or []):
            x = list(x)
            if x[:2] == ["BUY_SEED", "WHEAT"] and len(x) > 2:
                n = int(x[2]); m = int(round(n * frac))
                if n - m > 0: mk.append(["BUY_SEED", "WHEAT", n - m])
                if m > 0: mk.append(["BUY_SEED", to, m])
            else:
                mk.append(x)
        return {"farmer": cmds[0], "hands": cmds[1:], "market": mk[:10]}
    return f

def one(job):
    seed, seat, opp, frac = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    b0, b1 = play(sp.fidelity.make_agent(me), op_spec, seed, seat)
    t0, t1 = play(swap(sp.fidelity.make_agent(me), frac), op_spec, seed, seat)
    v0, v1 = play(swap(ExecF(record_full(me, op_spec, seed, seat), 0, "xy", "spawn"), frac), op_spec, seed, seat)
    return frac, b0, b0 - b1, t0, t0 - t1, v0, v0 - v1
if __name__ == "__main__":
    jobs = [(s, s % 2, o, fr) for s in range(1100, 1106) for o in ("y68s2", "y68r2") for fr in (0.25, 0.5)]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for fr in (0.25, 0.5):
        v = [r for r in res if r[0] == fr]
        print(f"换胡萝卜 {fr:.0%}: 带子底座 银行比 {statistics.median(r[3]/r[1] for r in v):.1%} 胜 {sum(r[4]>0 for r in v)}/{len(v)} 分差变化 {statistics.median(r[4]-r[2] for r in v):+.0f} | v0f底座 银行比 {statistics.median(r[5]/r[1] for r in v):.1%} 胜 {sum(r[6]>0 for r in v)}/{len(v)} 分差变化 {statistics.median(r[6]-r[2] for r in v):+.0f} | 原带子胜 {sum(r[2]>0 for r in v)}")
