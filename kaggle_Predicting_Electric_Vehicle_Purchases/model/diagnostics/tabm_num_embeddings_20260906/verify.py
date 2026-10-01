"""独立核对五折行身份、保存模型、预测、秩和AUC和预定门槛。"""
import os,sys
os.environ['OMP_NUM_THREADS']='4'
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2];sys.path.insert(0,str(P))
import hashlib,json,time,signal,resource
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.model_selection import StratifiedKFold
import torch
import worker

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def auc(y,p):
 n=int(y.sum());return float((rankdata(p)[y==1].sum()-n*(n+1)/2)/(n*(len(y)-n)))
start=time.monotonic();signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('verification 180 seconds')));signal.alarm(180)
def guard():
 assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss+torch.mps.driver_allocated_memory()<16*1024**3
r=json.loads((P/'result.json').read_text());c=json.loads((P/'contract.json').read_text());cfg=json.loads((P/'preregistration.json').read_text())
for f,d in c['code'].items():assert sha(P/f)==d,f
for f,d in c['sources'].items():assert sha(R/f)==d,f
assert sha(P/'diagnostic_oof.npz')==r['oof_sha'] and sha(P/'contract.json')==r['contract_sha']
raw=pd.read_csv(R/'data/train.csv');ids=raw.id.to_numpy();y=raw.Will_Buy_EV.map({'No':0,'Yes':1}).to_numpy()
with np.load(P/'diagnostic_oof.npz') as z:np.testing.assert_array_equal(z['ids'],ids);pred=z['pred'].copy();fold=z['fold'].copy()
assert pred.shape==(len(y),2) and np.isfinite(pred).all() and ((pred>=0)&(pred<=1)).all()
with np.load(R/'model/diagnostics/income_context_lowrank_20260906_retry1/diagnostic_oof.npz') as z:np.testing.assert_array_equal(z['ids'],ids);ref=z['pred'][:,0].copy()
errors=[];rows=[];manifest={}
for k,(fit,valid) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(np.zeros(len(y)),y),1):
 d=P/f'fold_{k}';meta=json.loads((d/'input.json').read_text());assert meta['contract_sha']==sha(P/'contract.json')
 for name,h in meta['hashes'].items():assert sha(d/name)==h,name
 np.testing.assert_array_equal(np.load(d/'fit_rows.npy'),fit);np.testing.assert_array_equal(np.load(d/'valid_rows.npy'),valid);np.testing.assert_array_equal(np.load(d/'valid_ids.npy'),ids[valid]);np.testing.assert_array_equal(np.flatnonzero(fold==k),valid)
 np.testing.assert_array_equal(np.load(d/'fit_y.npy'),y[fit]);np.testing.assert_array_equal(np.load(d/'valid_y.npy'),y[valid])
 xv=torch.from_numpy(np.load(d/'valid.npy')).to('mps');scores=[]
 for arm in [0,1]:
  q=d/f'arm_{arm}';a=json.loads((q/'result.json').read_text());assert a['input_sha']==sha(d/'input.json') and a['model_sha']==sha(q/'best.pt') and a['prediction_sha']==sha(q/'prediction.npy')
  saved=np.load(q/'prediction.npy');np.testing.assert_array_equal(saved,pred[valid,arm])
  m=worker.make(xv.shape[1],arm).to('mps');m.load_state_dict(torch.load(q/'best.pt',map_location='cpu',weights_only=True));rebuilt=worker.predict(m,xv,guard);error=float(abs(rebuilt-saved).max());assert error<=1e-6;errors.append(error)
  value=auc(y[valid],saved);assert abs(value-a['auc'])<1e-12;scores.append(value)
  # 重新按冻结早停改进门槛恢复最佳epoch，不以末轮或任意轮代替。
  best=-float('inf');epoch=None
  for row in a['history']:
   if row['auc']>best+cfg['min_delta']:best=row['auc'];epoch=row['epoch']
  assert epoch==a['best_epoch'] and abs(best-value)<1e-12
  for f in ['best.pt','prediction.npy','result.json']:manifest[str((q/f).relative_to(P))]=sha(q/f)
  del m;torch.mps.empty_cache()
 rows.append({'fold':k,'auc':scores,'delta':scores[1]-scores[0],'reference_auc':auc(y[valid],ref[valid]),'candidate_delta_vs_v85':scores[1]-auc(y[valid],ref[valid])});del xv;torch.mps.empty_cache()
values=[auc(y,pred[:,j]) for j in [0,1]];np.testing.assert_allclose(values,r['auc'],atol=1e-12,rtol=0);wins=sum(x['delta']>0 for x in rows);gate=values[1]-values[0]>=.0001 and wins==5 and values[1]>=.9452
assert gate==r['mechanism_gate_passed'] and wins==r['positive_folds']
primary=(raw.Environmental_Concern_Level.ge(4)&raw.Subsidy_Available.eq('Yes')&raw.Range_Anxiety_Level.eq('Low')).to_numpy();den=int(y.sum())*int(len(y)-y.sum());parts=[]
for p in [pred[:,0],pred[:,1],ref]:
 x={}
 for name,a,b in [('within_primary',primary,primary),('pos_primary_neg_other',primary,~primary),('pos_other_neg_primary',~primary,primary),('within_other',~primary,~primary)]:
  mask=((y==1)&a)|((y==0)&b);yy=y[mask];weight=int(yy.sum())*int(len(yy)-yy.sum())/den;x[name]=(1-auc(yy,p[mask]))*weight
 assert abs(1-sum(x.values())-auc(y,p))<1e-12;parts.append(x)
for name in ['result.json','diagnostic_oof.npz','run.py','worker.py','preregistration.json','contract.json','verify.py']:manifest[name]=sha(P/name)
(P/'artifact_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
out={'status':'PASS','scope':'十个最佳checkpoint预测重载、ID与标签、全部缓存哈希、五折和整体秩和AUC、最佳epoch与门槛复算；未重训模型，不是V100端到端验证','auc':values,'delta':values[1]-values[0],'positive_folds':wins,'candidate_delta_vs_v85':values[1]-auc(y,ref),'candidate_wins_vs_v85':sum(x['candidate_delta_vs_v85']>0 for x in rows),'gate_passed':gate,'max_prediction_reload_error':max(errors),'folds':rows,'pair_error_mass_plain_embed_v85':parts,'elapsed_seconds':time.monotonic()-start,'manifest_sha':sha(P/'artifact_manifest.json'),'submission_allowed':False}
(P/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False,indent=2));signal.alarm(0)
