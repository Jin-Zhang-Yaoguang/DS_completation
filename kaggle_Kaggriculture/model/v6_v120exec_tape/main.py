"""V6：V120 的执行器/市场层 + 可替换的生产骨架 tape。

V120 = _ACTIONS(骨架) → _V19_CORE(执行核) → _v76_adjacent_safe_buy_lead → _v118_reveal_liquidity。
本文件只替换骨架：
  V6_TAPE=v120        用 V120 自带骨架（= V120 本体，镜像对照）
  V6_TAPE=<episode>   用 V5 库 lib/OceanMix.json.gz 里该 episode 的 tape（默认 102549659）
"""
import gzip, importlib.util, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
V120_PATH = os.path.join(HERE, "..", "v120_hierarchical_top5_distillation", "main.py")
LIB_PATH = os.path.join(HERE, "..", "v5_tape_tree_hmoe", "lib", "OceanMix.json.gz")


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_v120 = _load_module("v6_v120_core", V120_PATH)
_MODE = os.environ.get("V6_TAPE", "102549659")

if _MODE == "v120":
    _TAPE = _v120._V120_DISTILLED_ROUTE
else:
    with gzip.open(LIB_PATH, "rt") as fh:
        _games = json.load(fh)["games"]
    _g = next((g for g in _games if str(g.get("ep")) == str(_MODE)), None)
    if _g is None:
        raise RuntimeError(f"episode {_MODE} not in library")
    _TAPE = [{"farmer": a.get("farmer") or ["PASS"], "hands": a.get("hands") or [], "market": a.get("market") or []}
             for a in _g["actions"]][:719]


def agent(obs, configuration=None):
    try:
        _v120._ACTIONS = _TAPE
        step = int(_v120._get(obs, "step", int(_v120._get(obs, "day", 0) or 0) * 24 + int(_v120._get(obs, "hour", 0) or 0)) or 0)
        action = _v120._V19_CORE(obs)
        action = _v120._v76_adjacent_safe_buy_lead(obs, action)
        return _v120._v118_reveal_liquidity(obs, action, step)
    except Exception:
        farms = obs.get("farms") or []
        player = obs.get("player", 0)
        n = len(farms[player].get("hands") or []) if farms and player < len(farms) else 0
        return {"farmer": ["PASS"], "hands": [["PASS"]] * n, "market": []}
