"""V11：V10 + 条件化的小麦→胡萝卜作物替换（规则蒸馏"多买"方向的可执行形式）。

tape 在 14 块地上做纯小麦轮作（3–4 天一轮）。当城镇已解锁胡萝卜买家（PET_CAFE / FARMERS_MARKET）
且 day >= DAY_LO 时，把这些地块上的 PLANT WHEAT 换成 PLANT CARROT：浇水/收割动作与作物无关，
胡萝卜同为 3 天成熟，收成由 tape 自己的周期性 HARVEST 拾取；补种子购买、卖胡萝卜单与饲料保险。
来源：Crop Dusta 规则「有胡萝卜店 → 胡萝卜种子 52 vs 17」（方差削减 0.29）；V120 系只卖 14 个胡萝卜，坑（327/季）几乎空着。
"""
import importlib.util, os
HERE = os.path.dirname(os.path.abspath(__file__))
V10_PATH = os.path.join(HERE, "..", "v10_rule_distill", "dist", "main.py")
DAY_LO = int(os.environ.get("V11_DAY_LO", "11")); DAY_HI = int(os.environ.get("V11_DAY_HI", "25"))
MIN_CARROT_SHOPS = int(os.environ.get("V11_MIN_SHOPS", "1"))
SEED_BATCH = int(os.environ.get("V11_SEED_BATCH", "14"))
WHEAT_FLOOR = int(os.environ.get("V11_WHEAT_FLOOR", "8"))
SELL_MIN = int(os.environ.get("V11_SELL_MIN", "4"))
K_TILES = int(os.environ.get("V11_K", "14"))
CROP = os.environ.get("V11_CROP", "CARROT")
CARROT_SHOPS = ("PET_CAFE", "FARMERS_MARKET")
SUB_TILES = set(list(sorted({(0,6),(0,7),(0,8),(1,7),(1,8),(1,9),(2,8),(2,9),(3,9),(4,9),(0,0),(0,1),(8,0),(9,1)}))[:K_TILES])

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

_v10 = _load_module("v11_v10_core", V10_PATH)
_S = {}

def agent(obs, configuration=None):
    try:
        base = _v10.agent(obs, configuration)
    except Exception:
        farms = obs.get("farms") or []; player = obs.get("player", 0)
        n = len(farms[player].get("hands") or []) if farms and player < len(farms) else 0
        return {"farmer": ["PASS"], "hands": [["PASS"]] * n, "market": []}
    try:
        player = obs.get("player", 0)
        day, hour = int(obs.get("day", 0)), int(obs.get("hour", 0)); turn = day * 24 + hour
        st = _S.get(player)
        if st is None or turn <= st["last"]:
            st = {"last": -1}
            _S[player] = st
        st["last"] = turn
        farm = obs["farms"][player]; priv = obs.get("private") or {}
        seeds = priv.get("seeds") or {}; shed = priv.get("shed") or {}
        shops = list((obs.get("town") or {}).get("unlocked_shops") or [])
        active = DAY_LO <= day <= DAY_HI and (CROP != "CARROT" or sum(1 for s in shops if s in CARROT_SHOPS) >= MIN_CARROT_SHOPS)
        pos = [tuple(farm["farmer"])] + [tuple(p) for p in (farm.get("hands") or [])]
        units = [base.get("farmer") or ["PASS"]] + list(base.get("hands") or [])
        market = [list(m) for m in (base.get("market") or [])]

        if active:
            # 1) 替换：纯小麦地块上的 PLANT WHEAT → PLANT CARROT（受当前种子数限制，防止原子校验整体丢弃）
            tape_carrot = sum(1 for u in units if u and u[0] == "PLANT" and len(u) > 1 and u[1] == CROP)
            avail = seeds.get(CROP, 0) - tape_carrot
            for i, u in enumerate(units):
                if avail <= 0:
                    break
                if i < len(pos) and u and u[0] == "PLANT" and len(u) > 1 and u[1] == "WHEAT" and pos[i] in SUB_TILES:
                    units[i] = ["PLANT", CROP]; avail -= 1
            # 2) 种子补货：保持一批在手
            if seeds.get("CARROT", 0) < SEED_BATCH // 2 and farm["money"] > 3000 and len(market) < 10 \
                    and not any(m[0] == "BUY_SEED" and m[1] == "CARROT" for m in market if len(m) > 1):
                market.append(["BUY_SEED", "CARROT", SEED_BATCH])
        # 3) 卖胡萝卜：shed 有货即分批卖（tape 本身几乎不卖胡萝卜）
        if day >= DAY_LO and shed.get("CARROT", 0) >= SELL_MIN and len(market) < 10 \
                and not any(m[0] == "SELL" and m[1] == "CARROT" for m in market if len(m) > 1):
            market.insert(0, ["SELL", "CARROT", min(12, shed["CARROT"])])
        # 4) 饲料保险
        if day >= DAY_LO and shed.get("WHEAT", 0) < WHEAT_FLOOR and farm["money"] > 2000 and len(market) < 10 \
                and not any(m[0] == "BUY_PRODUCT" and m[1] == "WHEAT" for m in market if len(m) > 1):
            market.append(["BUY_PRODUCT", "WHEAT", 10])

        base["farmer"] = units[0]; base["hands"] = units[1:]; base["market"] = market[:10]
        return base
    except Exception:
        return base
