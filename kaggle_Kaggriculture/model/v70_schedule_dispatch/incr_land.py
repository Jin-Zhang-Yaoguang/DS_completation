"""增量编译试点:step268 买第3块地(东南 x5-9,y5-9),每天加雇 NW 名专职工人做分区状态机(种/浇/收小麦),
增量收获记账并每天卖出;录制执行(ExecF)与带子市场层完全不动。"""
import sys, collections, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE / "proto"))
import sched_proto as sp
from sched_v0d import record_full
from sched_f import ExecF
from perturb import play

SE = [(x, y) for y in range(5, 10) for x in range(5, 10)]
def dist(a, b): return abs(a[0]-b[0]) + abs(a[1]-b[1])
def step_to(u, c):
    x, y = c
    if u[0] != x: return ["EAST"] if x > u[0] else ["WEST"]
    return ["SOUTH"] if y > u[1] else ["NORTH"]

class IncrLand:
    def __init__(self, rec, me_spec, buy_t=268, nw=3, crop=None, seed_cost=10, mature=None, active=True, hire_hour=4, sell_cap=25, plant_until=430):
        self.ex = ExecF(rec, 0, "xy", "spawn"); self.base = sp.fidelity.make_agent(me_spec)
        self.rec = rec; self.buy_t = buy_t; self.nw = nw; self.active = active; self.hire_hour = hire_hour; self.sell_cap = sell_cap; self.plant_until = plant_until
        self.last_hire = {}
        for tt, mkt in enumerate(rec.get("market") or []):
            if any(x and x[0] == "HIRE" for x in mkt): self.last_hire[tt // 24] = tt % 24
        self.MAT = {"MELON": 6, "WHEAT": 3}
        self.bought = False; self.seed_bal = collections.Counter(); self.harv_pend = collections.Counter(); self.prev_inv = {}
        self.todo_hire = 0; self.todo_seed = False; self.todo_sell = False
        self.stats = collections.Counter(); self.err = 0
    def __call__(self, obs):
        try: return self._call(obs)
        except Exception:
            self.err += 1
            if self.err <= 2: import traceback; traceback.print_exc()
            b = self.base(obs); e = self.ex(obs)
            return {"farmer": e["farmer"], "hands": e["hands"], "market": [list(x) for x in (b.get("market") or [])]}
    def _call(self, obs):
        t = int(obs.get("step", 0)); day = t // 24; p = int(obs.get("player", 0)); f = obs["farms"][p]
        b = self.base(obs); e = self.ex(obs)
        mk = [list(x) for x in (b.get("market") or [])]
        cmds = [e["farmer"]] + e["hands"]
        units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        tiles = f["tiles"]; pr = obs.get("private") or {}
        if not self.active or t < self.buy_t - 2:
            return {"farmer": cmds[0], "hands": cmds[1:], "market": mk}
        # 1) 买地
        if not self.bought and t >= self.buy_t and f["money"] >= 4500:
            mk = [["BUY_LAND"]] + mk; self.bought = True; self.stats["buy_t"] = t
        # 2) 每天:雇专职工 + 买种 + 卖增量收获(只在市场单有空位的步插入,上限 10 单/回合)
        if t % 24 == 0:
            self.todo_hire = self.nw if (self.bought and day >= self.buy_t // 24 + 1 and day <= 28) else 0
            self.todo_seed = True; self.todo_sell = True
        room = 10 - len(mk)
        if self.bought and 1 <= t % 24 <= 22 and room > 0:
            nrec0 = len(self.rec["pos"][t]) if t < len(self.rec["pos"]) else 0
            extra0 = [i for i in range(len(units)) if self.ex.map.get(i, i) >= nrec0]
            invs0 = pr.get("inventories") or []
            for cr in ("MELON",):
                if self.harv_pend[cr] <= 0 or room <= 0: continue
                avail = (pr.get("shed") or {}).get(cr, 0) + sum(invs0[i].get(cr, 0) for i in extra0 if i < len(invs0))
                n = min(self.harv_pend[cr], avail, self.sell_cap)
                if n > 0:
                    mk = [["SELL", cr, n]] + mk; self.harv_pend[cr] -= n; self.stats["sold_" + cr] += n; room -= 1
        if self.bought and 0 <= t % 24 <= 9 and room > 0:
            while self.todo_hire > 0 and room > 0 and t % 24 > self.last_hire.get(day, 3):
                mk.append(["HIRE"]); self.todo_hire -= 1; room -= 1; self.stats["hired"] += 1
            if self.todo_seed and room > 0 and day <= 27:
                cr = "MELON"
                empty = sum(1 for (x, y) in SE if tiles[y][x] is None)
                need = max(0, min(25, empty) - self.seed_bal[cr])
                if need > 0 and f["money"] > 3000 and t <= self.plant_until:
                    mk.append(["BUY_SEED", cr, need]); self.seed_bal[cr] += need; self.stats["seed_" + cr] += need
                self.todo_seed = False
        # 3) 专职工人 = 未绑定到录制单位的尾部单位
        nrec = len(self.rec["pos"][t]) if t < len(self.rec["pos"]) else 0
        extra = [i for i in range(len(units)) if self.ex.map.get(i, i) >= nrec]
        # 跟踪专职工人背包里作物增量(收获成功计数)
        invs = pr.get("inventories") or []
        for i in extra:
            for cr in ("MELON", "WHEAT"):
                cur = invs[i].get(cr, 0) if i < len(invs) else 0
                prev = self.prev_inv.get((i, cr), cur)
                if cur > prev: self.harv_pend[cr] += cur - prev; self.stats["harv_" + cr] += cur - prev
                self.prev_inv[(i, cr)] = cur
        if t % 24 == 0: self.prev_inv = {}
        claimed = set()
        for i in extra:
            if t % 24 in (0, 23): break
            u = units[i]; best = None
            for (x, y) in SE:
                if (x, y) in claimed: continue
                c = tiles[y][x]
                if c == "LOCKED": continue
                job = None
                if isinstance(c, dict) and c.get("kind") == "PLANT":
                    mat = self.MAT.get(c.get("crop"), 3)
                    if (c.get("yield_units") or 0) >= mat or (c.get("max_lifespan_step") or 9999) <= t + 3: job = ("HARVEST", 0)
                    elif not c.get("watered_today"): job = ("WATER", 1)
                elif c is None:
                    if self.seed_bal["MELON"] > 0 and t <= self.plant_until: job = ("PLANT", 2)
                if job is None: continue
                key = (job[1], dist(u, (x, y)))
                if best is None or key < best[0]: best = (key, (x, y), job[0])
            if best is None: self.stats["se_idle"] += 1; continue
            _, cell, op = best; claimed.add(cell)
            if u == cell:
                if op == "PLANT":
                    cmds[i] = ["PLANT", "MELON"]; self.seed_bal["MELON"] -= 1
                else: cmds[i] = [op]
                self.stats["se_" + op] += 1
            else:
                cmds[i] = step_to(u, cell); self.stats["se_move"] += 1
        return {"farmer": cmds[0], "hands": cmds[1:], "market": mk}

def one(job):
    seed, seat, opp, kind = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_full(me, op_spec, seed, seat)
    ag = IncrLand(rec, me, active=(kind != "hybrid"))
    b0, b1 = play(ag, op_spec, seed, seat)
    return seed, opp, kind, rec["bank"][0], rec["bank"][0]-rec["bank"][1], b0, b0-b1, dict(ag.stats)
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "smoke":
        r = one((1101, 1, "y68s2", "incr")); print(r[3:7]); print(r[7]); sys.exit()
    ks = ["hybrid", "incr"]
    jobs = [(s, s % 2, o, k) for s in range(1100, 1106) for o in ("y68s2", "y68r2") for k in ks]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    base = {(r[0], r[1]): r[5] for r in res if r[2] == "hybrid"}
    for k in ks:
        v = [r for r in res if r[2] == k]
        st = collections.Counter()
        for r in v: st.update(r[7])
        print(f"{k:7s}: 银行比中位 {statistics.median(r[5]/r[3] for r in v):.1%} 胜 {sum(r[6]>0 for r in v)}/{len(v)} 分差变化中位 {statistics.median(r[6]-r[4] for r in v):+.0f}  {{" + ", ".join(f"{a}:{c//len(v)}" for a, c in st.most_common(8)) + "}")
    inc = [r for r in res if r[2] == "incr"]
    print("逐局净增(incr 银行 - hybrid 银行):", sorted(round(r[5] - base[(r[0], r[1])]) for r in inc))
