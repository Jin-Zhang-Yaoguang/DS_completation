"""Diagnostic-only market category ablations over the recovered role route."""
from __future__ import annotations
import os
os.environ["ROLE_CAUSAL_COMPILER"] = "0"
import role_option_agent as ROLE

STATE={0:{},1:{}}

def agent(obs, configuration=None):
    action=ROLE.agent(obs, configuration)
    mode=os.environ.get("MARKET_ABLATION", "all")
    keep={
        "all":{"SELL","HIRE","BUY_LAND","BUY_SEED","BUY_ANIMAL","BUY_PRODUCT"},
        "fixed":{"HIRE","BUY_LAND","BUY_SEED","BUY_ANIMAL"},
        "sell_fixed":{"SELL","HIRE","BUY_LAND","BUY_SEED","BUY_ANIMAL"},
        "buyproduct_fixed":{"BUY_PRODUCT","HIRE","BUY_LAND","BUY_SEED","BUY_ANIMAL"},
        "sell_product":{"SELL","BUY_PRODUCT"},
    }.get(mode,set())
    action["market"]=[o for o in action.get("market",[]) if o and o[0] in keep]
    seat=1 if int(obs.get("player",0) or 0)==1 else 0
    step=int(obs.get("day",0) or 0)*24+int(obs.get("hour",0) or 0)
    state=STATE[seat]
    if step==0 or step<=int(state.get("last",-1)):state.clear()
    state["last"]=step
    return ROLE._causal_market_compiler(obs,action,step,state)

def model_status():return {"diagnostic_only":True,"market_tape":True,"promotable":False}
