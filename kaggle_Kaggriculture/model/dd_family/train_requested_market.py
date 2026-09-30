"""Controlled market-label experiment: keep ddbi goal weights, learn raw requests."""
from pathlib import Path
import hashlib,json,shutil,sys,time
import numpy as np
from sklearn.ensemble import ExtraTreesClassifier,ExtraTreesRegressor
from train_task_policy_v2 import export
B=Path(__file__).resolve().parent;D=B/'ddbj';SOURCE=B/'task_policy_data/ddbj'

def main():
    sys.path.insert(0,str(D));import task_features as F,tree_runtime
    assert not (D/'market_policy.npz').exists();assert (B/'ddbi/training_report.json').exists()
    assert (D/'task_features.py').read_bytes()==(B/'ddbi/task_features.py').read_bytes()
    cfg=json.loads((D/'config.json').read_text());manifest=json.loads((SOURCE/'manifest.json').read_text());assert manifest['completed']==28 and manifest['source_exact_states']
    pools={};seeds={};audits=[]
    for split in ['train','validation']:
        parts=[];seeds[split]=[]
        for p in sorted(SOURCE.glob(split+'_*.npz')):
            a=json.loads(p.with_suffix('.json').read_text());assert hashlib.sha256(p.read_bytes()).hexdigest()==a['sha256'];seeds[split].append(a['source_seed'])
            with np.load(p) as new,np.load(B/'task_policy_data/ddbi'/p.name) as old:
                for key in ['rank_x','rank_y','quantity_x','quantity_y','validation_x','validation_choice','validation_offsets']:
                    if key in new:assert np.array_equal(new[key],old[key]),(p.name,key)
                parts.append({k:new[k] for k in ['market_x','market_y','market_quantity']})
            audits.append(p.name)
        pools[split]={k:np.concatenate([p[k] for p in parts]) for k in parts[0]}
    assert len(set(seeds['train']))==21 and len(set(seeds['validation']))==7 and not set(seeds['train'])&set(seeds['validation'])
    for name in ['goal_rank.npz','goal_quantity.npz']:shutil.copy2(B/'ddbi'/name,D/name)
    tr=pools['train'];va=pools['validation'];report={'source':'Boey 21 train / 7 validation, test unopened','same_goal_training_arrays_as_ddbi':True,'same_goal_weights_as_ddbi':True,'labels':'Requested action token and requested quantity; all intents preserved in prefix, own shadow may fill zero. No future opponent outcome used.','models':{},'seed_split':seeds}
    for name in ['market_policy','market_quantity']:
        start=time.perf_counter()
        if name=='market_policy':
            model=ExtraTreesClassifier(n_estimators=cfg['market_trees'],max_depth=22,min_samples_leaf=1,max_features=1.,class_weight='balanced',n_jobs=4,random_state=cfg['seed']);x=tr['market_x'];y=tr['market_y'];v=va['market_x'];z=va['market_y']
        else:
            m=tr['market_y']>0;n=va['market_y']>0;x=np.concatenate([tr['market_x'][m],F.MHOT[tr['market_y'][m]]],axis=1);y=tr['market_quantity'][m];v=np.concatenate([va['market_x'][n],F.MHOT[va['market_y'][n]]],axis=1);z=va['market_quantity'][n]
            model=ExtraTreesRegressor(n_estimators=cfg['quantity_trees'],max_depth=18,min_samples_leaf=2,max_features=.8,n_jobs=4,random_state=cfg['seed'])
        model.fit(x,y);export(model,D/f'{name}.npz');runtime=tree_runtime.Model(D/f'{name}.npz');sample=v[:2048];expected=model.predict_proba(sample) if name=='market_policy' else model.predict(sample);error=float(np.max(np.abs(expected-runtime.predict(sample))));assert error<1e-6
        result={'train_rows':len(y),'validation_rows':len(z),'train_score':model.score(x,y),'validation_score':model.score(v,z),'export_max_abs_error':error,'seconds':time.perf_counter()-start};report['models'][name]=result;print(name,result,flush=True)
    report['hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.iterdir() if p.suffix in ['.py','.json','.npz']};(D/'training_report.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
