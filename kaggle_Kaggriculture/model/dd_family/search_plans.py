"""Bounded simulator-guided plan distillation. All queried seeds are development only."""
from pathlib import Path
import argparse,concurrent.futures,contextlib,copy,hashlib,io,json,sys,time,os
import numpy as np
B=Path(__file__).resolve().parent;D=B/'ddn';OUT=B/'plan_search_ddn'
def game(task):
    k,mode,op,seed,seat=task
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
    sys.path.insert(0,str(D));import main
    policy=main.Agent();policy.config['fixed_prototype']=k;policy.config['market_mode']=mode
    proto=json.loads((B/'protocol.json').read_text());row=next(x for x in proto['opponents'] if x['name']==op)
    path=B/row['file'];assert hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256']
    other=get_last_callable(path.read_text(),path=str(path));env=make('kaggriculture',configuration={'seed':seed},debug=False);env.reset(2)
    start=time.perf_counter()
    for t in range(719):
        observations=[copy.deepcopy(s.observation) for s in env.state]
        for o in observations:o['step']=t
        actions=[None,None];actions[seat]=policy.act(observations[seat]);actions[1-seat]=other(observations[1-seat]);env.step(actions)
    assert [s.status for s in env.state]==['DONE','DONE']
    reward=[float(s.reward) for s in env.state];margin=reward[seat]-reward[1-seat]
    return {'k':k,'mode':mode,'opponent':op,'seed':seed,'seat':seat,'margin':margin,'own_cash':reward[seat],
            'win':margin>0,'elapsed':time.perf_counter()-start,'stats':policy.stats}
def main_search():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['screen','refine'],required=True);ap.add_argument('--workers',type=int,default=6);a=ap.parse_args();OUT.mkdir(exist_ok=True)
    manifest=json.loads((D/'training_manifest.json').read_text());n=manifest['train_episodes'];protocol=json.loads((B/'protocol.json').read_text())
    if a.stage=='screen':
        # Coherent plans are cheap to reject. No source-game return prefilter.
        tasks=[(k,'teacher',op,protocol['development_seeds'][0],0) for k in range(n) for op in ['y68a','y68v']]
    else:
        screen=json.loads((OUT/'screen_summary.json').read_text());plans=screen['ranking'][:12]
        tasks=[(r['k'],mode,op,s,seat) for r in plans for mode in ['teacher','sellall'] for op in protocol['development_opponents'] for s in protocol['development_seeds'][1:] for seat in [0,1]]
    output=OUT/f'{a.stage}.jsonl';rows=[json.loads(l) for l in output.read_text().splitlines()] if output.exists() else []
    def key(r):return (r['k'],r['mode'],r['opponent'],r['seed'],r['seat'])
    finished={key(r) for r in rows};pending=[t for t in tasks if t not in finished]
    config={'stage':a.stage,'tasks':tasks,'source_main_sha256':hashlib.sha256((D/'main.py').read_bytes()).hexdigest(),
            'source_config_sha256':hashlib.sha256((D/'config.json').read_bytes()).hexdigest(),'all_results':'development, not gate'}
    plan=OUT/f'{a.stage}_plan.json'
    if plan.exists():assert json.loads(plan.read_text())==json.loads(json.dumps(config))
    else:plan.write_text(json.dumps(config,indent=2)+'\n')
    print('pending',a.stage,len(pending),flush=True)
    # Python 3.12 can stall after every worker reaches max_tasks_per_child.
    # Explicit bounded pools also bound memory while avoiding that recycle path.
    count=0
    for offset in range(0,len(pending),a.workers*6):
        with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
            for r in pool.map(game,pending[offset:offset+a.workers*6]):
                rows.append(r);count+=1
                with output.open('a') as f:f.write(json.dumps(r)+'\n')
                if count%10==0:print(a.stage,count,r['k'],r['opponent'],int(r['margin']),flush=True)
    ranking=[]
    for k,mode in sorted({(r['k'],r['mode']) for r in rows}):
        rs=[r for r in rows if r['k']==k and r['mode']==mode]
        ranking.append({'k':k,'mode':mode,'games':len(rs),'wins':sum(r['win'] for r in rs),
                        'mean_margin':float(np.mean([r['margin'] for r in rs])),
                        'worst_margin':min(r['margin'] for r in rs)})
    ranking.sort(key=lambda r:(r['wins']/r['games'],r['worst_margin'],r['mean_margin']),reverse=True)
    summary={'stage':a.stage,'expected':len(tasks),'completed':len(rows),'ranking':ranking}
    assert len(rows)==len(tasks)
    (OUT/f'{a.stage}_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(ranking[:12]),flush=True)
if __name__=='__main__':main_search()
