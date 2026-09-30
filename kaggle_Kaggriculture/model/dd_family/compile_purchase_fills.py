"""Replay official games and record actual animal purchases, not request sizes."""
from pathlib import Path
import concurrent.futures,contextlib,copy,hashlib,importlib,io,json,sys
import numpy as np
B=Path(__file__).resolve().parent;OUT=B/'executed_purchase_labels'

def run(task):
    source,k=task
    with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments import make
        eng=importlib.import_module('kaggle_environments.envs.kaggriculture.kaggriculture')
    row=json.loads((B/source/'training_manifest.json').read_text())['episodes'][k]
    raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];rep=json.loads(raw);seat=row['seat']
    cfg=dict(rep['configuration']);cfg['seed']=rep['info']['seed'];env=make('kaggriculture',configuration=cfg);env.reset(2)
    animals=['GOOSE','COW','SHEEP'];filled=np.zeros((719,3),np.int32);requested=np.zeros((719,3),np.int32);now=[0];original=eng._commit_unit
    def commit(op,item,price,farm,private,market,capacity=100):
        frame=sys._getframe(1);player=frame.f_locals['player_id']
        ok=original(op,item,price,farm,private,market,capacity)
        if ok and player==seat and op=='BUY_ANIMAL':filled[now[0],animals.index(item)]+=1
        return ok
    eng._commit_unit=commit
    checks=0
    try:
        for t in range(719):
            now[0]=t;actions=[copy.deepcopy(s['action']) for s in rep['steps'][t+1]]
            for order in actions[seat].get('market',[]):
                if order[0]=='BUY_ANIMAL':requested[t,animals.index(order[1])]+=int(order[2])
            env.step(actions)
            for player in [0,1]:
                ref=dict(rep['steps'][t+1][0]['observation']);ref.update(rep['steps'][t+1][player]['observation'])
                for field in ['farms','private','market','town','day','hour']:
                    assert env.state[player].observation[field]==ref[field],(source,k,t,player,field)
                    checks+=1
    finally:eng._commit_unit=original
    rewards=[float(s.reward) for s in env.state];assert rewards==rep['rewards'];assert np.all(filled<=requested)
    if source=='dde':
        sys.path.insert(0,str(B/'dde'));import action_space as a
        canon=np.load(B/'executed_new_teacher'/f'{k:03}_effective.npz')
        for j,item in enumerate(animals):
            ref=np.where(canon['market_tokens']==a.MARKET_INDEX['BUY_ANIMAL:'+item],canon['market_quantities'],0).sum(1)
            assert np.array_equal(ref,filled[:,j]),(source,k,item)
    target=OUT/source;target.mkdir(exist_ok=True,parents=True);np.savez_compressed(target/f'{k:03}.npz',filled=filled,requested=requested)
    audit={'source':source,'prototype':k,'source_sha256':row['sha256'],'field_checks':checks,'exact_rewards':True,'requested_animals':int(requested.sum()),'filled_animals':int(filled.sum()),'request_turns':int((requested.sum(1)>0).sum()),'fill_turns':int((filled.sum(1)>0).sum()),'zero_fill_turns':int(((requested.sum(1)>0)&(filled.sum(1)==0)).sum()),'clipped_turns':int(np.any(requested!=filled,axis=1).sum()),'label_sha256':hashlib.sha256((target/f'{k:03}.npz').read_bytes()).hexdigest()}
    (target/f'{k:03}.json').write_text(json.dumps(audit,indent=2)+'\n');return audit

def main():
    OUT.mkdir(exist_ok=True);tasks=[(s,k) for s in ['ddm','dde','ddo'] for k in range(len(json.loads((B/s/'training_manifest.json').read_text())['episodes']))]
    rows=[];pending=[]
    for s,k in tasks:
        p=OUT/s/f'{k:03}.json'
        if p.exists():rows.append(json.loads(p.read_text()))
        else:pending.append((s,k))
    print('pending',len(pending),flush=True)
    for offset in range(0,len(pending),24):
        with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:
            for row in pool.map(run,pending[offset:offset+24]):
                rows.append(row)
                if len(rows)%20==0:print('compiled',len(rows),flush=True)
    summary={key:sum(r[key] for r in rows) for key in ['field_checks','requested_animals','filled_animals','request_turns','fill_turns','zero_fill_turns','clipped_turns']}
    result={'episodes':len(rows),'expected':len(tasks),'summary':summary,'compiler_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'rows':sorted(rows,key=lambda r:(r['source'],r['prototype']))}
    assert len(rows)==len(tasks);(OUT/'manifest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(summary),flush=True)
if __name__=='__main__':main()
