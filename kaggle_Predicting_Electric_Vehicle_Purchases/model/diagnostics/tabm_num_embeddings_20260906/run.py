"""冻结严格特征并顺序监督五折TabM双臂诊断。"""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='4'
import fcntl,gc,hashlib,importlib.util,json,resource,subprocess,sys,time,traceback,warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
P=Path(__file__).resolve().parent;R=P.parents[2];C=json.loads((P/'preregistration.json').read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False)+'\n');t.replace(p)
def module(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def run():
 lock=(P/'run.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 if (P/'result.json').exists():raise RuntimeError('已有结果，不重跑')
 assert json.loads((P/'smoke.json').read_text())['worker_sha256']==sha(P/'worker.py')
 for path,digest in C['source_hashes'].items():assert sha(R/path)==digest,path
 contract={'code':{x:sha(P/x) for x in ['run.py','worker.py','preregistration.json','deps/tabm.py','deps/rtdl_num_embeddings.py']},'sources':C['source_hashes'],'python':sys.version}
 if (P/'contract.json').exists():assert json.loads((P/'contract.json').read_text())==contract
 else:write(P/'contract.json',contract)
 if (P/'RUN_STARTED.json').exists():start=json.loads((P/'RUN_STARTED.json').read_text())['start_unix']
 else:start=time.time();write(P/'RUN_STARTED.json',{'pid':os.getpid(),'start_unix':start,'budget_seconds':C['wall_seconds']})
 deadline=start+C['wall_seconds']
 def guard():
  assert time.time()<deadline,'wall budget';assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<C['memory_gib']*1024**3,'memory budget'
 guard();raw=pd.read_csv(R/'data/train.csv');y=raw.Will_Buy_EV.map({'No':0,'Yes':1}).to_numpy('int8');ids=raw.id.to_numpy();assert len(np.unique(ids))==len(ids)
 backend=module(R/'model/validation/e2e_v100_20260905/feature_backends.py','tabm_backend').load_backend('v85')
 with np.load(R/'model/diagnostics/income_context_lowrank_20260906_retry1/diagnostic_oof.npz') as z:
  np.testing.assert_array_equal(z['ids'],ids);reference=z['pred'][:,0].copy();ref_folds=z['fold'].copy()
 oof=np.full((len(y),2),np.nan);foldids=np.zeros(len(y),dtype='int8');rows=[]
 for fold,(fit,valid) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(np.zeros(len(y)),y),1):
  guard();d=P/f'fold_{fold}';d.mkdir(exist_ok=True);np.testing.assert_array_equal(np.flatnonzero(ref_folds==fold),valid)
  if not (d/'input.json').exists():
   print('ENCODE_START',fold,flush=True)
   with warnings.catch_warnings():warnings.simplefilter('ignore');xf,xv,names=backend.encode(fit,y[fit],valid,42+fold)
   assert xf.shape[1]==148;mean=xf.mean(0,dtype=np.float64);std=xf.std(0,dtype=np.float64);std[std<1e-6]=1
   xf=np.clip((xf-mean)/std,-12,12).astype('float32');xv=np.clip((xv-mean)/std,-12,12).astype('float32');assert np.isfinite(xf).all() and np.isfinite(xv).all()
   arrays={'fit.npy':xf,'valid.npy':xv,'fit_y.npy':y[fit],'valid_y.npy':y[valid],'fit_rows.npy':fit,'valid_rows.npy':valid,'valid_ids.npy':ids[valid],'mean.npy':mean,'std.npy':std}
   for name,array in arrays.items():np.save(d/name,array)
   write(d/'input.json',{'fold':fold,'names':names,'contract_sha':sha(P/'contract.json'),'hashes':{name:sha(d/name) for name in arrays}})
   del xf,xv,arrays;gc.collect()
  else:
   meta=json.loads((d/'input.json').read_text());assert meta['contract_sha']==sha(P/'contract.json')
   for name,digest in meta['hashes'].items():assert sha(d/name)==digest
  summaries=[]
  for arm in [0,1]:
   guard();print('ARM_START',fold,arm,flush=True);cap=C['memory_gib']*1024**3-resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
   env=dict(os.environ,TABM_DEADLINE=str(deadline),TABM_MEMORY_BYTES=str(cap),PYTHONFAULTHANDLER='1')
   child=subprocess.Popen([sys.executable,str(P/'worker.py'),'--fold',str(fold),'--arm',str(arm)],env=env)
   try:
    while child.poll() is None:
     time.sleep(1);guard()
    assert child.returncode==0,f'worker exit {child.returncode}'
   except BaseException:
    child.terminate()
    try:child.wait(timeout=5)
    except subprocess.TimeoutExpired:child.kill();child.wait()
    raise
   result=json.loads((d/f'arm_{arm}/result.json').read_text());p=np.load(d/f'arm_{arm}/prediction.npy');assert result['prediction_sha']==sha(d/f'arm_{arm}/prediction.npy') and result['input_sha']==sha(d/'input.json')
   oof[valid,arm]=p;summaries.append(result);print('ARM_COMPLETE',fold,arm,result['auc'],result['best_epoch'],flush=True)
  row={'fold':fold,'auc':[s['auc'] for s in summaries],'delta':summaries[1]['auc']-summaries[0]['auc'],'reference_auc':roc_auc_score(y[valid],reference[valid]),'best_epochs':[s['best_epoch'] for s in summaries]};rows.append(row);foldids[valid]=fold
  write(d/'summary.json',row);write(P/'progress.json',{'folds':rows,'elapsed_seconds':time.time()-start});print('FOLD_COMPLETE',json.dumps(row),flush=True)
 guard();assert np.isfinite(oof).all() and ((oof>=0)&(oof<=1)).all() and (foldids>0).all();auc=[float(roc_auc_score(y,oof[:,j])) for j in range(2)];ref=roc_auc_score(y,reference);wins=sum(row['delta']>0 for row in rows)
 np.savez_compressed(P/'diagnostic_oof.npz',ids=ids,fold=foldids,pred=oof)
 write(P/'result.json',{'status':'COMPLETE_DIAGNOSTIC','auc':auc,'delta':auc[1]-auc[0],'positive_folds':wins,'matched_v85_auc':ref,'candidate_delta_vs_v85':auc[1]-ref,'mechanism_gate_passed':auc[1]-auc[0]>=.0001 and wins==5 and auc[1]>=.9452,'folds':rows,'elapsed_seconds':time.time()-start,'parent_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'contract_sha':sha(P/'contract.json'),'oof_sha':sha(P/'diagnostic_oof.npz'),'test_predictions_generated':False,'submission_allowed':False,'counts_toward_cycle':False,'scope':'五折开发诊断，外层参与早停，不能称独立盲测或V100端到端比较。'})
if __name__=='__main__':
 try:run()
 except BaseException:write(P/'failure.json',{'status':'FAILED','at_unix':time.time(),'traceback':traceback.format_exc()});raise
