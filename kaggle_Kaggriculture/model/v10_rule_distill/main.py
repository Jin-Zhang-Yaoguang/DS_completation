"""V10：精确 V120 + 从 top 队 replay 蒸馏的条件规则（只用可观测量，不含任何 episode 标识）。

规则来源：tetsuya / Crop Dusta / MtN 2026-08-25~30 训练集（mine_rules.py），跨队一致：
  R1 羊：第 R1_DAY 天起，若尚未见到 YARN_STORE → 不买羊（top 队无 yarn 时追加羊中位 0–2，有则 5–7）
  R2 牛：第 R2_DAY 天起，若可见奶类商店（PIZZA/ICE_CREAM/SMOOTHIE）≤ R2_MAX → 不买牛（top 队奶店≤1 时追加牛 0，≥2 时 4）
  R3 草莓：第 R3_DAY 天起，若可见草莓商店（BRUNCH/ICE_CREAM/SMOOTHIE/FARMERS）≤ R3_MAX → 草莓种子购买量 ×R3_FRAC
在 tape 执行器上只能"少买"（加买需要重排动作链）；被跳过的购买对应的 PLACE/FEED/PLANT 自然 no-op。
"""
import importlib.util, os
HERE = os.path.dirname(os.path.abspath(__file__))
V120_PATH = os.path.join(HERE, "v120_core.py")
if not os.path.exists(V120_PATH):
    V120_PATH = os.path.join(HERE, "..", "v120_hierarchical_top5_distillation", "main.py")
DAIRY = {"PIZZA_SHOP", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP"}
STRAW = {"BRUNCH_SPOT", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP", "FARMERS_MARKET"}
R1 = os.environ.get("V10_R1", "1") == "1"; R1_DAY = int(os.environ.get("V10_R1_DAY", "10"))
R2 = os.environ.get("V10_R2", "1") == "1"; R2_DAY = int(os.environ.get("V10_R2_DAY", "9")); R2_MAX = int(os.environ.get("V10_R2_MAX", "1"))
R3 = os.environ.get("V10_R3", "0") == "1"; R3_DAY = int(os.environ.get("V10_R3_DAY", "6")); R3_MAX = int(os.environ.get("V10_R3_MAX", "1"))
R3_FRAC = float(os.environ.get("V10_R3_FRAC", "0.5"))

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

_v120 = _load_module("v10_v120_core", V120_PATH)

def agent(obs, configuration=None):
    try:
        base = _v120.agent(obs, configuration)
    except Exception:
        farms = obs.get("farms") or []; player = obs.get("player", 0)
        n = len(farms[player].get("hands") or []) if farms and player < len(farms) else 0
        return {"farmer": ["PASS"], "hands": [["PASS"]] * n, "market": []}
    try:
        day = int(obs.get("day", 0))
        shops = list((obs.get("town") or {}).get("unlocked_shops") or [])
        n_yarn = shops.count("YARN_STORE")
        n_dairy = sum(1 for s in shops if s in DAIRY)
        n_straw = sum(1 for s in shops if s in STRAW)
        out = []
        for m in (base.get("market") or []):
            if not m:
                continue
            op = m[0]
            if op == "BUY_ANIMAL" and len(m) > 1:
                if R1 and m[1] == "SHEEP" and day >= R1_DAY and n_yarn == 0:
                    continue
                if R2 and m[1] == "COW" and day >= R2_DAY and n_dairy <= R2_MAX:
                    continue
            if R3 and op == "BUY_SEED" and len(m) > 2 and m[1] == "STRAWBERRY" and day >= R3_DAY and n_straw <= R3_MAX:
                q = int(int(m[2]) * R3_FRAC)
                if q <= 0:
                    continue
                m = ["BUY_SEED", "STRAWBERRY", q]
            out.append(m)
        base["market"] = out
        return base
    except Exception:
        return base
