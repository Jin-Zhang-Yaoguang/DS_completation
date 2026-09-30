"""方案1编译器 v1:每天开头把维护任务(浇水/照料/收肥)插入每人结构航点的空隙(最小绕路),
结构与背包类任务沿用录制绑定;执行=按序列到格执行+L形寻路,结构任务不许提前。市场单由原带子 agent 现场生成。"""
import sys, collections, statistics
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE / "proto"))
import sched_proto as sp
from sched_v0d import record_full
from perturb import play

MAINT = {"WATER", "CARE", "COLLECT_FERTILIZER"}
def dist(a, b): return abs(a[0]-b[0]) + abs(a[1]-b[1])
def step_to(u, c):
    x, y = c
    if u[0] != x: return ["EAST"] if x > u[0] else ["WEST"]
    return ["SOUTH"] if y > u[1] else ["NORTH"]

class Compile1:
    def __init__(self, rec, me_spec, water_at=1):
        self.rec = rec; self.base = sp.fidelity.make_agent(me_spec); self.water_at = water_at
        self.sq = collections.defaultdict(list)      # (day, j) -> [[t, x, y, cmd], ...] 结构任务
        for t, i, x, y, c in rec["events"]:
            if c[0] not in MAINT: self.sq[(t // 24, i)].append([t, x, y, list(c)])
        self.map = {}; self.prev_n = 0
        self.plan = {}                                # i -> deque of [et|None, cell, cmd]
        self.day_planned = -1; self.stats = collections.Counter(); self.err = 0
    def _bind(self, t, units):
        tp = self.rec["pos"][t] if t < len(self.rec["pos"]) else []
        if t % 24 == 0 or len(units) < self.prev_n: self.map = {}
        self.map[0] = 0; used = set(self.map.values())
        for i in range(len(units)):
            if i in self.map: continue
            free = [j for j in range(len(tp)) if j not in used]
            cand = [j for j in free if tp[j] == units[i]]
            j = cand[0] if cand else (free[0] if free else i)
            self.map[i] = j; used.add(j)
        self.prev_n = len(units)
    def _plan_day(self, t, units, tiles):
        day = t // 24; end = day * 24 + 23
        # 按录制单位 j 建航点序列;起点=该 j 当天在录制中的首个位置与时刻(未出生的用出生点)
        nrec = max((len(self.rec["pos"][tt]) for tt in range(day * 24, min((day + 1) * 24, len(self.rec["pos"])))), default=len(units))
        seqs = {}
        for j in range(max(nrec, len(units))):
            st, pos = t, None
            for tt in range(day * 24 + 1, min((day + 1) * 24, len(self.rec["pos"]))):
                tp = self.rec["pos"][tt]
                if j < len(tp): st, pos = max(t, tt), tp[j]; break
            if pos is None: pos = units[j] if j < len(units) else (4, 4); st = t
            seqs[j] = [[st, pos, None]] + [[e[0], (e[1], e[2]), e[3]] for e in self.sq[(day, j)]]
        segs = {j: [dict(cap=(s[k+1][0] - s[k][0] if k == 0 else s[k+1][0] - s[k][0]) - dist(s[k][1], s[k+1][1]) - 1, ins=[]) for k in range(len(s)-1)] for j, s in seqs.items()}
        tail = {j: dict(start=(s[-1][0] if len(s) > 1 else s[0][0]), pos=s[-1][1], ins=[]) for j, s in seqs.items()}
        # 维护需求(不含今天新种苗:执行层种完原地浇)
        needs = []
        for y, row in enumerate(tiles):
            for x, c in enumerate(row):
                if not isinstance(c, dict): continue
                if c.get("kind") == "PLANT" and not c.get("watered_today"):
                    must = (c.get("consecutive_unwatered") or 0) >= 1
                    needs.append(((x, y), ["WATER"], 1 if must else 3))
                elif c.get("animal"):
                    if not c.get("cared_today"): needs.append(((x, y), ["CARE"], 2))
                    if c.get("fertilizer_available"): needs.append(((x, y), ["COLLECT_FERTILIZER"], 0))
        # 预测:当天结构里对动物格的 FEED → 其后收肥
        fed = {}; placed = {}
        for j2 in range(40):
            for e in self.sq.get((day, j2), []):
                if e[3][0] == "FEED": fed[(e[1], e[2])] = min(fed.get((e[1], e[2]), 9999), e[0])
                if e[3][0] == "PLACE" and len(e[3]) > 1 and e[3][1] in ("COW", "SHEEP", "GOOSE"):
                    placed[(e[1], e[2])] = min(placed.get((e[1], e[2]), 9999), e[0])
        for cell, ft in fed.items():
            c = tiles[cell[1]][cell[0]]
            if not (isinstance(c, dict) and c.get("fertilizer_available")):
                needs.append((cell, ["COLLECT_FERTILIZER", "@", ft + 1], 0))
        for cell, pt in placed.items():
            c = tiles[cell[1]][cell[0]]
            if not (isinstance(c, dict) and c.get("animal")):
                needs.append((cell, ["CARE", "@", pt + 1], 2))
        needs.sort(key=lambda n: n[2])
        for cell, cmd, _prio in needs:
            best = None
            for j, sq2 in seqs.items():
                for k, sg in enumerate(segs[j]):
                    p1 = sg["ins"][-1][0] if sg["ins"] else sq2[k][1]; p2 = sq2[k+1][1]
                    det = dist(p1, cell) + dist(cell, p2) - dist(p1, p2)
                    if det + 1 <= sg["cap"] and (best is None or det < best[0]): best = (det, j, k, None)
            if best is None:  # 尾部:结构结束最早、离得近的人
                for j in seqs:
                    tl = tail[j]
                    eta = tl["start"] + sum(dist(a, b) + 1 for a, b in zip([tl["pos"]] + [x[0] for x in tl["ins"]], [x[0] for x in tl["ins"]] + [cell]))
                    if eta <= end - 1 and (best is None or eta < best[0]): best = (eta, j, None, "tail")
            if best is None:
                if _prio <= 2:  # 必做:硬塞给尾部最早收工的人
                    j = min(seqs, key=lambda j2: tail[j2]["start"] + len(tail[j2]["ins"]) * 3)
                    tail[j]["ins"].append((cell, cmd)); self.stats["forced_tail"] += 1; self.stats["ins_" + cmd[0]] += 1
                else:
                    self.stats["unassigned"] += 1
                continue
            _, jj, k, mode = best
            if mode == "tail": tail[jj]["ins"].append((cell, cmd))
            else:
                sg = segs[jj][k]; p1 = sg["ins"][-1][0] if sg["ins"] else seqs[jj][k][1]
                sg["cap"] -= dist(p1, cell) + dist(cell, seqs[jj][k+1][1]) - dist(p1, seqs[jj][k+1][1]) + 1
                sg["ins"].append((cell, cmd))
            self.stats["ins_" + cmd[0]] += 1
        # 汇编每单位队列(按录制单位号 j)
        self.plan = {}
        for j, sq2 in seqs.items():
            q = collections.deque()
            for k in range(len(sq2) - 1):
                for cell, cmd in segs[j][k]["ins"]:
                    et2 = cmd[2] if len(cmd) > 2 and cmd[1] == "@" else None
                    q.append([et2, cell, [cmd[0]]])
                q.append([sq2[k+1][0], sq2[k+1][1], sq2[k+1][2]])
            for cell, cmd in tail[j]["ins"]:
                et2 = cmd[2] if len(cmd) > 2 and cmd[1] == "@" else None
                q.append([et2, cell, [cmd[0]]])
            self.plan[j] = q
        self.day_planned = day
    def __call__(self, obs):
        try: return self._call(obs)
        except Exception:
            self.err += 1
            if self.err <= 2: import traceback; traceback.print_exc()
            return {"farmer": ["PASS"], "hands": [], "market": []}
    def _call(self, obs):
        t = int(obs.get("step", 0)); day = t // 24; p = int(obs.get("player", 0)); f = obs["farms"][p]
        b = self.base(obs); tiles = f["tiles"]
        units = [tuple(f["farmer"])] + [tuple(h) for h in f["hands"]]
        self._bind(t, units)
        if day != self.day_planned and t % 24 >= 1: self._plan_day(t, units, tiles)
        cmds = []
        sticky = getattr(self, "sticky", {}); self.sticky = {}
        for i, u in enumerate(units):
            if i in sticky and sticky[i] == u:
                c = tiles[u[1]][u[0]]
                if isinstance(c, dict) and c.get("kind") == "PLANT" and not c.get("watered_today"):
                    cmds.append(["WATER"]); self.stats["sticky_water"] += 1; continue
            q = self.plan.get(self.map.get(i, i))
            cmd = ["PASS"]
            while q:
                et, cell, c = q[0]
                if u == cell:
                    tile = tiles[cell[1]][cell[0]]
                    if c[0] in MAINT and isinstance(tile, dict):
                        stale = ((c[0] == "WATER" and (tile.get("kind") != "PLANT" or tile.get("watered_today")))
                                 or (c[0] == "CARE" and ((not tile.get("animal") and (et is None or t > et + 2)) or tile.get("cared_today")))
                                 or (c[0] == "COLLECT_FERTILIZER" and not tile.get("fertilizer_available") and et is not None and t > et + 2))
                        if stale: q.popleft(); self.stats["skip_" + c[0]] += 1; continue
                        if c[0] == "COLLECT_FERTILIZER" and not tile.get("fertilizer_available"):
                            self.stats["wait_fert"] += 1; cmd = ["PASS"]; break
                    if et is None or t >= et:
                        cmd = list(c); q.popleft(); self.stats["do_" + c[0]] += 1
                        if c[0] == "PLANT": self.sticky[i] = u
                    else: self.stats["wait"] += 1
                    break
                if et is not None and c[0] not in MAINT and dist(u, cell) > 0 and et - t < dist(u, cell):
                    self.stats["late_struct"] += 1
                cmd = step_to(u, cell); self.stats["move"] += 1
                break
            else:
                self.stats["idle"] += 1
            cmds.append(cmd)
        return {"farmer": cmds[0], "hands": cmds[1:], "market": [list(x) for x in (b.get("market") or [])]}

def one(job):
    seed, seat, opp, kind = job
    me = f"sub:{sp.S}/y68x3b13_main.py"; op_spec = f"sub:{sp.S}/{opp}_main.py"
    rec = record_full(me, op_spec, seed, seat)
    if kind == "hybrid":
        from sched_f import ExecF
        class H:
            def __init__(s2): s2.ex = ExecF(rec, 0, "xy", "spawn"); s2.base = sp.fidelity.make_agent(me)
            def __call__(s2, obs):
                b2 = s2.base(obs); e2 = s2.ex(obs)
                return {"farmer": e2["farmer"], "hands": e2["hands"], "market": [list(x) for x in (b2.get("market") or [])]}
        ag = H()
    else: ag = Compile1(rec, me, water_at=0)
    b0, b1 = play(ag, op_spec, seed, seat)
    return seed, opp, kind, rec["bank"][0], rec["bank"][0]-rec["bank"][1], b0, b0-b1, dict(getattr(ag, "stats", {}))
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "smoke":
        r = one((1101, 1, "y68s2", "c1")); print(r[3:7]); print(r[7]); sys.exit()
    ks = ["hybrid", "c1"]
    jobs = [(s, s % 2, o, k) for s in range(1100, 1106) for o in ("y68s2", "y68r2") for k in ks]
    with ProcessPoolExecutor(7) as ex: res = list(ex.map(one, jobs))
    for k in ks:
        v = [r for r in res if r[2] == k]
        st = collections.Counter()
        for r in v: st.update(r[7])
        print(f"{k:8s}: 银行比中位 {statistics.median(r[5]/r[3] for r in v):.1%} 最低 {min(r[5]/r[3] for r in v):.1%} 胜 {sum(r[6]>0 for r in v)}/{len(v)} 分差变化中位 {statistics.median(r[6]-r[4] for r in v):+.0f}  {{" + ", ".join(f"{a}:{c//len(v)}" for a, c in st.most_common(10)) + "}")
