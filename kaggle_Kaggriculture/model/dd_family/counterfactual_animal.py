"""Single-decision policy interventions; only development seeds and public inputs."""
from pathlib import Path
import argparse,concurrent.futures,contextlib,copy,importlib.util,io,json,sys,time
import evaluate
B=Path(__file__).resolve().parent;D=B/'ddaa';OUT=B/'counterfactual_ddaa'
SEEDS=[919260010,919260011,919260012,919260013,*range(919261001,919261009),*range(919262001,919262009)]
def worker(task):
    seed,g,forced=task
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
    sys.path.insert(0,str(D))
    for name in ['main','contract','features','action_space','rules']:sys.modules.pop(name,None)
    spec=importlib.util.spec_from_file_location('cf_policy',D/'main.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    agent=module.Agent();agent.forced_choices={} if g<0 else {g:forced}
    proto=json.loads((B/'protocol.json').read_text());op=next(r for r in proto['opponents'] if r['name']=='y68v');p=B/op['file'];assert evaluate.sha(p)==op['sha256']
    other=get_last_callable(p.read_text(),path=str(p));env=make('kaggriculture',configuration={'seed':seed});env.reset(2);start=time.perf_counter()
    for t in range(719):
        obs=[copy.deepcopy(s.observation) for s in env.state]
        for o in obs:o['step']=t
        env.step([agent.act(obs[0]),other(obs[1])])
    assert [s.status for s in env.state]==['DONE','DONE']
    cash=[float(s.reward) for s in env.state]
    return {'seed':seed,'group':g,'forced':forced,'margin':cash[0]-cash[1],'own_cash':cash[0],'opponent_cash':cash[1],'allocations':agent.stats['allocations'],'invalid_units':agent.stats['invalid_units'],'elapsed':time.perf_counter()-start}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['baseline','intervene'],required=True);ap.add_argument('--workers',type=int,default=6);a=ap.parse_args();OUT.mkdir(exist_ok=True)
    if a.stage=='baseline':tasks=[(s,-1,None) for s in SEEDS]
    else:
        base=[json.loads(l) for l in (OUT/'baseline.jsonl').read_text().splitlines()];assert len(base)==len(SEEDS)
        tasks=[(r['seed'],x['group'],x['original'] if x['chosen']=='SHEEP' else 'SHEEP') for r in base for x in r['allocations'] if x['original']!='SHEEP']
    plan={'stage':a.stage,'tasks':tasks,'candidate_hashes':evaluate.snapshot(D),'driver_sha256':evaluate.sha(Path(__file__)),'opponent':'y68v','seat':0,'label':'counterfactual final margin difference; same seed, official RNG feedback retained','panel':'development'}
    plan=json.loads(json.dumps(plan));pp=OUT/f'{a.stage}_plan.json'
    if pp.exists():assert json.loads(pp.read_text())==plan
    else:pp.write_text(json.dumps(plan,indent=2)+'\n')
    target=OUT/f'{a.stage}.jsonl';rows=[json.loads(x) for x in target.read_text().splitlines()] if target.exists() else [];done={(r['seed'],r['group']) for r in rows};pending=[t for t in tasks if (t[0],t[1]) not in done]
    print('pending',a.stage,len(pending),flush=True)
    for off in range(0,len(pending),a.workers*6):
        with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
            fs=[pool.submit(worker,t) for t in pending[off:off+a.workers*6]]
            for f in concurrent.futures.as_completed(fs):
                r=f.result();rows.append(r)
                with target.open('a') as dest:dest.write(json.dumps(r)+'\n')
                if len(rows)%10==0:print(a.stage,len(rows),r['seed'],r['group'],r['margin'],flush=True)
    assert evaluate.snapshot(D)==plan['candidate_hashes'];assert len(rows)==len(tasks)
    if a.stage=='intervene':
        baselines={r['seed']:r for r in base};dataset=[]
        for r in rows:
            ref=baselines[r['seed']];x=next(x for x in ref['allocations'] if x['group']==r['group']);observed=next(x for x in r['allocations'] if x['group']==r['group']);assert observed['features']==x['features'],'intervention must share exact decision input'
            advantage=(r['margin']-ref['margin'])*(1 if r['forced']=='SHEEP' else -1)
            dataset.append({'seed':r['seed'],'group':r['group'],'original':x['original'],'count':x['count'],'step':x['step'],'features':x['features'],'sheep_advantage':advantage,'base_margin':ref['margin'],'changed_margin':r['margin']})
        (OUT/'dataset.json').write_text(json.dumps(dataset,indent=2)+'\n');print('dataset',len(dataset),flush=True)
if __name__=='__main__':main()
