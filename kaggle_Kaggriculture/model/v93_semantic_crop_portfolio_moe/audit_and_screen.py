#!/usr/bin/env python3
from __future__ import annotations
import concurrent.futures, importlib.util, json, os, statistics
from pathlib import Path

HERE=Path(__file__).resolve().parent; MODEL=HERE.parent
spec=importlib.util.spec_from_file_location('v93base',MODEL/'v88_reference_trajectory_state_tube_moe/audit_and_screen.py'); base=importlib.util.module_from_spec(spec); assert spec and spec.loader; spec.loader.exec_module(base)
base.HERE=HERE; base.POLICIES={'full':HERE/'main.py','ablation':HERE/'ablation_main.py','comparator':MODEL/'v76_adjacent_safe_buy_lead/main.py'}; base.SEEDS=tuple(range(93101,93117))
def play(task): return base.play(task)
def main():
    tasks=[(m,f,s,t) for m in base.POLICIES for f in base.OPPONENTS for s in base.SEEDS for t in (0,1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16,os.cpu_count() or 1)) as pool: rows=list(pool.map(play,tasks,chunksize=1))
    scores={m:statistics.mean(r['score'] for r in rows if r['mode']==m) for m in base.POLICIES}
    families={m:{f:statistics.mean(r['score'] for r in rows if r['mode']==m and r['family']==f) for f in base.OPPONENTS} for m in base.POLICIES}
    full=[r for r in rows if r['mode']=='full']; comp=[r for r in rows if r['mode']=='comparator']
    rerouted_games=sum(int(r.get('stats',{}).get('rerouted_plants',0))>0 for r in full); rerouted=sum(int(r.get('stats',{}).get('rerouted_plants',0)) for r in full)
    expert_games={}; expert_calls={}
    for row in full:
        for e,n in (row.get('stats',{}).get('experts',{}) or {}).items(): expert_calls[e]=expert_calls.get(e,0)+int(n); expert_games[e]=expert_games.get(e,0)+int(int(n)>0)
    fa=base.paired(rows,'full','ablation'); fc=base.paired(rows,'full','comparator'); arch=base.static_audit()
    ccat=statistics.mean(r['margin'] < -10000 for r in full); pcat=statistics.mean(r['margin'] < -10000 for r in comp); safety=sum(r['violations'] for r in rows); all719=all(r['calls']==719 for r in rows)
    gate=bool(not arch['complete_agent_call_detected'] and all719 and safety==0 and rerouted_games>=8 and fa['uplift_pp']>0 and fa['positive_zero_negative'][0]>fa['positive_zero_negative'][2] and scores['full']>=.60 and families['full']['v76']>=.50 and 100*(ccat-pcat)<=1)
    payload={'schema':'kaggriculture-v93-preconstruction-audit-v1','engine':str(base.kagsim.ENGINE_VERSION),'official_replay_sources_consumed':0,'synthetic_seed_range':[min(base.SEEDS),max(base.SEEDS)],'games':len(rows),'static_architecture_audit':arch,'score_rate':scores,'score_rate_by_opponent':families,'full_vs_ablation':fa,'full_vs_comparator':fc,'direct_v76_score_rate':families['full']['v76'],'candidate_catastrophic_rate':ccat,'comparator_catastrophic_rate':pcat,'catastrophic_rate_delta_pp':100*(ccat-pcat),'rerouted_crop_games':rerouted_games,'rerouted_plant_actions':rerouted,'expert_game_coverage':expert_games,'expert_call_coverage':expert_calls,'all_719_calls':all719,'safety_violations':safety,'fallback_calls_full':sum(int(r.get('stats',{}).get('fallback',0)) for r in full),'decision':'PASS_PRECONSTRUCTION' if gate else 'REJECT_PRECONSTRUCTION','rows':rows}
    (HERE/'preconstruction_audit_results.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n'); print(json.dumps({k:v for k,v in payload.items() if k!='rows'},ensure_ascii=False,indent=2))
if __name__=='__main__': main()
