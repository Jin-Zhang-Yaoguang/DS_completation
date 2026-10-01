"""Donor-only income composition inversion added to frozen V85 5-fold features."""
from __future__ import annotations
import os
for _key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_key]='6'
import datetime,fcntl,hashlib,importlib.util,json,platform,resource,sys,time,traceback,warnings,gc
from pathlib import Path
import lightgbm as lgb,numpy as np,pandas as pd
from scipy.special import expit,logit
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder,StandardScaler
from threadpoolctl import threadpool_limits
HERE=Path(__file__).resolve().parent;TOP=HERE.parent;ROOT=HERE.parents[2];P1=TOP/'p1_source_group_constraints_5f';STATUS=TOP/'status.json';BACKEND=ROOT/'model/validation/e2e_v100_20260905/feature_backends.py'
NUM=['Age','Daily_Commute_km','Charging_Stations_Near_Home','Charging_Stations_Near_Work','Environmental_Concern_Level']
CAT=['Gender','City_Type','Current_Car_Type','Home_Charging_Possible','Subsidy_Available','Range_Anxiety_Level']
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def write(p,d):
 t=p.with_name(p.name+'.tmp')
 with t.open('w') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 t.replace(p)
def log(x):
 s=f'{now()} {x}';print(s,flush=True)
 with (HERE/'train_log.txt').open('a') as f:f.write(s+'\n')
def rss():
 x=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss;return int(x if platform.system()=='Darwin' else x*1024)
def guard(start):
 if time.monotonic()-start>=7200:raise TimeoutError('P2 120min budget exhausted')
 if rss()>16*1024**3:raise MemoryError('P2 16 GiB budget exhausted')
def prob(x,n):
 if x.shape!=(n,) or not np.isfinite(x).all() or ((x<0)|(x>1)).any():raise ValueError('invalid probabilities')
def load_backend():
 s=importlib.util.spec_from_file_location('p2_v85_backend',BACKEND);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
 with warnings.catch_warnings():warnings.simplefilter('ignore');return m.load_backend('v85')
def model():
 pre=ColumnTransformer([('num',StandardScaler(),NUM),('cat',OneHotEncoder(handle_unknown='ignore',dtype=np.float32),CAT)],remainder='drop',sparse_threshold=.3)
 return Pipeline([('pre',pre),('lr',LogisticRegression(C=1.0,solver='lbfgs',max_iter=200,class_weight=None))])
def state(raw,y,donor):
 frame=raw.iloc[donor];labels=y[donor];m=model();m.fit(frame[NUM+CAT],labels)
 eta=logit(np.clip(m.predict_proba(frame[NUM+CAT])[:,1],1e-6,1-1e-6))
 income=frame['Annual_Income_USD'].to_numpy();keys,code=np.unique(income,return_inverse=True);n=np.bincount(code,minlength=len(keys)).astype(float);sy=np.bincount(code,weights=labels,minlength=len(keys));prior=float(labels.mean());alpha=20.0
 p=(sy+alpha*prior)/(n+alpha);prior_eta=float(logit(prior));raw_shift=logit(np.clip(p,1e-8,1-1e-8))-prior_eta;shift=np.clip(raw_shift,-6,6)
 for _ in range(12):
  z=expit(eta+shift[code]);s=np.bincount(code,weights=z,minlength=len(keys));h=np.bincount(code,weights=z*(1-z),minlength=len(keys));q=expit(prior_eta+shift)
  curve=(s+alpha*q)/(n+alpha);gradient=(h+alpha*q*(1-q))/(n+alpha);shift=np.clip(shift+(p-curve)/np.maximum(gradient,1e-7),-6,6)
 curve=(np.bincount(code,weights=expit(eta+shift[code]),minlength=len(keys))+alpha*expit(prior_eta+shift))/(n+alpha)
 if not np.isfinite(shift).all() or float(np.max(np.abs(curve-p)))>1e-3:raise ValueError('composition inversion did not converge')
 return {'keys':keys,'shift':shift,'offset':shift-raw_shift,'counts':n,'prior':prior,'max_curve_error':float(np.max(np.abs(curve-p)))}
def transform(st,income):
 income=np.asarray(income);idx=np.searchsorted(st['keys'],income);safe=np.minimum(idx,len(st['keys'])-1);seen=(idx<len(st['keys']))&(st['keys'][safe]==income)
 out=np.zeros((len(income),2),dtype=np.float32);out[seen,0]=st['shift'][safe[seen]];out[seen,1]=st['offset'][safe[seen]]
 if not np.isfinite(out).all():raise ValueError('nonfinite composition features')
 return out,seen
def composition_fold(raw,y,fit,valid,fold):
 inner=list(StratifiedKFold(5,shuffle=True,random_state=42+fold).split(np.zeros(len(fit)),y[fit]))
 zfit=np.full((len(fit),2),np.nan,np.float32);coverage=np.zeros(len(fit),np.int8);inner_rows=[]
 for k,(donor_local,hold_local) in enumerate(inner,1):
  donor=fit[donor_local];hold=fit[hold_local];assert not np.intersect1d(donor,hold).size
  st=state(raw,y,donor);vals,seen=transform(st,raw.iloc[hold]['Annual_Income_USD'].to_numpy());zfit[hold_local]=vals;coverage[hold_local]+=1
  inner_rows.append({'inner_fold':k,'donor_rows':len(donor),'hold_rows':len(hold),'income_groups':len(st['keys']),'seen_fraction':float(seen.mean()),'max_curve_error':st['max_curve_error'],'donor_idx_sha256':hashlib.sha256(donor.tobytes()).hexdigest(),'hold_idx_sha256':hashlib.sha256(hold.tobytes()).hexdigest()})
 if not np.all(coverage==1) or not np.isfinite(zfit).all():raise ValueError('inner composition coverage incomplete')
 outer=state(raw,y,fit);zvalid,seen=transform(outer,raw.iloc[valid]['Annual_Income_USD'].to_numpy())
 return zfit,zvalid,{'inner':inner_rows,'outer_income_groups':len(outer['keys']),'outer_seen_fraction':float(seen.mean()),'outer_max_curve_error':outer['max_curve_error']}
def update(phase,fold=None,**more):
 d=json.loads(STATUS.read_text());d.update({'updated_at_utc':now(),'phase':phase,'current_experiment':'p2_composition_shift_5f','process':{'pid':os.getpid(),'active':phase=='P2_RUNNING'},'checkpoint':{'fold':fold,'of':5} if fold else None});d.update(more);write(STATUS,d)
def preflight():
 cfg=json.loads((HERE/'preregistration.json').read_text());p1=json.loads((P1/'result.json').read_text());verify=json.loads((P1/'verification.json').read_text());freeze=json.loads((P1/'freeze_manifest.json').read_text())
 if p1['status']!='COMPLETE_DIAGNOSTIC' or verify['status']!='PASS':raise ValueError('P1 matched A control invalid')
 for rel,record in freeze['source_files'].items():
  if sha(ROOT/rel)!=record['sha256']:raise ValueError(f'source drift {rel}')
 if lgb.__version__!='4.6.0':raise ValueError('LightGBM drift')
 raw=pd.read_csv(ROOT/'data/train.csv');y=raw.Will_Buy_EV.eq('Yes').to_numpy(np.int8);ids=raw.id.to_numpy(np.int64)
 if hashlib.sha256(y.tobytes()).hexdigest()!=freeze['labels_sha256'] or hashlib.sha256(ids.tobytes()).hexdigest()!=freeze['raw_train_ids_sha256']:raise ValueError('row identity drift')
 backend=load_backend();expected=[c for c in backend.static if c not in backend.te_columns]+[f'{c}_TE_{tag}' for tag in ('auto','10') for c in backend.te_columns]
 if len(expected)!=148 or hashlib.sha256(pd.util.hash_pandas_object(backend.static,index=False).to_numpy(np.uint64).tobytes()).hexdigest()!=freeze['pre_te_train_values_sha256']:raise ValueError('V85 source mismatch')
 folds=list(StratifiedKFold(5,shuffle=True,random_state=42).split(np.zeros(len(y)),y));saved=np.load(P1/'fold_assignments_5f_seed42.npy')
 for k,(_,va) in enumerate(folds,1):
  if not np.all(saved[va]==k):raise ValueError('fold drift')
 old_a=np.load(P1/'oof_a.npy');prob(old_a,len(y));assert abs(float(roc_auc_score(y,old_a))-p1['pooled_oof_auc']['A'])<1e-12
 contract={'prereg_sha256':sha(HERE/'preregistration.json'),'runner_sha256':sha(Path(__file__)),'p1_result_sha256':sha(P1/'result.json'),'p1_verification_sha256':sha(P1/'verification.json'),'p1_a_oof_sha256':sha(P1/'oof_a.npy'),'p1_freeze_sha256':sha(P1/'freeze_manifest.json'),'v85_backend_sha256':sha(BACKEND)}
 contract_sha=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
 write(HERE/'preflight.json',{'status':'PASS','at_utc':now(),'contract':contract,'contract_sha256':contract_sha,'a_auc':p1['pooled_oof_auc']['A'],'feature_count_b':150})
 return raw,y,backend,folds,old_a,expected,contract_sha

def train():
 start=time.monotonic();raw,y,backend,folds,old_a,names,contract_sha=preflight();lock=HERE/'run.lock'
 with lock.open('a+') as h:
  try:fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise RuntimeError('P2 already running')
  h.seek(0);h.truncate();h.write(json.dumps({'pid':os.getpid(),'contract_sha256':contract_sha,'at_utc':now()}));h.flush();os.fsync(h.fileno())
  if (HERE/'result.json').exists():raise RuntimeError('P2 result already exists')
  write(HERE/'RUN_STARTED.json',{'pid':os.getpid(),'contract_sha256':contract_sha,'at_utc':now()});update('P2_RUNNING',next_action='Train donor-only composition five-fold diagnostic')
  log(f'P2 started pid={os.getpid()} contract={contract_sha}')
  base=json.loads((ROOT/'model/v85_naji_v74_40f/frozen_config.json').read_text());params=base['lightgbm_base_params'].copy();assert params['n_jobs']==8;params['n_jobs']=6
  oof=np.full(len(y),np.nan);rows=[]
  with threadpool_limits(limits=6):
   for fold,(fit,valid) in enumerate(folds,1):
    guard(start);path=HERE/f'fold_{fold:02d}.npz';modelpath=HERE/f'fold_{fold:02d}.txt'
    if path.exists():
     with np.load(path,allow_pickle=False) as z:
      if int(z['fold'])!=fold or str(z['contract_sha256'])!=contract_sha or not np.array_equal(z['valid_idx'],valid) or str(z['model_sha256'])!=sha(modelpath):raise ValueError('P2 checkpoint mismatch')
      pred=z['pred'].astype(float);prob(pred,len(valid));auc=float(z['auc']);assert abs(roc_auc_score(y[valid],pred)-auc)<1e-12
      info=json.loads(str(z['composition_info_json']))
     log(f'fold={fold} resumed')
    else:
     tic=time.monotonic();zfit,zvalid,info=composition_fold(raw,y,fit,valid,fold);guard(start)
     xf,xv,base_names=backend.encode(fit,y[fit],valid,42+fold)
     if base_names!=names:raise ValueError('V85 base feature schema mismatch')
     xf=np.column_stack([xf,zfit]);xv=np.column_stack([xv,zvalid]);b_names=names+['composition_shift','composition_adjustment']
     if xf.shape[1]!=150 or xv.shape[1]!=150:raise ValueError('P2 final feature width mismatch')
     params_fold=params.copy();seed=42+fold
     for key in base['lightgbm_fold_seed_fields']:params_fold[key]=seed
     model=lgb.LGBMClassifier(**params_fold)
     model.fit(xf,y[fit],eval_set=[(xv,y[valid])],eval_metric='auc',feature_name=b_names,callbacks=[lgb.early_stopping(350,verbose=False),lgb.log_evaluation(period=0)])
     if model.booster_.feature_name()!=b_names:raise ValueError('model feature names mismatch')
     best=int(model.best_iteration_ or params['n_estimators']);pred=model.predict_proba(xv,num_iteration=best)[:,1].astype(float);prob(pred,len(valid));auc=float(roc_auc_score(y[valid],pred))
     tmp=modelpath.with_suffix('.tmp.txt');model.booster_.save_model(str(tmp));tmp.replace(modelpath)
     tmppath=path.with_suffix('.tmp.npz')
     with tmppath.open('wb') as f:
      np.savez_compressed(f,fold=np.array(fold),valid_idx=valid,pred=pred,auc=np.array(auc),best=np.array(best),model_sha256=np.array(sha(modelpath)),contract_sha256=np.array(contract_sha),composition_info_json=np.array(json.dumps(info)))
      f.flush();os.fsync(f.fileno())
     tmppath.replace(path)
     np.savez_compressed(HERE/f'composition_{fold:02d}.npz',fit_idx=fit,valid_idx=valid,fit_features=zfit,valid_features=zvalid)
     log(f'fold={fold}/5 auc={auc:.9f} best={best} elapsed={time.monotonic()-tic:.1f}s rss_gib={rss()/1024**3:.2f}')
     del xf,xv,zfit,zvalid,model;gc.collect()
    a_auc=float(roc_auc_score(y[valid],old_a[valid]));mix_auc=float(roc_auc_score(y[valid],.5*(old_a[valid]+pred)))
    oof[valid]=pred;rows.append({'fold':fold,'a_auc':a_auc,'b_auc':auc,'fixed_blend_auc':mix_auc,'b_delta':auc-a_auc,'fixed_blend_delta':mix_auc-a_auc,'composition':info})
    write(HERE/'progress.json',{'completed_folds':fold,'folds':rows,'elapsed_seconds':time.monotonic()-start,'peak_rss_bytes':rss(),'contract_sha256':contract_sha});update('P2_RUNNING',fold=fold)
  prob(oof,len(y));a=float(roc_auc_score(y,old_a));b=float(roc_auc_score(y,oof));mix=.5*(old_a+oof);m=float(roc_auc_score(y,mix));np.save(HERE/'oof_proba.npy',oof);np.save(HERE/'fixed_blend_oof.npy',mix)
  wins_b=sum(x['b_delta']>0 for x in rows);wins_m=sum(x['fixed_blend_delta']>0 for x in rows);gates={'B':b>a and wins_b==5,'fixed_blend':m>a and wins_m==5}
  guard(start);result={'status':'COMPLETE_DIAGNOSTIC','experiment_id':'P2_INCOME_COMPOSITION_INVERSION_5F_20260926','pooled_oof_auc':{'A':a,'B':b,'fixed_blend':m},'delta_vs_a':{'B':b-a,'fixed_blend':m-a},'positive_folds':{'B':wins_b,'fixed_blend':wins_m},'gates':gates,'research_plus_0_0001':{'B':b-a>=.0001 and wins_b==5,'fixed_blend':m-a>=.0001 and wins_m==5},'folds':rows,'elapsed_seconds':time.monotonic()-start,'peak_rss_bytes':rss(),'contract_sha256':contract_sha,'oof_sha256':sha(HERE/'oof_proba.npy'),'test_predictions_generated':False,'submission_allowed_from_diagnostic':False}
  write(HERE/'result.json',result);log(f'P2 complete A={a:.9f} B={b:.9f} blend={m:.9f} gates={gates}');update('P2_DIAGNOSTIC_COMPLETE',process={'pid':os.getpid(),'active':False},oof=result['pooled_oof_auc'],p2_gate=gates,next_action='Independent verification; formal 40fold if pass, otherwise close and report new evidence gap')
def main():
 try:train()
 except BaseException:
  err={'status':'FAILED','at_utc':now(),'traceback':traceback.format_exc()};write(HERE/'failure.json',err);update('P2_FAILED',process={'pid':os.getpid(),'active':False},blocker=err['traceback'][-3000:],next_action='Audit failed fold and frozen contract');raise
if __name__=='__main__':main()
