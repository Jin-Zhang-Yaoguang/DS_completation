"""V15 闭环调度器 v2：每步由观测现算动作（原创，不回放任何 tape）。

- 布局：动物压在棚接入格与其邻环；作物由近到远。
- 任务捆绑：一次到访完成 浇水→收获→补种→浇水 / 喂→照料→收肥→收产品，减少走动。
- 喂养前校验单位随身小麦；饲料按已有动物两天量采购。
- 市场：10 槽预算；SELL 前置；购买计划为跨小时/跨天待办。
"""
import os, json

BS = 10
ACCESS = [(4, 4), (5, 4), (4, 5), (5, 5)]
QUAD_OF = lambda x, y: ("N" if y < 5 else "S") + ("W" if x < 5 else "E")
CROPS = {
    "WHEAT": dict(seed=10, first=2, maxday=4, interval=0, maxy=6, ongoing=False),
    "CARROT": dict(seed=20, first=2, maxday=3, interval=0, maxy=4, ongoing=False),
    "TOMATO": dict(seed=50, first=8, maxday=8, interval=1, maxy=4, ongoing=True),
    "STRAWBERRY": dict(seed=100, first=10, maxday=10, interval=2, maxy=4, ongoing=True),
    "MELON": dict(seed=80, first=10, maxday=12, interval=0, maxy=6, ongoing=False),
}
ANIMALS = {"GOOSE": dict(cost=300, struct="COOP", first=4, interval=1, held=4, product="EGG"),
           "COW": dict(cost=400, struct="PASTURE", first=8, interval=2, held=6, product="MILK"),
           "SHEEP": dict(cost=500, struct="PASTURE", first=6, interval=3, held=6, product="WOOL")}
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]
BASE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}
LAND_PRICES = [1000, 2000, 4000]
FIB = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, 987]

DEFAULT_PLAN = {
    # 雇工数按 V120 路线（fib 累计费用：9 人 88 / 10 人 143 / 11 人 232 / 12 人 376）
    "hands": {0: 5, 1: 4, 2: 4, 3: 5, 4: 4, 5: 5, 6: 8, 7: 8, 8: 10, 9: 9, 10: 11, 11: 11, 12: 9, 13: 10, 14: 10, 15: 11},
    "hands_default": 12,
    # 动物：V120 路线 10 牛 8 羊
    "animals": {0: [["COW", 2], ["SHEEP", 2]], 2: [["COW", 1]], 3: [["COW", 1]], 6: [["COW", 2]], 7: [["COW", 2]],
                8: [["COW", 1], ["SHEEP", 2]], 9: [["COW", 1], ["SHEEP", 1]], 10: [["SHEEP", 2]], 11: [["SHEEP", 1]]},
    "animal_last_day": 16,
    "land": {6: 1, 11: 1},
    "melon_tiles": 12,
    "straw": {5: 4, 6: 8, 7: 4, 8: 4, 9: 4, 11: 9},
    "wheat_tiles": 7, "wheat_tiles_mid": 14, "wheat_tiles_late": 40,
    "animal_cash_reserve": 40,
    "feed_days": 3, "wheat_buy_cap": 80,
    "fert_reserve": 6, "fertilize_crops": ["STRAWBERRY"],
    "harvest_wheat_age": 4,
    "deposit_min": 10,
    "pasture_radius": 3.0, "pasture_reserve": 18,
    "last_plant_day": {"WHEAT": 25, "CARROT": 26, "STRAWBERRY": 16, "MELON": 15, "TOMATO": 18},
}
_raw = os.environ.get("V15_PARAMS", "")
PLAN = json.loads(json.dumps(DEFAULT_PLAN))
if _raw:
    _ov = json.load(open(_raw)) if os.path.exists(_raw) else json.loads(_raw)
    for k, v in _ov.items():
        if isinstance(v, dict) and isinstance(PLAN.get(k), dict):
            d = dict(PLAN[k]); d.update({(int(kk) if str(kk).lstrip("-").isdigit() else kk): vv for kk, vv in v.items()}); PLAN[k] = d
        else:
            PLAN[k] = v
# json 往返把 int 键变成 str，统一回 int
for k in ("hands", "animals", "land", "straw"):
    PLAN[k] = {(int(kk) if str(kk).lstrip("-").isdigit() else kk): vv for kk, vv in PLAN[k].items()}

_S = {}


def _dist(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _step_toward(src, dst):
    dx, dy = dst[0] - src[0], dst[1] - src[1]
    if abs(dx) >= abs(dy) and dx != 0:
        return ["EAST"] if dx > 0 else ["WEST"]
    if dy != 0:
        return ["SOUTH"] if dy > 0 else ["NORTH"]
    if dx != 0:
        return ["EAST"] if dx > 0 else ["WEST"]
    return ["PASS"]


def _nearest_access(pos):
    return min(ACCESS, key=lambda a: _dist(pos, a))


def _layout(unlocked):
    tiles = [(x, y) for y in range(BS) for x in range(BS) if QUAD_OF(x, y) in unlocked]
    key = lambda t: (abs(t[0] - 4.5) + abs(t[1] - 4.5), t[1], t[0])
    tiles.sort(key=key)
    return tiles


def _state(seat, turn):
    st = _S.get(seat)
    if st is None or turn <= st["last"]:
        st = {"last": -1, "task": {}, "day_plan": {}, "pending": None}
        _S[seat] = st
    st["last"] = turn
    return st


class Task:
    __slots__ = ("kind", "target", "ops", "prio", "key", "progress")

    def __init__(self, kind, target, ops, prio, key=None):
        self.kind, self.target, self.ops, self.prio = kind, tuple(target), list(ops), prio
        self.key = key or (kind, self.target); self.progress = 0

    def started(self):
        return self.kind == "place" or self.progress > 0 or any(isinstance(op, tuple) for op in self.ops)


def agent(obs, configuration=None):
    try:
        return _agent(obs)
    except Exception:
        farms = obs.get("farms") or []
        p = int(obs.get("player", 0) or 0)
        n = len(farms[p].get("hands") or []) if farms and p < len(farms) else 0
        return {"farmer": ["PASS"], "hands": [["PASS"]] * n, "market": []}


def _agent(obs):
    seat = int(obs.get("player", 0) or 0)
    day = int(obs.get("day", 0) or 0); hour = int(obs.get("hour", 0) or 0); turn = day * 24 + hour
    farm = obs["farms"][seat]; private = obs.get("private") or {}
    tiles = farm["tiles"]; money = float(farm.get("money") or 0)
    unlocked = list(farm.get("unlocked_quadrants") or ["NW"])
    shed = dict(private.get("shed") or {}); seeds = dict(private.get("seeds") or {})
    invs = [dict(i or {}) for i in (private.get("inventories") or [{}])]
    positions = [tuple(farm["farmer"])] + [tuple(h) for h in (farm.get("hands") or [])]
    n_units = len(positions)
    while len(invs) < n_units: invs.append({})
    prices = dict((obs.get("market") or {}).get("prices") or {})
    st = _state(seat, turn)
    LAST = 29
    ENDGAME = turn >= 24 * 29 + 16

    def T(x, y): return tiles[y][x]
    animal_tiles, plant_tiles, weed_tiles, empty_tiles, struct_empty = [], [], [], [], []
    for y in range(BS):
        for x in range(BS):
            t = tiles[y][x]
            if t == "LOCKED": continue
            if t is None: empty_tiles.append((x, y))
            elif isinstance(t, dict):
                if "animal" in t: animal_tiles.append((x, y))
                elif t.get("kind") == "PLANT": plant_tiles.append((x, y))
                elif t.get("kind") == "WEED": weed_tiles.append((x, y))
                elif t.get("kind") in ("PASTURE", "COOP"): struct_empty.append((x, y))
    n_animals = len(animal_tiles)
    shed_animals = [(a, int(shed.get(a, 0))) for a in ANIMALS if int(shed.get(a, 0)) > 0]
    carried = sum(int(i.get(a, 0)) for i in invs for a in ANIMALS)
    order = _layout(unlocked)
    empty_set = set(empty_tiles)

    # 牧场环 = 已解锁且到棚中心曼哈顿距离 <= 3 的地块（NW 6 / +NE 6 / +SW 6），作物永不占用
    pasture_set = set(animal_tiles) | set(struct_empty)
    for (x, y) in order:
        if abs(x - 4.5) + abs(y - 4.5) <= PLAN.get("pasture_radius", 3.0) and len(pasture_set) < PLAN.get("pasture_reserve", 18):
            pasture_set.add((x, y))
    want_past = max(0, sum(n for _, n in shed_animals) + carried - len(struct_empty))
    build_tiles = []
    for t in order:
        if want_past <= 0: break
        if t in pasture_set and t in empty_set:
            build_tiles.append(t); want_past -= 1
    # 作物地块（按距离排序，排除牧场环）
    crop_cands = [t for t in order if t in empty_set and t not in pasture_set]

    # ---------- 种子预算（本步可用于 PLANT 的种子，供捆绑任务使用） ----------
    seed_budget = {c: int(seeds.get(c, 0)) for c in CROPS}
    lp = PLAN["last_plant_day"]

    crop_count = {c: 0 for c in CROPS}
    for (x, y) in plant_tiles: crop_count[T(x, y)["crop"]] += 1
    straw_cap = sum(int(v) for d, v in PLAN["straw"].items() if int(d) <= day)
    caps = {"MELON": PLAN["melon_tiles"], "STRAWBERRY": straw_cap, "TOMATO": PLAN.get("tomato_cap", 0), "CARROT": PLAN.get("carrot_cap", 0), "WHEAT": 10 ** 6}

    def pick_crop():
        """给一个空地选作物：按配额（含现有植株）依次甜瓜、草莓、番茄、胡萝卜，其余小麦。"""
        for c in ("MELON", "STRAWBERRY", "TOMATO", "CARROT", "WHEAT"):
            if seed_budget.get(c, 0) > 0 and day <= lp[c] and crop_count[c] < caps[c]:
                seed_budget[c] -= 1; crop_count[c] += 1
                return c
        return None

    tasks = []
    unfed_total = 0
    for (x, y) in animal_tiles:
        t = T(x, y); ops = []
        if not t.get("fed_today") and day < LAST: ops.append(["FEED"]); unfed_total += 1
        if not t.get("cared_today") and day < LAST: ops.append(["CARE"])
        if t.get("fertilizer_available"): ops.append(["COLLECT_FERTILIZER"])
        yu = int(t.get("yield_units", 0) or 0); held = ANIMALS[t["animal"]]["held"]
        if yu > 0: ops.append(["HARVEST"])
        if ops:
            if not t.get("fed_today"):
                prio = 0 if int(t.get("consecutive_unfed", 0) or 0) >= 1 else 2
            else:
                prio = 5
            tasks.append(Task("animal", (x, y), ops, prio))
    for (x, y) in plant_tiles:
        t = T(x, y); cd = CROPS[t["crop"]]; age = day - int(t.get("planted_day", day)); ops = []
        yu = int(t.get("yield_units", 0) or 0)
        need_water = (not t.get("watered_today")) and (cd["ongoing"] or age <= cd["maxday"]) and day <= LAST
        if cd["ongoing"]:
            hi = prices.get(t["crop"], BASE[t["crop"]]) >= PLAN.get("eager_price_frac", 0.6) * BASE[t["crop"]]
            ripe = yu >= 2 or (yu >= 1 and (hi or hour >= 18 or day >= LAST - 1))
        else:
            # 达最大产量或到最后可收日即收；浇水在窗口内每天+1，所以先浇再判
            yu_after = yu + (1 if (need_water and (cd["maxday"] + 1) // 2 <= age <= cd["maxday"]) else 0)
            ripe = yu > 0 and (yu_after >= cd["maxy"] or age >= cd["maxday"] or day >= LAST or (age >= cd["maxday"] - 1 and hour >= 21))
            if t["crop"] == "MELON" and age < cd["first"]: ripe = False
            # 甜瓜抢先：第 9 天晚上（age 9, hour>=H）提前收（产量 5），赶在对手第 10 天倾倒前卖
            meh = PLAN.get("melon_early_hour")
            if t["crop"] == "MELON" and meh is not None and age == cd["first"] - 1 and hour >= int(meh) and yu >= 4:
                ripe = True
        if need_water: ops.append(["WATER"])
        want_fert = (cd["ongoing"] and age >= cd["first"] - 2 and int(t.get("fertilized_until_day", -1)) < day
                     and day <= LAST - 2 and t["crop"] in PLAN.get("fertilize_crops", ["STRAWBERRY"]))
        if want_fert: ops.append(["FERTILIZE"])
        if ripe:
            ops.append(["HARVEST"])
            if not cd["ongoing"] and day <= lp["WHEAT"] and not ENDGAME:
                c = pick_crop()
                if c: ops += [["PLANT", c], ["WATER"]]
        if ops:
            urgent = need_water and int(t.get("consecutive_unwatered", 0) or 0) >= 1
            prio = 1 if urgent else (3 if need_water else 4)
            if ripe and yu * BASE[t["crop"]] >= 600: prio = min(prio, 2)   # 高价值成熟品：抢先收卖
            if ENDGAME and ripe: prio = 1
            tasks.append(Task("plant", (x, y), ops, prio))
    for t in build_tiles:
        tasks.append(Task("build", t, [["BUILD_PASTURE"]], 1))
    free_structs = [t for t in struct_empty]
    for a, n in shed_animals:
        for _ in range(n):
            if not free_structs: break
            tgt = free_structs.pop(0)
            tasks.append(Task("place", ACCESS[0], [["PICKUP", a, 1], ("GOTO", tgt), ["PLACE", a]], 1, key=("place", tgt)))
    # 新种植（空地）
    if not ENDGAME:
        for t in crop_cands:
            c = pick_crop()
            if c is None: break
            tasks.append(Task("plant_new", t, [["PLANT", c], ["WATER"]], 3))
    # 除草并补种
    if not ENDGAME:
        for (x, y) in weed_tiles:
            ops = [["DIG"]]
            c = None if (x, y) in pasture_set else pick_crop()
            if c: ops += [["PLANT", c], ["WATER"]]
            tasks.append(Task("dig", (x, y), ops, 4 if c else 6))

    deposit_want = {}
    for u in range(n_units):
        inv = invs[u]
        value = sum(v * BASE.get(k, 0) for k, v in inv.items() if k in PRODUCTS and k not in ("WHEAT", "FERTILIZER"))
        nprod = sum(v for k, v in inv.items() if k in PRODUCTS and k not in ("WHEAT", "FERTILIZER"))
        if nprod <= 0: continue
        acc = _nearest_access(positions[u]); dd = _dist(positions[u], acc)
        if value >= PLAN.get("deposit_value", 600) or ENDGAME or hour >= 21: pr = 2
        elif value >= 250 and dd <= 3: pr = 3
        elif nprod >= PLAN.get("deposit_min", 10): pr = 4
        elif dd == 0: pr = 3
        else: continue
        deposit_want[u] = (pr, acc)
    unfed_total = max(0, unfed_total - sum(int(i.get("WHEAT", 0)) for i in invs))
    # ---------- 粘性任务维护 ----------
    unit_actions = [["PASS"] for _ in range(n_units)]
    task_by_key = {t.key: t for t in tasks}
    for u in list(st["task"].keys()):
        if u >= n_units: st["task"].pop(u, None)
    claimed = set()
    prev_target = {}
    for u in range(n_units):
        cur = st["task"].get(u)
        if cur is None: continue
        if cur.started():
            claimed.add(cur.key); continue
        # 未开始：释放回池，记住目标用于粘性加成
        prev_target[u] = cur.key
        st["task"].pop(u, None)
    # 施肥校验：首 op 为 FERTILIZE 而无肥料 → 去掉该 op
    for u in range(n_units):
        cur = st["task"].get(u)
        if cur is None or not cur.ops or isinstance(cur.ops[0], tuple): continue
        if cur.ops[0][0] == "FERTILIZE" and int(invs[u].get("FERTILIZER", 0)) <= 0:
            cur.ops = [op for op in cur.ops if isinstance(op, tuple) or op[0] != "FERTILIZE"]
            if not cur.ops: st["task"].pop(u, None); claimed.discard(cur.key)
    # 喂养校验：当前任务首个 op 是 FEED 但单位没小麦 → 改道取麦或去掉 FEED
    for u in range(n_units):
        cur = st["task"].get(u)
        if cur is None or not cur.ops or isinstance(cur.ops[0], tuple): continue
        if cur.ops[0][0] == "FEED" and int(invs[u].get("WHEAT", 0)) <= 0:
            if int(shed.get("WHEAT", 0)) > 0:
                k = min(int(shed.get("WHEAT", 0)), 6, max(1, unfed_total))
                acc = _nearest_access(positions[u])
                cur.ops = [["PICKUP", "WHEAT", k], ("GOTO", cur.target)] + cur.ops; cur.target = acc
                shed["WHEAT"] = int(shed.get("WHEAT", 0)) - k; unfed_total = max(0, unfed_total - k)
            else:
                cur.ops = [op for op in cur.ops if isinstance(op, tuple) or op[0] != "FEED"]
                if not cur.ops: st["task"].pop(u, None); claimed.discard(cur.key)
    # 入库：空闲单位（或可被 prio2 入库抢占的单位）直接指派
    for u, (pr, acc) in deposit_want.items():
        cur = st["task"].get(u)
        if cur is None or (pr == 2 and cur.prio >= 4 and not cur.started()):
            if cur is not None: claimed.discard(cur.key)
            st["task"][u] = Task("deposit", acc, [["DROP"]], pr, key=("deposit", u)); claimed.add(("deposit", u))

    # ---------- 角色与分区（每天重算一次；手数变化时也重算） ----------
    roles = st.get("roles")
    n_anim_all = n_animals + sum(n for _, n in shed_animals) + carried
    if roles is None or roles.get("day") != day or roles.get("n") != n_units:
        n_ranch = 0
        if n_anim_all > 0:
            n_ranch = min(n_units, max(1, -(-n_anim_all // PLAN.get("animals_per_ranch", 4))))
        if n_units <= 2: n_ranch = min(n_ranch, 1)
        by_near = sorted(range(n_units), key=lambda u: (_dist(positions[u], _nearest_access(positions[u])), u))
        ranch = set(by_near[:n_ranch])
        field = [u for u in range(n_units) if u not in ranch]
        crop_tiles_all = sorted([tt for tt in order if tt not in pasture_set], key=lambda tt: (tt[1], tt[0] if tt[1] % 2 == 0 else -tt[0]))
        zones = {}
        if field:
            k = len(field); n = len(crop_tiles_all)
            for i, u in enumerate(field):
                lo, hi = (i * n) // k, ((i + 1) * n) // k
                zones[u] = set(crop_tiles_all[lo:hi])
        roles = {"day": day, "n": n_units, "ranch": ranch, "zones": zones}
        st["roles"] = roles
    ranch = roles["ranch"]; zones = roles["zones"]

    def _fix_fert(t, u, pos):
        if not any((not isinstance(op, tuple)) and op[0] == "FERTILIZE" for op in t.ops): return True
        if int(invs[u].get("FERTILIZER", 0)) > 0: return True
        if int(shed.get("FERTILIZER", 0)) > 0 and not any(isinstance(op, tuple) for op in t.ops):
            k = min(int(shed.get("FERTILIZER", 0)), 4)
            acc = _nearest_access(pos)
            t.ops = [["PICKUP", "FERTILIZER", k], ("GOTO", t.target)] + t.ops; t.target = acc
            shed["FERTILIZER"] = int(shed.get("FERTILIZER", 0)) - k; invs[u]["FERTILIZER"] = k
            return True
        t.ops = [op for op in t.ops if isinstance(op, tuple) or op[0] != "FERTILIZE"]
        return bool(t.ops)

    RANCH_KINDS = ("animal", "place", "build")

    remain = {"ranch": 0, "field": 0}
    for tk in tasks:
        if tk.key in claimed or tk.kind == "deposit": continue
        remain["ranch" if tk.kind in RANCH_KINDS else "field"] += 1

    def role_pen(u, tk):
        """动态软角色：本角色还有未领任务时，跨角色罚分大（30）；否则小（2）。"""
        is_r = tk.kind in RANCH_KINDS
        own = (u in ranch) if is_r else (u not in ranch)
        if own or (not ranch) or (not zones): return 0
        mine_left = remain["field"] if (u not in ranch) else remain["ranch"]
        return PLAN.get("role_penalty", 30) if mine_left > 0 else 2

    def eff_dist(u, tk):
        d = _dist(positions[u], tk.target) + role_pen(u, tk)
        if prev_target.get(u) == tk.key: d -= 1
        if tk.ops and not isinstance(tk.ops[0], tuple) and tk.ops[0][0] == "FEED" and int(invs[u].get("WHEAT", 0)) <= 0:
            acc = _nearest_access(positions[u]); d = _dist(positions[u], acc) + 1 + _dist(acc, tk.target)
        if tk.kind not in RANCH_KINDS and u in zones and tk.target not in zones[u]:
            d += PLAN.get("zone_penalty", 6)
        return d

    n_ranch_units = max(1, len(ranch))
    by_prio = {}
    for tk in tasks:
        if tk.key in claimed: continue
        by_prio.setdefault(tk.prio, []).append(tk)
    for prio in sorted(by_prio):
        pool = by_prio[prio]
        while pool:
            cand_units = []
            for u in range(n_units):
                cur = st["task"].get(u)
                if cur is None: cand_units.append((u, 0))
                elif prio <= 2 and cur.prio >= prio + 2 and not cur.started(): cand_units.append((u, 2))
            if not cand_units: break
            best = None
            for tk in pool:
                for u, pen in cand_units:
                    d = eff_dist(u, tk) + pen
                    if best is None or d < best[0]: best = (d, u, tk)
            d, u, tk = best
            if d >= 10 ** 6: break
            pool.remove(tk)
            if tk.kind != "deposit": remain["ranch" if tk.kind in RANCH_KINDS else "field"] -= 1
            if st["task"].get(u) is not None: claimed.discard(st["task"][u].key)
            t = Task(tk.kind, tk.target, tk.ops, tk.prio, key=tk.key)
            if t.ops and not isinstance(t.ops[0], tuple) and t.ops[0][0] == "FEED" and int(invs[u].get("WHEAT", 0)) <= 0:
                if int(shed.get("WHEAT", 0)) > 0:
                    k = min(int(shed.get("WHEAT", 0)), 8, max(1, -(-unfed_total // n_ranch_units)))
                    acc = _nearest_access(positions[u])
                    t.ops = [["PICKUP", "WHEAT", k], ("GOTO", t.target)] + t.ops; t.target = acc
                    shed["WHEAT"] = int(shed.get("WHEAT", 0)) - k; unfed_total = max(0, unfed_total - k)
                    invs[u]["WHEAT"] = k
                else:
                    t.ops = [op for op in t.ops if isinstance(op, tuple) or op[0] != "FEED"]
                    if not t.ops: continue
            if not _fix_fert(t, u, positions[u]): continue
            st["task"][u] = t; claimed.add(t.key)
    # 站在接入格且带货（非小麦/肥料）：先卸货一步再继续
    for u in range(n_units):
        cur = st["task"].get(u)
        if cur is None or cur.kind == "deposit": continue
        inv = invs[u]; nprod = sum(v for k, v in inv.items() if k in PRODUCTS and k not in ("WHEAT", "FERTILIZER"))
        if nprod > 0 and positions[u] in ACCESS and hour < 23 and not (cur.ops and not isinstance(cur.ops[0], tuple) and cur.ops[0][0] in ("PICKUP", "DROP")):
            cur.ops.insert(0, ["DROP"])
    # ---------- 执行 ----------
    for u in range(n_units):
        t = st["task"].get(u)
        if t is None: continue
        pos = positions[u]
        while t.ops and isinstance(t.ops[0], tuple) and pos == t.target:
            t.target = tuple(t.ops.pop(0)[1])
        if pos != t.target:
            unit_actions[u] = _step_toward(pos, t.target); continue
        if not t.ops:
            st["task"].pop(u, None); continue
        op = t.ops.pop(0)
        if isinstance(op, tuple):
            t.target = tuple(op[1]); unit_actions[u] = _step_toward(pos, t.target) if pos != t.target else ["PASS"]; continue
        unit_actions[u] = list(op); t.progress += 1
        if op[0] == "FEED": invs[u]["WHEAT"] = int(invs[u].get("WHEAT", 0)) - 1
        if op[0] == "FERTILIZE": invs[u]["FERTILIZER"] = int(invs[u].get("FERTILIZER", 0)) - 1
        if op[0] == "DROP": invs[u] = {k: v for k, v in invs[u].items() if k == "WHEAT" and False}
        if not t.ops:
            st["task"].pop(u, None)

    market = _market(farm, shed, seeds, invs, money, day, hour, turn, n_animals, shed_animals, carried, plant_tiles, empty_tiles, prices, st, unlocked)
    return {"farmer": unit_actions[0], "hands": unit_actions[1:], "market": market[:10]}


def _market(farm, shed, seeds, invs, money, day, hour, turn, n_animals, shed_animals, carried, plant_tiles, empty_tiles, prices, st, unlocked):
    orders = []
    n_anim_now = n_animals + sum(n for _, n in shed_animals) + carried
    n_anim_soon = n_anim_now + sum(int(n) for _, n in PLAN["animals"].get(day, []))
    pend = st.get("pending")
    if pend is None:
        pend = st["pending"] = {"animals": [], "straw": 0, "land": 0, "melon": PLAN["melon_tiles"]}
    dk = ("plan_added", day)
    if not st["day_plan"].get(dk):
        st["day_plan"][dk] = True
        for a, n in PLAN["animals"].get(day, []): pend["animals"].append([a, int(n)])
        pend["straw"] += int(PLAN["straw"].get(day, 0))
        pend["land"] += int(PLAN["land"].get(day, 0))
    feed_reserve = n_anim_now * PLAN["feed_days"] + 4 if turn < 24 * 29 else 0
    has_straw = any(farm["tiles"][y][x].get("crop") == "STRAWBERRY" for (x, y) in plant_tiles)
    fert_reserve = PLAN["fert_reserve"] if (turn < 24 * 27 and has_straw and day >= 6) else 0
    sells = []
    for item in PRODUCTS:
        q = int(shed.get(item, 0))
        if item == "WHEAT": q -= feed_reserve
        if item == "FERTILIZER": q -= fert_reserve
        if q > 0: sells.append((q * prices.get(item, BASE[item]), ["SELL", item, q]))
    sells.sort(key=lambda s: -s[0])
    max_sell = 10 if turn >= 24 * 29 + 16 else 6
    orders += [o for _, o in sells[:max_sell]]
    cash = money + sum(v * 0.7 for v, _ in sells[:max_sell])
    if turn >= 24 * 29 + 20:
        return orders
    # 饲料
    wheat_have = int(shed.get("WHEAT", 0)) + sum(int(i.get("WHEAT", 0)) for i in invs)
    need_feed = n_anim_soon * PLAN["feed_days"] + 2
    wp = prices.get("WHEAT", 25)
    if n_anim_soon and day <= 27 and wheat_have < n_anim_soon + 2 and wp <= PLAN["wheat_buy_cap"] and len(orders) < 10:
        q = min(need_feed - wheat_have, 24)
        if day == 0: q = max(q, 8)
        if cash >= q * wp:
            orders.insert(0, ["BUY_PRODUCT", "WHEAT", q]); cash -= q * wp
        elif cash >= wp:
            q = int(cash // wp); orders.insert(0, ["BUY_PRODUCT", "WHEAT", q]); cash -= q * wp
    # 雇工
    want_hands = PLAN["hands"].get(day, PLAN["hands_default"])
    if day == 29: want_hands = min(want_hands, 8)
    hired = int(farm.get("hires_today", 0) or 0)
    if hour <= 2 and hired < want_hands:
        n = want_hands - hired; cost = 0; k = 0
        for i in range(n):
            c = FIB[hired + i]
            if cost + c > cash - 3 or len(orders) + k >= 10: break
            cost += c; k += 1
        orders += [["HIRE"]] * k; cash -= cost
    # 土地
    n_extra = len(unlocked) - 1
    if pend["land"] > 0 and n_extra < 3 and len(orders) < 10:
        price = LAND_PRICES[n_extra]
        if cash >= price + 60:
            orders.append(["BUY_LAND"]); cash -= price; pend["land"] -= 1
    # 动物
    if day <= PLAN["animal_last_day"]:
        rest = []
        for a, n in pend["animals"]:
            cost = ANIMALS[a]["cost"] * n
            if cash >= cost + PLAN["animal_cash_reserve"] and len(orders) < 10 and sum(shed.values()) + n < 95:
                orders.append(["BUY_ANIMAL", a, n]); cash -= cost
            else:
                rest.append([a, n])
        pend["animals"] = rest
    else:
        pend["animals"] = []
    # 种子
    lp = PLAN["last_plant_day"]
    if pend["melon"] > 0 and day <= lp["MELON"] and len(orders) < 10:
        n = pend["melon"]; c = 80 * n
        if cash >= c + 10:
            orders.append(["BUY_SEED", "MELON", n]); cash -= c; pend["melon"] = 0
        elif cash >= 170:
            n = int((cash - 10) // 80); orders.append(["BUY_SEED", "MELON", n]); cash -= n * 80; pend["melon"] -= n
    if pend["straw"] > 0 and day <= lp["STRAWBERRY"] and len(orders) < 10:
        n = pend["straw"]; c = 100 * n
        if cash >= c + 10:
            orders.append(["BUY_SEED", "STRAWBERRY", n]); cash -= c; pend["straw"] = 0
        elif cash >= 110:
            n = int((cash - 10) // 100); orders.append(["BUY_SEED", "STRAWBERRY", n]); cash -= n * 100; pend["straw"] -= n
    if day <= lp["WHEAT"] and len(orders) < 10:
        target_wheat = PLAN["wheat_tiles"] if day < 6 else (PLAN["wheat_tiles_mid"] if day < 11 else PLAN["wheat_tiles_late"])
        have_wheat_plants = sum(1 for (x, y) in plant_tiles if farm["tiles"][y][x].get("crop") == "WHEAT")
        n_empty = len(empty_tiles)
        buf = 0 if day < 3 else 6
        want = max(0, min(target_wheat - have_wheat_plants + buf, n_empty + buf) - int(seeds.get("WHEAT", 0)))
        if want >= (1 if day < 3 else 3) and day <= 26:
            c = 10 * want
            if cash >= c + 5:
                orders.append(["BUY_SEED", "WHEAT", want]); cash -= c
            elif cash >= 35:
                n = int((cash - 5) // 10); orders.append(["BUY_SEED", "WHEAT", n]); cash -= n * 10
    return orders
