"""V14 规则搜索：V10 底盘 + 零额外劳动的计划级变异层（由 V14_PARAMS 指定）。

变异类型（全部只用可观测量：商店、日期、市场价格/库存、自家棚/种子）：
  animal_rules : 购买动物时按 regime 丢弃或换型（COW<->SHEEP，牧场兼容，零劳动）
  seed_rules   : 购买种子时按 regime 丢弃或换作物（之后 PLANT 同步改写，SELL 补单）
  late_swap    : 晚期把 PLANT WHEAT 改成稀缺作物（默认 CARROT），提前一天买种、收后即卖
  hold         : 饱和产品的卖出节流（价格低于 base 的比例时暂缓，仓压/终局释放）
"""
import os, json

_HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else \
    "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v14_rule_search"
_BASE_SRC = open(os.path.join(_HERE, "..", "v10_rule_distill", "dist", "main.py")).read()
_NS = {"__name__": "v14_base"}
exec(compile(_BASE_SRC, "v10_dist_main.py", "exec"), _NS)
_BASE_AGENT = _NS["agent"]

_raw = os.environ.get("V14_PARAMS", "")
if _raw and os.path.exists(_raw):
    P = json.load(open(_raw))
elif _raw:
    P = json.loads(_raw)
else:
    P = {}

DAIRY = ("PIZZA_SHOP", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP")
STRAW = ("ICE_CREAM_SHOP", "SMOOTHIE_SHOP", "BRUNCH_SPOT", "FARMERS_MARKET")
EGGS = ("BAKERY", "BRUNCH_SPOT")
CARROTS = ("PET_CAFE", "FARMERS_MARKET")
TOMATOES = ("PIZZA_SHOP", "FARMERS_MARKET")
BASE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}
SEED_COST = {"WHEAT": 10, "CARROT": 20, "TOMATO": 50, "STRAWBERRY": 100, "MELON": 80}
I0 = 10000
_ST = {}


def _feat(obs):
    shops = list((obs.get("town") or {}).get("unlocked_shops") or [])
    inv = (obs.get("market") or {}).get("inventory") or {}
    return {
        "day": int(obs.get("day", 0) or 0), "hour": int(obs.get("hour", 0) or 0),
        "n_shops": len(shops),
        "yarn": sum(1 for s in shops if s == "YARN_STORE"),
        "dairy": sum(1 for s in shops if s in DAIRY),
        "straw": sum(1 for s in shops if s in STRAW),
        "egg": sum(1 for s in shops if s in EGGS),
        "carrot": sum(1 for s in shops if s in CARROTS),
        "tomato": sum(1 for s in shops if s in TOMATOES),
        "pocket": {k: I0 - int(v) for k, v in inv.items()},
        "prices": dict((obs.get("market") or {}).get("prices") or {}),
    }


def _match(when, f):
    for k, v in (when or {}).items():
        if k.startswith("pocket_"):
            parts = k.split("_"); item, kind = parts[1], parts[2]
            d = f["pocket"].get(item, 0)
            if kind == "min" and d < v: return False
            if kind == "max" and d > v: return False
        elif k.endswith("_max"):
            if f.get(k[:-4], 0) > v: return False
        elif k.endswith("_min"):
            if f.get(k[:-4], 0) < v: return False
        elif k.startswith("pocket_"):
            # pocket_CARROT_min : 市场库存低于 I0 的深度
            parts = k.split("_"); item, kind = parts[1], parts[2]
            d = f["pocket"].get(item, 0)
            if kind == "min" and d < v: return False
            if kind == "max" and d > v: return False
    return True


def agent(obs, configuration=None):
    act = _BASE_AGENT(obs, configuration)
    try:
        return _mutate(obs, act)
    except Exception:
        return act


def _mutate(obs, act):
    f = _feat(obs); day, hour = f["day"], f["hour"]
    seat = int(obs.get("player", 0) or 0)
    st = _ST.setdefault(seat, {"last": -1, "crop_map": {}, "late_on": None})
    turn = day * 24 + hour
    if turn <= st["last"]:
        st.clear(); st.update({"last": -1, "crop_map": {}, "late_on": None})
    st["last"] = turn
    farm = (obs.get("farms") or [{}])[seat] if seat < len(obs.get("farms") or []) else {}
    private = obs.get("private") or {}
    shed = dict(private.get("shed") or {}); seeds = dict(private.get("seeds") or {})
    market = [list(o) for o in (act.get("market") or []) if isinstance(o, list) and o]
    units = [list(act.get("farmer") or ["PASS"])] + [list(h) if h else ["PASS"] for h in (act.get("hands") or [])]

    # 1) 动物规则
    for r in P.get("animal_rules", []):
        if day < r.get("day_from", 0) or day > r.get("day_to", 99) or not _match(r.get("when"), f):
            continue
        out = []
        for o in market:
            if o[0] == "BUY_ANIMAL" and len(o) > 2 and o[1] == r["animal"]:
                a = r.get("act", "drop")
                if a == "drop":
                    continue
                if a.startswith("to_"):
                    o = ["BUY_ANIMAL", a[3:], o[2]]
            out.append(o)
        market = out

    # 2) 种子规则（换作物：之后 PLANT 与 SELL 同步）
    for r in P.get("seed_rules", []):
        if day < r.get("day_from", 0) or day > r.get("day_to", 99) or not _match(r.get("when"), f):
            continue
        out = []
        for o in market:
            if o[0] == "BUY_SEED" and len(o) > 2 and o[1] == r["crop"]:
                a = r.get("act", "drop")
                if a == "drop":
                    continue
                if a.startswith("to_"):
                    st["crop_map"][r["crop"]] = a[3:]
                    o = ["BUY_SEED", a[3:], o[2]]
            out.append(o)
        market = out
    if st["crop_map"]:
        for u in units:
            if u and u[0] == "PLANT" and len(u) > 1 and u[1] in st["crop_map"]:
                u[1] = st["crop_map"][u[1]]
        for src, dst in st["crop_map"].items():
            if shed.get(dst, 0) > 0 and not any(o[0] == "SELL" and len(o) > 1 and o[1] == dst for o in market):
                market.insert(0, ["SELL", dst, int(shed[dst])])

    # 3) 晚期稀缺作物替换
    ls = P.get("late_swap")
    if ls:
        crop = ls.get("crop", "CARROT"); d0, d1 = ls.get("day_from", 24), ls.get("day_to", 27)
        if st["late_on"] is None and day >= d0 - 1:
            st["late_on"] = bool(_match(ls.get("when"), f))
        if st["late_on"]:
            # 提前一天买种
            if day == d0 - 1 and hour == ls.get("buy_hour", 0):
                market.insert(0, ["BUY_SEED", crop, int(ls.get("seeds", 40))])
            if d0 <= day <= d1:
                avail = int(seeds.get(crop, 0)) - sum(1 for u in units if u and u[0] == "PLANT" and len(u) > 1 and u[1] == crop)
                for u in units:
                    if avail <= 0: break
                    if u and u[0] == "PLANT" and len(u) > 1 and u[1] == "WHEAT":
                        u[1] = crop; avail -= 1
            if day >= d0 and shed.get(crop, 0) >= int(ls.get("sell_min", 1)) and not any(o[0] == "SELL" and len(o) > 1 and o[1] == crop for o in market):
                market.insert(0, ["SELL", crop, int(shed[crop])])

    # 3b) 肥料即收即卖（保留少量供 FERTILIZE）
    fa = P.get("fert_asap")
    if fa is not None:
        reserve = int(fa.get("reserve", 4)); have = int(shed.get("FERTILIZER", 0))
        if have > reserve and turn < 716:
            q = have - reserve
            for o in market:
                if o[0] == "SELL" and len(o) > 2 and o[1] == "FERTILIZER":
                    o[2] = max(int(o[2]), q); q = 0; break
            if q > 0 and turn % 4 != 0:   # 避开需求 tick 步（V120 栈另有处理）
                market.insert(0, ["SELL", "FERTILIZER", q])
    # 3c) 末期雇工上限
    hc = P.get("hire_cap") or {}
    if hc and str(day) in hc:
        cap = int(hc[str(day)]); n = int(farm.get("hires_today", 0) or 0); out = []
        for o in market:
            if o[0] == "HIRE":
                if n >= cap: continue
                n += 1
            out.append(o)
        market = out
    # 3d) 末期种子剪枝
    sp = P.get("seed_prune_day")
    if sp is not None and day >= int(sp):
        market = [o for o in market if o[0] != "BUY_SEED"]
    # 4) 卖出节流
    hold = P.get("hold") or {}
    if hold:
        shed_total = sum(shed.values())
        for o in market:
            if o[0] != "SELL" or len(o) < 3 or o[1] not in hold:
                continue
            h = hold[o[1]]
            price = f["prices"].get(o[1], BASE[o[1]])
            if price < h.get("floor_frac", 0.5) * BASE[o[1]] and shed_total < h.get("shed_max", 85) and turn < h.get("release_step", 700):
                keep = int(h.get("keep_frac", 0.0) * int(o[2]))
                o[2] = max(0, keep)
        market = [o for o in market if not (o[0] == "SELL" and len(o) > 2 and int(o[2]) <= 0)]

    act["market"] = market[:10]
    act["farmer"] = units[0]; act["hands"] = units[1:]
    return act
