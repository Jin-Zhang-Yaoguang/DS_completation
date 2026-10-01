"""Conditional 40-fold source-group LightGBM, frozen after P1 preregistration."""
from __future__ import annotations
import os
for _key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
 os.environ[_key]='6'
import argparse,datetime,fcntl,hashlib,importlib.util,json,platform,resource,sys,time,traceback,warnings,gc
from pathlib import Path
import lightgbm as lgb,numpy as np,pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
HERE=Path(__file__).resolve().parent;TOP=HERE.parent;PROJECT=HERE.parents[2]
DIAG=TOP/'p1_source_group_constraints_5f';STATUS=TOP/'status.json'
V85=PROJECT/'model/v85_naji_v74_40f'
V100=PROJECT/'model/v100_v90_ctboost_nested_cv_blend'
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def jsonwrite(path,value):
 tmp=path.with_name(path.name+'.tmp')
 with tmp.open('w') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 tmp.replace(path)
def log(message):
 s=f'{now()} {message}';print(s,flush=True)
 with (HERE/'train_log.txt').open('a') as f:f.write(s+'\n')
def rss():
 r=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
 return int(r if platform.system()=='Darwin' else r*1024)
def guard(start):
 if time.monotonic()-start>=43200:raise TimeoutError('40-fold 12h budget exhausted')
 if rss()>16*1024**3:raise MemoryError('40-fold 16 GiB RSS budget exhausted')
def valid_probs(a,n):
 if a.shape!=(n,) or not np.isfinite(a).all() or ((a<0)|(a>1)).any():raise ValueError('invalid probabilities')
def update_status(phase,fold=None,**extra):
 x=json.loads(STATUS.read_text());x.update({'phase':phase,'updated_at_utc':now(),'current_experiment':'p1_source_group_constraints_40f','process':{'pid':os.getpid(),'active':phase=='P1_FORMAL_RUNNING'},'checkpoint':{'fold':fold,'of':40} if fold else None});x.update(extra);jsonwrite(STATUS,x)
def module_at(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
def eligibility():
 pre=json.loads((HERE/'conditional_preregistration.json').read_text());diag=json.loads((DIAG/'result.json').read_text());ver=json.loads((DIAG/'verification.json').read_text());freeze=json.loads((DIAG/'freeze_manifest.json').read_text());mapping=json.loads((DIAG/'feature_origin_map.json').read_text())
 if diag['status']!='COMPLETE_DIAGNOSTIC' or ver['status']!='PASS' or not diag['diagnostic_gate']['any_pass']:raise ValueError('P1 diagnostic did not qualify')
 for rel,rec in freeze['source_files'].items():
  if sha(PROJECT/rel)!=rec['sha256']:raise ValueError(f'frozen source changed: {rel}')
 if sha(DIAG/'feature_origin_map.json')!=freeze['feature_origin_map_sha256']:raise ValueError('group map changed')
 with np.load(PROJECT/'model/diagnostics/original_prior_reliability_20260905/diagnostic_oof.npz',allow_pickle=False) as old:
  old_a=old['a'];diff=0.0
  for fold in range(1,6):
   with np.load(DIAG/f'fold_{fold:02d}_A.npz',allow_pickle=False) as d:
    diff=max(diff,float(np.max(np.abs(d['valid_pred']-old_a[d['valid_idx']]))))
 if diff>1e-9:raise ValueError(f'A reference drift: {diff}; matched A40 training required')
 b_ok=diag['diagnostic_gate']['B'];blend_ok=diag['diagnostic_gate']['fixed_blend']
 selected='fixed_v85_b_50_50' if blend_ok and diag['pooled_delta_vs_a']['fixed_blend']>=diag['pooled_delta_vs_a']['B'] else 'b_only' if b_ok else None
 if selected is None:raise ValueError('No eligible diagnostic arm')
 if lgb.__version__!='4.6.0':raise ValueError('LightGBM version mismatch')
 contract={'prereg_sha256':sha(HERE/'conditional_preregistration.json'),'diag_result_sha256':sha(DIAG/'result.json'),'diag_verification_sha256':sha(DIAG/'verification.json'),'freeze_sha256':sha(DIAG/'freeze_manifest.json'),'mapping_sha256':sha(DIAG/'feature_origin_map.json'),'runner_sha256':sha(Path(__file__)),'v85_runner_sha256':sha(V85/'v85_naji_v74_40f.py'),'selected_c':selected}
 contract_sha=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
 return pre,diag,freeze,mapping,selected,contract,contract_sha,diff

def preflight():
 pre,diag,freeze,mapping,selected,contract,contract_sha,diff=eligibility()
 v85=module_at(V85/'v85_naji_v74_40f.py','takeover_formal_v85')
 cfg=v85.load_frozen_config();probe=v85.load_probe()
 with warnings.catch_warnings():warnings.simplefilter('ignore');data=v85.validate_data_contract(cfg,probe)
 names=data['final_feature_names'];groups=mapping['groups_zero_based']
 if names!=mapping['final_features'] or sorted(i for g in groups for i in g)!=list(range(148)):raise ValueError('feature group schema mismatch')
 y=data['y'].to_numpy(np.int8)
 if hashlib.sha256(y.tobytes()).hexdigest()!=freeze['labels_sha256']:raise ValueError('labels mismatch')
 if hashlib.sha256(pd.util.hash_pandas_object(data['x'],index=False).to_numpy(np.uint64).tobytes()).hexdigest()!=freeze['pre_te_train_values_sha256']:raise ValueError('preTE train mismatch')
 folds=list(StratifiedKFold(40,shuffle=True,random_state=42).split(data['x'],y));fidx=np.zeros(len(y),np.int16)
 for i,(_,va) in enumerate(folds,1):fidx[va]=i
 if not np.array_equal(fidx,np.load(DIAG/'fold_assignments_40f_seed42.npy')):raise ValueError('40 fold assignment mismatch')
 for path,n in [(V85/'oof_proba.npy',len(y)),(V85/'test_proba.npy',len(data['x_test'])),(V100/'oof_proba.npy',len(y)),(V100/'test_proba.npy',len(data['x_test']))]:valid_probs(np.load(path,mmap_mode='r'),n)
 jsonwrite(HERE/'preflight.json',{'status':'PASS','checked_at_utc':now(),'contract_sha256':contract_sha,'contract':contract,'selected_c':selected,'a_fivefold_max_abs_vs_archive':diff,'folds':40,'feature_count':len(names)})
 return v85,cfg,data,folds,names,groups,selected,contract_sha

def save_fold(path,fold,valid_idx,vpred,tpred,auc,best,contract_sha,modelpath):
 tmp=path.with_suffix('.tmp.npz')
 with tmp.open('wb') as f:
  np.savez_compressed(f,fold=np.array(fold),valid_idx=valid_idx.astype(np.int64),valid_pred=vpred.astype(np.float64),test_pred=tpred.astype(np.float64),auc=np.array(auc),best=np.array(best),contract_sha256=np.array(contract_sha),model_sha256=np.array(sha(modelpath)))
  f.flush();os.fsync(f.fileno())
 tmp.replace(path)
def load_fold(path,fold,valid_idx,ntest,contract_sha):
 with np.load(path,allow_pickle=False) as d:
  if int(d['fold'])!=fold or str(d['contract_sha256'])!=contract_sha or not np.array_equal(d['valid_idx'],valid_idx):raise ValueError('fold checkpoint identity mismatch')
  vp=d['valid_pred'].astype(np.float64);tp=d['test_pred'].astype(np.float64);valid_probs(vp,len(valid_idx));valid_probs(tp,ntest)
  model=HERE/f'model_{fold:02d}.txt'
  if sha(model)!=str(d['model_sha256']):raise ValueError('model checkpoint SHA mismatch')
  return vp,tp,float(d['auc']),int(d['best'])

def run():
 start=time.monotonic();v85,cfg,data,folds,names,groups,selected,contract_sha=preflight()
 lock=HERE/'run.lock'
 with lock.open('a+') as h:
  try:fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise RuntimeError('P1 formal already running')
  h.seek(0);h.truncate();h.write(json.dumps({'pid':os.getpid(),'contract_sha256':contract_sha,'started_at_utc':now()}));h.flush();os.fsync(h.fileno())
  if (HERE/'cv_results.json').exists():raise RuntimeError('formal result already exists; refuse duplicate')
  jsonwrite(HERE/'RUN_STARTED.json',{'pid':os.getpid(),'at_utc':now(),'contract_sha256':contract_sha,'selected_c':selected})
  update_status('P1_FORMAL_RUNNING',next_action='Train and checkpoint 40-fold constrained V85')
  log(f'formal 40fold started pid={os.getpid()} contract={contract_sha} selected={selected}')
  x,y,xt=data['x'],data['y'],data['x_test'];yn=y.to_numpy(np.int8);ntest=len(xt)
  params=cfg['lightgbm_base_params'].copy();assert params['n_jobs']==8;params['n_jobs']=6
  oof=np.full(len(y),np.nan,dtype=np.float64);testsum=np.zeros(ntest,np.float64);rows=[]
  for fold,(fit,valid) in enumerate(folds,1):
   guard(start);path=HERE/f'fold_{fold:02d}.npz'
   if path.exists():vp,tp,auc,best=load_fold(path,fold,valid,ntest,contract_sha);log(f'fold={fold}/40 resumed auc={auc:.9f}')
   else:
    tic=time.monotonic()
    with warnings.catch_warnings():warnings.simplefilter('ignore');xf,xv,xtf=v85.encode_naji_fold(x,y,xt,data['target_encode_columns'],fit,valid,fold)
    if list(xf.columns)!=names:raise ValueError('encoded columns mismatch')
    p=params.copy();seed=42+fold
    for key in cfg['lightgbm_fold_seed_fields']:p[key]=seed
    p['interaction_constraints']=groups
    model=lgb.LGBMClassifier(**p)
    model.fit(xf,y.iloc[fit],eval_set=[(xv,y.iloc[valid])],eval_metric='auc',feature_name=names,callbacks=[lgb.early_stopping(350,verbose=False),lgb.log_evaluation(period=0)])
    if model.booster_.params.get('interaction_constraints')!=groups or model.booster_.feature_name()!=names:raise ValueError('constraints or names not active')
    best=int(model.best_iteration_ or params['n_estimators'])
    vp=model.predict_proba(xv,num_iteration=best)[:,1].astype(np.float64);tp=model.predict_proba(xtf,num_iteration=best)[:,1].astype(np.float64)
    valid_probs(vp,len(valid));valid_probs(tp,ntest);auc=float(roc_auc_score(yn[valid],vp))
    modelpath=HERE/f'model_{fold:02d}.txt';tmp=modelpath.with_suffix('.tmp.txt');model.booster_.save_model(str(tmp));tmp.replace(modelpath)
    save_fold(path,fold,valid,vp,tp,auc,best,contract_sha,modelpath)
    log(f'fold={fold}/40 auc={auc:.9f} best={best} elapsed={time.monotonic()-tic:.1f}s rss_gib={rss()/1024**3:.2f}')
    del xf,xv,xtf,model;gc.collect()
   if abs(float(roc_auc_score(yn[valid],vp))-auc)>1e-12:raise ValueError('fold AUC mismatch')
   oof[valid]=vp;testsum+=tp/40
   rows.append({'fold':fold,'auc':auc,'best_iteration':best,'valid_rows':len(valid)})
   jsonwrite(HERE/'progress.json',{'completed_folds':fold,'folds':rows,'updated_at_utc':now(),'contract_sha256':contract_sha,'elapsed_seconds':time.monotonic()-start,'peak_rss_bytes':rss()})
   update_status('P1_FORMAL_RUNNING',fold=fold)
  valid_probs(oof,len(y));valid_probs(testsum,ntest);np.save(HERE/'oof_proba.npy',oof);np.save(HERE/'test_proba.npy',testsum)
  a_oof=np.load(V85/'oof_proba.npy',mmap_mode='r');a_test=np.load(V85/'test_proba.npy',mmap_mode='r');v100_oof=np.load(V100/'oof_proba.npy',mmap_mode='r');v100_test=np.load(V100/'test_proba.npy',mmap_mode='r')
  c_oof=oof if selected=='b_only' else .5*(a_oof+oof)
  c_test=testsum if selected=='b_only' else .5*(a_test+testsum)
  m_oof=.5*(v100_oof+c_oof);m_test=.5*(v100_test+c_test)
  for name,arr in [('c_oof',c_oof),('c_test',c_test),('m_oof',m_oof),('m_test',m_test)]:
   a=np.asarray(arr,dtype=np.float64);valid_probs(a,len(y) if name.endswith('oof') else ntest);np.save(HERE/f'{name}.npy',a)
  base_auc=float(roc_auc_score(yn,v100_oof));b_auc=float(roc_auc_score(yn,oof));c_auc=float(roc_auc_score(yn,c_oof));m_auc=float(roc_auc_score(yn,m_oof));a_auc=float(roc_auc_score(yn,a_oof))
  meta=list(StratifiedKFold(5,shuffle=True,random_state=42).split(np.zeros(len(y)),yn))
  block=[]
  for k,(_,va) in enumerate(meta,1):
   ref=float(roc_auc_score(yn[va],v100_oof[va]));ca=float(roc_auc_score(yn[va],c_oof[va]));ma=float(roc_auc_score(yn[va],m_oof[va]));block.append({'block':k,'v100_auc':ref,'c_auc':ca,'m_auc':ma,'c_delta':ca-ref,'m_delta':ma-ref})
  gates={'c':c_auc>base_auc and all(r['c_delta']>0 for r in block),'m':m_auc>base_auc and all(r['m_delta']>0 for r in block)}
  guard(start)
  result={'status':'COMPLETE','experiment_id':'P1_SOURCE_GROUP_CONSTRAINTS_40F_20260926','model':'V85 source-group constrained LightGBM','n_folds':40,'selected_c':selected,'base':'v85_naji_v74_40f','base_oof_auc':a_auc,'fold_auc':[r['auc'] for r in rows],'best_iterations':[r['best_iteration'] for r in rows],'oof_auc':b_auc,'oof_delta_vs_base':b_auc-a_auc,'v100_oof_auc':base_auc,'c_oof_auc':c_auc,'m_oof_auc':m_auc,'c_delta_vs_v100':c_auc-base_auc,'m_delta_vs_v100':m_auc-base_auc,'meta_blocks':block,'gates':gates,'research_plus_0_0001':{'c':c_auc-base_auc>=.0001 and all(r['c_delta']>0 for r in block),'m':m_auc-base_auc>=.0001 and all(r['m_delta']>0 for r in block)},'params':{**params,'interaction_constraints':groups},'elapsed_seconds':time.monotonic()-start,'peak_rss_bytes':rss(),'contract_sha256':contract_sha,'evidence_level':'full-data 40fold outer-validation early-stopped development OOF; final E2E required','submission_allowed_from_this_result':False,'artifact_sha256':{n:sha(HERE/n) for n in ['oof_proba.npy','test_proba.npy','c_oof.npy','c_test.npy','m_oof.npy','m_test.npy']}}
  jsonwrite(HERE/'cv_results.json',result)
  jsonwrite(HERE/'sources.json',{'contract_sha256':contract_sha,'preregistration':str(HERE/'conditional_preregistration.json'),'frozen_sources':str(DIAG/'freeze_manifest.json'),'v85_reuse':str(V85),'v100_comparator':str(V100),'result_sha256':sha(HERE/'cv_results.json')})
  log(f"formal complete B={b_auc:.9f} C={c_auc:.9f} M={m_auc:.9f} V100={base_auc:.9f} gates={gates}")
  update_status('P1_FORMAL_COMPLETE',process={'pid':os.getpid(),'active':False},checkpoint={'fold':40,'of':40},oof={'B':b_auc,'C':c_auc,'M':m_auc,'V100':base_auc},formal_gate=gates,next_action='Independent formal verification; E2E if pass, otherwise P2')
def main():
 a=argparse.ArgumentParser();a.add_argument('--preflight',action='store_true');args=a.parse_args()
 try:
  if args.preflight:
   *_,selected,contract=preflight();print(json.dumps({'status':'PASS','selected_c':selected,'contract_sha256':contract}));return
  run()
 except BaseException:
  error={'status':'FAILED','at_utc':now(),'traceback':traceback.format_exc(),'pid':os.getpid()};jsonwrite(HERE/'failure.json',error)
  update_status('P1_FORMAL_FAILED',process={'pid':os.getpid(),'active':False},blocker=error['traceback'][-3000:],next_action='Audit and resume same contract if valid')
  raise
if __name__=='__main__':main()
