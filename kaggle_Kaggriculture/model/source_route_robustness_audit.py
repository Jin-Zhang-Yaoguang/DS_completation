#!/usr/bin/env python3
"""Synthetic qualification of high-reward public routes as motor-primitive sources."""
from __future__ import annotations
import concurrent.futures,importlib.util,json,os,statistics,sys
from pathlib import Path
MODEL=Path(__file__).resolve().parent;ROOT=MODEL.parent;REPLAYS=ROOT/'model_data/v17_rc1_online_2026-08-27/top5_leaderboard_replays';CP=MODEL/'community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim';sys.path.insert(0,str(sorted((CP/'build').glob('lib.*'))[-1]));import kagsim
EPISODES=(100414724,100410172,100403354,100453792,100403384,100446681,100458412,100417004)
OPP={'v20':MODEL/'v20_demand_timing_moe/main.py','v21':MODEL/'v21_top_meta_moe/main.py','v32':MODEL/'v32_clone_horizon_preempt/main.py','v54':MODEL/'v54_terminal_water_bypass/main.py','v66':MODEL/'v66_margin_gated_sell_bubble/main.py','v76':MODEL/'v76_adjacent_safe_buy_lead/main.py'};SEEDS=tuple(range(96101,96109))
def replay_path(e):return REPLAYS/f'episode-{e}-replay.json'
def route(e):
 r=json.loads(replay_path(e).read_text());s=r['info']['TeamNames'].index('lucaskna');return [x[s].get('action') or {} for x in r['steps'][1:720]]
def load(p,n):
 s=importlib.util.spec_from_file_location(n,p);m=importlib.util.module_from_spec(s);assert s and s.loader;s.loader.exec_module(m);return m
def play(t):
 e,f,seed,seat=t;a=route(e);r=load(OPP[f],f'rs{e}{f}{seed}{seat}{os.getpid()}');g=kagsim.Game(seed)
 while not g.done:
  x=[None,None];x[seat]=a[g.step_count];x[1-seat]=r.agent(g.observe(1-seat));g.step(*x)
 own,opp=float(g.reward(seat)),float(g.reward(1-seat));m=own-opp;return {'episode':e,'family':f,'seed':seed,'seat':seat,'own':own,'margin':m,'score':1 if m>0 else .5 if m==0 else 0,'catastrophic':m < -10000}
def main():
 tasks=[(e,f,s,t) for e in EPISODES for f in OPP for s in SEEDS for t in (0,1)]
 with concurrent.futures.ProcessPoolExecutor(max_workers=min(16,os.cpu_count() or 1)) as p:rows=list(p.map(play,tasks,chunksize=1))
 stats={}
 for e in EPISODES:
  z=[r for r in rows if r['episode']==e];stats[str(e)]={'games':len(z),'panel_score_rate':statistics.mean(r['score'] for r in z),'mean_bank':statistics.mean(r['own'] for r in z),'mean_margin':statistics.mean(r['margin'] for r in z),'catastrophic_rate':statistics.mean(r['catastrophic'] for r in z),'direct_v76_score_rate':statistics.mean(r['score'] for r in z if r['family']=='v76')}
 out={'schema':'kaggriculture-public-route-source-robustness-v1','status':'SOURCE_QUALIFICATION_NOT_MODEL_EVIDENCE','official_replay_sources_consumed':0,'synthetic_seed_range':[min(SEEDS),max(SEEDS)],'games':len(rows),'episodes':list(EPISODES),'route_stats':stats,'rows':rows};path=MODEL/'source_route_robustness_audit.json';path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='rows'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
