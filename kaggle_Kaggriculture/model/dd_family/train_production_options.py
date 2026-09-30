"""Fit factorized task policy on source train seeds; export exact numpy inference."""
from pathlib import Path
import argparse,hashlib,json,time
import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier,ExtraTreesClassifier,ExtraTreesRegressor
B=Path(__file__).resolve().parent

def export(model,path,hist=False):
    arrays={k:[] for k in ['feature','threshold','left','right','value']};roots=[];offset=0;depth=0
    if hist:
        trees=[p[0].nodes for p in model._predictors]
        for t in trees:
            n=len(t);leaf=t['is_leaf'].astype(bool);ids=np.arange(n)+offset;roots.append(offset)
            arrays['feature'].append(np.where(leaf,0,t['feature_idx']));arrays['threshold'].append(t['num_threshold']);arrays['left'].append(np.where(leaf,ids,t['left']+offset));arrays['right'].append(np.where(leaf,ids,t['right']+offset));arrays['value'].append(t['value']);depth=max(depth,int(t['depth'].max()));offset+=n
    else:
        for estimator in model.estimators_:
            t=estimator.tree_;n=t.node_count;leaf=t.children_left<0;ids=np.arange(n)+offset;roots.append(offset)
            arrays['feature'].append(np.where(leaf,0,t.feature));arrays['threshold'].append(t.threshold);arrays['left'].append(np.where(leaf,ids,t.children_left+offset));arrays['right'].append(np.where(leaf,ids,t.children_right+offset))
            values=t.value[:,0,:]
            if not hasattr(model,'classes_'):values=values[:,0]
            arrays['value'].append(values);depth=max(depth,t.max_depth);offset+=n
    out={k:np.concatenate(v) for k,v in arrays.items()}
    for k in ['feature','left','right']:out[k]=out[k].astype(np.int32)
    out.update(roots=np.asarray(roots,np.int32),depth=np.asarray(depth),dimensions=np.asarray(model.n_features_in_),kind=np.asarray(0 if hist else 1),baseline=np.asarray(float(model._baseline_prediction[0,0]) if hist else 0))
    if hasattr(model,'classes_'):out['classes']=np.asarray(model.classes_,np.int32)
    np.savez_compressed(path,**out)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('version');a=ap.parse_args();D=B/a.version;source=B/'task_policy_data'/a.version
    import sys;sys.path.insert(0,str(D));import task_features as F,tree_runtime
    assert not (D/'goal_rank.npz').exists(),'Create a new version for a changed trained candidate'
    cfg=json.loads((D/'config.json').read_text());manifest=json.loads((source/'manifest.json').read_text());assert manifest['completed']==28 and manifest['source_exact_states']
    pools={'train':{},'validation':{}};source_seeds={}
    for split in pools:
        paths=sorted(source.glob(split+'_*.npz'));parts=[];source_seeds[split]=[]
        for p in paths:
            audit=json.loads(p.with_suffix('.json').read_text());assert hashlib.sha256(p.read_bytes()).hexdigest()==audit['sha256'];source_seeds[split].append(audit['source_seed'])
            with np.load(p) as z:parts.append({k:z[k] for k in ['rank_x','rank_y','quantity_x','quantity_y','market_x','market_y','market_quantity']})
        for k in parts[0]:pools[split][k]=np.concatenate([p[k] for p in parts])
        del parts
    assert len(set(source_seeds['train']))==21 and len(set(source_seeds['validation']))==7 and not set(source_seeds['train'])&set(source_seeds['validation'])
    tr=pools['train'];va=pools['validation'];report={'version':a.version,'source_seeds':source_seeds,'source_states_verified':28*719,'test_used':False,'selection':'Fixed hyperparameters; validation reported, no test used. Full-candidate metrics every 32nd source query.','models':{}}
    models=[('goal_rank',HistGradientBoostingClassifier(max_iter=cfg['rank_iterations'],max_leaf_nodes=cfg['rank_leaves'],learning_rate=.1,min_samples_leaf=30,l2_regularization=1,early_stopping=False,random_state=cfg['seed']),'rank_x','rank_y'),
            ('goal_quantity',ExtraTreesRegressor(n_estimators=cfg['quantity_trees'],max_depth=18,min_samples_leaf=2,n_jobs=4,random_state=cfg['seed']),'quantity_x','quantity_y'),
            ('market_policy',ExtraTreesClassifier(n_estimators=cfg['market_trees'],max_depth=22,min_samples_leaf=1,max_features=1.,class_weight='balanced',n_jobs=4,random_state=cfg['seed']),'market_x','market_y')]
    for name,model,xkey,ykey in models:
        start=time.perf_counter()
        weights=None
        if name=='goal_rank':
            starts=np.flatnonzero(tr['rank_y']);ends=np.r_[starts[1:],len(tr['rank_y'])];tokens=tr['rank_x'][starts,-(F.UT+11):-11].argmax(1);counts=np.bincount(tokens,minlength=F.UT);w=np.minimum(8,np.sqrt(counts.max()/np.maximum(1,counts[tokens])));w*=np.where(tr['rank_x'][starts,0]<3,4,1);weights=np.repeat(w,ends-starts)
        model.fit(tr[xkey],tr[ykey],sample_weight=weights);export(model,D/f'{name}.npz',name=='goal_rank');runtime=tree_runtime.Model(D/f'{name}.npz');x=va[xkey][:2048]
        expected=model.decision_function(x) if name=='goal_rank' else model.predict_proba(x) if name=='market_policy' else model.predict(x)
        error=float(np.max(np.abs(expected-runtime.predict(x))));assert error<1e-6,(name,error)
        r={'train_rows':len(tr[ykey]),'validation_rows':len(va[ykey]),'train_score':model.score(tr[xkey],tr[ykey]),'validation_score':model.score(va[xkey],va[ykey]),'export_max_abs_error':error,'seconds':time.perf_counter()-start}
        if name=='goal_rank':
            valid=[]
            for p in sorted(source.glob('validation_*.npz')):
                with np.load(p) as z:
                    scores=runtime.predict(z['validation_x']);offsets=z['validation_offsets'];labels=z['validation_choice']
                    for j,chosen in enumerate(labels):
                        v=scores[offsets[j]:offsets[j+1]];valid.append({'candidates':len(v),'top1':int(v.argmax())==int(chosen),'top5':int(chosen) in np.argsort(v)[-5:]})
            r['full_option_candidate_validation']={'queries':len(valid),'top1':float(np.mean([v['top1'] for v in valid])),'top5':float(np.mean([v['top5'] for v in valid])),'mean_candidates':float(np.mean([v['candidates'] for v in valid]))}
        report['models'][name]=r;print(name,json.dumps(r),flush=True)
    start=time.perf_counter();train_mask=(tr['market_y']>0)&(tr['market_y']<F.WAIT_MARKET);valid_mask=(va['market_y']>0)&(va['market_y']<F.WAIT_MARKET)
    x=np.concatenate([tr['market_x'][train_mask],F.MHOT[tr['market_y'][train_mask]]],axis=1);v=np.concatenate([va['market_x'][valid_mask],F.MHOT[va['market_y'][valid_mask]]],axis=1)
    model=ExtraTreesRegressor(n_estimators=cfg['quantity_trees'],max_depth=18,min_samples_leaf=2,max_features=.8,n_jobs=4,random_state=cfg['seed']);model.fit(x,tr['market_quantity'][train_mask]);export(model,D/'market_quantity.npz');runtime=tree_runtime.Model(D/'market_quantity.npz');err=float(np.max(np.abs(runtime.predict(v)-model.predict(v))));assert err<1e-6
    report['models']['market_quantity']={'train_rows':len(x),'validation_rows':len(v),'train_score':model.score(x,tr['market_quantity'][train_mask]),'validation_score':model.score(v,va['market_quantity'][valid_mask]),'export_max_abs_error':err,'seconds':time.perf_counter()-start}
    report['algorithm']='Offline supervised gradient-boosted production-option ranking and ExtraTrees quantities/market. Not PPO, self-play, or oracle relabelling.'
    report['hashes']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in D.iterdir() if p.suffix in ['.py','.npz','.json']}
    (D/'training_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report['models']['market_quantity']),flush=True)
if __name__=='__main__':main()
