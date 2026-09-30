"""Parallel safety/pool evaluation for the screened multi-day residual."""
from __future__ import annotations

import argparse, json, multiprocessing as mp
from pathlib import Path
import numpy as np
import base_agent, main
from train_ppo import _fixed_opponent


class Residual:
    def __init__(self, days=(12,15,18,20,23,24,28), head=3, value=0):
        self.days=set(int(x) for x in days); self.head=int(head); self.value=int(value); self.macro=main.DEFAULT_MACRO.copy()
    def __call__(self, obs):
        step=int(obs.get('step',0) or 0); day=int(obs.get('day',step//24) or 0); hour=int(obs.get('hour',step%24) or 0)
        if step==0: self.macro=main.DEFAULT_MACRO.copy()
        if hour==0:
            self.macro=main.DEFAULT_MACRO.copy()
            if day in self.days: self.macro[self.head]=self.value
        return main.apply_macro(obs,base_agent.agent(obs),self.macro,step)


def _play(seed, seat, candidate, opponent_name):
    from kaggle_environments import make
    env=make('kaggriculture',configuration={'seed':int(seed)},debug=False); env.reset(2)
    opponent=_fixed_opponent(opponent_name)
    for step in range(719):
        env.state[0].observation.step=step; env.state[1].observation.step=step
        own=candidate(env.state[seat].observation); other=opponent(env.state[1-seat].observation)
        env.step([own,other] if seat==0 else [other,own])
    rewards=[float(s.reward or 0) for s in env.state]; own,other=rewards[seat],rewards[1-seat]
    return {'score':1.0 if own>other else 0.0 if own<other else .5,'margin':own-other,'status':[str(s.status) for s in env.state]}


def _task(payload):
    seed,seat,opp,days=payload
    b=_play(seed,seat,base_agent.agent,opp); c=_play(seed,seat,Residual(days),opp)
    return {'seed':int(seed),'seat':int(seat),'opponent':opp,'baseline':b,'candidate':c,
            'score_uplift':c['score']-b['score'],'margin_uplift':c['margin']-b['margin']}


def run(seed_start,seeds,opponents,workers,output,days):
    tasks=[(int(seed_start)+7919*i,seat,opp,days) for i in range(int(seeds)) for seat in (0,1) for opp in opponents]
    ctx=mp.get_context('spawn')
    with ctx.Pool(processes=int(workers)) as pool: rows=list(pool.imap(_task,tasks,chunksize=1))
    summary={}
    for opp in opponents:
        ss=[r for r in rows if r['opponent']==opp]
        u=np.asarray([r['score_uplift'] for r in ss],dtype=float)
        rng=np.random.default_rng(20260819+sum(map(ord,opp)))
        draws=u[rng.integers(0,len(u),size=(4000,len(u)))].mean(axis=1)
        summary[opp]={'games':len(ss),'baseline_score':float(np.mean([r['baseline']['score'] for r in ss])),
                      'candidate_score':float(np.mean([r['candidate']['score'] for r in ss])),
                      'score_delta':float(u.mean()),'bootstrap_ci95':[float(np.quantile(draws,.025)),float(np.quantile(draws,.975))],
                      'mean_margin_uplift':float(np.mean([r['margin_uplift'] for r in ss])),
                      'errors':sum(r['baseline']['status']!=['DONE','DONE'] or r['candidate']['status']!=['DONE','DONE'] for r in ss)}
    result={'schema':'kaggriculture-ppo-v2-residual-pool-1','seed_start':int(seed_start),'seeds':int(seeds),
            'days':[int(x) for x in days],'opponents':list(opponents),'summary':summary,'rows':rows}
    Path(output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); return result


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--seed-start',type=int,default=99500000); p.add_argument('--seeds',type=int,default=16); p.add_argument('--workers',type=int,default=8); p.add_argument('--opponents',nargs='+',default=['v1','v2','starter','random','forced_low','forced_high']); p.add_argument('--days',nargs='+',type=int,default=[12,15,18,20,23,24,28]); p.add_argument('--output',type=Path,default=Path('evaluation_topdays_pool_16.json')); a=p.parse_args()
    d=run(a.seed_start,a.seeds,a.opponents,a.workers,a.output,a.days); print(json.dumps(d['summary'],ensure_ascii=False,indent=2))
