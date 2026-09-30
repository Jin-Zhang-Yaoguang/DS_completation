"""V29：V26-a30 + 商店条件适应层（R1 无yarn跳羊移植 + R3 胡萝卜店转产）。"""
from pathlib import Path
HERE = Path(__file__).resolve().parent
BASE = (HERE.parent / "v26_f_base" / "variant_a30.py").read_text()

EXTRA = '''

# ==================== V29 adaptive layer (appended) ====================
_V29_R3_DAILY_CAP = 5     # 每天最多把 5 次种麦换成种胡萝卜
_V29_R3_FROM, _V29_R3_TO = 6, 24
_V29_STATE = {}


def _v29_layer(obs, act, seat):
    day = int(obs.get("day", 0)); hour = int(obs.get("hour", 0)); t = day * 24 + hour
    st = _V29_STATE.setdefault(seat, {"last": -1, "carrot_swapped": {}})
    if t <= st["last"]: st.clear(); st.update({"last": -1, "carrot_swapped": {}})
    st["last"] = t
    town = (obs.get("town") or {}).get("unlocked_shops") or []
    n_yarn = sum(1 for s in town if s == "YARN_STORE")
    n_pet = sum(1 for s in town if s == "PET_CAFE")
    market = [list(o) for o in (act.get("market") or []) if o]
    # R1: 第 8 天起未见 yarn -> 删买羊单（F 带 d8-11 共 7 只）
    pass
    # R3: 胡萝卜店 >=2 -> 种麦换种胡萝卜（限额）+ 种子单联动
    if n_pet >= 2 and _V29_R3_FROM <= day <= _V29_R3_TO:
        seeds = (obs.get("private") or {}).get("seeds") or {}
        n_car_seed = int(seeds.get("CARROT", 0))
        swapped = st["carrot_swapped"].get(day, 0)
        # 种子单：把 BUY_SEED WHEAT 部分转为 CARROT
        for o in market:
            if o[0] == "BUY_SEED" and len(o) >= 3 and o[1] == "WHEAT" and int(o[2]) >= 2:
                k = min(int(o[2]) - 1, _V29_R3_DAILY_CAP)
                if k > 0:
                    o[2] = int(o[2]) - k
                    market.append(["BUY_SEED", "CARROT", k])
                break
        # 种植动作：PLANT WHEAT -> PLANT CARROT（有种子且未超额度）
        if n_car_seed > 0 and swapped < _V29_R3_DAILY_CAP:
            units = [("farmer", act.get("farmer"))] + [(i, h) for i, h in enumerate(act.get("hands") or [])]
            budget = min(n_car_seed, _V29_R3_DAILY_CAP - swapped)
            for tag, x in units:
                if budget <= 0: break
                if x and len(x) >= 2 and str(x[0]) == "PLANT" and str(x[1]) == "WHEAT":
                    if tag == "farmer": act["farmer"] = ["PLANT", "CARROT"]
                    else: act["hands"][tag] = ["PLANT", "CARROT"]
                    budget -= 1; swapped += 1
            st["carrot_swapped"][day] = swapped
    act["market"] = market[:10]
    return act


_V29_PREV = kaggriculture_agent_v25


def kaggriculture_agent_v29(obs, configuration=None):
    act = _V29_PREV(obs, configuration)
    try:
        act = _v29_layer(obs, act, obs.get("player", 0))
    except Exception:
        pass
    return act
'''
(HERE / "main.py").write_text(BASE + EXTRA)
print("main.py:", len(BASE + EXTRA))
