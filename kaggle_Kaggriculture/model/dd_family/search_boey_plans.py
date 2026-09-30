"""Search coherent Boey replay plans with the repaired, original-species executor."""
from pathlib import Path
import argparse,concurrent.futures,contextlib,copy,io,json,sys,time
import numpy as np
import evaluate
B=Path(__file__).resolve().parent;D=B/'ddbd';OUT=B/'plan_search_ddbd'

def worker(task):
    k,seed=task
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
    sys.path.insert(0,str(D));import main
    policy=main.Agent(prototype=k)
    op=next(o for o in json.loads((B/'protocol.json').read_text())['opponents'] if o['name']=='y68v');path=B/op['file'];assert evaluate.sha(path)==op['sha256'];other=get_last_callable(path.read_text(),path=str(path))
    env=make('kaggriculture',configuration={'seed':seed});env.reset(2);times=[];daily=[]
    for t in range(719):
        obs=[copy.deepcopy(s.observation) for s in env.state]
        for o in obs:o['step']=t
        start=time.perf_counter();action=policy.act(obs[0]);times.append(time.perf_counter()-start);assert len(action['market'])<=10
        env.step([action,other(obs[1])]);assert all(s.status==('DONE' if t==718 else 'ACTIVE') for s in env.state)
        if t%24==22 or t==718:
            farm=env.state[0].observation.farms[0];tiles=[v for row in farm['tiles'] for v in row if isinstance(v,dict)]
            daily.append({'day':t//24,'cash':farm['money'],'hands':len(farm['hands']),'animals':sum(bool(v.get('animal')) for v in tiles),'crops':sum(bool(v.get('crop')) for v in tiles),'shops':list(env.state[0].observation.town['unlocked_shops'])})
    own,opp=[float(s.reward) for s in env.state]
    return {'k':k,'seed':seed,'seat':0,'opponent':'y68v','own_cash':own,'opponent_cash':opp,'margin':own-opp,'win':own>opp,'max_seconds':max(times),'overage_remaining':60-sum(max(0,t-1) for t in times),'daily':daily,'stats':policy.stats}

def rank(rows,seeds):
    out=[]
    for k in sorted({r['k'] for r in rows}):
        rs=[r for r in rows if r['k']==k and r['seed'] in seeds]
        if len(rs)!=len(seeds):continue
        out.append({'k':k,'games':len(rs),'wins':sum(r['win'] for r in rs),'mean_margin':float(np.mean([r['margin'] for r in rs])),'worst_margin':min(r['margin'] for r in rs)})
    return sorted(out,key=lambda r:(r['wins'],r['worst_margin'],r['mean_margin']),reverse=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['screen','refine'],required=True);ap.add_argument('--workers',type=int,default=4);args=ap.parse_args();OUT.mkdir(exist_ok=True)
    screen_seeds=[919260011,919261006,919262004,919262007]
    if args.stage=='screen':ids=list(range(json.loads((D/'training_manifest.json').read_text())['train_episodes']));seeds=screen_seeds
    else:
        s=json.loads((OUT/'screen_summary.json').read_text());assert s['complete'];ids=[r['k'] for r in s['ranking'][:8]];seeds=[x for x in [*range(919260010,919260014),*range(919261001,919261009),*range(919262001,919262009)] if x not in screen_seeds]
    hashes=evaluate.snapshot(D);plan={'stage':args.stage,'prototypes':ids,'seeds':seeds,'expected_games':len(ids)*len(seeds),'candidate_hashes':hashes,'driver_sha256':evaluate.sha(Path(__file__)),'protocol_sha256':evaluate.sha(B/'protocol.json'),'boundary':'Development-only coherent teacher-plan selection. The teacher split is by source seed; these simulator openings are a separate development panel.'};pf=OUT/f'{args.stage}_plan.json'
    if pf.exists():assert json.loads(pf.read_text())==plan
    else:pf.write_text(json.dumps(plan,indent=2)+'\n')
    ledger=OUT/f'{args.stage}_games.jsonl';rows=[json.loads(l) for l in ledger.read_text().splitlines()] if ledger.exists() else [];done={(r['k'],r['seed']) for r in rows};tasks=[(k,s) for k in ids for s in seeds if (k,s) not in done];print(args.stage,'pending',len(tasks),flush=True)
    for offset in range(0,len(tasks),args.workers*6):
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
            for row in pool.map(worker,tasks[offset:offset+args.workers*6]):
                rows.append(row)
                with ledger.open('a') as f:f.write(json.dumps(row)+'\n')
        summary={'complete':len(rows)==plan['expected_games'],'completed':len(rows),'expected':plan['expected_games'],'ranking':rank(rows,seeds)}
        (OUT/f'{args.stage}_progress.json').write_text(json.dumps(summary,indent=2)+'\n');print(args.stage,'completed',len(rows),'top',summary['ranking'][:2],flush=True)
    assert evaluate.snapshot(D)==hashes and len(rows)==plan['expected_games']
    summary={'complete':True,'completed':len(rows),'expected':plan['expected_games'],'ranking':rank(rows,seeds)};(OUT/f'{args.stage}_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary['ranking'][:8]),flush=True)

if __name__=='__main__':main()
