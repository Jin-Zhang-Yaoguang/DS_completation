"""调度器最小原型:带子任务重执行器。
录制:底盘跑一局,记录每步每单位的工作指令(格+动作)与市场单。
执行:按单位绑定的任务队列,自己寻路,到格执行;slack 控制可提前的步数。
"""
import sys, json, collections
from pathlib import Path
M = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model")
S = Path(__file__).resolve().parent.parent / "agents"
sys.path.insert(0, str(M/"v16_online_fidelity")); sys.path.insert(0, str(M/"v4_demand_race"/"harness"))
import fidelity, engine
MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}

def record(me_spec, opp_spec, seed, seat):
    me = fidelity.make_agent(me_spec); op = fidelity.make_agent(opp_spec)
    k = engine.load_kagsim(); g = k.Game(seed=seed); o = 1 - seat
    rec = {"market": [], "events": [], "units": []}
    t = 0
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]
        a = [None, None]; a[seat] = me(obs[seat]); a[o] = op(obs[o])
        f = obs[seat]["farms"][seat]
        units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        cmds = [a[seat].get("farmer") or ["PASS"]] + list(a[seat].get("hands") or [])
        rec["market"].append([list(x) for x in (a[seat].get("market") or [])])
        rec["units"].append(len(units))
        for i, c in enumerate(cmds[:len(units)]):
            if c and c[0] not in MOVES and c[0] != "PASS":
                rec["events"].append([t, i, units[i][0], units[i][1], list(c)])
        g.step(a[0], a[1]); t += 1
    rec["bank"] = [float(g.reward(seat)), float(g.reward(o))]
    return rec

class Executor:
    def __init__(self, rec, slack=0):
        self.rec = rec; self.slack = slack
        self.q = collections.defaultdict(collections.deque)  # (day, unit) -> events
        for t, i, x, y, c in rec["events"]:
            self.q[(t // 24, i)].append((t, x, y, c))
        self.stats = collections.Counter()
    def __call__(self, obs):
        t = int(obs.get("step", 0)); day = t // 24
        p = int(obs.get("player", 0)); f = obs["farms"][p]
        units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        cmds = []
        for i, (ux, uy) in enumerate(units):
            q = self.q[(day, i)]
            cmd = ["PASS"]
            while q:
                et, x, y, c = q[0]
                if (ux, uy) == (x, y):
                    if t >= et - self.slack:
                        cmd = list(c); q.popleft(); self.stats["work"] += 1
                        self.stats["late"] += (t > et); self.stats["early"] += (t < et)
                    else:
                        self.stats["wait"] += 1
                    break
                # L 形寻路:先横后纵
                if ux != x: cmd = ["EAST"] if x > ux else ["WEST"]
                else: cmd = ["SOUTH"] if y > uy else ["NORTH"]
                self.stats["move"] += 1
                break
            else:
                self.stats["idle"] += 1
            cmds.append(cmd)
        mk = self.rec["market"][t] if t < len(self.rec["market"]) else []
        return {"farmer": cmds[0], "hands": cmds[1:], "market": [list(x) for x in mk]}
    def leftover(self):
        return sum(len(v) for v in self.q.values())

def run_exec(rec, opp_spec, seed, seat, slack):
    ex = Executor(rec, slack); op = fidelity.make_agent(opp_spec)
    k = engine.load_kagsim(); g = k.Game(seed=seed); o = 1 - seat
    while not engine._val(g.done):
        obs = [g.observe(0), g.observe(1)]; a = [None, None]; a[seat] = ex(obs[seat]); a[o] = op(obs[o]); g.step(a[0], a[1])
    return float(g.reward(seat)), float(g.reward(o)), dict(ex.stats), ex.leftover()

if __name__ == "__main__":
    opp = f"sub:{S}/y68s2_main.py"; me = f"sub:{S}/y68x3b13_main.py"
    seed, seat = int(sys.argv[1]) if len(sys.argv) > 1 else 1101, 0
    rec = record(me, opp, seed, seat)
    print(f"带子: 我 {rec['bank'][0]:.0f} 对手 {rec['bank'][1]:.0f} 分差 {rec['bank'][0]-rec['bank'][1]:+.0f}  工作事件 {len(rec['events'])}")
    for slack in (0, 2, 6, 24):
        b0, b1, st, left = run_exec(rec, opp, seed, seat, slack)
        print(f"执行器 slack={slack:2d}: 我 {b0:.0f} 对手 {b1:.0f} 分差 {b0-b1:+.0f}  银行比 {b0/rec['bank'][0]:.1%}  未完成事件 {left}  {st}")
