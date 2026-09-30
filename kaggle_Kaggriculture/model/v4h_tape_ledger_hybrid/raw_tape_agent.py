"""纯 tape 重放（仅 hands 对齐），作为母体对照。"""
import json, os
_TAPE = None
def _load():
    global _TAPE
    if _TAPE is None:
        here = os.path.dirname(os.path.abspath(__file__))
        _TAPE = json.load(open(os.path.join(here, "tape.json")))
def agent(obs, config=None):
    _load()
    t = obs["day"] * 24 + obs["hour"]
    a = dict(_TAPE[t]) if t < len(_TAPE) else {"farmer": ["PASS"], "hands": [], "market": []}
    n = len(obs["farms"][obs["player"]].get("hands") or [])
    a["hands"] = (list(a.get("hands") or []) + [["PASS"]] * n)[:n]
    return a
