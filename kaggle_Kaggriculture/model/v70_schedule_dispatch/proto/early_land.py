"""提前买第2块地(西南角 x0-4,y5-9)验证:混合底座 + 提前买地 + 空闲单位在新地上种一轮小麦(带子 265 接手前收完)。"""
import sys, collections, statistics
from concurrent.futures import ProcessPoolExecutor
import sched_proto as sp
from sched_v0d import record_full
from sched_f import ExecF
from perturb import play

SW = [(x, y) for y in range(5, 10) for x in range(0, 5)]
def dist(a, b): return abs(a[0]-b[0]) + abs(a[1]-b[1])
def step_to(u, c):
    x, y = c
    if u[0] != x: return ["EAST"] if x > u[0] else ["WEST"]
    return ["SOUTH"] if y > u[1] else ["NORTH"]

class EarlyLand:
    def __init__(self, rec, me_spec, buy_at=197, farm=True, n_cells=12, harvest_by=258, plant_until=212, cash_buffer=300):
        self.ex = ExecF(rec, 0, "xy", "spawn"); self.base = sp.fidelity.make_agent(me_spec)
        self.buy_at = buy_at; self.farm = farm; self.n = n_cells; self.hby = harvest_by; self.puntil = plant_until; self.buf = cash_buffer
        self.bought = False; self.seed_bought = False; self.planted = {}; self.claim = {}; self.stats = collections.Counter()
    def __call__(self, obs):
        t = int(obs.get("step", 0)); p = int(obs.get("player", 0)); f = obs["farms"][p]
        b = self.base(obs); e = self.ex(obs)
        mk = [list(x) for x in (b.get("market") or [])]
        # 带子自己的买地:提前买过后,拦截 400 步前的 BUY_LAND
        if self.bought and t < 400:
            n0 = len(mk); mk = [x for x in mk if not (x and x[0] == "BUY_LAND")]; self.stats["blocked_land"] += n0 - len(mk)
        if not self.bought and self.buy_at <= t < 260:
            if f["money"] >= 2000 + self.buf:
                mk = [["BUY_LAND"]] + mk; self.bought = True; self.stats["buy_step"] = t
        cmds = [e["farmer"]] + e["hands"]
        if self.farm and self.bought and t % 24 not in (0, 23) and t < self.hby + 4:
            tiles = f["tiles"]
            if not self.seed_bought and all(tiles[y][x] != "LOCKED" for x, y in SW[:1]):
                mk = [["BUY_SEED", "WHEAT", self.n]] + mk; self.seed_bought = True
            units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
            day = t // 24
            idle = [i for i in range(len(units)) if i in self.ex.map and not self.ex.q[(day, self.ex.map[i])]]
            # 需求:种植/浇水/收获
            need = []
            for (x, y) in SW:
                c = tiles[y][x]
                if c == "LOCKED": continue
                if c is None and t <= self.puntil and len(self.planted) < self.n and self.seed_bought:
                    need.append(((x, y), ["PLANT", "WHEAT"], 0))
                elif isinstance(c, dict) and c.get("kind") == "PLANT" and (x, y) in self.planted:
                    if t >= self.hby or (t - self.planted[(x, y)] >= 60 and (c.get("yield_units") or 0) >= 3):
                        need.append(((x, y), ["HARVEST"], 2))
                    elif not c.get("watered_today"):
                        need.append(((x, y), ["WATER"], 1))
            taken = set()
            for i in idle:
                cand = [nd for nd in need if nd[0] not in taken]
                if not cand: break
                cell, cmd, pr = min(cand, key=lambda nd: (-nd[2], dist(units[i], nd[0])))
                taken.add(cell)
                if units[i] == cell:
                    cmds[i] = cmd; self.stats["farm_" + cmd[0]] += 1
                    if cmd[0] == "PLANT": self.planted[cell] = t
                    if cmd[0] == "HARVEST": self.planted.pop(cell, None)
                else:
                    cmds[i] = step_to(units[i], cell)
        return {"farmer": cmds[0], "hands": cmds[1:], "market": mk[:10]}

class Hybrid:
    def __init__(self, rec, me_spec):
        self.ex = ExecF(rec, 0, "xy", "spawn"); self.base = sp.fidelity.make_agent(me_spec)
    def __call__(self, obs):
        b = self.base(obs); e = self.ex(obs)
        return {"farmer": e["farmer"], "hands": e["hands"], "market": [list(x) for x in (b.get("market") or [])]}

def one(job):
    seed, seat, opp, kind = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_full(me, op_spec, seed, seat)
    if kind == "hybrid": ag = Hybrid(rec, me)
    elif kind == "买地不种": ag = EarlyLand(rec, me, farm=False)
    else: ag = EarlyLand(rec, me, farm=True)
    b0, b1 = play(ag, op_spec, seed, seat)
    st = dict(getattr(ag, "stats", {}))
    return seed, opp, kind, rec["bank"][0], rec["bank"][0] - rec["bank"][1], b0, b0 - b1, st

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "smoke":
        r = one((1101, 1, "y68s2", "提前买地+种小麦")); print(r); sys.exit()
    KINDS = ["hybrid", "买地不种", "提前买地+种小麦"]
    jobs = [(s, s % 2, o, k) for s in range(1100, 1106) for o in ("y68s2", "y68r2") for k in KINDS]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for k in KINDS:
        v = [r for r in res if r[2] == k]
        print(f"{k:14s}: 银行比中位 {statistics.median(r[5]/r[3] for r in v):.1%} 胜 {sum(r[6]>0 for r in v)}/{len(v)} 分差变化中位 {statistics.median(r[6]-r[4] for r in v):+.0f}  买地步中位 {statistics.median([r[7].get('buy_step',0) for r in v]) if k!='hybrid' else '-'}  种/浇/收中位 {[statistics.median([r[7].get('farm_'+c,0) for r in v]) for c in ('PLANT','WATER','HARVEST')] if k=='提前买地+种小麦' else '-'}")
