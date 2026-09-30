"""V17：V120 底盘 + 开局市场护栏（防御对手开局抬价扰动）。

机制（对 fam_B/C 型"买53卖48"扰动的免疫）：
1. 清单重排：第 0 天的市场单按 [BUY_ANIMAL, HIRE, BUY_SEED, BUY_PRODUCT] 优先级重排，
   贵而关键的动物/雇佣先成交，被价格扰动挤掉的只会是可后补的便宜单。
2. 资产守卫：第 0-2 天每步核对 (牛+羊) 实际持有 vs tape 预期；缺则在市场单前插入补买
   （钱够时），一次最多补 1 只，避免重复补买。
"""
import importlib.util
from pathlib import Path

_V120 = Path(__file__).resolve().parent.parent / "v120_hierarchical_top5_distillation" / "main.py"
_spec = importlib.util.spec_from_file_location("v17_base_v120", _V120)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)

_ORDER = {"BUY_ANIMAL": 0, "HIRE": 1, "BUY_SEED": 2, "BUY_PRODUCT": 3}
RESORT_DAY0 = False   # True: 第 0 天全天重排（进攻版经验最优）；False: 仅开局两步
_EXPECT = {}   # seat -> {"cow": n, "sheep": n}，从 tape 意图累计
_BOUGHT = {}   # seat -> 已补买数量


def _count_animals(obs, seat):
    cows = sheep = 0
    farm = (obs.get("farms") or [])[seat]
    for row in farm.get("tiles") or []:
        for x in row or []:
            if isinstance(x, dict):
                a = x.get("animal")
                if isinstance(a, dict):
                    if a.get("kind") == "COW": cows += 1
                    elif a.get("kind") == "SHEEP": sheep += 1
                elif x.get("kind") == "COW": cows += 1
                elif x.get("kind") == "SHEEP": sheep += 1
    shed = (obs.get("private") or {}).get("shed") or {}
    cows += int(shed.get("COW", 0)); sheep += int(shed.get("SHEEP", 0))
    inv = (obs.get("private") or {}).get("inventories") or []
    for i in inv:
        cows += int(i.get("COW", 0)); sheep += int(i.get("SHEEP", 0))
    return cows, sheep


def agent(obs, configuration=None):
    act = _base.agent(obs, configuration)
    try:
        seat = obs.get("player", 0)
        day = int(obs.get("day", 0)); hour = int(obs.get("hour", 0)); t = day * 24 + hour
        market = [list(o) for o in (act.get("market") or []) if o]
        exp = _EXPECT.setdefault(seat, {"COW": 0, "SHEEP": 0})
        if t == 0:
            exp["COW"] = 0; exp["SHEEP"] = 0; _BOUGHT[seat] = 0
        for o in market:
            if o and o[0] == "BUY_ANIMAL" and len(o) >= 3 and str(o[1]) in exp:
                exp[str(o[1])] += int(o[2])
        # 1) 开局两步：清单重排（稳定排序保持同类原顺序）
        if (t <= 1 or (RESORT_DAY0 and day == 0)) and market:
            market.sort(key=lambda o: _ORDER.get(str(o[0]), 9))
        # 2) 第 0-2 天：资产守卫补买
        if 1 <= day <= 2 and _BOUGHT.get(seat, 0) < 4:
            cows, sheep = _count_animals(obs, seat)
            money = (obs.get("farms") or [])[seat].get("money", 0)
            for kind, have in (("SHEEP", sheep), ("COW", cows)):
                need = exp.get(kind, 0) - have
                if need > 0 and money >= 500 and len(market) < 10:
                    market.insert(0, ["BUY_ANIMAL", kind, 1])
                    _BOUGHT[seat] = _BOUGHT.get(seat, 0) + 1
                    break
        act["market"] = market[:10]
    except Exception:
        pass
    return act
