"""Diagnostic only: replay one Top20 trajectory to screen teacher experts."""
from __future__ import annotations
import copy,json,os
from pathlib import Path

HERE=Path(__file__).resolve().parent
EPISODE=int(os.environ["TOP20_SCREEN_EPISODE"])
SEAT=int(os.environ["TOP20_SCREEN_SEAT"])
path=next(HERE.joinpath("replay_data").rglob(f"episode-{EPISODE}-replay.json"))
replay=json.loads(path.read_bytes())
ACTIONS=[copy.deepcopy(replay["steps"][step+1][SEAT].get("action") or {}) for step in range(719)]

def agent(obs,configuration=None):
    del configuration
    step=int(obs.get("day",0) or 0)*24+int(obs.get("hour",0) or 0)
    action=copy.deepcopy(ACTIONS[min(max(step,0),718)])
    farm=(obs.get("farms") or [{},{}])[int(obs.get("player",0) or 0)]
    expected=len(farm.get("hands") or [])
    hands=[list(order or ["PASS"]) for order in action.get("hands") or []]
    hands=(hands+[["PASS"]]*expected)[:expected]
    return {"farmer":list(action.get("farmer") or ["PASS"]),"hands":hands,"market":[list(o) for o in action.get("market") or []]}

def model_status():return {"diagnostic_only":True,"tape":True,"promotable":False,"episode":EPISODE,"seat":SEAT}
