"""参数路由版:t<72 用全局 best_cfg;t=72 读首店热切世界专属 cfg(缺省回落全局)。"""
import json, importlib.util
from pathlib import Path
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sched_core", HERE / "scheduler.py")
_m = importlib.util.module_from_spec(spec); spec.loader.exec_module(_m)

_GLOBAL = json.load(open(HERE / "best_cfg_58k.json"))["cfg"]
_WORLD = {}
for f in HERE.glob("world2_cfg_*.json"):
    _WORLD[f.stem.replace("world2_cfg_", "")] = json.load(open(f))["cfg"]

_S = {}
_ROUTED = {}


def agent(obs, configuration=None):
    seat = obs.get("player", 0)
    t = int(obs.get("day", 0)) * 24 + int(obs.get("hour", 0))
    if t == 0 or seat not in _S:
        _S[seat] = _m.Sched(_m.Cfg(**_GLOBAL))
        _ROUTED[seat] = False
    if not _ROUTED[seat] and t >= 73:
        try:
            shops = (obs.get("town") or {}).get("unlocked_shops") or []
            first = shops[0] if shops else None
            first = first if isinstance(first, str) else (first or {}).get("name")
            if first:
                if first in _WORLD:
                    _S[seat].cfg = _m.Cfg(**_WORLD[first])
                _ROUTED[seat] = True
        except Exception:
            _ROUTED[seat] = True
    try:
        return _S[seat].act(obs)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}
