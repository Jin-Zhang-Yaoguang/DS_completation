"""V17a：V17 防御层 + 进攻扰动（开局买53卖48抬价，打断跟随型 tape 的资金链）。"""
import importlib.util
from pathlib import Path

_V17 = Path(__file__).resolve().parent / "main.py"
_spec = importlib.util.spec_from_file_location("v17a_base", _V17)
_base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_base)
_base.RESORT_DAY0 = True


def agent(obs, configuration=None):
    act = _base.agent(obs, configuration)
    try:
        day = int(obs.get("day", 0)); hour = int(obs.get("hour", 0)); t = day * 24 + hour
        market = [list(o) for o in (act.get("market") or []) if o]
        if t == 0:
            market.insert(0, ["BUY_PRODUCT", "WHEAT", 53])
        elif t == 1:
            market.insert(0, ["SELL", "WHEAT", 48])
        act["market"] = market[:10]
    except Exception:
        pass
    return act
