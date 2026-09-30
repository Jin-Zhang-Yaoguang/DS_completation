"""Compile train-only hand-permutation coverage and audit four exact control runs."""
from pathlib import Path
import collections,concurrent.futures,contextlib,copy,gzip,hashlib,io,json
import numpy as np
from worker_orbit_support import canonical
B=Path(__file__).resolve().parent
OUT=B/'prefix_policy_data/worker_orbit'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def compile_one(task):
    k,row=task;p=Path(row['path']);assert sha(p)==row['sha256'];rep=json.loads(p.read_text());seat=row['seat'];keys=[];actions=[]
    for t in range(719):
        obs=dict(rep['steps'][t][0]['observation']);obs.update(rep['steps'][t][seat]['observation']);obs.update(step=t,player=seat)
        state,action=canonical(obs,rep['steps'][t+1][seat]['action']);keys.append(state);actions.append(action)
    return k,keys,actions

def audit_one(seed):
    keys=np.load(OUT/'physical_keys.npy',mmap_mode='r');actions=np.load(OUT/'action_keys.npy',mmap_mode='r')
    with gzip.open(B/f'ddam/runs/broad01/games/y68v_{seed}_0.json.gz','rt') as f:saved=json.load(f)
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        from kaggle_environments.agent import get_last_callable
    op=next(r for r in json.loads((B/'protocol.json').read_text())['opponents'] if r['name']=='y68v');p=B/op['file'];assert sha(p)==op['sha256'];other=get_last_callable(p.read_text(),path=str(p));env=make('kaggriculture',configuration={'seed':seed},debug=False);env.reset(2);rows=[]
    for t in range(719):
        obs=copy.deepcopy(env.state[0].observation);obs.update(step=t,player=0);matched=np.flatnonzero(keys[t]==canonical(obs).encode());choices=len(set(actions[t,matched]));rows.append({'step':t,'matching_sources':len(matched),'joint_action_choices':choices,'source_indices':matched.tolist() if choices>1 else []})
        o=copy.deepcopy(env.state[1].observation);o['step']=t;env.step([saved['trace'][t]['action'],other(o)]);assert env.state[0].observation.farms[0]['money']==saved['trace'][t]['cash']
    assert [float(s.reward) for s in env.state]==[saved['own_cash'],saved['opponent_cash']]
    result={'seed':seed,'exact_719_cash_and_final_rewards':True,'supported_steps':sum(r['matching_sources']>0 for r in rows),'branch_steps':sum(r['joint_action_choices']>1 for r in rows),'branch_after_day3':sum(r['joint_action_choices']>1 for r in rows if r['step']>=72),'branches':[r for r in rows if r['joint_action_choices']>1]}
    (OUT/f'audit_{seed}.json').write_text(json.dumps({**result,'rows':rows},indent=2)+'\n');return result

def main():
    OUT.mkdir(exist_ok=False)
    source=B/'ddam/training_manifest.json';rows=json.loads(source.read_text())['episodes'];assert len(rows)==146 and all(r['split']=='train' for r in rows)
    prior=json.loads((B/'prefix_policy_data/manifest.json').read_text());assert prior['source_manifest_sha256']==sha(source)
    keys=np.empty((719,len(rows)),dtype='S32');actions=np.empty_like(keys)
    with concurrent.futures.ProcessPoolExecutor(max_workers=6) as pool:
        for k,state,action in pool.map(compile_one,enumerate(rows)):keys[:,k]=state;actions[:,k]=action
    np.save(OUT/'physical_keys.npy',keys);np.save(OUT/'action_keys.npy',actions)
    daily=[]
    for day in range(30):
        branches=0
        for t in range(day*24,min(719,(day+1)*24)):
            groups=collections.defaultdict(list)
            for k,state in enumerate(keys[t]):groups[state].append(k)
            branches+=sum(len(set(actions[t,ids]))>1 for ids in groups.values())
        daily.append({'day':day,'branch_groups':branches})
    manifest={'sources':len(rows),'source_manifest_sha256':sha(source),'encoder_sha256':sha(B/'worker_orbit_support.py'),'driver_sha256':sha(Path(__file__)),'hashes':{p.name:sha(p) for p in OUT.glob('*.npy')},'daily':daily,'status':'COVERAGE_UPPER_BOUND_ONLY','restriction':'Worker renumbering does not preserve sequential shared-resource execution automatically; no deployable branching policy claimed.'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'compiled':len(rows),'daily':daily}),flush=True)
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:audits=list(pool.map(audit_one,[919261002,919261005,919262004,919262007]))
    (OUT/'summary.json').write_text(json.dumps(audits,indent=2)+'\n');print(json.dumps(audits),flush=True)
if __name__=='__main__':main()
