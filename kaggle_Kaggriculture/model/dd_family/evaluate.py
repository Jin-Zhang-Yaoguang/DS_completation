"""Official dynamic matches, isolated agents, immutable run hashes and seed panels."""
from pathlib import Path
import argparse,copy,concurrent.futures,gzip,hashlib,importlib.util,json,os,sys,time,traceback
import numpy as np
B=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def snapshot(directory):
    return {str(p.relative_to(directory)):sha(p) for p in sorted(directory.rglob('*'))
            if p.is_file() and p.suffix in ['.py','.json','.npy','.npz']
            and 'runs' not in p.relative_to(directory).parts and p.name!='freeze.json'}
def worker(task):
    version,panel,run,name,seed,seat=task
    import contextlib,io
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
    import importlib.metadata
    assert importlib.metadata.version('kaggle-environments')=='1.32.7'
    protocol=json.loads((B/'protocol.json').read_text());op=next(x for x in protocol['opponents'] if x['name']==name)
    path=B/op['file'];assert sha(path)==op['sha256']
    directory=B/version;sys.path.insert(0,str(directory))
    # Process worker may serve multiple games; purge candidate-local module globals.
    for mod in ['main','contract','features','action_space','rules']:
        sys.modules.pop(mod,None)
    spec=importlib.util.spec_from_file_location('dd_candidate',directory/'main.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    start=time.perf_counter();construct=time.perf_counter();policy=module.Agent();initial=time.perf_counter()-construct
    other=get_last_callable(path.read_text(),path=str(path))
    env=make('kaggriculture',configuration={'seed':seed},debug=False);env.reset(2)
    daily=[];trace=[];times=[];bank=60.;errors=[]
    for step in range(719):
        obs=[copy.deepcopy(s.observation) for s in env.state]
        for o in obs:o['step']=step
        t=time.perf_counter();a=policy.act(obs[seat]);dt=time.perf_counter()-t+(initial if step==0 else 0)
        times.append(dt);bank-=max(0.,dt-1.)
        # Requests can be infeasible under simultaneous market competition; schema must be valid.
        assert isinstance(a,dict) and set(a)=={'farmer','hands','market'}
        assert len(a['hands'])==len(obs[seat]['farms'][seat]['hands'])
        b=other(obs[1-seat]);acts=[None,None];acts[seat]=a;acts[1-seat]=b
        env.step(acts)
        if step<718:assert all(s.status=='ACTIVE' for s in env.state),(step,[s.status for s in env.state])
        f=env.state[seat].observation.farms[seat]
        trace.append({'step':step,'action':a,'cash':f['money'],'diagnostic':copy.deepcopy(getattr(policy,'last',{}))})
        if step%24==22 or step==718:
            tiles=[v for row in f['tiles'] for v in row if isinstance(v,dict)]
            daily.append({'day':step//24,'cash':f['money'],'hands':len(f['hands']),
                          'animals':sum(bool(v.get('animal')) for v in tiles),
                          'crops':sum(bool(v.get('crop')) for v in tiles),
                          'land':len(f['unlocked_quadrants']),
                          'shops':list(env.state[seat].observation.town['unlocked_shops'])})
    assert [s.status for s in env.state]==['DONE','DONE']
    rewards=[float(s.reward) for s in env.state];margin=rewards[seat]-rewards[1-seat]
    result={'version':version,'panel':panel,'run':run,'opponent':name,'opponent_sha256':op['sha256'],
            'seed':seed,'seat':seat,'margin':margin,'own_cash':rewards[seat],'opponent_cash':rewards[1-seat],
            'win':margin>0,'draw':margin==0,'status':'DONE','steps':719,'overage_remaining':bank,
            'max_seconds':max(times),'p99_seconds':float(np.quantile(times,.99)),
            'elapsed':time.perf_counter()-start,'daily':daily,'stats':getattr(policy,'stats',{}),'trace':trace,
            'shops':list(env.state[seat].observation.town['unlocked_shops'])}
    target=directory/'runs'/run/'games'/f'{name}_{seed}_{seat}.json.gz';target.parent.mkdir(exist_ok=True,parents=True)
    with gzip.open(str(target)+'.tmp','wt') as f:json.dump(result,f,separators=(',',':'))
    os.replace(str(target)+'.tmp',target)
    return {k:v for k,v in result.items() if k not in ['daily','trace']}

def summarize(out,expected):
    rows=[]
    for p in sorted((out/'games').glob('*.json.gz')):
        with gzip.open(p,'rt') as f:r=json.load(f)
        rows.append({k:v for k,v in r.items() if k not in ['daily','trace']})
    groups={};rng=np.random.default_rng(734593)
    for op in sorted({r['opponent'] for r in rows}):
        rs=[r for r in rows if r['opponent']==op];seeds=sorted({r['seed'] for r in rs})
        pairs=np.array([np.mean([r['margin'] for r in rs if r['seed']==s]) for s in seeds])
        lower=float(np.quantile(rng.choice(pairs,(10000,len(pairs)),replace=True).mean(1),.025))
        seats={str(s):sum(r['win'] for r in rs if r['seat']==s) for s in [0,1]}
        wins=sum(r['win'] for r in rs)
        groups[op]={'games':len(rs),'wins':wins,'draws':sum(r['draw'] for r in rs),'seat_wins':seats,
                    'mean_margin':float(np.mean([r['margin'] for r in rs])),
                    'paired_seed_margin_lower95':lower,
                    'pass':len(rs)==32 and wins>=30 and min(seats.values())>=14 and lower>0
                           and all(r['overage_remaining']>=0 for r in rs)}
    result={'completed':len(rows),'expected':expected,'wins':sum(r['win'] for r in rows),
            'mean_margin':float(np.mean([r['margin'] for r in rows])) if rows else None,
            'groups':groups,'passed':len(rows)==expected and bool(groups) and all(g['pass'] for g in groups.values()),
            'rows':rows}
    (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('version');ap.add_argument('--panel',default='development',choices=['development','gate','confirmation']);ap.add_argument('--run',required=True);ap.add_argument('--workers',type=int,default=4);ap.add_argument('--limit-seeds',type=int);ap.add_argument('--opponents',nargs='+');ap.add_argument('--seeds',type=int,nargs='+');a=ap.parse_args()
    protocol=json.loads((B/'protocol.json').read_text());reg=json.loads((B/'registry.json').read_text());v=next(x for x in reg['versions'] if x['version']==a.version)
    directory=B/a.version;out=directory/'runs'/a.run;out.mkdir(parents=True,exist_ok=True)
    if a.panel=='development':
        seeds=a.seeds or protocol['development_seeds'];names=protocol['development_opponents']
        assert len(seeds)==len(set(seeds))
        assert all(919260000<=s<919290000 for s in seeds),'development-only seed range'
    else:
        assert not a.limit_seeds and not a.opponents and not a.seeds,'No partial gate'
        base=919300000+v['index']*1000+(100 if a.panel=='confirmation' else 0)
        seeds=list(range(base,base+16));names=[x['name'] for x in protocol['opponents']]
        if a.panel=='confirmation':
            gates=[p for p in (directory/'runs').glob('*/plan.json') if json.loads(p.read_text())['panel']=='gate']
            assert any(json.loads((p.parent/'summary.json').read_text())['passed'] for p in gates),'gate must pass before confirmation'
    if a.limit_seeds:seeds=seeds[:a.limit_seeds]
    if a.opponents:names=a.opponents
    known={o['name'] for o in protocol['opponents']};assert set(names)<=known
    hashes=snapshot(directory)
    if a.panel!='development':
        freeze=directory/'freeze.json'
        if freeze.exists():assert json.loads(freeze.read_text())==hashes,'candidate changed after freeze'
        else:freeze.write_text(json.dumps(hashes,indent=2)+'\n')
    tasks=[(a.version,a.panel,a.run,n,s,seat) for n in names for s in seeds for seat in [0,1]]
    plan={'version':a.version,'panel':a.panel,'seeds':seeds,'opponents':names,'expected':len(tasks),
          'hashes':hashes,'protocol_sha256':sha(B/'protocol.json'),'engine':'1.32.7',
          'driver_sha256':sha(Path(__file__)),
          'seed_caveat':'Official weed RNG consumes draws according to farm emptiness; matched seeds do not guarantee identical shop histories across policies.'}
    if (out/'plan.json').exists():assert json.loads((out/'plan.json').read_text())==plan,'run immutable'
    else:(out/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    pending=[t for t in tasks if not (out/'games'/f'{t[3]}_{t[4]}_{t[5]}.json.gz').exists()]
    print('pending',len(pending),'total',len(tasks),flush=True)
    failed=False
    count=0
    for offset in range(0,len(pending),a.workers*6):
        with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as pool:
            futures={pool.submit(worker,t):t for t in pending[offset:offset+a.workers*6]}
            for f in concurrent.futures.as_completed(futures):
                count+=1
                try:r=f.result()
                except Exception:
                    failed=True;r={'task':futures[f],'error':traceback.format_exc()}
                    with (out/'errors.jsonl').open('a') as dest:dest.write(json.dumps(r)+'\n')
                    print(r,flush=True);continue
                print(count,r['opponent'],r['seed'],r['seat'],int(r['own_cash']),int(r['margin']),flush=True)
    assert snapshot(directory)==hashes,'candidate mutated during run'
    result=summarize(out,len(tasks));print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)
    if failed or result['completed']!=len(tasks):raise SystemExit(1)
if __name__=='__main__':main()
