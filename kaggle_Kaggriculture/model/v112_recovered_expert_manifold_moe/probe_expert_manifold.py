#!/usr/bin/env python3
from __future__ import annotations
import base64,concurrent.futures,importlib.util,json,os,statistics,sys,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;MODEL=HERE.parent;PROJECT=MODEL.parent;REP=PROJECT/"model_data/v17_rc1_online_2026-08-27/top5_leaderboard_replays";CP=MODEL/"community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim";sys.path.insert(0,str(sorted((CP/"build").glob("lib.*"))[-1]));import kagsim
BASE=100439801;EXPERTS=(100485613,100439801,100501596,100398798,100414724,100458412,100446711,100465032);SEEDS=tuple(range(112101,112133));SWITCH=216;OPP={"v20":MODEL/"v20_demand_timing_moe/main.py","v76":MODEL/"v76_adjacent_safe_buy_lead/main.py"};GEN=HERE/"generated_probe_experts"
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
def replay(e):return json.loads((REP/f"episode-{e}-replay.json").read_text())
def source(e):
 r=replay(e);s=r["info"]["TeamNames"].index("lucaskna");acts=[x[s].get("action") or {} for x in r["steps"][1:720]];targets=[]
 for step in range(719):
  o=r["steps"][step][s]["observation"];f=o["farms"][s];p=o["private"];targets.append({"money":int(f["money"]),"hands":len(f["hands"]),"quadrants":len(f["unlocked_quadrants"]),"positions":[f["farmer"],*f["hands"]],"seeds":{k:int(v) for k,v in p["seeds"].items()},"shed":{k:int(v) for k,v in p["shed"].items()}})
 return acts,targets
def generate():
 GEN.mkdir(exist_ok=True);ba,bt=source(BASE);template=(MODEL/"v88_reference_trajectory_state_tube_moe/main_template.py").read_text()
 for e in EXPERTS:
  ea,et=source(e);data={"actions":ba[:SWITCH]+ea[SWITCH:],"targets":bt[:SWITCH]+et[SWITCH:]};packed=base64.b85encode(zlib.compress(json.dumps(data,separators=(",",":")).encode(),9)).decode();text=template.replace("__REFERENCE_PAYLOAD__",packed).replace("__MODE__","full").replace("if not _FULL:","if not _FULL or step < 216:",1);compile(text,f"v112-probe-{e}","exec");(GEN/f"expert_{e}.py").write_text(text)
def signature(o):
 s=int(o.get("player",0) or 0);f=o["farms"];shops=tuple((o.get("town",{}) or {}).get("unlocked_shops",[]) or []);return {"shops":shops[:3],"seat":s,"money_gap":int(f[s].get("money",0) or 0)-int(f[1-s].get("money",0) or 0),"own_hands":len(f[s].get("hands",[]) or []),"rival_hands":len(f[1-s].get("hands",[]) or [])}
def play(t):
 e,fam,seed,seat=t;own=load(GEN/f"expert_{e}.py",f"v112e{e}{fam}{seed}{seat}{os.getpid()}");rival=load(OPP[fam],f"v112o{e}{fam}{seed}{seat}{os.getpid()}");g=kagsim.Game(seed);sig=None
 while not g.done:
  if g.step_count==SWITCH:sig=signature(g.observe(seat))
  pair=[None,None];pair[seat]=own.agent(g.observe(seat));pair[1-seat]=rival.agent(g.observe(1-seat));g.step(pair[0],pair[1])
 a,b=float(g.reward(seat)),float(g.reward(1-seat));m=a-b;return {"expert":e,"family":fam,"seed":seed,"seat":seat,"signature":sig,"margin":m,"score":1 if m>0 else .5 if m==0 else 0,"catastrophic":m < -10000}
def distance(a,b):return (sum(x!=y for x,y in zip(a["shops"],b["shops"])),int(a["seat"]!=b["seat"]),abs(a["own_hands"]-b["own_hands"])+abs(a["rival_hands"]-b["rival_hands"]),abs(a["money_gap"]-b["money_gap"]))
def main():
 generate();tasks=[(e,f,s,t) for e in EXPERTS for f in OPP for s in SEEDS for t in (0,1)]
 with concurrent.futures.ProcessPoolExecutor(max_workers=min(16,os.cpu_count() or 1)) as p:rows=list(p.map(play,tasks,chunksize=1))
 idx={(r["expert"],r["family"],r["seed"],r["seat"]):r for r in rows};stats={str(e):{"score":statistics.mean(r["score"] for r in rows if r["expert"]==e),"catastrophic_rate":statistics.mean(r["catastrophic"] for r in rows if r["expert"]==e),"mean_margin":statistics.mean(r["margin"] for r in rows if r["expert"]==e)} for e in EXPERTS};best=max(EXPERTS,key=lambda e:(stats[str(e)]["score"],-stats[str(e)]["catastrophic_rate"],stats[str(e)]["mean_margin"]));selected=[]
 for fam in OPP:
  for seed in SEEDS:
   for seat in (0,1):
    test=idx[(BASE,fam,seed,seat)];train=[s for s in SEEDS if s%4!=seed%4];neigh=[]
    for ts in train:
     for tf in OPP:ref=idx[(BASE,tf,ts,seat)];neigh.append((distance(test["signature"],ref["signature"]),tf,ts))
    near=[(tf,ts) for _,tf,ts in sorted(neigh)[:16]];utility={}
    for e in EXPERTS:
     z=[idx[(e,tf,ts,seat)] for tf,ts in near];utility[e]=(statistics.mean(r["score"] for r in z),-statistics.mean(r["catastrophic"] for r in z),statistics.mean(r["margin"] for r in z))
    chosen=max(EXPERTS,key=lambda e:utility[e]);selected.append((idx[(chosen,fam,seed,seat)],idx[(best,fam,seed,seat)],chosen))
 d=[a["score"]-b["score"] for a,b,_ in selected];sr=statistics.mean(a["score"] for a,_,_ in selected);sc=statistics.mean(a["catastrophic"] for a,_,_ in selected);bs=stats[str(best)]["score"];bc=stats[str(best)]["catastrophic_rate"];counts={str(e):sum(c==e for _,_,c in selected) for e in EXPERTS};gate=sr>bs and sum(x>0 for x in d)>sum(x<0 for x in d) and sc<=bc+.01
 out={"schema":"kaggriculture-v112-expert-manifold-probe-v1","status":"PASS_EXPERT_MANIFOLD_SOURCE_QUALIFICATION" if gate else "REJECT_EXPERT_MANIFOLD_SOURCE_QUALIFICATION","strategy_proof":False,"final_candidate_historical_agent_dependency_forbidden":True,"official_evaluation_sources_consumed":0,"synthetic_seed_range":[min(SEEDS),max(SEEDS)],"games":len(rows),"expert_stats":stats,"best_fixed_expert":best,"router_score":sr,"best_fixed_score":bs,"beu_pp":100*(sr-bs),"positive_zero_negative":[sum(x>0 for x in d),sum(x==0 for x in d),sum(x<0 for x in d)],"router_catastrophic_rate":sc,"best_fixed_catastrophic_rate":bc,"selected_counts":counts,"rows":rows};(HERE/"expert_manifold_probe.json").write_text(json.dumps(out,indent=2)+"\n");print(json.dumps({k:v for k,v in out.items() if k!="rows"},indent=2))
if __name__=="__main__":main()
