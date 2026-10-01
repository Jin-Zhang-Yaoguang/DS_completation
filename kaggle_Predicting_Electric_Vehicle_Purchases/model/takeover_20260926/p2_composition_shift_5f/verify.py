"""Independent P2 diagnostic artifact and paired-gate reconstruction."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
import lightgbm as lgb,numpy as np,pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
HERE=Path(__file__).resolve().parent;TOP=HERE.parent;ROOT=HERE.parents[2];P1=TOP/'p1_source_group_constraints_5f'
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def check(x,n):
 if x.shape!=(n,) or not np.isfinite(x).all() or ((x<0)|(x>1)).any():raise ValueError('invalid probability array')
def main():
 result=json.loads((HERE/'result.json').read_text());pre=json.loads((HERE/'preflight.json').read_text());frozen=json.loads((P1/'freeze_manifest.json').read_text());mapping=json.loads((P1/'feature_origin_map.json').read_text())
 if result['status']!='COMPLETE_DIAGNOSTIC' or pre['status']!='PASS' or result['contract_sha256']!=pre['contract_sha256']:raise ValueError('P2 completion contract invalid')
 for rel,record in frozen['source_files'].items():
  if sha(ROOT/rel)!=record['sha256']:raise ValueError('frozen source drift')
 raw=pd.read_csv(ROOT/'data/train.csv');y=raw.Will_Buy_EV.eq('Yes').to_numpy(np.int8);ids=raw.id.to_numpy(np.int64)
 if hashlib.sha256(y.tobytes()).hexdigest()!=frozen['labels_sha256'] or hashlib.sha256(ids.tobytes()).hexdigest()!=frozen['raw_train_ids_sha256']:raise ValueError('P2 row identity drift')
 a=np.load(P1/'oof_a.npy');b=np.full(len(y),np.nan);rows=[];names=mapping['final_features']+['composition_shift','composition_adjustment']
 for fold,(fit,valid) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(np.zeros(len(y)),y),1):
  with np.load(HERE/f'fold_{fold:02d}.npz',allow_pickle=False) as z:
   if int(z['fold'])!=fold or str(z['contract_sha256'])!=pre['contract_sha256'] or not np.array_equal(z['valid_idx'],valid) or str(z['model_sha256'])!=sha(HERE/f'fold_{fold:02d}.txt'):raise ValueError('P2 fold checkpoint drift')
   pred=z['pred'].astype(float);check(pred,len(valid));reported=float(z['auc']);auc=float(roc_auc_score(y[valid],pred))
   if abs(auc-reported)>1e-12:raise ValueError('P2 fold AUC mismatch')
   info=json.loads(str(z['composition_info_json']))
  with np.load(HERE/f'composition_{fold:02d}.npz',allow_pickle=False) as c:
   if not np.array_equal(c['fit_idx'],fit) or not np.array_equal(c['valid_idx'],valid) or c['fit_features'].shape!=(len(fit),2) or c['valid_features'].shape!=(len(valid),2) or not np.isfinite(c['fit_features']).all() or not np.isfinite(c['valid_features']).all():raise ValueError('composition row or finite check failed')
  inner=list(StratifiedKFold(5,shuffle=True,random_state=42+fold).split(np.zeros(len(fit)),y[fit]))
  if len(info['inner'])!=5:raise ValueError('inner donor audit incomplete')
  for k,((donor_local,hold_local),record) in enumerate(zip(inner,info['inner']),1):
   donor=fit[donor_local];hold=fit[hold_local]
   if record['inner_fold']!=k or record['donor_idx_sha256']!=hashlib.sha256(donor.tobytes()).hexdigest() or record['hold_idx_sha256']!=hashlib.sha256(hold.tobytes()).hexdigest() or record['donor_rows']!=len(donor) or record['hold_rows']!=len(hold) or record['max_curve_error']>1e-3:raise ValueError('inner donor-only audit drift')
  model=lgb.Booster(model_file=str(HERE/f'fold_{fold:02d}.txt'))
  if model.feature_name()!=names:raise ValueError('P2 trained feature schema drift')
  b[valid]=pred;ref=float(roc_auc_score(y[valid],a[valid]));mix=float(roc_auc_score(y[valid],.5*(a[valid]+pred)))
  saved=result['folds'][fold-1]
  for field,value in [('a_auc',ref),('b_auc',auc),('fixed_blend_auc',mix),('b_delta',auc-ref),('fixed_blend_delta',mix-ref)]:
   if abs(saved[field]-value)>1e-12:raise ValueError('P2 result fold arithmetic mismatch')
  rows.append({'fold':fold,'a_auc':ref,'b_auc':auc,'fixed_blend_auc':mix,'b_delta':auc-ref,'fixed_blend_delta':mix-ref})
 check(a,len(y));check(b,len(y));np.testing.assert_array_equal(b,np.load(HERE/'oof_proba.npy'));mix=.5*(a+b);np.testing.assert_array_equal(mix,np.load(HERE/'fixed_blend_oof.npy'))
 pooled={'A':float(roc_auc_score(y,a)),'B':float(roc_auc_score(y,b)),'fixed_blend':float(roc_auc_score(y,mix))}
 for key,value in pooled.items():
  if abs(result['pooled_oof_auc'][key]-value)>1e-12:raise ValueError('P2 pooled AUC drift')
 gates={'B':pooled['B']>pooled['A'] and all(r['b_delta']>0 for r in rows),'fixed_blend':pooled['fixed_blend']>pooled['A'] and all(r['fixed_blend_delta']>0 for r in rows)}
 if gates!=result['gates']:raise ValueError('P2 gate drift')
 out={'status':'PASS','result_sha256':sha(HERE/'result.json'),'reconstructed_auc':pooled,'gates':gates,'folds':rows,'checked_models':5,'checked_inner_donor_partitions':25,'note':'Audits saved composition features and donor index hashes; does not independently retrain nuisance models or constitute E2E validation.'}
 (HERE/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':'PASS','auc':pooled,'gates':gates}))
if __name__=='__main__':main()
