"""Majkel 旋钮层生成器:y68d 底盘 + 旋钮 cfg -> 候选包(单文件,末尾显式 _ENTRY)。
所有旋钮默认值 = y68d 原行为(全默认候选与父包逐局相同)。
"""
import json, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
PARENT = HERE / "y68f_parent.py"

# 旋钮空间: name -> (类型, 取值列表或区间, 默认)
SPACE = {
    "beat_phase":   ("cat", [-1, 0, 1, 2, 3], -1),   # ① 奶/毛/莓只在 t%4==phase 小批卖;-1 关
    "beat_from":    ("int", (6, 24), 12),            # ①③ 压单类旋钮的起始日(前期靠当步卖货付款)
    "beat_mode":    ("cat", [0, 1], 0),              # ① 0=推迟(非节拍步删卖单) 1=叠加(不删底盘卖单,节拍步追加卖剩余库存)
    "beat_lot":     ("int", (0, 8), 0),              # ① 节拍步每品卖出下限;0 = 整批卖出(推迟不减量)
    "whole_hour":   ("cat", [-1] + list(range(24)), -1),  # ② 鸡蛋/胡萝卜整仓卖出的小时;-1 关
    "fert_hold":    ("int", (0, 100), 0),            # ③ 肥料价格低于它时不卖;0 关
    "gate":         ("float", (0.9, 1.5), 1.1),      # ④ R68 施肥巡回门槛倍数(y68f 为 1.1)
    "wheat_cap":    ("int", (0, 30), 0),             # ⑤ 空闲工人补种小麦的地块上限;0 关
    "wheat_from":   ("int", (6, 20), 9),             # ⑤ 补种开始日
    "tomato_shops": ("int", (1, 3), 3),              # ⑥ V219 番茄投资所需披萨店+农贸市场数
    "sheep_yarn":   ("int", (1, 3), 2),              # ⑥ V233 羊只投资所需毛线店数
    "clear_day":    ("cat", [0, 25, 26, 27, 28, 29], 0),  # ⑦ 末日清仓起始日;0 关
    "clear_frac":   ("float", (0.1, 1.0), 0.5),      # ⑦ 清仓日每步卖出库存比例
    "feed_buf":     ("int", (0, 3), 0),              # ⑧ 小麦库存 < feed_buf×动物数 时补买;0 关
    "shed_guard":   ("int", (60, 100), 85),          # 压单类旋钮的仓库水位保护:预计库存总量超过它时不压单
    "day1_hire_extra": ("int", (0, 3), 0),           # ⑨ 第1天(step0)在原生雇工基础上追加雇工数;0关(线上镜像战:对手day1多雇2人,后续持续失血34~40k)
    "open_tape":    ("cat", [0, 1], 0),               # ⑩ 强制前6步逐字复刻 Majkel 开局(453局零方差实录);0关=底盘原生开局
    "fert_start_day": ("int", (0, 15), 0),            # ⑪ 施肥起始日硬开关:day<此值时强制不施肥;0关(Majkel d0-9严格0肥,d10起直接进稳态)
    "beat_period":  ("cat", [4, 2], 4),               # ⑫ 节拍卖出周期;Majkel 约d16起呈隔日(周期2)收获/卖出节拍
    "clear_stop_invest": ("cat", [0, 1], 0),          # ⑬ 末日清仓时连带停止种植/施肥/照料/喂养(只留收获与卖出);0关(Majkel d28-29连投入一起停)
}
DEFAULT = {k: v[2] for k, v in SPACE.items()}

LAYER = r'''

# ==================== y72 Majkel 旋钮层(GA/FunSearch 线) ====================
_MJ = __CFG__
_MJ_BASE = agent
_MJ_BEAT = ("MILK", "WOOL", "STRAWBERRY")
_MJ_CLEAR = ("CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL")
_MJ_TAPE = [
    {"farmer": ["PASS"], "hands": [], "market": [["BUY_ANIMAL", "COW", 1], ["BUY_PRODUCT", "WHEAT", 5]]},
    {"farmer": ["PICKUP", "COW", 1], "hands": [], "market": [["SELL", "WHEAT", 1], ["HIRE"], ["HIRE"], ["HIRE"], ["HIRE"], ["BUY_ANIMAL", "COW", 1], ["BUY_ANIMAL", "SHEEP", 3]]},
    {"farmer": ["BUILD_PASTURE"], "hands": [["PICKUP", "SHEEP", 1], ["PICKUP", "SHEEP", 1], ["PICKUP", "COW", 1], ["PICKUP", "SHEEP", 1]], "market": [["SELL", "WHEAT", 1]]},
    {"farmer": ["PLACE", "COW", 1], "hands": [["NORTH"], ["NORTH"], ["NORTH"], ["WEST"]], "market": [["SELL", "WHEAT", 1], ["BUY_PRODUCT", "WHEAT", 1]]},
    {"farmer": ["PICKUP", "WHEAT", 3], "hands": [["WEST"], ["WEST"], ["NORTH"], ["BUILD_PASTURE"]], "market": [["SELL", "WHEAT", 1], ["BUY_PRODUCT", "WHEAT", 1]]},
    {"farmer": ["FEED"], "hands": [["BUILD_PASTURE"], ["WEST"], ["NORTH"], ["PLACE", "SHEEP", 1]], "market": [["BUY_PRODUCT", "WHEAT", 1]]},
]

def _mj_avail(obs, action, item):
    tmp = dict(action); tmp["market"] = [o for o in (action.get("market") or []) if not (o and o[0] == "SELL")]
    try:
        return max(0, int(projected_shed(tmp, FarmView(obs)).get(item, 0)))
    except Exception:
        return max(0, int(((obs.get("private") or {}).get("shed") or {}).get(item, 0)))

def _mj_set_sell(market, item, qty):
    market[:] = [o for o in market if not (o and o[0] == "SELL" and len(o) > 1 and o[1] == item)]
    if qty > 0 and len(market) < 10:
        market.append(["SELL", item, int(qty)])

def _mj_layer(obs, act):
    c = _MJ; step = int(obs["step"]); day = step // 24; hour = step % 24
    if step >= 718:
        return act
    act = copy.deepcopy(act)
    market = [list(o) for o in (act.get("market") or []) if o]
    prices = obs["market"]["prices"]
    farm = obs["farms"][int(obs["player"])]
    priv = obs.get("private") or {}
    # ⑩ 强制前6步逐字复刻 Majkel 开局(453局零方差实录,与对手/地图无关)
    if c["open_tape"] and step < len(_MJ_TAPE):
        tape = _MJ_TAPE[step]
        act["farmer"] = list(tape["farmer"])
        act["hands"] = [list(h) for h in tape["hands"]]
        market = [list(o) for o in tape["market"]]
    # ⑨ 第1天追加雇工(Fibonacci 计价,早期便宜;不移除原生 HIRE,只追加)
    if c["day1_hire_extra"] and step == 0:
        money = float(farm.get("money", 0))
        add = 0
        while add < c["day1_hire_extra"] and len(market) < 10 and money > 200:
            market.append(["HIRE"]); add += 1
    # ⑦ 末日清仓(优先于节拍)
    clearing = c["clear_day"] and day >= c["clear_day"]
    if clearing:
        for item in _MJ_CLEAR:
            have = _mj_avail(obs, act, item)
            planned = sum(int(o[2]) for o in market if o[0] == "SELL" and len(o) > 2 and o[1] == item)
            q = max(planned, int(-(-have * c["clear_frac"] // 1)))
            if q > 0: _mj_set_sell(market, item, min(have, q))
        # ⑬ 连带停止投入(只留收获/移动/卖出)
        if c["clear_stop_invest"]:
            cmds = [act.get("farmer") or ["PASS"], *(act.get("hands") or [])]
            changed = False
            for i, cm in enumerate(cmds):
                if cm and cm[0] in ("PLANT", "FERTILIZE", "CARE", "FEED"):
                    cmds[i] = ["PASS"]; changed = True
            if changed:
                act["farmer"], act["hands"] = cmds[0], cmds[1:]
    # ⑪ 施肥起始日硬开关(在此日之前强制不施肥,替换为 PASS)
    if c["fert_start_day"] and day < c["fert_start_day"]:
        cmds = [act.get("farmer") or ["PASS"], *(act.get("hands") or [])]
        changed = False
        for i, cm in enumerate(cmds):
            if cm and cm[0] == "FERTILIZE":
                cmds[i] = ["PASS"]; changed = True
        if changed:
            act["farmer"], act["hands"] = cmds[0], cmds[1:]
    # ① 节拍卖出
    shed_total = sum(_mj_avail(obs, act, it) for it in PRODUCTS)
    funding = any(o[0] in ("BUY_SEED", "BUY_ANIMAL", "BUY_PRODUCT", "HIRE", "BUY_LAND") for o in market) or float(farm.get("money", 0)) < 3000
    guard_ok = shed_total <= c["shed_guard"] and day >= c["beat_from"] and not funding
    if c["beat_phase"] >= 0 and step >= 72 and not clearing:
        for item in _MJ_BEAT:
            have = _mj_avail(obs, act, item)
            planned = sum(int(o[2]) for o in market if o[0] == "SELL" and len(o) > 2 and o[1] == item)
            if c["beat_mode"] == 1:
                if step % c["beat_period"] == c["beat_phase"] % c["beat_period"] and day >= c["beat_from"] and have > planned:
                    extra = (have - planned) if c["beat_lot"] == 0 else min(have - planned, c["beat_lot"])
                    _mj_set_sell(market, item, planned + extra)
            elif step % c["beat_period"] == c["beat_phase"] % c["beat_period"] or hour == 23:
                q = have if c["beat_lot"] == 0 else min(have, max(planned, c["beat_lot"]))
                _mj_set_sell(market, item, q)
            elif guard_ok:
                _mj_set_sell(market, item, 0)
    # ② 整仓卖出小时
    if c["whole_hour"] >= 0 and hour == c["whole_hour"] and step >= 72:
        for item in ("EGG", "CARROT"):
            _mj_set_sell(market, item, _mj_avail(obs, act, item))
    # ③ 卖肥门槛
    if c["fert_hold"] and guard_ok and hour != 23 and int(prices.get("FERTILIZER", 0)) < c["fert_hold"]:
        _mj_set_sell(market, "FERTILIZER", 0)
    # ⑧ 饲料缓冲
    if c["feed_buf"] and 6 <= day <= 27:
        animals = sum(1 for row in farm["tiles"] for t in row if isinstance(t, dict) and t.get("animal"))
        wheat = int((priv.get("shed") or {}).get("WHEAT", 0))
        need = c["feed_buf"] * animals - wheat
        if need > 0 and len(market) < 10 and not any(o[0] == "BUY_PRODUCT" and o[1] == "WHEAT" for o in market):
            market.append(["BUY_PRODUCT", "WHEAT", int(need)])
    # ⑤ 空闲工人补种/浇水小麦
    if c["wheat_cap"] and c["wheat_from"] <= day <= 25:
        positions = [farm["farmer"], *farm["hands"]]
        cmds = [act.get("farmer") or ["PASS"], *(act.get("hands") or [])]
        wheat_tiles = sum(1 for row in farm["tiles"] for t in row if isinstance(t, dict) and t.get("crop") == "WHEAT")
        seeds = int((priv.get("seeds") or {}).get("WHEAT", 0))
        planting = sum(1 for cm in cmds if cm and cm[:2] == ["PLANT", "WHEAT"])
        changed = False
        for i, cm in enumerate(cmds):
            if i >= len(positions) or cm != ["PASS"]: continue
            x, y = positions[i]; tile = farm["tiles"][y][x]
            if isinstance(tile, dict) and tile.get("crop") == "WHEAT" and not tile.get("watered_today"):
                cmds[i] = ["WATER"]; changed = True
            elif tile is None and wheat_tiles + planting < c["wheat_cap"] and planting < seeds:
                cmds[i] = ["PLANT", "WHEAT"]; planting += 1; changed = True
        if changed:
            act["farmer"], act["hands"] = cmds[0], cmds[1:]
        if seeds < 5 and wheat_tiles < c["wheat_cap"] and len(market) < 10 and not any(o[0] == "BUY_SEED" and o[1] == "WHEAT" for o in market):
            market.append(["BUY_SEED", "WHEAT", 10])
    act["market"] = market[:10]
    return act

def agent(observation, configuration=None):
    act = _MJ_BASE(observation, configuration)
    try:
        return _mj_layer(observation, act)
    except Exception:
        return act

_ENTRY = agent
'''

def full_cfg(cfg):
    out = dict(DEFAULT); out.update(cfg or {}); return out

def build(cfg, out_dir=HERE / "cands"):
    c = full_cfg(cfg)
    src = PARENT.read_text()
    reps = [
        ("if value<1.1*cost+50 or farm['money']<total_cost+cost+3000:break",
         "if value<_MJ['gate']*cost+50 or farm['money']<total_cost+cost+3000:break"),
        ("if sum(s in ('PIZZA_SHOP','FARMERS_MARKET') for s in obs['town']['unlocked_shops']) < 3:",
         "if sum(s in ('PIZZA_SHOP','FARMERS_MARKET') for s in obs['town']['unlocked_shops']) < _MJ['tomato_shops']:"),
        ("if obs['town']['unlocked_shops'].count('YARN_STORE')<2 or prices['WOOL']<220",
         "if obs['town']['unlocked_shops'].count('YARN_STORE')<_MJ['sheep_yarn'] or prices['WOOL']<220"),
    ]
    for old, new in reps:
        assert src.count(old) == 1, old[:60]
        src = src.replace(old, new)
    src += LAYER.replace("__CFG__", json.dumps(c, sort_keys=True))
    h = hashlib.sha1(json.dumps(c, sort_keys=True).encode()).hexdigest()[:10]
    p = Path(out_dir) / f"mj_{h}.py"
    if not p.exists():
        p.write_text(src)
    return p, c

if __name__ == "__main__":
    p, c = build({})
    print(p, c)
