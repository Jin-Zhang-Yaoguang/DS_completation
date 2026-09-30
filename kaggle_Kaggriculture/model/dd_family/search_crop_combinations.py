"""Test measured-benefit crop combinations without assuming additive gains."""
from pathlib import Path
import concurrent.futures,contextlib,copy,hashlib,io,json,sys,time
import numpy as np
import evaluate
B=Path(__file__).resolve().parent;D=B/'ddbb';OUT=B/'crop_counterfactuals_ddbb'

def ident(ids):return hashlib.sha256(json.dumps(ids).encode()).hexdigest()[:12] if ids else 'baseline'

def worker(task):
    ids,seed=task
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
    sys.path.insert(0,str(D));import main,contract
    policy=main.Agent();decisions=[]
    def prepare(obs):
        for j in ids:
            job=policy.perennial.data['jobs'][j]
            if obs['step']!=job['purchase_step']:continue
            p=next(p for p in job['alternatives'] if p['crop']!=job['crop']);policy.perennial.selected[j]=p;policy.perennial.stats['chosen']+=1;policy.perennial.stats['species_changes']+=1
            decisions.append({'step':obs['step'],'job':j,'crop':p['crop'],'features':contract.encode(obs)['global'].tolist()})
    policy.perennial.prepare=prepare
    op=next(o for o in json.loads((B/'protocol.json').read_text())['opponents'] if o['name']=='y68v');path=B/op['file'];assert evaluate.sha(path)==op['sha256'];other=get_last_callable(path.read_text(),path=str(path))
    env=make('kaggriculture',configuration={'seed':seed});env.reset(2);times=[]
    for t in range(719):
        obs=[copy.deepcopy(s.observation) for s in env.state]
        for o in obs:o['step']=t
        start=time.perf_counter();action=policy.act(obs[0]);times.append(time.perf_counter()-start);assert len(action['market'])<=10
        env.step([action,other(obs[1])]);assert all(s.status==('DONE' if t==718 else 'ACTIVE') for s in env.state)
    own,opp=[float(s.reward) for s in env.state]
    return {'id':ident(ids),'jobs':ids,'seed':seed,'own_cash':own,'opponent_cash':opp,'margin':own-opp,'win':own>opp,'max_seconds':max(times),'decisions':decisions,'stats':policy.stats['perennial'],'shops':list(env.state[0].observation.town['unlocked_shops'])}

def main():
    source=OUT/'pilot02_games.jsonl';rs=[json.loads(l) for l in source.read_text().splitlines()];seeds=sorted({r['seed'] for r in rs});controls={r['seed']:r['margin'] for r in rs if r['job']==-1}
    sys.path.insert(0,str(D));import action_space as space
    jobs=json.loads((D/'perennial_programs.json').read_text())['jobs'];mt=np.load(D/'data/market_tokens.npy',mmap_mode='r')[:,35];mq=np.load(D/'data/market_quantities.npy',mmap_mode='r')[:,35]
    proposals=[[],[8,9]]+[[j for j,x in enumerate(jobs) if x['crop']==c] for c in ['TOMATO','STRAWBERRY']]
    for seed in seeds:
        positive=[r['job'] for r in sorted(rs,key=lambda r:r['margin'],reverse=True) if r['seed']==seed and r['job']>=0 and r['margin']>controls[seed]]
        proposals.extend([positive[:k] for k in [3,6,12,len(positive)]]);proposals.append(positive+[8,9])
    seen=set();population=[];excluded=[]
    for ids in proposals:
        ids=sorted(set(ids));cid=ident(ids)
        if cid in seen:continue
        seen.add(cid);extra={}
        for j in ids:
            job=jobs[j];slot=job['purchase_step'],job['purchase_slot'];extra[slot]=extra.get(slot,0)+1
        overflow=False
        for t in {t for t,s in extra}:
            slots=sum(space.MARKET_TOKENS[int(tok)] not in ['STOP','SELL:EGG','SELL:MILK','SELL:WOOL'] for tok in mt[t])
            slots+=sum(0<n<int(mq[t,s]) for (tt,s),n in extra.items() if tt==t)
            if slots>10:overflow=True
        if overflow:excluded.append(ids)
        else:population.append(ids)
    plan={'population':population,'excluded_slot_overflow':excluded,'seeds':seeds,'source_sha256':evaluate.sha(source),'candidate_hashes':evaluate.snapshot(D),'driver_sha256':evaluate.sha(Path(__file__)),'expected_games':len(population)*len(seeds),'boundary':'Development combinations selected with hindsight; not a trained state policy.'}
    pf=OUT/'combinations_plan.json'
    if pf.exists():assert json.loads(pf.read_text())==plan
    else:pf.write_text(json.dumps(plan,indent=2)+'\n')
    ledger=OUT/'combinations_games.jsonl';rows=[json.loads(l) for l in ledger.read_text().splitlines()] if ledger.exists() else [];done={(r['id'],r['seed']) for r in rows};tasks=[(ids,s) for ids in population for s in seeds if (ident(ids),s) not in done]
    print('population',len(population),'excluded',len(excluded),'pending',len(tasks),flush=True)
    for offset in range(0,len(tasks),24):
        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
            for r in pool.map(worker,tasks[offset:offset+24]):
                rows.append(r)
                with ledger.open('a') as f:f.write(json.dumps(r)+'\n')
        print('completed',len(rows),'/',plan['expected_games'],flush=True)
    assert evaluate.snapshot(D)==plan['candidate_hashes'] and len(rows)==plan['expected_games']
    panels=[]
    for seed in seeds:
        same=[r for r in rows if r['seed']==seed];base=next(r for r in same if not r['jobs']);assert base['margin']==controls[seed];best=max(same,key=lambda r:r['margin'])
        panels.append({'seed':seed,'baseline_margin':base['margin'],'best_margin':best['margin'],'best_jobs':best['jobs'],'uplift':best['margin']-base['margin'],'winning_combinations':sum(r['win'] for r in same)})
    out={'games':len(rows),'population':len(population),'panels':panels};(OUT/'combinations_summary.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True)

if __name__=='__main__':main()
