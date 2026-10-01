import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='8'
import gc,hashlib,json,signal,time,resource,traceback,warnings
from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(name,data):
 p=HERE/(name+'.tmp');p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');p.replace(HERE/name)
def run():
 c=json.loads((HERE/'preregistration.json').read_text());t=time.monotonic()
 def guard():
  assert time.monotonic()-t<c['budget_seconds'],'time budget'
  assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<c['rss_gib']*1024**3,'RSS budget'
 def timeout(*_):raise TimeoutError('wall budget')
 signal.signal(signal.SIGALRM,timeout);signal.alarm(c['budget_seconds'])
 for name,digest in c['source_hashes'].items():assert sha(ROOT/name)==digest,name
 with (HERE/'RUN_STARTED.json').open('x') as f:json.dump({'pid':os.getpid(),'time':time.time(),'code_sha256':sha(Path(__file__)),'prereg_sha256':sha(HERE/'preregistration.json')},f)
 source=ROOT/'model/validation/e2e_v100_20260905/feature_backends.py';text=source.read_text()
 old='return train_frame[features].reset_index(drop=True), te_cols'
 new='return train_frame[features].reset_index(drop=True), test_frame[features].reset_index(drop=True), te_cols'
 assert text.count(old)==1
 # Only expose the already-built test feature frame; frozen feature operations unchanged.
 adapted=text.replace(old,new);(HERE/'feature_adapter_snapshot.py').write_text(adapted)
 ns={'__file__':str(source),'__name__':'prior_online_feature_adapter'};exec(compile(adapted,str(source),'exec'),ns)
 train=pd.read_csv(ROOT/'data/train.csv');test=pd.read_csv(ROOT/'data/test.csv');orig=pd.read_csv(ROOT/'data/original_dataset/EV_Adoption_and_Range_Anxiety_Dataset.csv');sample=pd.read_csv(ROOT/'data/sample_submission.csv')
 y=train.Will_Buy_EV.map({'Yes':1,'No':0}).to_numpy();assert np.isfinite(y).all();n=len(y);nt=len(test)
 assert list(sample)==['id','Will_Buy_EV'] and np.array_equal(sample.id,test.id)
 with warnings.catch_warnings():
  warnings.simplefilter('ignore');tr,te,cols=ns['build_naji_static'](train.drop(columns='Will_Buy_EV'),test,orig)
 assert list(tr)==list(te) and len(tr)==n and len(te)==nt
 backend=ns['Backend']('v85',pd.concat([tr,te],ignore_index=True),te_columns=cols);del tr,te;gc.collect()
 orig['label']=orig.Will_Buy_EV.map({'Yes':1,'No':0});mu=orig.label.mean();stats=orig.groupby('Annual_Income_USD').label.agg(['sum','count'])
 income=pd.concat([train.Annual_Income_USD,test.Annual_Income_USD],ignore_index=True);counts=income.map(stats['count']).fillna(0).to_numpy();sums=income.map(stats['sum']).fillna(0).to_numpy();replacement=(sums+2*mu)/(counts+2)
 column='Annual_Income_USD_org_mean';assert column not in cols
 reference=np.load(ROOT/'model/diagnostics/original_prior_reliability_20260905/diagnostic_oof.npz',allow_pickle=False);assert np.array_equal(reference['ids'],train.id)
 params=json.loads((ROOT/'model/v85_naji_v74_40f/frozen_config.json').read_text())['lightgbm_base_params']
 oof=np.full(n,np.nan);pred=np.zeros(nt);rows=[]
 for fold,(fit,valid) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(np.zeros(n),y),1):
  guard();print('FOLD_START',fold,flush=True);query=np.concatenate([valid,np.arange(n,n+nt)])
  with warnings.catch_warnings():
   warnings.simplefilter('ignore');xf,xq,names=backend.encode(fit,y[fit],query,42+fold)
  j=names.index(column);xf[:,j]=replacement[fit];xq[:,j]=replacement[query];seed=42+fold
  model=lgb.LGBMClassifier(**params,**{k:seed for k in ('random_state','bagging_seed','feature_fraction_seed','data_random_seed')})
  model.fit(xf,y[fit],eval_set=[(xq[:len(valid)],y[valid])],callbacks=[lgb.early_stopping(350,verbose=False)])
  probs=model.predict_proba(xq)[:,1];assert np.isfinite(probs).all() and ((probs>=0)&(probs<=1)).all()
  error=float(np.max(np.abs(probs[:len(valid)]-reference['b'][valid])));assert error<=c['require_reference_reproduction_max_abs'],error
  oof[valid]=probs[:len(valid)];pred+=probs[len(valid):]/5
  model.booster_.save_model(str(HERE/f'fold_{fold}.txt'))
  np.savez(HERE/f'fold_{fold}.npz',valid_rows=valid,valid_ids=train.id.to_numpy()[valid],valid_proba=probs[:len(valid)],test_ids=test.id.to_numpy(),test_proba=probs[len(valid):])
  rows.append({'fold':fold,'auc':roc_auc_score(y[valid],oof[valid]),'best_iteration':model.best_iteration_,'reference_max_abs':error});write('progress.json',{'folds':rows,'elapsed_seconds':time.monotonic()-t});print(json.dumps(rows[-1]),flush=True)
  del xf,xq,model,probs;gc.collect();guard()
 assert np.isfinite(oof).all();assert np.array_equal(oof,reference['b']);assert np.isfinite(pred).all() and ((pred>=0)&(pred<=1)).all()
 np.save(HERE/'oof_proba.npy',oof);np.save(HERE/'test_proba.npy',pred);sample['Will_Buy_EV']=pred;sample.to_csv(HERE/'submission.csv',index=False)
 guard();write('result.json',{'status':'COMPLETE_EXPLORATORY_REBUILD','oof_auc':roc_auc_score(y,oof),'reference_max_abs':float(np.max(np.abs(oof-reference['b']))),'folds':rows,'elapsed_seconds':time.monotonic()-t,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'submission_sha256':sha(HERE/'submission.csv'),'code_sha256':sha(Path(__file__)),'superiority_to_v100_proven':False,'research_promotion':False,'submission_budget':1});signal.alarm(0)
if __name__=='__main__':
 try:run()
 except BaseException:write('failure.json',{'status':'FAILED','traceback':traceback.format_exc()});raise
