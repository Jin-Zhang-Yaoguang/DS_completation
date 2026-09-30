"""Extract actual sales with features before either player's current actions.

Only item stock already present at decision time is included; same-turn deposits
are excluded from labels to avoid applying post-action features to pre-action
inference. Every full source replay is independently state-checked.
"""
from pathlib import Path
import concurrent.futures,contextlib,copy,hashlib,importlib,io,json,sys
import numpy as np
B=Path(__file__).resolve().parent;OUT=B/'executed_sale_labels'

def run(task):
    source,k=task
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        eng=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
    sys.path.insert(0,str(B/'ddat'));import sale_policy as policy
    row=json.loads((B/source/'training_manifest.json').read_text())['episodes'][k];raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];rep=json.loads(raw);seat=row['seat'];cfg=dict(rep['configuration']);cfg['seed']=rep['info']['seed']
    env=make('kaggriculture',configuration=cfg);env.reset(2);now=[0];filled=np.zeros((719,3),np.int32);features=np.zeros((719,3,len(policy.FEATURES)),np.float32);available=np.zeros((719,3),np.int32);post_unit=np.zeros((719,3),np.int32)
    commit=eng._commit_unit;market=eng._process_market
    def hook_commit(op,item,price,farm,private,ms,capacity=100):
        player=sys._getframe(1).f_locals['player_id'];ok=commit(op,item,price,farm,private,ms,capacity)
        if ok and player==seat and op=='SELL' and item in policy.ITEMS:filled[now[0],policy.ITEMS.index(item)]+=1
        return ok
    def hook_market(state,environment):
        for j,item in enumerate(policy.ITEMS):post_unit[now[0],j]=state[seat].observation.private['shed'].get(item,0)
        return market(state,environment)
    eng._commit_unit=hook_commit;eng._process_market=hook_market;checks=0
    try:
        for t in range(719):
            now[0]=t;obs=copy.deepcopy(env.state[seat].observation);obs['step']=t
            for j,item in enumerate(policy.ITEMS):
                available[t,j]=obs['private']['shed'].get(item,0)
                if available[t,j]>0:features[t,j]=policy.features(obs,item)
            env.step([copy.deepcopy(s['action']) for s in rep['steps'][t+1]])
            for player in [0,1]:
                ref=dict(rep['steps'][t+1][0]['observation']);ref.update(rep['steps'][t+1][player]['observation'])
                for field in ['farms','private','market','town','day','hour']:
                    assert env.state[player].observation[field]==ref[field],(source,k,t,player,field);checks+=1
    finally:eng._commit_unit=commit;eng._process_market=market
    rewards=[float(s.reward) for s in env.state];assert rewards==rep['rewards']
    eligible=(available>0)&(post_unit==available)
    assert np.all(filled[eligible]<=available[eligible])
    target=OUT/source;target.mkdir(exist_ok=True,parents=True)
    np.savez_compressed(target/f'{k:03}.npz',features=features,available=available,filled=filled,eligible=eligible)
    audit={'source':source,'prototype':k,'source_sha256':row['sha256'],'seed':row['seed'],'field_checks':checks,'samples':int(eligible.sum()),'sale_samples':int((eligible&(filled>0)).sum()),'partial_sale_samples':int((eligible&(filled>0)&(filled<available)).sum()),'excluded_stock_changes':int(((available>0)&(post_unit!=available)).sum()),'label_sha256':hashlib.sha256((target/f'{k:03}.npz').read_bytes()).hexdigest()}
    (target/f'{k:03}.json').write_text(json.dumps(audit,indent=2)+'\n');return audit

def main():
    OUT.mkdir(exist_ok=True);tasks=[(s,k) for s in ['ddm','dde','ddo'] for k in range(len(json.loads((B/s/'training_manifest.json').read_text())['episodes']))];rows=[];pending=[]
    for s,k in tasks:
        p=OUT/s/f'{k:03}.json'
        if p.exists():rows.append(json.loads(p.read_text()))
        else:pending.append((s,k))
    print('pending',len(pending),flush=True)
    for offset in range(0,len(pending),24):
        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
            for r in pool.map(run,pending[offset:offset+24]):
                rows.append(r)
                if len(rows)%20==0:print('compiled',len(rows),flush=True)
    result={'episodes':len(rows),'expected':len(tasks),'summary':{key:sum(r[key] for r in rows) for key in ['field_checks','samples','sale_samples','partial_sale_samples','excluded_stock_changes']},'compiler_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'feature_sha256':hashlib.sha256((B/'ddat/sale_policy.py').read_bytes()).hexdigest(),'rows':sorted(rows,key=lambda r:(r['source'],r['prototype']))}
    assert len(rows)==len(tasks);(OUT/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['summary']),flush=True)
if __name__=='__main__':main()
