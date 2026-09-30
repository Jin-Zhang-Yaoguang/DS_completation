"""v55 离线带生成器 MVP:fam_F 前缀(t<72)+ 配方驱动贪心调度器(t>=72)。
只在开发机运行(不受 1s 限制),产物是动作带。
配方参照金牌解剖:高密度施肥(d13-27)、番茄(d12+)/胡萝卜(d24+)轮作、
匀产匀卖小批量、每日雇工、动物链全程维护。
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TAPES = HERE.parent / "v16_online_fidelity" / "tapes"
_FAMF = json.load(open(TAPES / "fam_F_new.json"))["actions"]

DIRS = {"NORTH": (-1, 0), "SOUTH": (1, 0), "EAST": (0, 1), "WEST": (0, -1)}
PREMIUM = {"STRAWBERRY": 1, "MILK": 1, "WOOL": 1, "MELON": 1, "EGG": 1}  # lot 由 cfg.prem_lot 控制
BULK = {"WHEAT": 0, "FERTILIZER": 6, "CARROT": 2, "TOMATO": 2}  # WHEAT 阈值由 cfg 控制
SHED_SPOTS = {(4, 4), (4, 5), (5, 4), (5, 5)}  # 中心 2x2(经验交互点)
BASE_PRICE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250,
              "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}


class Cfg:
    hire_per_day = 12
    fert_lo, fert_hi = 10, 27
    fert_crops = ("STRAWBERRY", "TOMATO")
    feed_reserve = 3
    tomato_from, carrot_from = 12, 23
    plant_stop = 26
    sell_every = 2
    keep_fert = 12
    prem_lot = 5
    wheat_sell_th = 20
    seed_money = 250
    feed_money = 150
    early_hands = 8
    pasture_target = 10
    animal_workers = 2
    fert_workers = 2
    share_wheat = 10
    share_straw = 16
    share_tomato = 8
    share_carrot = 10
    price_floor = 0.0
    coop_target = 3
    build_until = 8
    cow_until = 9
    goose_until = 16
    patrol = 1
    own_opening = 0
    share_melon = 12
    sell_timing = 1

    def __init__(self, **kw):
        for k, v in kw.items():
            setattr(self, k, v)


class Sched:
    def __init__(self, cfg=None):
        self.cfg = cfg or Cfg()
        self.day_hired = -1
        self.tick = 0
        self.ema = {}

    # ---------- 感知 ----------
    def parse(self, obs):
        seat = obs.get("player", 0)
        farm = obs["farms"][seat]
        self.tiles = farm["tiles"]
        self.money = farm.get("money", 0)
        self.pos = [tuple(farm.get("farmer") or (4, 4))] + [tuple(h) for h in (farm.get("hands") or [])]
        priv = obs.get("private") or {}
        self.shed = dict(priv.get("shed") or {})
        self.seeds = dict(priv.get("seeds") or {})
        self.invs = [dict(x or {}) for x in (priv.get("inventories") or [])]
        while len(self.invs) < len(self.pos):
            self.invs.append({})
        self.day = int(obs.get("day", 0))
        self.hour = int(obs.get("hour", 0))
        self.market = obs.get("market") or {}
        self.prices = self.market.get("prices") or {}
        for it, pv in self.prices.items():
            self.ema[it] = pv if it not in self.ema else self.ema[it] * 0.92 + pv * 0.08

    def unlocked(self, x, y):
        t = self.tiles[y][x]
        return t != "LOCKED"

    # ---------- 任务生成 ----------
    def build_tasks(self):
        """返回 [(prio, (r,c), kind, need_carry)] prio 小者优先"""
        tasks = []
        c = self.cfg
        for y in range(10):
            for x in range(10):
                t = self.tiles[y][x]
                if not isinstance(t, dict):
                    continue
                k = t.get("kind")
                if k == "PLANT":
                    crop = t.get("crop")
                    yu = int(t.get("yield_units", 0) or 0)
                    watered = t.get("watered_today")
                    lifespan = int(t.get("max_lifespan_step", 99999) or 99999)
                    once = crop in ("WHEAT", "CARROT", "MELON")
                    if yu > 0 and ((not once) or self.tick >= lifespan - 30):
                        tasks.append((10, (x, y), "HARVEST", None, "farm"))
                    if not watered and self.day <= 28:
                        tasks.append((8, (x, y), "WATER", None, "farm"))
                    if (crop in c.fert_crops and c.fert_lo <= self.day <= c.fert_hi
                            and int(t.get("fertilized_until_day", -1)) < self.day):
                        tasks.append((14, (x, y), "FERTILIZE", "FERTILIZER", "fert"))
                elif k == "WEED":
                    tasks.append((50, (x, y), "DIG", None, "farm"))
                elif k in ("PASTURE", "COOP"):
                    if not t.get("animal"):
                        if k == "COOP":
                            if self.shed.get("GOOSE", 0) > 0:
                                tasks.append((11, (x, y), ("PLACE", "GOOSE"), "GOOSE", "animal"))
                        else:
                            for have in ("COW", "SHEEP"):
                                if self.shed.get(have, 0) > 0:
                                    tasks.append((11, (x, y), ("PLACE", have), have, "animal"))
                                    break
                    if t.get("animal"):
                        if not t.get("fed_today"):
                            pr = 5 if int(t.get("consecutive_unfed", 0) or 0) >= 1 else 15
                            tasks.append((pr, (x, y), "FEED", "WHEAT", "animal"))
                        if not t.get("cared_today"):
                            tasks.append((25, (x, y), "CARE", None, "animal"))
                        if int(t.get("yield_units", 0) or 0) > 0:
                            tasks.append((12, (x, y), "HARVEST", None, "animal"))
                        if t.get("fertilizer_available"):
                            tasks.append((18, (x, y), "COLLECT_FERTILIZER", None, "animal"))
                elif k == "EMPTY" or t == {} or k is None:
                    pass
        # 建栏:牧栏总数低于目标时,取一块空地建
        n_pasture = sum(1 for y in range(10) for x in range(10)
                        if isinstance(self.tiles[y][x], dict) and self.tiles[y][x].get("kind") in ("PASTURE", "COOP"))
        if n_pasture < getattr(c, "pasture_target", 10) and self.day <= getattr(c, "build_until", 8):
            n_coop = sum(1 for y in range(10) for x in range(10)
                         if isinstance(self.tiles[y][x], dict) and self.tiles[y][x].get("kind") == "COOP")
            build = "BUILD_COOP" if n_coop < getattr(c, "coop_target", 3) else "BUILD_PASTURE"
            spots = [(abs(x - 4.5) + abs(y - 4.5), x, y)
                     for y in range(10) for x in range(10)
                     if (self.tiles[y][x] is None or self.tiles[y][x] == "EMPTY") and self.unlocked(x, y)]
            if spots:
                _, x, y = min(spots)
                tasks.append((12, (x, y), build, None, "farm"))
        # 补种:空可用格(种子由 market 常备)
        if self.day <= c.plant_stop:
            crop = self.pick_crop()
            if crop and self.seeds.get(crop, 0) > 0:
                for y in range(10):
                    for x in range(10):
                        t = self.tiles[y][x]
                        empty = (t is None) or (t == "EMPTY") or (isinstance(t, dict) and t.get("kind") in (None, "EMPTY"))
                        if empty and self.unlocked(x, y):
                            tasks.append((13, (x, y), ("PLANT", crop), None, "farm"))
        return tasks

    def pick_crop(self):
        d, c = self.day, self.cfg
        cur = {}
        for y in range(10):
            for x in range(10):
                t = self.tiles[y][x]
                if isinstance(t, dict) and t.get("kind") == "PLANT":
                    cur[t.get("crop")] = cur.get(t.get("crop"), 0) + 1
        # 瓜:开局窗口(d<=2)
        if d <= 2 and cur.get("MELON", 0) < getattr(c, "share_melon", 12):
            return "MELON"
        # 多茬窗口作物绝对优先(早种多收),麦垫底填空
        if d <= 16 and cur.get("STRAWBERRY", 0) < getattr(c, "share_straw", 16):
            return "STRAWBERRY"
        if c.tomato_from <= d <= 22 and cur.get("TOMATO", 0) < getattr(c, "share_tomato", 8):
            return "TOMATO"
        if d >= c.carrot_from and cur.get("CARROT", 0) < getattr(c, "share_carrot", 10):
            return "CARROT"
        if d <= 24 and cur.get("WHEAT", 0) < getattr(c, "share_wheat", 10):
            return "WHEAT"
        return None

    # ---------- 分配与移动 ----------
    ROLE_OF = {}  # ui -> role,动态算

    def role_of(self, ui, n_units):
        if ui == 0:
            return None
        aw = self.cfg.animal_workers
        fw = self.cfg.fert_workers
        if ui <= aw:
            return "animal"
        if ui <= aw + fw and self.day >= self.cfg.fert_lo:
            return "fert"
        return "farm"

    def assign(self, tasks):
        """角色过滤 + 组内贪心 + 动物划区承包。返回 unit -> action"""
        acts = [None] * len(self.pos)
        taken = set()
        n_units = len(self.pos)
        order = sorted(range(len(tasks)), key=lambda i: tasks[i][0])
        aw = max(1, self.cfg.animal_workers)
        animal_cells = sorted((x, y) for y in range(10) for x in range(10)
                              if isinstance(self.tiles[y][x], dict)
                              and self.tiles[y][x].get("kind") in ("PASTURE", "COOP"))
        cell_owner = {}
        if animal_cells:
            per = max(1, (len(animal_cells) + aw - 1) // aw)
            for idx, cell in enumerate(animal_cells):
                cell_owner[cell] = 1 + min(idx // per, aw - 1)  # unit 1..aw
        # 农耕带状承包:x 坐标 % 农耕工人数
        fw = self.cfg.fert_workers
        farm_units = [u for u in range(1, n_units) if self.role_of(u, n_units) == "farm"]
        farm_owner = {}
        if farm_units:
            nf = len(farm_units)
            for y in range(10):
                for x in range(10):
                    farm_owner[(x, y)] = farm_units[min(x * nf // 10, nf - 1)]
        for ui in range(len(self.pos)):
            role = self.role_of(ui, n_units)
            if role == "farm" and getattr(self.cfg, "patrol", 1):
                acts[ui] = self.patrol_act(ui, n_units)
                continue
            best = None
            for ti in order:
                if ti in taken:
                    continue
                prio, (r, c), kind, need, tag = tasks[ti]
                if role is not None and tag != role:
                    continue
                if tag == "animal" and role == "animal" and cell_owner.get((r, c), ui) != ui:
                    continue
                if tag == "farm" and role == "farm" and farm_owner.get((r, c), ui) != ui:
                    continue
                dist = abs(self.pos[ui][0] - r) + abs(self.pos[ui][1] - c)
                # 需要携带物的任务:没带就先去 shed(距离加惩罚)
                carry_pen = 0
                if need and self.invs[ui].get(need, 0) <= 0:
                    if (self.shed.get(need, 0) if need != "WHEAT" else max(self.shed.get(need, 0), 1)) <= 0:
                        continue
                    sd = min(abs(self.pos[ui][0] - sr) + abs(self.pos[ui][1] - sc) for sr, sc in SHED_SPOTS)
                    carry_pen = sd + 1
                score = prio * 100 + dist + carry_pen
                if dist == 0 and carry_pen == 0:
                    score = prio - 10000  # 本格任务零成本,绝对优先
                if best is None or score < best[0]:
                    best = (score, ti, dist, carry_pen)
            if best is None:
                for ti in order:
                    if ti in taken:
                        continue
                    prio, (r, c), kind, need, tag = tasks[ti]
                    if need and self.invs[ui].get(need, 0) <= 0 and self.shed.get(need, 0) <= 0:
                        continue
                    dist = abs(self.pos[ui][0] - r) + abs(self.pos[ui][1] - c)
                    best = (0, ti, dist, 0)
                    break
                if best is None:
                    acts[ui] = ["PASS"]
                    continue
            _, ti, dist, carry_pen = best
            taken.add(ti)
            prio, (r, c), kind, need, tag = tasks[ti]
            if need and self.invs[ui].get(need, 0) <= 0:
                # 先去 shed 取
                acts[ui] = self.goto_or(ui, min(SHED_SPOTS, key=lambda s: abs(self.pos[ui][0]-s[0])+abs(self.pos[ui][1]-s[1])),
                                        ["PICKUP", need, 4])
            elif dist == 0:
                acts[ui] = [kind[0], kind[1]] if isinstance(kind, tuple) else [kind]
            else:
                acts[ui] = self.step_to(ui, (r, c))
        return acts

    def patrol_act(self, ui, n_units):
        """蛇形巡回自己的 x 带:脚下有活干活,否则走蛇形下一格。"""
        farm_units = [u for u in range(1, n_units) if self.role_of(u, n_units) == "farm"]
        if ui not in farm_units:
            return ["PASS"]
        idx = farm_units.index(ui)
        nf = len(farm_units)
        x0 = idx * 10 // nf
        x1 = (idx + 1) * 10 // nf - 1
        x, y = self.pos[ui]
        # 脚下活
        t = self.tiles[y][x]
        day = self.day
        if isinstance(t, dict) and t.get("kind") == "PLANT":
            crop = t.get("crop")
            yu = int(t.get("yield_units", 0) or 0)
            lifespan = int(t.get("max_lifespan_step", 99999) or 99999)
            once = crop in ("WHEAT", "CARROT", "MELON")
            if yu > 0 and ((not once) or self.tick >= lifespan - 30):
                return ["HARVEST"]
            if not t.get("watered_today") and day <= 28:
                return ["WATER"]
        elif (t is None or t == "EMPTY") and self.unlocked(x, y) and day <= self.cfg.plant_stop:
            crop = self.pick_crop()
            if crop and self.seeds.get(crop, 0) > 0:
                return ["PLANT", crop]
        elif isinstance(t, dict) and t.get("kind") == "WEED":
            return ["DIG"]
        # 蛇形下一格(带内)
        if not (x0 <= x <= x1):
            return ["EAST"] if x < x0 else ["WEST"]
        down = (x - x0) % 2 == 0
        ny = y + 1 if down else y - 1
        if 0 <= ny <= 9 and self.unlocked(x, ny if False else x) or True:
            if (down and y < 9) or ((not down) and y > 0):
                # 检查目标格未锁
                ty = y + (1 if down else -1)
                if self.tiles[ty][x] != "LOCKED":
                    return ["SOUTH"] if down else ["NORTH"]
            # 换列
            if x < x1:
                return ["EAST"]
            return ["WEST"] if x > x0 else (["SOUTH"] if y < 9 else ["NORTH"])
        return ["PASS"]

    def goto_or(self, ui, target, action_at):
        if self.pos[ui] == target or (self.pos[ui] in SHED_SPOTS and target in SHED_SPOTS):
            return action_at
        return self.step_to(ui, target)

    def step_to(self, ui, target):
        x0, y0 = self.pos[ui]
        x1, y1 = target
        if abs(x1 - x0) >= abs(y1 - y0):
            return ["EAST"] if x1 > x0 else ["WEST"] if x1 < x0 else ["PASS"]
        return ["SOUTH"] if y1 > y0 else ["NORTH"] if y1 < y0 else ["PASS"]

    # ---------- 市场 ----------
    def market_orders(self):
        c = self.cfg
        orders = []
        if getattr(c, "own_opening", 0) and self.day == 0 and self.hour == 0:
            for _ in range(getattr(c, "open_hire", 7)):
                orders.append(["HIRE"])
            orders.append(["BUY_SEED", "MELON", getattr(c, "share_melon", 12)])
            orders.append(["BUY_ANIMAL", "COW", getattr(c, "open_cows", 2)])
            return orders[:10]
        # 每日雇工:渐进 + 现金守卫(HIRE 当日 Fibonacci 涨价,穷时只雇 1)
        target = c.early_hands if self.day < 6 else (c.hire_per_day if self.day <= 26 else 6)
        have = len(self.pos) - 1
        if have < target and self.day <= 29:
            for _ in range(max(0, min(target - have, 3))):
                orders.append(["HIRE"])
        # 买地扩张
        n_locked = sum(1 for y in range(10) for x in range(10) if self.tiles[y][x] == "LOCKED")
        if (n_locked >= 75 and self.day >= 4) or (n_locked >= 50 and self.day >= 9 and self.money > 2400):
            orders.append(["BUY_LAND"])
        # 买动物:有空栏且富余
        n_empty_pa = sum(1 for y in range(10) for x in range(10)
                         if isinstance(self.tiles[y][x], dict)
                         and self.tiles[y][x].get("kind") == "PASTURE"
                         and not self.tiles[y][x].get("animal"))
        n_empty_co = sum(1 for y in range(10) for x in range(10)
                         if isinstance(self.tiles[y][x], dict)
                         and self.tiles[y][x].get("kind") == "COOP"
                         and not self.tiles[y][x].get("animal"))
        stock_pa = self.shed.get("COW", 0) + self.shed.get("SHEEP", 0)
        stock_co = self.shed.get("GOOSE", 0)
        if n_empty_pa > stock_pa and self.day <= getattr(c, "cow_until", 9):
            kind = "COW" if (self.tick // 24) % 3 != 2 else "SHEEP"
            orders.append(["BUY_ANIMAL", kind, 1])
        if n_empty_co > stock_co and self.day <= getattr(c, "goose_until", 16):
            orders.append(["BUY_ANIMAL", "GOOSE", 1])
        # 饲料
        total_wheat = self.shed.get("WHEAT", 0) + sum(i.get("WHEAT", 0) for i in self.invs)
        n_animals = sum(1 for y in range(10) for x in range(10)
                        if isinstance(self.tiles[y][x], dict) and self.tiles[y][x].get("animal"))
        if total_wheat < n_animals * c.feed_reserve:
            orders.append(["BUY_PRODUCT", "WHEAT", n_animals * c.feed_reserve])
        # 种子补给
        crop = self.pick_crop()
        if crop and self.seeds.get(crop, 0) < 10 and self.day <= c.plant_stop:
            orders.append(["BUY_SEED", crop, 10])
        # 卖出:premium 小批量匀卖(现金紧张时降低门槛加速变现)
        if self.tick % c.sell_every == 0 or self.money < 400:
            for item in PREMIUM:
                lot = c.prem_lot
                pv = self.prices.get(item, 0)
                em = self.ema.get(item, pv)
                if getattr(c, "sell_timing", 1):
                    lot = lot * 2 if pv > em * 1.02 else (max(1, lot // 2) if pv < em * 0.98 else lot)
                q = self.shed.get(item, 0)
                if q >= (1 if self.money < 400 else min(lot, c.prem_lot)):
                    orders.append(["SELL", item, min(q, lot)])
        if self.money < 200:
            for item, q in self.shed.items():
                if q > 0 and item not in ("WHEAT", "COW", "SHEEP", "GOOSE") and item not in PREMIUM:
                    orders.append(["SELL", item, q])
        # 大宗:超阈值即卖(肥料留用 keep_fert)
        for item, th in BULK.items():
            q = self.shed.get(item, 0)
            if item == "WHEAT":
                if self.money < 400:      # 起步期:清仓变现雇人
                    keep = min(n_animals, 4)
                    th = 1
                else:
                    keep = n_animals * c.feed_reserve + 4
                    th = c.wheat_sell_th
            elif item == "FERTILIZER":
                keep = c.keep_fert
            else:
                keep = 0
            if q - keep >= max(th, 1):
                orders.append(["SELL", item, min(q - keep, max(th, 1))])
        return orders[:10]

    # ---------- 主入口 ----------
    def act(self, obs):
        day = int(obs.get("day", 0) or 0)
        hour = int(obs.get("hour", 0) or 0)
        t = day * 24 + hour
        if t < 72 and not getattr(self.cfg, "own_opening", 0):
            a = _FAMF[t]
            return {"farmer": list(a.get("farmer") or ["PASS"]),
                    "hands": [list(h) for h in (a.get("hands") or [])],
                    "market": [list(o) for o in (a.get("market") or [])]}
        self.parse(obs)
        self.tick = t
        tasks = self.build_tasks()
        acts = self.assign(tasks)
        return {"farmer": acts[0] if acts else ["PASS"],
                "hands": acts[1:],
                "market": self.market_orders()}


_S = {}
_BEST = None


def _best_cfg():
    global _BEST
    if _BEST is None:
        try:
            _BEST = Cfg(**json.load(open(HERE / "best_cfg.json"))["cfg"])
        except Exception:
            _BEST = Cfg()
    return _BEST


def agent(obs, configuration=None):
    seat = obs.get("player", 0)
    t = int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))
    if t == 0 or seat not in _S:
        _S[seat] = Sched(_best_cfg())
    try:
        return _S[seat].act(obs)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
