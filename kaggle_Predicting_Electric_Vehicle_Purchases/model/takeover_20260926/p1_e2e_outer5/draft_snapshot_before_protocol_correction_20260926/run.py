"""Conditional outer-five source-group V85 cache; no outer-hold scoring."""
from __future__ import annotations
import os
for _key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[_key]='6'
import argparse,datetime,fcntl,hashlib,importlib.util,json,platform,resource,sys,time,traceback,warnings,gc
from pathlib import Path
import lightgbm as lgb,numpy as np,pandas as pd
from threadpoolctl import threadpool_limits
HERE=Path(__file__).resolve().parent;TOP=HERE.parent;PROJECT=HERE.parents[2]
ARCH=PROJECT/'model/validation/e2e_v100_20260905';FORMAL=TOP/'p1_source_group_constraints_40f';DIAG=TOP/'p1_source_group_constraints_5f';STATUS=TOP/'status.json'
sys.path.insert(0,str(ARCH))
import cpu_runner as cpu
from feature_backends import load_backend

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def write_json(path,d):
 tmp=path.with_name(path.name+'.tmp')
 with tmp.open('w') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 tmp.replace(path)
def log(message):
 s=f'{now()} {message}';print(s,flush=True)
 with (HERE/'train_log.txt').open('a') as f:f.write(s+'\n')
def rss():
 r=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
 return int(r if platform.system()=='Darwin' else r*1024)
def check(p,n):
 if p.shape!=(n,) or not np.isfinite(p).all() or ((p<0)|(p>1)).any():raise ValueError('invalid probabilities')
def status(phase,outer=None,atom=None,**extra):
 d=json.loads(STATUS.read_text());d.update({'updated_at_utc':now(),'phase':phase,'current_experiment':'p1_e2e_outer5','process':{'pid':os.getpid(),'active':phase=='P1_E2E_RUNNING'},'checkpoint':{'outer':outer,'atom':atom} if outer else None});d.update(extra);write_json(STATUS,d)
class Budget:
 def __init__(self):
  old=json.loads((HERE/'budget.json').read_text()) if (HERE/'budget.json').exists() else {'spent_seconds':0.0}
  self.prior=float(old['spent_seconds']);self.start=time.monotonic();self.check()
 def check(self):
  spent=self.prior+time.monotonic()-self.start
  record={'spent_seconds':spent,'peak_rss_bytes':rss(),'pid':os.getpid(),'updated_at_utc':now()}
  write_json(HERE/'budget.json',record)
  if spent>=43200:raise TimeoutError('P1 E2E 12h budget exceeded')
  if record['peak_rss_bytes']>16*1024**3:raise MemoryError('P1 E2E 16 GiB budget exceeded')
 def callback(self,env):
  if env.iteration%50==0:self.check()

def eligibility():
 formal=json.loads((FORMAL/'cv_results.json').read_text());verify=json.loads((FORMAL/'verification.json').read_text());pr=json.loads((HERE/'conditional_preregistration.json').read_text());mapdoc=json.loads((DIAG/'feature_origin_map.json').read_text());frozen=json.loads((DIAG/'freeze_manifest.json').read_text())
 if formal['status']!='COMPLETE' or verify['status']!='PASS' or not any(formal['gates'].values()):raise ValueError('formal P1 comparison not qualified')
 selected='M' if formal['gates']['m'] else 'C'
 if sha(FORMAL/'cv_results.json')!=verify['result_sha256']:raise ValueError('formal result changed')
 if sha(DIAG/'feature_origin_map.json')!=frozen['feature_origin_map_sha256']:raise ValueError('feature group map changed')
 prior=json.loads((ARCH/'completion_review.json').read_text());independent=json.loads((ARCH/'independent_reconstruction.json').read_text());snapshot=json.loads((ARCH/'cache_snapshot.json').read_text())
 if prior['status']!='VERIFIED_COMPLETE_AB_GATE_FAILED' or independent['status']!='INDEPENDENT_RECONSTRUCTION_PASS_UNSCORED' or snapshot['status']!='ALL_15_CACHES_REBUILT_UNSCORED':raise ValueError('archived V100 E2E cache status invalid')
 for rel,digest in snapshot['files'].items():
  if sha(ARCH/rel)!=digest:raise ValueError(f'archived E2E cache drift: {rel}')
 if lgb.__version__!='4.6.0':raise ValueError('LightGBM drift')
 contract={'conditional_prereg_sha256':sha(HERE/'conditional_preregistration.json'),'formal_result_sha256':sha(FORMAL/'cv_results.json'),'formal_verification_sha256':sha(FORMAL/'verification.json'),'p1_map_sha256':sha(DIAG/'feature_origin_map.json'),'archived_cache_snapshot_sha256':sha(ARCH/'cache_snapshot.json'),'archived_completion_review_sha256':sha(ARCH/'completion_review.json'),'archived_cpu_runner_sha256':sha(ARCH/'cpu_runner.py'),'archived_feature_backend_sha256':sha(ARCH/'feature_backends.py'),'archived_splits_sha256':sha(ARCH/'splits.npz'),'runner_sha256':sha(Path(__file__)),'selected_final':selected}
 contract_sha=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
 return formal,pr,mapdoc,frozen,selected,contract,contract_sha

def preflight():
 formal,pr,mapdoc,frozen,selected,contract,contract_sha=eligibility()
 labels=pd.read_csv(PROJECT/'data/train.csv',usecols=['Will_Buy_EV']).Will_Buy_EV.eq('Yes').to_numpy(np.int8);ids=pd.read_csv(PROJECT/'data/train.csv',usecols=['id']).id.to_numpy(np.int64)
 if hashlib.sha256(labels.tobytes()).hexdigest()!=frozen['labels_sha256'] or hashlib.sha256(ids.tobytes()).hexdigest()!=frozen['raw_train_ids_sha256']:raise ValueError('training labels or IDs changed')
 with warnings.catch_warnings():warnings.simplefilter('ignore');backend=load_backend('v85')
 names=mapdoc['final_features'];groups=mapdoc['groups_zero_based']
 expected=[c for c in backend.static if c not in backend.te_columns]+[f'{c}_TE_{tag}' for tag in ('auto','10') for c in backend.te_columns]
 if names!=expected or sorted(i for g in groups for i in g)!=list(range(148)):raise ValueError('group schema drift')
 if hashlib.sha256(pd.util.hash_pandas_object(backend.static,index=False).to_numpy(np.uint64).tobytes()).hexdigest()!=frozen['pre_te_train_values_sha256']:raise ValueError('static input changed')
 with np.load(ARCH/'splits.npz',allow_pickle=False) as z:
  for outer in range(1,6):
   train=z[f'outer_{outer:02d}_train_idx'];hold=z[f'outer_{outer:02d}_valid_idx'];fold=z[f'outer_{outer:02d}_v85_fold'];assert not np.intersect1d(train,hold).size and len(fold)==len(train) and set(np.unique(fold))==set(range(40))
   with np.load(ARCH/f'outer_{outer:02d}/v85/cache.npz',allow_pickle=False) as a:
    assert np.array_equal(a['train_idx'],train) and np.array_equal(a['valid_idx'],hold) and np.array_equal(a['valid_id'],ids[hold]);check(a['valid_proba'],len(hold))
   with np.load(ARCH/f'assembled/outer_{outer:02d}/predictions.npz',allow_pickle=False) as a:
    assert np.array_equal(a['valid_idx'],hold) and np.array_equal(a['valid_id'],ids[hold]);check(a['baseline_proba'],len(hold))
 write_json(HERE/'preflight.json',{'status':'PASS','at_utc':now(),'contract':contract,'contract_sha256':contract_sha,'selected_final':selected,'outer_folds':5,'group_sizes':mapdoc['group_sizes']})
 return backend,labels,ids,groups,selected,contract_sha

def checkpoint(path,contract_sha,expected):
 manifest=path/'manifest.json';npz=path/'predictions.npz';model=path/'model.txt'
 if not manifest.exists():return None
 meta=json.loads(manifest.read_text())
 if meta['status']!='COMPLETE' or meta['contract_sha256']!=contract_sha or any(meta[k]!=v for k,v in expected.items() if k not in ('oof_idx','valid_idx')) or sha(npz)!=meta['prediction_sha256'] or sha(model)!=meta['model_sha256']:raise ValueError(f'checkpoint mismatch: {path}')
 with np.load(npz,allow_pickle=False) as a:
  if not np.array_equal(a['oof_idx'],expected['oof_idx']) or not np.array_equal(a['valid_idx'],expected['valid_idx']):raise ValueError('checkpoint row mismatch')
  check(a['oof_proba'],len(expected['oof_idx']));check(a['valid_proba'],len(expected['valid_idx']))
 return meta

def train():
 backend,y,ids,groups,selected,contract_sha=preflight()
 lock=HERE/'run.lock'
 with lock.open('a+') as h:
  try:fcntl.flock(h,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:raise RuntimeError('E2E P1 single instance already active')
  h.seek(0);h.truncate();h.write(json.dumps({'pid':os.getpid(),'contract_sha256':contract_sha,'at_utc':now()}));h.flush();os.fsync(h.fileno())
  if (HERE/'cache_complete.json').exists():raise RuntimeError('E2E cache already complete')
  write_json(HERE/'RUN_STARTED.json',{'pid':os.getpid(),'at_utc':now(),'contract_sha256':contract_sha,'selected_final':selected})
  status('P1_E2E_RUNNING',next_action='Train 5 outer x 40 atoms with internal early stop; no U scoring')
  log(f'E2E start pid={os.getpid()} selected={selected} contract={contract_sha}')
  budget=Budget();base=json.loads((PROJECT/'model/v85_naji_v74_40f/frozen_config.json').read_text());params=base['lightgbm_base_params'].copy();assert params['n_jobs']==8;params['n_jobs']=6;params['interaction_constraints']=groups
  with threadpool_limits(limits=6):
   with np.load(ARCH/'splits.npz',allow_pickle=False) as z:
    for outer in range(1,6):
     train=z[f'outer_{outer:02d}_train_idx'];hold=z[f'outer_{outer:02d}_valid_idx'];folds=z[f'outer_{outer:02d}_v85_fold'];oof=np.full(len(train),np.nan);valid_sum=np.zeros(len(hold));coverage=np.zeros(len(train),np.int8)
     for atom in range(1,41):
      fit_local=np.flatnonzero(folds!=atom-1);valid_local=np.flatnonzero(folds==atom-1)
      fitrows=train[fit_local];oofrows=train[valid_local];query=np.concatenate([oofrows,hold]);directory=HERE/f'outer_{outer:02d}/atom_{atom:02d}';directory.mkdir(parents=True,exist_ok=True)
      expected={'outer':outer,'atom':atom,'fit_idx_sha256':cpu.arr_sha(fitrows),'fit_y_sha256':cpu.arr_sha(y[fitrows]),'query_idx_sha256':cpu.arr_sha(query),'oof_idx':oofrows,'valid_idx':hold}
      # Arrays are intentionally kept out of the serialized expected metadata.
      ids_expected={k:v for k,v in expected.items() if k not in ('oof_idx','valid_idx')}
      meta=checkpoint(directory,contract_sha,expected) if (directory/'manifest.json').exists() else None
      if meta is None:
       budget.check();start=time.monotonic();p=params.copy();seed=42+atom
       for key in base['lightgbm_fold_seed_fields']:p[key]=seed
       pred,scope,model=cpu.fit_atom(backend,fitrows,y[fitrows],query,p,42+atom,424370000+outer*1000+100+atom,350,budget)
       if model.booster_.params.get('interaction_constraints')!=groups or model.booster_.feature_name()!=scope['feature_names']:
        raise ValueError('E2E constraints or schema not active')
       check(pred,len(query));modelpath=directory/'model.txt';tmp=directory/'model.tmp.txt';model.booster_.save_model(str(tmp));tmp.replace(modelpath)
       cpu.atomic_npz(directory/'predictions.npz',oof_idx=oofrows,valid_idx=hold,oof_id=ids[oofrows],valid_id=ids[hold],oof_proba=pred[:len(oofrows)],valid_proba=pred[len(oofrows):])
       metadata={**ids_expected,**scope,'status':'COMPLETE','contract_sha256':contract_sha,'prediction_sha256':sha(directory/'predictions.npz'),'model_sha256':sha(modelpath),'elapsed_seconds':time.monotonic()-start,'outer_U_labels_used':False}
       write_json(directory/'manifest.json',metadata);meta=metadata
       log(f'outer={outer}/5 atom={atom}/40 seconds={metadata["elapsed_seconds"]:.1f} selected_iteration={scope["selected_iteration"]} rss_gib={rss()/1024**3:.2f}')
       del pred,model;gc.collect()
      else:log(f'outer={outer}/5 atom={atom}/40 resumed')
      with np.load(directory/'predictions.npz',allow_pickle=False) as a:
       if not np.array_equal(a['oof_id'],ids[oofrows]) or not np.array_equal(a['valid_id'],ids[hold]):raise ValueError('E2E row id mismatch')
       oof[valid_local]=a['oof_proba'];coverage[valid_local]+=1;valid_sum+=a['valid_proba']/40
      budget.check();write_json(HERE/'progress.json',{'outer':outer,'atom':atom,'completed_atoms_total':(outer-1)*40+atom,'spent_seconds':json.loads((HERE/'budget.json').read_text())['spent_seconds'],'peak_rss_bytes':rss(),'contract_sha256':contract_sha,'updated_at_utc':now()});status('P1_E2E_RUNNING',outer=outer,atom=atom)
     if not np.all(coverage==1) or not np.isfinite(oof).all():raise ValueError('E2E inner OOF incomplete')
     check(valid_sum,len(hold));cache_path=HERE/f'outer_{outer:02d}/cache.npz'
     cache_arrays=dict(train_idx=train,valid_idx=hold,train_id=ids[train],valid_id=ids[hold],oof_proba=oof,valid_proba=valid_sum,atom_fold=folds)
     if cache_path.exists():
      with np.load(cache_path,allow_pickle=False) as old:
       if set(old.files)!=set(cache_arrays) or any(not np.array_equal(old[k],v) for k,v in cache_arrays.items()):raise ValueError('existing outer cache mismatch')
     else:cpu.atomic_npz(cache_path,**cache_arrays)
     write_json(HERE/f'outer_{outer:02d}/cache_manifest.json',{'status':'CACHE_COMPLETE_UNSCORED','outer':outer,'contract_sha256':contract_sha,'cache_sha256':sha(HERE/f'outer_{outer:02d}/cache.npz'),'atom_manifest_sha256':{str(i):sha(HERE/f'outer_{outer:02d}/atom_{i:02d}/manifest.json') for i in range(1,41)},'outer_U_labels_used':False})
     log(f'outer={outer}/5 cache complete without U scoring')
  budget.check();write_json(HERE/'cache_complete.json',{'status':'CACHE_COMPLETE_UNSCORED','completed_at_utc':now(),'contract_sha256':contract_sha,'atoms':200,'spent_seconds':json.loads((HERE/'budget.json').read_text())['spent_seconds'],'peak_rss_bytes':rss(),'candidate_selected_before_U_scoring':selected})
  status('P1_E2E_CACHE_COMPLETE',process={'pid':os.getpid(),'active':False},checkpoint={'outer':5,'atom':40},next_action='Independent cache verification and paired outer U scoring')
  log('E2E cache complete unscored')

def main():
 a=argparse.ArgumentParser();a.add_argument('--preflight',action='store_true');args=a.parse_args()
 try:
  if args.preflight:
   *_,chosen,contract=preflight();print(json.dumps({'status':'PASS','selected_final':chosen,'contract_sha256':contract}));return
  train()
 except BaseException:
  err={'status':'FAILED','at_utc':now(),'pid':os.getpid(),'traceback':traceback.format_exc()};write_json(HERE/'failure.json',err);status('P1_E2E_FAILED',process={'pid':os.getpid(),'active':False},blocker=err['traceback'][-3000:],next_action='Audit checkpoint and resume same contract if valid');raise
if __name__=='__main__':main()
