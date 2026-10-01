#!/usr/bin/env python3
"""P3 single preregistered internal V85-family replacement; no model refit."""
from __future__ import annotations
import hashlib, importlib.util, json, os, sys, time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
PRE=OUT/'preregistration.json'
FREEZE=OUT/'source_freeze.json'
START=time.monotonic()

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def write(name, data):
 p=OUT/name
 if p.exists(): raise RuntimeError(f'Immutable P3 output already exists: {p}')
 temp=p.with_name('.'+p.name+f'.tmp.{os.getpid()}')
 with temp.open('x') as f:
  json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(temp,p)

def save(name, a):
 p=OUT/name
 if p.exists(): raise RuntimeError(f'Immutable P3 output already exists: {p}')
 temp=p.with_name('.'+p.name+f'.tmp.{os.getpid()}')
 with temp.open('xb') as f: np.save(f,a,allow_pickle=False);f.flush();os.fsync(f.fileno())
 os.replace(temp,p)

def mod(path, name):
 s=importlib.util.spec_from_file_location(name,path)
 assert s and s.loader
 m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m)
 return m

def same(name, observed, archived, tol):
 if observed.shape!=archived.shape: raise RuntimeError(f'{name} shape drift')
 delta=float(np.max(np.abs(observed-archived)))
 if not np.allclose(observed,archived,atol=tol,rtol=0):
  raise RuntimeError(f'{name} archive replay mismatch max_delta={delta}')
 return {'max_abs_delta':delta,'exact':bool(np.array_equal(observed,archived)),'shape':list(observed.shape)}

def main():
 pre=json.loads(PRE.read_text()); frozen=json.loads(FREEZE.read_text())
 if pre['status']!='FROZEN_BEFORE_P3_SCORE' or pre['source_freeze_sha256']!=sha(FREEZE):raise RuntimeError('pre-registration drift')
 for relative,rec in frozen['files'].items():
  p=ROOT/relative
  if p.stat().st_size!=rec['bytes'] or sha(p)!=rec['sha256']:raise RuntimeError(f'source drift: {relative}')
 train=pd.read_csv(ROOT/'data/train.csv',usecols=['id','Will_Buy_EV']);test=pd.read_csv(ROOT/'data/test.csv',usecols=['id']); y=train.Will_Buy_EV.eq('Yes').to_numpy(np.int8)
 ident=frozen['identity']
 for name,a,key in [('train_id',train.id.to_numpy('<i8'),'train_id_sha256_int64'),('test_id',test.id.to_numpy('<i8'),'test_id_sha256_int64'),('target',y,'target_sha256_int8')]:
  if hashlib.sha256(a.tobytes()).hexdigest()!=ident[key]:raise RuntimeError(f'{name} identity drift')
 fold=np.full(len(y),-1,np.int8)
 for k,(_,idx) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(np.zeros(len(y)),y)):fold[idx]=k
 if hashlib.sha256(fold.tobytes()).hexdigest()!=ident['meta_fold_sha256_int8']:raise RuntimeError('fold drift')
 def arr(path):return np.load(ROOT/path,allow_pickle=False).astype(np.float64,copy=False)
 a='model/v80_strict_v61_outer104395303_40f/';b='model/v85_naji_v74_40f/';v90='model/v90_v89_member_verify_budget_retry/';v100='model/v100_v90_ctboost_nested_cv_blend/';p1='model/takeover_20260926/p1_source_group_constraints_40f/'
 v80o,v80t=arr(a+'oof_proba.npy'),arr(a+'test_proba.npy')
 v85o,v85t=arr(b+'oof_proba.npy'),arr(b+'test_proba.npy')
 bo,bt=arr(p1+'oof_proba.npy'),arr(p1+'test_proba.npy')
 co,ct=arr(p1+'c_oof.npy'),arr(p1+'c_test.npy')
 same('P1 C OOF definition',co,0.5*(v85o+bo),1e-15);same('P1 C test definition',ct,0.5*(v85t+bt),1e-15)
 if any(x.shape!=(len(y),) for x in [v80o,v85o,bo,co]) or any(x.shape!=(len(test),) for x in [v80t,v85t,bt,ct]):raise RuntimeError('CPU rows drift')
 with np.load(ROOT/'model/diagnostics/ctboost_remote_probe_20260905/remote_output/oof.npz',allow_pickle=False) as z:
  if set(z.files)!={'id','target','prediction','fold'}:raise RuntimeError('CT schema drift')
  if not np.array_equal(z['id'],train.id.to_numpy()) or not np.array_equal(z['target'],y) or not np.array_equal(z['fold'],fold):raise RuntimeError('CT OOF identity/fold drift')
  cto=z['prediction'].astype(np.float64)
 cts=pd.read_csv(ROOT/'model/diagnostics/ctboost_remote_probe_20260905/remote_output/submission.csv')
 if list(cts.columns)!=['id','Will_Buy_EV'] or not cts.id.equals(test.id):raise RuntimeError('CT test IDs drift')
 ctt=cts.Will_Buy_EV.to_numpy(np.float64)
 m90=mod(ROOT/v90/'v90_v89_member_verify_budget_retry.py','p3_frozen_v90')
 m100=mod(ROOT/v100/'v100_v90_ctboost_nested_cv_blend.py','p3_frozen_v100')
 if list(m90.WEIGHT_GRID)!=pre['v90_grid'] or m100.WEIGHT_GRID.tolist()!=pre['v100_grid']:raise RuntimeError('weight grids drift')
 old90=m90.run_meta_cv(y,v80o,v85o,v80t,v85t)
 replay={'v90_oof':same('V90 OOF',old90['oof'],arr(v90+'oof_proba.npy'),1e-15),'v90_test':same('V90 test',old90['test'],arr(v90+'test_proba.npy'),1e-15),'v90_weights':[r['selected_v85_weight'] for r in old90['fold_rows']]}
 old100=m100.nested_blend(y,old90['oof'],cto,old90['test'],ctt)
 replay.update({'v100_oof':same('V100 OOF',old100['oof'],arr(v100+'oof_proba.npy'),1e-15),'v100_test':same('V100 test',old100['test'],arr(v100+'test_proba.npy'),1e-15),'v100_final_ct_weight':old100['final_ctboost_weight'],'v100_auc':float(roc_auc_score(y,old100['oof']))})
 if abs(replay['v100_auc']-pre['baseline_v100_oof_auc'])>1e-12:raise RuntimeError('V100 benchmark AUC drift')
 write('baseline_replay.json',replay)
 print('Baseline V90/V100 replay PASS; beginning single P3 candidate',flush=True)
 new90=m90.run_meta_cv(y,v80o,co,v80t,ct)
 new100=m100.nested_blend(y,new90['oof'],cto,new90['test'],ctt)
 foldrows=[]
 for k in range(5):
  idx=fold==k
  base=float(roc_auc_score(y[idx],old100['oof'][idx])); cand=float(roc_auc_score(y[idx],new100['oof'][idx]))
  foldrows.append({'fold':k+1,'rows':int(idx.sum()),'baseline_auc':base,'candidate_auc':cand,'delta':cand-base,'p3_v90_weight':new90['fold_rows'][k]['selected_v85_weight'],'p3_v100_ct_weight':new100['fold_rows'][k]['selected_ctboost_weight']})
 auc=float(roc_auc_score(y,new100['oof']));delta=auc-replay['v100_auc'];wins=sum(row['delta']>0 for row in foldrows)
 result={'status':'COMPLETE','created_utc':datetime.now(timezone.utc).isoformat(),'candidate':'P3 internal C replaces V85','source_freeze_sha256':sha(FREEZE),'preregistration_sha256':sha(PRE),'runner_sha256':sha(Path(__file__)),'baseline_replay_sha256':sha(OUT/'baseline_replay.json'),'baseline_auc':replay['v100_auc'],'candidate_auc':auc,'delta':delta,'positive_meta_blocks':wins,'folds':foldrows,'gate_pass':bool(auc>pre['development_gate']['pooled_auc_strictly_greater'] and wins==5),'research_delta_at_least_0p0001':bool(delta>=0.0001),'v90_weights':[r['selected_v85_weight'] for r in new90['fold_rows']],'v100_final_ct_weight':new100['final_ctboost_weight'],'elapsed_seconds':time.monotonic()-START,'limit':'Development OOF on existing 40-fold base predictions; not end-to-end outer validation'}
 save('p3_v90_oof.npy',new90['oof']);save('p3_v90_test.npy',new90['test']);save('p3_v100_oof.npy',new100['oof']);save('p3_v100_test.npy',new100['test']);write('development_result.json',result)
 print(json.dumps({k:result[k] for k in ['baseline_auc','candidate_auc','delta','positive_meta_blocks','gate_pass','research_delta_at_least_0p0001','elapsed_seconds']},indent=2),flush=True)
if __name__=='__main__':main()
