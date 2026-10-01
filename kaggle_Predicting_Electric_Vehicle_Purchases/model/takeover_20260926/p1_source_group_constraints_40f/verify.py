"""Independent P1 40-fold artifact, probability, and tree-constraint verifier."""
import hashlib,json
from pathlib import Path
import lightgbm as lgb,numpy as np,pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2];DIAG=HERE.parent/'p1_source_group_constraints_5f'
V85=PROJECT/'model/v85_naji_v74_40f';V100=PROJECT/'model/v100_v90_ctboost_nested_cv_blend'
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def nleaf(node,origins,seen=frozenset()):
 if 'split_feature' not in node:return 1
 field=origins[int(node['split_feature'])];updated=seen|{field}
 if len(updated)>1:raise ValueError(f'cross-group tree path: {updated}')
 return nleaf(node['left_child'],origins,updated)+nleaf(node['right_child'],origins,updated)
def check(arr,n):
 if arr.shape!=(n,) or not np.isfinite(arr).all() or ((arr<0)|(arr>1)).any():raise ValueError('invalid probability artifact')
def main():
 r=json.loads((HERE/'cv_results.json').read_text());frozen=json.loads((DIAG/'freeze_manifest.json').read_text());mapping=json.loads((DIAG/'feature_origin_map.json').read_text());pr=json.loads((HERE/'preflight.json').read_text());source=json.loads((HERE/'sources.json').read_text())
 assert r['status']=='COMPLETE' and source['result_sha256']==sha(HERE/'cv_results.json') and r['contract_sha256']==pr['contract_sha256']
 for rel,record in frozen['source_files'].items():assert sha(PROJECT/rel)==record['sha256'],rel
 y=pd.read_csv(PROJECT/'data/train.csv',usecols=['Will_Buy_EV']).Will_Buy_EV.eq('Yes').to_numpy(np.int8)
 assert hashlib.sha256(y.tobytes()).hexdigest()==frozen['labels_sha256']
 ntest=286571;out=np.full(len(y),np.nan);total=np.zeros(ntest);rows=[];leaf_paths=0
 names=mapping['final_features'];origins=[mapping['feature_to_origin'][name] for name in names]
 for fold,(_,valid) in enumerate(StratifiedKFold(40,shuffle=True,random_state=42).split(np.zeros(len(y)),y),1):
  ck=HERE/f'fold_{fold:02d}.npz';model=HERE/f'model_{fold:02d}.txt'
  with np.load(ck,allow_pickle=False) as z:
   assert int(z['fold'])==fold and np.array_equal(z['valid_idx'],valid) and str(z['contract_sha256'])==r['contract_sha256'] and str(z['model_sha256'])==sha(model)
   vp=z['valid_pred'].astype(float);tp=z['test_pred'].astype(float);check(vp,len(valid));check(tp,ntest)
   auc=float(roc_auc_score(y[valid],vp));assert abs(auc-float(z['auc']))<1e-12 and abs(auc-r['fold_auc'][fold-1])<1e-12
   out[valid]=vp;total+=tp/40;rows.append({'fold':fold,'auc':auc})
  b=lgb.Booster(model_file=str(model));assert b.feature_name()==names
  for tree in b.dump_model()['tree_info']:leaf_paths+=nleaf(tree['tree_structure'],origins)
 check(out,len(y));check(total,ntest)
 np.testing.assert_array_equal(out,np.load(HERE/'oof_proba.npy'));np.testing.assert_allclose(total,np.load(HERE/'test_proba.npy'),atol=1e-15,rtol=0)
 a_oof=np.load(V85/'oof_proba.npy');a_test=np.load(V85/'test_proba.npy');v100_oof=np.load(V100/'oof_proba.npy');v100_test=np.load(V100/'test_proba.npy')
 chosen=json.loads((DIAG/'result.json').read_text())
 expected_choice='fixed_v85_b_50_50' if chosen['diagnostic_gate']['fixed_blend'] and chosen['pooled_delta_vs_a']['fixed_blend']>=chosen['pooled_delta_vs_a']['B'] else 'b_only'
 assert r['selected_c']==expected_choice
 co=out if expected_choice=='b_only' else .5*(a_oof+out);ct=total if expected_choice=='b_only' else .5*(a_test+total);mo=.5*(v100_oof+co);mt=.5*(v100_test+ct)
 for name,expected in [('c_oof',co),('c_test',ct),('m_oof',mo),('m_test',mt)]:np.testing.assert_allclose(np.load(HERE/f'{name}.npy'),expected,atol=1e-15,rtol=0)
 auc={'V85':float(roc_auc_score(y,a_oof)),'V100':float(roc_auc_score(y,v100_oof)),'B':float(roc_auc_score(y,out)),'C':float(roc_auc_score(y,co)),'M':float(roc_auc_score(y,mo))}
 for key,field in [('V100','v100_oof_auc'),('B','oof_auc'),('C','c_oof_auc'),('M','m_oof_auc')]:assert abs(auc[key]-r[field])<1e-12
 blocks=[]
 for k,(_,valid) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(np.zeros(len(y)),y),1):
  base=float(roc_auc_score(y[valid],v100_oof[valid]));c=float(roc_auc_score(y[valid],co[valid]));m=float(roc_auc_score(y[valid],mo[valid]));blocks.append({'block':k,'c_delta':c-base,'m_delta':m-base})
 for row,record in zip(blocks,r['meta_blocks']):
  assert row['block']==record['block']
  for k in ['c_delta','m_delta']:assert abs(row[k]-record[k])<1e-12
 gates={'c':auc['C']>auc['V100'] and all(x['c_delta']>0 for x in blocks),'m':auc['M']>auc['V100'] and all(x['m_delta']>0 for x in blocks)}
 assert gates==r['gates']
 report={'status':'PASS','reconstructed_auc':auc,'gates':gates,'checked_leaf_paths':leaf_paths,'cross_group_paths':0,'reconstructed_folds':40,'result_sha256':sha(HERE/'cv_results.json'),'note':'OOF and saved-model path check; does not retrain full models or constitute end-to-end outer validation'}
 (HERE/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':'PASS','auc':auc,'gates':gates,'leaf_paths':leaf_paths}))
if __name__=='__main__':main()
