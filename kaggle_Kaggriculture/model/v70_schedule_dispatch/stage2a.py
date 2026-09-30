"""阶段2a:结构类任务沿用录制(按出生位置绑定到人),维护类(浇水/照料/收肥)由状态生成,收获按日程时间点进入自由任务池;
调度器每步:结构任务临近则优先,否则就近认领维护任务(格子级互斥),L 形寻路。市场单由原带子 agent 现场生成。"""
import sys, collections, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE / "proto"))
import sched_proto as sp
from sched_v0d import record_full
from sched_v0c import ExecC
from perturb import play, perturbed, make_plan

MAINT_STATE = {"WATER", "CARE", "COLLECT_FERTILIZER"}
PURE = {"WATER", "CARE"}
def dist(a, b): return abs(a[0]-b[0]) + abs(a[1]-b[1])
def step_to(u, c, vfirst=False):
    x, y = c
    if vfirst:
        if u[1] != y: return ["SOUTH"] if y > u[1] else ["NORTH"]
        return ["EAST"] if x > u[0] else ["WEST"]
    if u[0] != x: return ["EAST"] if x > u[0] else ["WEST"]
    return ["SOUTH"] if y > u[1] else ["NORTH"]

class Stage2A:
    def __init__(self, rec, me_spec, lead=1, vfirst=False, harvest_free=True, water_at=1, pen=None, pool_ops=("WATER", "CARE", "COLLECT_FERTILIZER"), care_late=16, owner=False):
        self.rec = rec; self.water_at = water_at; self.pen = pen or {"HARVEST": 2, "COLLECT_FERTILIZER": 4, "CARE": 6}; self.base = sp.fidelity.make_agent(me_spec); self.lead = lead; self.vfirst = vfirst; self.hfree = harvest_free
        # 结构队列:剔除维护类(以及可选的收获)
        self.pool_ops = set(pool_ops); self.care_late = care_late; self.owner = owner
        own = collections.defaultdict(collections.Counter)
        for t_, i_, x_, y_, c_ in rec["events"]:
            if c_[0] in pool_ops: own[(t_ // 24, x_, y_)][i_] += 1
        self.own = {k: v.most_common(1)[0][0] for k, v in own.items()}
        drop = set(pool_ops) | ({"HARVEST"} if harvest_free else set())
        srec = dict(rec); srec["events"] = [e for e in rec["events"] if e[4][0] not in drop]
        self.q = collections.defaultdict(collections.deque)
        for t, i, x, y, c in srec["events"]: self.q[(t // 24, i)].append((t, x, y, c))
        self.map = {}; self.prev_n = 0; self.err = 0
        self.harv = collections.defaultdict(list)       # day -> [(t, x, y)]
        if harvest_free:
            for t, i, x, y, c in rec["events"]:
                if c[0] == "HARVEST": self.harv[t // 24].append([t, x, y])
        self.stats = collections.Counter()
    def _bind(self, t, units):
        tp = self.rec["pos"][t] if t < len(self.rec["pos"]) else []
        if t % 24 == 0 or len(units) < self.prev_n: self.map = {}
        self.map[0] = 0
        used = set(self.map.values())
        for i in range(len(units)):
            if i in self.map: continue
            free = [j for j in range(len(tp)) if j not in used]
            cand = [j for j in free if tp[j] == units[i]]
            j = cand[0] if cand else (free[0] if free else i)
            self.map[i] = j; used.add(j)
        self.prev_n = len(units)
    def __call__(self, obs):
        try:
            return self._call(obs)
        except Exception as e:
            self.err += 1
            if self.err <= 2: import traceback; traceback.print_exc()
            return {"farmer": ["PASS"], "hands": [], "market": []}
    def _call(self, obs):
        t = int(obs.get("step", 0)); day = t // 24; p = int(obs.get("player", 0)); f = obs["farms"][p]
        b = self.base(obs)
        units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        self._bind(t, units)
        tiles = f["tiles"]
        # 维护任务池
        pool = {}
        if t % 24 != 0:
            for y, row in enumerate(tiles):
                for x, c in enumerate(row):
                    if not isinstance(c, dict): continue
                    if c.get("kind") == "PLANT":
                        if "WATER" in self.pool_ops and not c.get("watered_today") and ((c.get("consecutive_unwatered") or 0) >= self.water_at or c.get("planted_day") == day):
                            pool[(x, y)] = (["WATER"], 0)
                    elif c.get("animal"):
                        if "COLLECT_FERTILIZER" in self.pool_ops and c.get("fertilizer_available"): pool[(x, y)] = (["COLLECT_FERTILIZER"], self.pen["COLLECT_FERTILIZER"])
                        elif "CARE" in self.pool_ops and not c.get("cared_today"): pool[(x, y)] = (["CARE"], 0 if t % 24 >= self.care_late else self.pen["CARE"])
            if self.hfree:
                keep = []
                for h in self.harv[day]:
                    ht, hx, hy = h; c = tiles[hy][hx]
                    alive = isinstance(c, dict) and (c.get("kind") == "PLANT" or c.get("animal"))
                    if not alive: continue
                    keep.append(h)
                    if t >= ht: pool[(hx, hy)] = (["HARVEST"], self.pen["HARVEST"])   # 收获优先于同格维护
                self.harv[day] = keep
        claimed = set(); cmds = []
        sticky = getattr(self, "sticky", {}); self.sticky = {}
        for i, u in enumerate(units):
            if i in sticky and sticky[i] == u:
                c = tiles[u[1]][u[0]]
                if isinstance(c, dict) and c.get("kind") == "PLANT" and not c.get("watered_today"):
                    cmds.append(["WATER"]); claimed.add(u); self.stats["sticky_water"] += 1; continue
            j = self.map.get(i, i); q = self.q[(day, j)]
            cmd = None
            if q:
                et, x, y, c = q[0]
                if u == (x, y) and t >= et:
                    cmd = list(c); q.popleft(); self.stats["struct"] += 1
                    if c[0] == "PLANT": self.sticky[i] = u
                elif t >= et - dist(u, (x, y)) - self.lead:
                    cmd = step_to(u, (x, y), self.vfirst) if u != (x, y) else ["PASS"]; self.stats["struct_move"] += 1
            if cmd is None:
                cand = [(dist(u, cell) + pool[cell][1], dist(u, cell), cell) for cell in pool if cell not in claimed
                        and (not self.owner or self.own.get((day, cell[0], cell[1]), j) == j)]
                if cand:
                    _, d0, cell = min(cand); claimed.add(cell)
                    if d0 == 0:
                        cmd = list(pool[cell][0]); self.stats["m_" + pool[cell][0][0]] += 1
                        if pool[cell][0][0] == "HARVEST":
                            self.harv[day] = [h for h in self.harv[day] if (h[1], h[2]) != cell]
                    else:
                        cmd = step_to(u, cell, self.vfirst); self.stats["m_move"] += 1
                else:
                    cmd = ["PASS"]; self.stats["idle"] += 1
            cmds.append(cmd)
        return {"farmer": cmds[0], "hands": cmds[1:], "market": [list(x) for x in (b.get("market") or [])]}

class Hybrid:
    def __init__(self, rec, me_spec):
        from sched_f import ExecF
        self.ex = ExecF(rec, 0, "xy", "spawn"); self.base = sp.fidelity.make_agent(me_spec)
    def __call__(self, obs):
        b = self.base(obs); e = self.ex(obs)
        return {"farmer": e["farmer"], "hands": e["hands"], "market": [list(x) for x in (b.get("market") or [])]}

def one(job):
    seed, seat, opp, kind = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_full(me, op_spec, seed, seat)
    ag = Hybrid(rec, me) if kind == "hybrid" else Stage2A(rec, me, **KINDS[kind])
    b0, b1 = play(ag, op_spec, seed, seat)
    return seed, opp, kind, rec["bank"][0], rec["bank"][0]-rec["bank"][1], b0, b0-b1, dict(getattr(ag, "stats", {}))
KINDS = {"2a_浇水照料": {"harvest_free": False, "pool_ops": ("WATER", "CARE")},
         "2a_格子归属": {"harvest_free": False, "pool_ops": ("WATER", "CARE"), "owner": True},
         "2a_格子归属_仅浇水": {"harvest_free": False, "pool_ops": ("WATER",), "owner": True}}
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "smoke":
        print(one((1101, 1, "y68s2", "2a"))); sys.exit()
    ks = ["hybrid"] + list(KINDS)
    jobs = [(s, s % 2, o, k) for s in range(1100, 1106) for o in ("y68s2", "y68r2") for k in ks]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for k in ks:
        v = [r for r in res if r[2] == k]
        st = collections.Counter()
        for r in v: st.update(r[7])
        print(f"{k:12s}: 银行比中位 {statistics.median(r[5]/r[3] for r in v):.1%} 最低 {min(r[5]/r[3] for r in v):.1%} 胜 {sum(r[6]>0 for r in v)}/{len(v)} 分差变化中位 {statistics.median(r[6]-r[4] for r in v):+.0f}  统计(均) {{" + ", ".join(f"{a}:{c//len(v)}" for a, c in st.most_common(9)) + "}")
