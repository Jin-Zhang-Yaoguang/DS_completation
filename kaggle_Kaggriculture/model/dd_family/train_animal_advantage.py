"""Distill single-intervention marginal returns; grouped development validation."""
from pathlib import Path
import hashlib,json,shutil,os
import numpy as np
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor,ExtraTreesRegressor,GradientBoostingRegressor
B=Path(__file__).resolve().parent;D=B/'ddaa';OUT=B/'counterfactual_ddaa'

def main():
    rows=json.loads((OUT/'dataset.json').read_text());assert len(rows)==200
    X=np.asarray([r['features']+[float(r['original']=='COW'),float(r['original']=='GOOSE'),r['count']/5,(r['step']%24)/24] for r in rows],np.float32)
    count=np.array([r['count'] for r in rows]);raw=np.array([r['sheep_advantage'] for r in rows]);y=np.clip(raw/count,-20000,20000)
    val=np.array([r['seed']>=919262000 for r in rows]);assert sum(val)==80
    baseline_rows=[json.loads(x) for x in (OUT/'baseline.jsonl').read_text().splitlines()]
    baseline_choices={(r['seed'],x['group']):x['chosen']=='SHEEP' for r in baseline_rows for x in r['allocations']}
    baseline_selected=np.array([baseline_choices[r['seed'],r['group']] for r in rows])[val]
    baseline_regret=float(np.where(baseline_selected,np.maximum(-raw[val],0),np.maximum(raw[val],0)).mean())
    candidates=[]
    for depth in [2,3,4]:candidates.append((f'tree{depth}',DecisionTreeRegressor(max_depth=depth,min_samples_leaf=8,random_state=723)))
    candidates += [('rf',RandomForestRegressor(n_estimators=96,max_depth=4,min_samples_leaf=6,max_features=.8,random_state=723,n_jobs=1)),('extra',ExtraTreesRegressor(n_estimators=96,max_depth=4,min_samples_leaf=6,max_features=.8,random_state=723,n_jobs=1)),('gbr',GradientBoostingRegressor(n_estimators=64,max_depth=2,min_samples_leaf=8,learning_rate=.04,loss='huber',random_state=723))]
    ranking=[];best=None
    for name,model in candidates:
        model.fit(X[~val],y[~val]);pred=model.predict(X[val]);actual=raw[val]
        regret=np.where(pred>0,np.maximum(-actual,0),np.maximum(actual,0))
        score=float(regret.mean());metric={'name':name,'mean_intervention_regret':score,'sign_accuracy':float(np.mean((pred>0)==(actual>0))),'wrong_switch_loss':float(np.maximum(-actual[pred>0],0).sum()),'validation_switches':int((pred>0).sum())};ranking.append(metric)
        if best is None or score<best[0]:best=(score,name,model)
    _,name,model=best;trees=[];bias=0.
    if isinstance(model,DecisionTreeRegressor):estimators=[model];weights=[1.]
    elif isinstance(model,GradientBoostingRegressor):estimators=[m[0] for m in model.estimators_];weights=[model.learning_rate]*len(estimators);bias=float(model.init_.constant_[0,0])
    else:estimators=model.estimators_;weights=[1/len(estimators)]*len(estimators)
    for estimator,weight in zip(estimators,weights):
        tree=estimator.tree_;trees.append({'left':tree.children_left.tolist(),'right':tree.children_right.tolist(),'feature':tree.feature.tolist(),'threshold':tree.threshold.tolist(),'value':tree.value[:,0,0].tolist(),'weight':weight})
    export={'bias':bias,'trees':trees,'feature_suffix':['original_is_cow','original_is_goose','group_count/5','hour/24'],'decision_threshold':0.,'target':'expected marginal final margin per animal of SHEEP over original animal under ddy continuation'}
    pred=[]
    for x in X:
        z=bias
        for tree in trees:
            n=0
            while tree['left'][n]>=0:n=tree['left'][n] if x[tree['feature'][n]]<=tree['threshold'][n] else tree['right'][n]
            z+=tree['weight']*tree['value'][n]
        pred.append(z)
    assert np.allclose(pred,model.predict(X),atol=1e-8)
    archive=OUT/'source_candidate'
    if archive.exists():raise FileExistsError(archive)
    archive.mkdir();(archive/'data').mkdir()
    for p in D.iterdir():
        if p.is_file():shutil.copy2(p,archive/p.name)
    for p in (D/'data').iterdir():os.link(p,archive/'data'/p.name)
    (D/'advantage_model.json').write_text(json.dumps(export,indent=2)+'\n')
    report={'training_examples':int((~val).sum()),'validation_examples':int(val.sum()),'training_seeds':12,'validation_seeds':8,'chosen':name,'baseline_mean_intervention_regret':baseline_regret,'ranking':ranking,'export_parity':True,'dataset_sha256':hashlib.sha256((OUT/'dataset.json').read_bytes()).hexdigest(),'training_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'caveat':'Single-intervention outcomes do not prove composed policy returns. All seeds are development, including internal validation.'}
    (D/'advantage_training.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
