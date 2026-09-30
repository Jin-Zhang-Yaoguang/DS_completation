"""C 线:混合 agent——农场动作查生成带,市场单由调度器实时计算(适应对战价格)。"""
import json, importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("sched_mod", HERE / "scheduler.py")
_m = importlib.util.module_from_spec(spec); spec.loader.exec_module(_m)

TAPE = json.load(open(HERE / "gen51_s11.json"))["actions"]
_H = {}


def agent(obs, configuration=None):
    seat = obs.get("player", 0)
    day = int(obs.get("day", 0) or 0)
    hour = int(obs.get("hour", 0) or 0)
    t = day * 24 + hour
    if t == 0 or seat not in _H:
        _H[seat] = _m.Sched(_m._best_cfg())
    s = _H[seat]
    a = TAPE[t] if t < len(TAPE) else {}
    farm_part = {"farmer": list(a.get("farmer") or ["PASS"]),
                 "hands": [list(h) for h in (a.get("hands") or [])]}
    try:
        s.parse(obs)
        s.tick = t
        market = s.market_orders() if t >= 72 else [list(o) for o in (a.get("market") or [])]
    except Exception:
        market = [list(o) for o in (a.get("market") or [])]
    return {**farm_part, "market": market}
