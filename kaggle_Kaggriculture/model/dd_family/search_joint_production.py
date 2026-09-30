"""Complete-game joint livestock search with balanced development strata."""
from pathlib import Path
import argparse,concurrent.futures,contextlib,copy,hashlib,io,json,sys,time
import numpy as np
import evaluate
B=Path(__file__).resolve().parent;D=B/'ddaw';OUT=B/'joint_production_ddaw'
SPECIES=['GOOSE','COW','SHEEP']

def ident(genome):return 'baseline' if genome is None else hashlib.sha256(json.dumps(genome).encode()).hexdigest()[:12]
def worker(task):
    genome,seed=task
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
    sys.path.insert(0,str(D));import main,production
    policy=main.Agent();policy.genome=genome
    op=next(o for o in json.loads((B/'protocol.json').read_text())['opponents'] if o['name']=='y68v');path=B/op['file'];assert evaluate.sha(path)==op['sha256'];other=get_last_callable(path.read_text(),path=str(path))
    panel=json.loads((OUT/'seed_panels.json').read_text());prefix=next(r['prefix_observation_sha256'] for r in panel['rows'] if r['seed']==seed)
    env=make('kaggriculture',configuration={'seed':seed});env.reset(2);times=[];daily=[];context=None
    for t in range(719):
        obs=[copy.deepcopy(s.observation) for s in env.state]
        for o in obs:o['step']=t
        if t==72:
            assert hashlib.sha256(json.dumps(obs[0],sort_keys=True).encode()).hexdigest()==prefix,(seed,'prefix mismatch')
            context=production.state_features(obs[0]).tolist()
        start=time.perf_counter();action=policy.act(obs[0]);times.append(time.perf_counter()-start);assert len(action['market'])<=10
        env.step([action,other(obs[1])])
        if t%24==22:
            farm=env.state[0].observation.farms[0];tiles=[v for row in farm['tiles'] for v in row if isinstance(v,dict)]
            daily.append({'day':t//24,'cash':farm['money'],'animals':{kind:sum(v.get('animal')==kind for v in tiles) for kind in SPECIES},'crops':sum(bool(v.get('crop')) for v in tiles),'shops':list(env.state[0].observation.town['unlocked_shops'])})
    assert all(s.status=='DONE' for s in env.state);own,opp=[float(s.reward) for s in env.state]
    return {'id':ident(genome),'genome':genome,'seed':seed,'seat':0,'opponent':'y68v','own_cash':own,'opponent_cash':opp,'margin':own-opp,'win':own>opp,'max_seconds':max(times),'context72':context,'decisions':policy.decisions,'allocations':policy.stats['allocations'],'daily':daily}

def rank(rows,seeds):
    ranking=[]
    for cid in sorted({r['id'] for r in rows}):
        rs=[r for r in rows if r['id']==cid and r['seed'] in seeds]
        if len(rs)!=len(seeds):continue
        margin=np.asarray([r['margin'] for r in rs]);ranking.append({'id':cid,'genome':rs[0]['genome'],'games':len(rs),'wins':sum(r['win'] for r in rs),'mean_margin':float(margin.mean()),'min_margin':float(margin.min()),'risk_score':float(margin.mean()-.5*margin.std())})
    ranking.sort(key=lambda r:(r['wins'],r['risk_score'],r['mean_margin']),reverse=True);return ranking

def initial():
    original=[g['original'] for g in json.loads((D/'animal_program.json').read_text())['groups']];population=[None,original]
    for kind in SPECIES:population.append(original[:3]+[kind]*11)
    rng=np.random.default_rng(91173)
    while len(population)<20:
        genome=original[:]
        for j in range(3,14):
            if rng.random()<.65:genome[j]=str(rng.choice(SPECIES))
        if genome not in population:population.append(genome)
    return population

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--stage',choices=['round0','round1','round2','refine'],required=True);ap.add_argument('--workers',type=int,default=4);args=ap.parse_args()
    panels=json.loads((OUT/'seed_panels.json').read_text())['panels'];target=OUT/'games.jsonl';rows=[json.loads(l) for l in target.read_text().splitlines()] if target.exists() else []
    planfile=OUT/f'{args.stage}_plan.json';hashes=evaluate.snapshot(D)
    if planfile.exists():
        plan=json.loads(planfile.read_text());assert plan['candidate_hashes']==hashes and plan['driver_sha256']==evaluate.sha(Path(__file__));population=plan['population'];seeds=plan['seeds']
    else:
        if args.stage=='round0':population=initial();seeds=panels['search']
        elif args.stage=='refine':
            ranked=rank(rows,panels['search']);population=[r['genome'] for r in ranked if r['genome'] is not None][:6]+[None];seeds=panels['refine']
        else:
            previous=int(args.stage[-1])-1;assert (OUT/f'round{previous}_summary.json').exists();ranked=rank(rows,panels['search']);parents=[r['genome'] for r in ranked if r['genome'] is not None][:6];rng=np.random.default_rng(91173+int(args.stage[-1]));known={r['id'] for r in rows};population=[];seeds=panels['search']
            while len(population)<20:
                a,b=rng.integers(len(parents),size=2);genome=parents[a][:]
                for j in range(3,14):
                    if rng.random()<.5:genome[j]=parents[b][j]
                    if rng.random()<.2:genome[j]=str(rng.choice(SPECIES))
                cid=ident(genome)
                if cid not in known:known.add(cid);population.append(genome)
        plan={'stage':args.stage,'population':population,'seeds':seeds,'candidate_hashes':hashes,'driver_sha256':evaluate.sha(Path(__file__)),'seed_manifest_sha256':evaluate.sha(OUT/'seed_panels.json'),'protocol_sha256':evaluate.sha(B/'protocol.json'),'objective':'Full final own-minus-opponent cash, ranking by strict wins then mean minus half standard deviation. No single-intervention additivity assumption.','boundary':'Development-only black-box dynamic y68v evaluation; opponent actions/code never become candidate data or inference.'};planfile.write_text(json.dumps(plan,indent=2)+'\n')
    done={(r['id'],r['seed']) for r in rows};tasks=[(g,s) for g in population for s in seeds if (ident(g),s) not in done];print(args.stage,'pending',len(tasks),flush=True);completed=0
    for offset in range(0,len(tasks),args.workers*6):
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
            for r in pool.map(worker,tasks[offset:offset+args.workers*6]):
                rows.append(r);completed+=1
                with target.open('a') as f:f.write(json.dumps(r)+'\n')
                if completed%16==0:print(args.stage,'completed',completed,'/',len(tasks),flush=True)
    assert evaluate.snapshot(D)==hashes
    full_seeds=panels['search']+panels['refine'] if args.stage=='refine' else panels['search'];ranking=rank(rows,full_seeds)
    summary={'stage':args.stage,'new_games':completed,'ranking':ranking,'games_in_ledger':len(rows)};(OUT/f'{args.stage}_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps({'stage':args.stage,'top':ranking[:8]}),flush=True)
if __name__=='__main__':main()
