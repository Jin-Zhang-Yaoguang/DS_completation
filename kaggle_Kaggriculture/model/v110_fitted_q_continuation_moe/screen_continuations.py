#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures
from functools import lru_cache
import importlib.util,json,os,statistics,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;MODEL=HERE.parent;PROJECT=MODEL.parent;REP=PROJECT/"model_data/v17_rc1_online_2026-08-27/top5_leaderboard_replays";CP=MODEL/"community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim";sys.path.insert(0,str(sorted((CP/"build").glob("lib.*"))[-1]));import kagsim
BASE=100439801;EXPERTS=(100501596,100398798,100414724,100410172,100458412,100446711,100465032);DAYS=tuple(range(9,29));MODES=("base",)+tuple(f"d{d}_e{e}" for d in DAYS for e in EXPERTS);SEEDS=tuple(range(110101,110109));OPP={"v20":MODEL/"v20_demand_timing_moe/main.py","v76":MODEL/"v76_adjacent_safe_buy_lead/main.py"}
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
@lru_cache(maxsize=None)
def route(e):
 r=json.loads((REP/f"episode-{e}-replay.json").read_text());s=r["info"]["TeamNames"].index("lucaskna");return tuple(x[s].get("action") or {} for x in r["steps"][1:720])
def action(mode,step):
 if mode=="base":return route(BASE)[step]
 left,right=mode.split("_e");return route(int(right))[step] if step>=int(left[1:])*24 else route(BASE)[step]
def norm(a,o):
 s=int(o.get("player",0) or 0);n=len(o["farms"][s].get("hands",[]) or []);h=[list(x or ["PASS"]) for x in a.get("hands",[])];h.extend([["PASS"] for _ in range(max(0,n-len(h)))]);return {"farmer":list(a.get("farmer") or ["PASS"]),"hands":h[:n],"market":[list(x) for x in (a.get("market",[]) or [])[:10]]}
def play(t):
 mode,fam,seed,seat=t;rival=load(OPP[fam],f"v110_{mode}_{fam}_{seed}_{seat}_{os.getpid()}");g=kagsim.Game(seed)
 while not g.done:
  pair=[None,None];pair[seat]=norm(action(mode,g.step_count),g.observe(seat));pair[1-seat]=rival.agent(g.observe(1-seat));g.step(pair[0],pair[1])
 own,opp=float(g.reward(seat)),float(g.reward(1-seat));margin=own-opp;return {"mode":mode,"family":fam,"seed":seed,"seat":seat,"margin":margin,"score":1 if margin>0 else .5 if margin==0 else 0,"catastrophic":margin < -10000}
def main():
 tasks=[(m,f,s,t) for m in MODES for f in OPP for s in SEEDS for t in (0,1)]
 with concurrent.futures.ProcessPoolExecutor(max_workers=min(16,os.cpu_count() or 1)) as p:rows=list(p.map(play,tasks,chunksize=2))
 idx={(r["mode"],r["family"],r["seed"],r["seat"]):r for r in rows};base=[r for r in rows if r["mode"]=="base"];bs=statistics.mean(r["score"] for r in base);bc=statistics.mean(r["catastrophic"] for r in base);stats={}
 for mode in MODES[1:]:
  cur=[];d=[];md=[]
  for f in OPP:
   for s in SEEDS:
    for t in (0,1):
     a=idx[(mode,f,s,t)];b=idx[("base",f,s,t)];cur.append(a);d.append(a["score"]-b["score"]);md.append(a["margin"]-b["margin"])
  cat=statistics.mean(r["catastrophic"] for r in cur);stats[mode]={"score":statistics.mean(r["score"] for r in cur),"uplift_pp":100*statistics.mean(d),"positive_zero_negative":[sum(x>0 for x in d),sum(x==0 for x in d),sum(x<0 for x in d)],"mean_margin_delta":statistics.mean(md),"catastrophic_rate":cat,"catastrophic_delta_pp":100*(cat-bc)}
 qualified=[m for m,v in stats.items() if v["uplift_pp"]>0 and v["positive_zero_negative"][0]>v["positive_zero_negative"][2] and v["catastrophic_delta_pp"]<=1];ranked=sorted(stats,key=lambda m:(stats[m]["uplift_pp"],-stats[m]["catastrophic_delta_pp"],stats[m]["mean_margin_delta"]),reverse=True);out={"schema":"kaggriculture-v110-continuation-screen-v1","status":"PASS_CONTINUATION_QUALIFICATION" if qualified else "REJECT_CONTINUATION_QUALIFICATION","strategy_proof":False,"official_evaluation_sources_consumed":0,"synthetic_seed_range":[min(SEEDS),max(SEEDS)],"games":len(rows),"base_score":bs,"base_catastrophic_rate":bc,"qualified":qualified,"top20":[{"mode":m,**stats[m]} for m in ranked[:20]],"stats":stats,"rows":rows};(HERE/"continuation_screen.json").write_text(json.dumps(out,indent=2)+"\n");print(json.dumps({k:v for k,v in out.items() if k not in {"stats","rows"}},indent=2))
if __name__=="__main__":main()
