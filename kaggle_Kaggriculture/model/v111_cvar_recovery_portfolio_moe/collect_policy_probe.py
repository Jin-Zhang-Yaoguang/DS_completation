#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures,importlib.util,json,os,statistics,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;MODEL=HERE.parent;CP=MODEL/"community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim";sys.path.insert(0,str(sorted((CP/"build").glob("lib.*"))[-1]));import kagsim
SEEDS=tuple(range(111001,111097));SWITCH=216;POLICIES={"growth":MODEL/"v88_reference_trajectory_state_tube_moe/ablation_main.py","recovery":MODEL/"v88_reference_trajectory_state_tube_moe/main.py"};OPP={"v20":MODEL/"v20_demand_timing_moe/main.py","v21":MODEL/"v21_top_meta_moe/main.py","v32":MODEL/"v32_clone_horizon_preempt/main.py","v54":MODEL/"v54_terminal_water_bypass/main.py","v66":MODEL/"v66_margin_gated_sell_bubble/main.py","v76":MODEL/"v76_adjacent_safe_buy_lead/main.py"}
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
def features(o):
 s=int(o.get("player",0) or 0);farms=o["farms"];own=farms[s];rival=farms[1-s];private=o.get("private",{}) or {};shed=private.get("shed",{}) or {};inv=private.get("inventories",[]) or [];shops=list((o.get("town",{}) or {}).get("unlocked_shops",[]) or [])
 out={"seat":s,"money_gap":int(own.get("money",0) or 0)-int(rival.get("money",0) or 0),"own_money":int(own.get("money",0) or 0),"rival_money":int(rival.get("money",0) or 0),"own_hands":len(own.get("hands",[]) or []),"rival_hands":len(rival.get("hands",[]) or []),"own_quadrants":len(own.get("unlocked_quadrants",[]) or []),"rival_quadrants":len(rival.get("unlocked_quadrants",[]) or []),"shed_units":sum(max(0,int(v or 0)) for v in shed.values()),"carried_units":sum(max(0,int(v or 0)) for x in inv for v in (x or {}).values())}
 for name in ("BAKERY","BRUNCH_SPOT","FARMERS_MARKET","ICE_CREAM_SHOP","PET_CAFE","PIZZA_SHOP","SMOOTHIE_SHOP","YARN_STORE"):out["shop_"+name]=shops.count(name)
 return out
def play(t):
 mode,fam,seed,seat=t;growth=load(POLICIES["growth"],f"v111g{mode}{fam}{seed}{seat}{os.getpid()}");recovery=load(POLICIES["recovery"],f"v111r{mode}{fam}{seed}{seat}{os.getpid()}");rival=load(OPP[fam],f"v111o{mode}{fam}{seed}{seat}{os.getpid()}");g=kagsim.Game(seed);snapshot=None
 while not g.done:
  obs=g.observe(seat);ga=growth.agent(obs);ra=recovery.agent(obs)
  if g.step_count==SWITCH:snapshot=features(obs)
  own=ra if mode=="recovery" and g.step_count>=SWITCH else ga;pair=[None,None];pair[seat]=own;pair[1-seat]=rival.agent(g.observe(1-seat));g.step(pair[0],pair[1])
 a,b=float(g.reward(seat)),float(g.reward(1-seat));margin=a-b;return {"mode":mode,"family":fam,"seed":seed,"seat":seat,"features":snapshot,"margin":margin,"score":1 if margin>0 else .5 if margin==0 else 0,"catastrophic":margin < -10000}
def main():
 tasks=[(m,f,s,t) for m in POLICIES for f in OPP for s in SEEDS for t in (0,1)]
 with concurrent.futures.ProcessPoolExecutor(max_workers=min(16,os.cpu_count() or 1)) as p:rows=list(p.map(play,tasks,chunksize=1))
 out={"schema":"kaggriculture-v111-policy-probe-data-v1","strategy_proof":False,"final_candidate_historical_agent_dependency_forbidden":True,"official_evaluation_sources_consumed":0,"synthetic_seed_range":[min(SEEDS),max(SEEDS)],"games":len(rows),"switch_step":SWITCH,"scores":{m:statistics.mean(r["score"] for r in rows if r["mode"]==m) for m in POLICIES},"catastrophic_rates":{m:statistics.mean(r["catastrophic"] for r in rows if r["mode"]==m) for m in POLICIES},"rows":rows};(HERE/"policy_probe_data.json").write_text(json.dumps(out,indent=2)+"\n");print(json.dumps({k:v for k,v in out.items() if k!="rows"},indent=2))
if __name__=="__main__":main()
