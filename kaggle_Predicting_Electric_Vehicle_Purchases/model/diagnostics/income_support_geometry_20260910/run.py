"""固定收入支持集几何追加；复用匹配且重新回放的V85对照。"""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='8'
import fcntl,gc,hashlib,importlib.util,json,sys,time,signal,resource,traceback,warnings
from pathlib import Path
import numpy as np,pandas as pd,lightgbm as lgb
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
P=Path(__file__).resolve().parent;R=P.parents[2];C=json.loads((P/'preregistration.json').read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,d):
 t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(d,ensure_ascii=False,indent=2,allow_nan=False));t.replace(p)
def geometry(values):
 v=np.unique(values);assert len(v)>1 and np.isfinite(v).all();diff=np.diff(v);a=np.log1p(np.r_[diff[0],diff]);b=np.log1p(np.r_[diff,diff[-1]]);return np.c_[a,b,np.log1p(np.r_[diff[0],diff]+np.r_[diff,diff[-1]]),a-b][np.searchsorted(v,values)]
def run():
 lock=(P/'run.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);assert not (P/'result.json').exists()
 prev=json.loads((R/'model/diagnostics/realmlp_periodic_20260910/verification.json').read_text());assert prev['status']=='PASS' and not prev['gate_passed'],'先完成RealMLP分支'
 for path,h in C['source_hashes'].items():assert sha(R/path)==h,path
 # 手算不等间距、重复值的几何，防止把频次或行序错误引入间距。
 t=geometry(np.array([1.,4.,4.,10.]));np.testing.assert_allclose(t[1],t[2]);np.testing.assert_allclose(t[1,:2],np.log1p([3,6]));assert np.isfinite(t).all()
 contract={'runner':sha(__file__),'preregistration':sha(P/'preregistration.json'),'source_hashes':C['source_hashes']}
 if (P/'contract.json').exists():assert contract==json.loads((P/'contract.json').read_text())
 else:write(P/'contract.json',contract)
 if (P/'RUN_STARTED.json').exists():start=json.loads((P/'RUN_STARTED.json').read_text())['start']
 else:start=time.time();write(P/'RUN_STARTED.json',{'pid':os.getpid(),'start':start})
 def guard():assert time.time()-start<C['wall_seconds'],'wall';assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<C['memory_gib']*1024**3,'memory'
 signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('wall budget')));signal.alarm(max(1,int(C['wall_seconds']-(time.time()-start))))
 raw=pd.read_csv(R/'data/train.csv');test=pd.read_csv(R/'data/test.csv',usecols=['Annual_Income_USD']);y=raw.Will_Buy_EV.eq('Yes').to_numpy('int8');ids=raw.id.to_numpy();g=geometry(np.r_[raw.Annual_Income_USD,test.Annual_Income_USD])[:len(raw)]
 spec=importlib.util.spec_from_file_location('geo_backend',R/'model/validation/e2e_v100_20260905/feature_backends.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);backend=m.load_backend('v85');params=json.loads((R/'model/v85_naji_v74_40f/frozen_config.json').read_text())['lightgbm_base_params'];refdir=R/'model/diagnostics/income_context_lowrank_20260906_retry1';z=np.load(refdir/'diagnostic_oof.npz');np.testing.assert_array_equal(z['ids'],ids);ref=z['pred'][:,0].copy();pred=np.full(len(y),np.nan);folds=np.zeros(len(y),int);rows=[]
 for fold,(fit,valid) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(ids,y),1):
  guard();np.testing.assert_array_equal(z['fold'][valid],fold)
  if (P/f'fold_{fold}.json').exists():
   row=json.loads((P/f'fold_{fold}.json').read_text());assert sha(P/f'fold_{fold}.npy')==row['prediction_sha'];pred[valid]=np.load(P/f'fold_{fold}.npy');folds[valid]=fold;rows.append(row);continue
  with warnings.catch_warnings():warnings.simplefilter('ignore');xf,xv,names=backend.encode(fit,y[fit],valid,42+fold)
  assert xf.shape[1]==148
  cache=np.load(refdir/f'fold_{fold}_query.npz');np.testing.assert_array_equal(cache['valid'],valid);np.testing.assert_array_equal(cache['x'],xv)
  old=lgb.Booster(model_file=str(refdir/f'fold_{fold}_arm_0.txt'));base_replay=old.predict(xv,num_threads=8);np.testing.assert_allclose(base_replay,ref[valid],atol=1e-12,rtol=0);del old,cache
  xf=np.c_[xf,g[fit]];xv=np.c_[xv,g[valid]];seed=42+fold;model=lgb.LGBMClassifier(**params,**{k:seed for k in ['random_state','bagging_seed','feature_fraction_seed','data_random_seed']})
  def callback(env):
   if env.iteration%100==0:guard()
  callback.order=5
  model.fit(xf,y[fit],eval_set=[(xv,y[valid])],callbacks=[lgb.early_stopping(C['early_stopping'],verbose=False),callback]);q=model.predict_proba(xv)[:,1];assert np.isfinite(q).all();model.booster_.save_model(str(P/f'fold_{fold}.txt'));replay=lgb.Booster(model_file=str(P/f'fold_{fold}.txt')).predict(xv,num_threads=8);np.testing.assert_allclose(replay,q,atol=1e-12,rtol=0)
  np.save(P/f'fold_{fold}.npy',q);pred[valid]=q;folds[valid]=fold;row={'fold':fold,'baseline_auc':float(roc_auc_score(y[valid],ref[valid])),'candidate_auc':float(roc_auc_score(y[valid],q)),'rounds':model.best_iteration_,'prediction_sha':sha(P/f'fold_{fold}.npy'),'model_sha':sha(P/f'fold_{fold}.txt'),'baseline_replay_max_abs':float(abs(base_replay-ref[valid]).max()),'candidate_replay_max_abs':float(abs(replay-q).max())};row['delta']=row['candidate_auc']-row['baseline_auc'];write(P/f'fold_{fold}.json',row);rows.append(row);print('FOLD',json.dumps(row),flush=True);del xf,xv,model;gc.collect()
  write(P/'progress.json',{'folds':fold,'seconds':time.time()-start})
 sys.path.insert(0,str(R/'model/research_runtime'));from paired_auc import paired_auc
 report=paired_auc(y,ref,pred,folds);report.update({'status':'COMPLETE_DIAGNOSTIC','gate_passed':report['delta']>=.0001 and report['positive_folds']==5,'seconds':time.time()-start,'test_generated':False,'submission_allowed':False,'counts_toward_cycle':False,'fold_replays':rows});np.savez_compressed(P/'diagnostic_oof.npz',ids=ids,fold=folds,pred=pred,baseline=ref);write(P/'result.json',report);signal.alarm(0);print('RESULT',json.dumps(report),flush=True)
if __name__=='__main__':
 try:run()
 except BaseException:write(P/'failure.json',{'traceback':traceback.format_exc(),'time':time.time()});raise
