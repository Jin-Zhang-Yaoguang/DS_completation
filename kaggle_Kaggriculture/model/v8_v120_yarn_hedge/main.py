"""V8：精确 V120 + 羊毛赌注对冲。
V120 在第 9–11 天追加 4 只羊押注 YARN_STORE；本版在 day >= V8_SKIP_FROM_DAY 且尚未见到
YARN_STORE 时跳过 BUY_ANIMAL SHEEP（其余动作原样，后续 PLACE/FEED/SELL WOOL 自然 no-op）。"""
import importlib.util, os
HERE = os.path.dirname(os.path.abspath(__file__))
V120_PATH = os.path.join(HERE, "..", "v120_hierarchical_top5_distillation", "main.py")
SKIP_FROM = int(os.environ.get("V8_SKIP_FROM_DAY", "9"))

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

_v120 = _load_module("v8_v120_core", V120_PATH)

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
        if day >= SKIP_FROM and "YARN_STORE" not in shops:
            base["market"] = [m for m in (base.get("market") or [])
                              if not (m and m[0] == "BUY_ANIMAL" and len(m) > 1 and m[1] == "SHEEP")]
        return base
    except Exception:
        return base
