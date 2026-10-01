"""Fixed source-prior reliability paired diagnostic; never emits test predictions."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[key]='8'
import gc, hashlib, importlib.util, json, resource, signal, time, traceback, warnings
from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,data):
    temp=HERE/(name+'.tmp');temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');temp.replace(HERE/name)
def shrink(s,n,mu,mass): return (s+mass*mu)/(n+mass)
def run():
    cfg=json.loads((HERE/'diagnostic_preregistration.json').read_text())
    for path,digest in cfg['source_hashes'].items():
        p=HERE/path if path=='support_audit.json' else ROOT/path
        assert sha(p)==digest,path
    assert shrink(1.,1.,.2,2.)==1.4/3.
    assert shrink(0.,0.,.2,2.)==.2
    start=time.monotonic()
    def guard():
        assert time.monotonic()-start < cfg['budget_seconds'],'wall budget'
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss < cfg['rss_gib']*1024**3,'RSS budget'
    def deadline(*_): raise TimeoutError('hard wall budget')
    signal.signal(signal.SIGALRM,deadline);signal.alarm(cfg['budget_seconds'])
    with (HERE/'RUN_STARTED.json').open('x') as f:
        json.dump({'pid':os.getpid(),'started_unix':time.time(),'code_sha256':sha(Path(__file__)),'prereg_sha256':sha(HERE/'diagnostic_preregistration.json')},f)
    path=ROOT/'model/validation/e2e_v100_20260905/feature_backends.py'
    spec=importlib.util.spec_from_file_location('frozen_prior_backend',path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore');backend=mod.load_backend('v85')
    train=pd.read_csv(ROOT/'data/train.csv');original=pd.read_csv(ROOT/'data/original_dataset/EV_Adoption_and_Range_Anxiety_Dataset.csv')
    y=train.Will_Buy_EV.map({'Yes':1,'No':0}).to_numpy();assert np.isfinite(y).all()
    original['label']=original.Will_Buy_EV.map({'Yes':1,'No':0});mu=original.label.mean()
    stats=original.groupby('Annual_Income_USD').label.agg(['sum','count']);income=train.Annual_Income_USD
    n=income.map(stats['count']).fillna(0).to_numpy();s=income.map(stats['sum']).fillna(0).to_numpy()
    candidate=shrink(s,n,mu,cfg['source_prior_mass'])
    old=np.divide(s,n,out=np.full(len(n),mu,dtype=float),where=n>0)
    column='Annual_Income_USD_org_mean'
    assert column not in backend.te_columns
    np.testing.assert_allclose(backend.static[column].to_numpy(),old,rtol=0,atol=1e-15)
    params=json.loads((ROOT/'model/v85_naji_v74_40f/frozen_config.json').read_text())['lightgbm_base_params'];assert params['n_jobs']==8
    oof=np.full((len(y),2),np.nan);fold_ids=np.full(len(y),-1,dtype=np.int8);rows=[]
    for fold,(fit,valid) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(np.zeros(len(y)),y),1):
        guard();print('FOLD_START',fold,flush=True)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore');xf,xv,names=backend.encode(fit,y[fit],valid,42+fold)
        j=names.index(column);np.testing.assert_allclose(xf[:,j],old[fit],atol=1e-15,rtol=0)
        foldrow={'fold':fold,'rows':len(valid),'arms':[]}
        for arm in range(2):
            if arm: xf[:,j]=candidate[fit];xv[:,j]=candidate[valid]
            seed=42+fold;model=lgb.LGBMClassifier(**params,**{k:seed for k in ('random_state','bagging_seed','feature_fraction_seed','data_random_seed')})
            model.fit(xf,y[fit],eval_set=[(xv,y[valid])],callbacks=[lgb.early_stopping(350,verbose=False)])
            pred=model.predict_proba(xv)[:,1];assert np.isfinite(pred).all() and ((pred>=0)&(pred<=1)).all()
            oof[valid,arm]=pred;foldrow['arms'].append({'auc':roc_auc_score(y[valid],pred),'iterations':model.best_iteration_});del model;guard()
        foldrow['delta']=foldrow['arms'][1]['auc']-foldrow['arms'][0]['auc'];rows.append(foldrow);fold_ids[valid]=fold
        np.savez(HERE/f'fold_{fold}.npz',valid_ids=train.id.to_numpy()[valid],valid_rows=valid,a=oof[valid,0],b=oof[valid,1])
        write('progress.json',{'folds':rows,'elapsed_seconds':time.monotonic()-start});print(json.dumps(foldrow),flush=True)
        del xf,xv;gc.collect()
    assert np.isfinite(oof).all() and (fold_ids>0).all()
    a,b=[roc_auc_score(y,oof[:,i]) for i in range(2)];wins=sum(r['delta']>0 for r in rows)
    np.savez(HERE/'diagnostic_oof.npz',ids=train.id.to_numpy(),fold=fold_ids,a=oof[:,0],b=oof[:,1])
    guard();write('result.json',{'status':'COMPLETE_DIAGNOSTIC','a_auc':a,'b_auc':b,'delta':b-a,'positive_folds':wins,'diagnostic_gate_passed':b>a and wins==5,'research_strength_passed':b-a>=.0001 and wins==5,'folds':rows,'elapsed_seconds':time.monotonic()-start,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'code_sha256':sha(Path(__file__)),'oof_sha256':sha(HERE/'diagnostic_oof.npz'),'submission_allowed':False,'test_predictions_generated':False});signal.alarm(0)
if __name__=='__main__':
    try:run()
    except BaseException:
        write('failure.json',{'status':'FAILED','traceback':traceback.format_exc()});raise
