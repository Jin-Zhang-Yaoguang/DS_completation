"""Full dynamic single-crop interventions, with a replay-identical control."""
from pathlib import Path
import argparse,ast,concurrent.futures,contextlib,copy,gzip,hashlib,io,json,sys,time,traceback
import numpy as np
import evaluate
B=Path(__file__).resolve().parent;D=B/'ddbb';OUT=B/'crop_counterfactuals_ddbb'

def worker(task):
    job_id,seed=task
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
    sys.path.insert(0,str(D));import main,contract
    policy=main.Agent();features=None;prefix=None;decision=None
    if job_id>=0:
        job=policy.perennial.data['jobs'][job_id];program=next(p for p in job['alternatives'] if p['crop']!=job['crop'])
        def prepare(obs):
            nonlocal features,prefix,decision
            if int(obs['step'])!=job['purchase_step']:return
            features=contract.encode(obs)['global'].tolist();prefix=hashlib.sha256(json.dumps(obs,sort_keys=True).encode()).hexdigest()
            policy.perennial.selected[job_id]=program;policy.perennial.stats['chosen']+=1;policy.perennial.stats['species_changes']+=1
            decision={'step':job['purchase_step'],'job':job_id,'original':job['crop'],'chosen':program['crop'],'expected_units':program['yield_units']}
            policy.perennial.stats['decisions'].append(decision)
        policy.perennial.prepare=prepare
    op=next(o for o in json.loads((B/'protocol.json').read_text())['opponents'] if o['name']=='y68v');path=B/op['file'];assert evaluate.sha(path)==op['sha256'];other=get_last_callable(path.read_text(),path=str(path))
    env=make('kaggriculture',configuration={'seed':seed});env.reset(2);times=[];daily=[];tracehash=hashlib.sha256();contexts={}
    purchase_steps={j['purchase_step'] for j in policy.perennial.data['jobs']}
    for t in range(719):
        obs=[copy.deepcopy(s.observation) for s in env.state]
        for o in obs:o['step']=t
        if job_id<0 and t in purchase_steps:contexts[str(t)]=hashlib.sha256(json.dumps(obs[0],sort_keys=True).encode()).hexdigest()
        start=time.perf_counter();action=policy.act(obs[0]);times.append(time.perf_counter()-start);assert len(action['market'])<=10
        tracehash.update(json.dumps(action,sort_keys=True).encode())
        env.step([action,other(obs[1])]);assert all(s.status==('DONE' if t==718 else 'ACTIVE') for s in env.state)
        if t%24==22 or t==718:daily.append({'day':t//24,'cash':env.state[0].observation.farms[0]['money'],'shops':list(env.state[0].observation.town['unlocked_shops'])})
    own,opp=[float(s.reward) for s in env.state]
    if job_id<0:
        known=json.loads((B/'ddam/runs/broad01/summary.json').read_text())['rows'];expected=next((r for r in known if r['seed']==seed and r['seat']==0),None)
        if expected:assert [own,opp]==[expected['own_cash'],expected['opponent_cash']],(seed,'control mismatch')
    return {'job':job_id,'seed':seed,'seat':0,'opponent':'y68v','own_cash':own,'opponent_cash':opp,'margin':own-opp,'win':own>opp,'max_seconds':max(times),'overage_remaining':60-sum(max(0,t-1) for t in times),'features':features,'decision':decision,'prefix_sha256':prefix,'control_prefixes':contexts,'trace_sha256':tracehash.hexdigest(),'stats':policy.stats['perennial'],'daily':daily}

def summarize(rows,seeds):
    controls={r['seed']:r for r in rows if r['job']<0};panels=[]
    for seed in seeds:
        if seed not in controls:continue
        rs=[r for r in rows if r['seed']==seed];base=controls[seed]
        for r in rs:
            if r['job']>=0:assert r['prefix_sha256']==base['control_prefixes'][str(r['decision']['step'])],(seed,r['job'],'pre-intervention mismatch')
        best=max(rs,key=lambda r:r['margin'])
        panels.append({'seed':seed,'games':len(rs),'baseline_margin':base['margin'],'oracle_margin':best['margin'],'oracle_job':best['job'],'oracle_uplift':best['margin']-base['margin'],'positive_interventions':sum(r['margin']>base['margin'] for r in rs),'winning_interventions':sum(r['win'] for r in rs)})
    ranking=[]
    for j in sorted({r['job'] for r in rows}):
        rs=[r for r in rows if r['job']==j and r['seed'] in seeds]
        if len(rs)==len(seeds):ranking.append({'job':j,'wins':sum(r['win'] for r in rs),'mean_margin':float(np.mean([r['margin'] for r in rs])),'mean_uplift':float(np.mean([r['margin']-controls[r['seed']]['margin'] for r in rs]))})
    ranking.sort(key=lambda r:r['mean_uplift'],reverse=True)
    return {'games':len(rows),'seeds':seeds,'panels':panels,'ranking':ranking,'boundary':'Oracle is a retrospective diagnostic on development outcomes; not an executable policy or a generalization result.'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',required=True);ap.add_argument('--seeds',nargs='+',type=int,required=True);ap.add_argument('--jobs',nargs='+',type=int);ap.add_argument('--workers',type=int,default=4);ap.add_argument('--import-stage');args=ap.parse_args()
    assert all(919260000<=s<919290000 for s in args.seeds)
    OUT.mkdir(exist_ok=True);programs=json.loads((D/'perennial_programs.json').read_text())['jobs']
    sys.path.insert(0,str(D));import action_space as space
    mt=np.load(D/'data/market_tokens.npy',mmap_mode='r')[:,35];mq=np.load(D/'data/market_quantities.npy',mmap_mode='r')[:,35];excluded=[]
    for j,job in enumerate(programs):
        t,s=job['purchase_step'],job['purchase_slot'];used=sum(space.MARKET_TOKENS[int(tok)] not in ['STOP','SELL:EGG','SELL:MILK','SELL:WOOL'] for tok in mt[t])
        if used+int(mq[t,s]>1)>10:excluded.append(j)
    ids=args.jobs if args.jobs is not None else [-1]+[j for j,x in enumerate(programs) if j not in excluded and any(p['crop']!=x['crop'] for p in x['alternatives'])]
    assert not set(ids)&set(excluded),'single intervention exceeds original market slot capacity'
    assert -1 in ids and len(ids)==len(set(ids));hashes=evaluate.snapshot(D)
    plan={'stage':args.stage,'seeds':args.seeds,'jobs':ids,'excluded_slot_overflow_jobs':excluded,'candidate_hashes':hashes,'driver_sha256':evaluate.sha(Path(__file__)),'protocol_sha256':evaluate.sha(B/'protocol.json'),'expected_games':len(ids)*len(args.seeds),'import_stage':args.import_stage};pf=OUT/f'{args.stage}_plan.json'
    imported=[]
    if args.import_stage:
        old=OUT/f'{args.import_stage}_plan.json';oldplan=json.loads(old.read_text());oldledger=OUT/f'{args.import_stage}_games.jsonl'
        assert oldplan['candidate_hashes']==hashes and oldplan['protocol_sha256']==plan['protocol_sha256']
        def worker_ast(path):return ast.dump(next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='worker'))
        assert evaluate.sha(B/'search_crop_counterfactuals_v1.py')==oldplan['driver_sha256']
        assert worker_ast(B/'search_crop_counterfactuals_v1.py')==worker_ast(Path(__file__))
        plan['import_ledger_sha256']=evaluate.sha(oldledger)
        imported=[json.loads(l) for l in oldledger.read_text().splitlines() if json.loads(l)['job'] in ids and json.loads(l)['seed'] in args.seeds]
    if pf.exists():assert json.loads(pf.read_text())==plan
    else:pf.write_text(json.dumps(plan,indent=2)+'\n')
    ledger=OUT/f'{args.stage}_games.jsonl'
    if not ledger.exists() and imported:ledger.write_text(''.join(json.dumps(r)+'\n' for r in imported))
    rows=[json.loads(l) for l in ledger.read_text().splitlines()] if ledger.exists() else [];done={(r['job'],r['seed']) for r in rows};tasks=[(j,s) for j in ids for s in args.seeds if (j,s) not in done]
    print('pending',len(tasks),'total',plan['expected_games'],flush=True)
    completed=0
    for offset in range(0,len(tasks),args.workers*6):
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
            for row in pool.map(worker,tasks[offset:offset+args.workers*6]):
                rows.append(row);completed+=1
                with ledger.open('a') as f:f.write(json.dumps(row)+'\n')
                if completed%16==0:print('completed',completed,'/',len(tasks),flush=True)
        (OUT/f'{args.stage}_progress.json').write_text(json.dumps(summarize(rows,args.seeds),indent=2)+'\n')
    assert evaluate.snapshot(D)==hashes
    summary=summarize(rows,args.seeds);assert len(rows)==plan['expected_games'];(OUT/f'{args.stage}_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'panels':summary['panels'],'top':summary['ranking'][:8]}),flush=True)

if __name__=='__main__':main()
