"""Verify all P1 E2E checkpoints before first new outer-U scoring."""
import hashlib,json
from pathlib import Path
import lightgbm as lgb,numpy as np,pandas as pd
from sklearn.metrics import roc_auc_score
HERE=Path(__file__).resolve().parent;TOP=HERE.parent;PROJECT=HERE.parents[2];ARCH=PROJECT/'model/validation/e2e_v100_20260905';DIAG=TOP/'p1_source_group_constraints_5f';FORMAL=TOP/'p1_source_group_constraints_40f'
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def leaves(node,origins,seen=frozenset()):
 if 'split_feature' not in node:return 1
 z=seen|{origins[int(node['split_feature'])]}
 if len(z)>1:raise ValueError(f'cross-group path: {z}')
 return leaves(node['left_child'],origins,z)+leaves(node['right_child'],origins,z)
def prob(p,n):
 if p.shape!=(n,) or not np.isfinite(p).all() or ((p<0)|(p>1)).any():raise ValueError('invalid probabilities')
def main():
 complete=json.loads((HERE/'cache_complete.json').read_text());pre=json.loads((HERE/'preflight.json').read_text());formal=json.loads((FORMAL/'cv_results.json').read_text());mapping=json.loads((DIAG/'feature_origin_map.json').read_text())
 assert complete['status']=='CACHE_COMPLETE_UNSCORED' and complete['atoms']==200 and complete['contract_sha256']==pre['contract_sha256'] and complete['candidate_selected_before_U_scoring'] in ('M','C')
 assert complete['candidate_selected_before_U_scoring']==('M' if formal['gates']['m'] else 'C')
 ids=pd.read_csv(PROJECT/'data/train.csv',usecols=['id']).id.to_numpy(np.int64);n=len(ids);baseline=np.full(n,np.nan);candidate=np.full(n,np.nan);fold_id=np.zeros(n,np.int8);count=np.zeros(n,np.int8);leaf_count=0;outer_reports=[]
 origins=[mapping['feature_to_origin'][x] for x in mapping['final_features']]
 with np.load(ARCH/'splits.npz',allow_pickle=False) as z:
  for outer in range(1,6):
   train=z[f'outer_{outer:02d}_train_idx'];hold=z[f'outer_{outer:02d}_valid_idx'];atom_fold=z[f'outer_{outer:02d}_v85_fold']
   cache=HERE/f'outer_{outer:02d}/cache.npz';manifest=json.loads((HERE/f'outer_{outer:02d}/cache_manifest.json').read_text())
   assert manifest['status']=='CACHE_COMPLETE_UNSCORED' and manifest['contract_sha256']==pre['contract_sha256'] and manifest['cache_sha256']==sha(cache) and not manifest['outer_U_labels_used']
   oof=np.full(len(train),np.nan);valid=np.zeros(len(hold));coverage=np.zeros(len(train),np.int8)
   for atom in range(1,41):
    local=np.flatnonzero(atom_fold==atom-1);oofrows=train[local];fitrows=train[atom_fold!=atom-1];directory=HERE/f'outer_{outer:02d}/atom_{atom:02d}';meta=json.loads((directory/'manifest.json').read_text())
    assert meta['status']=='COMPLETE' and meta['contract_sha256']==pre['contract_sha256'] and not meta['outer_U_labels_used'] and meta['query_labels_available'] is False and meta['final_fit_eval_set_used'] is False
    assert meta['fit_idx_sha256']==hashlib.sha256(np.asarray(fitrows,dtype='<i8').tobytes()).hexdigest()
    assert meta['query_idx_sha256']==hashlib.sha256(np.asarray(np.concatenate([oofrows,hold]),dtype='<i8').tobytes()).hexdigest()
    assert meta['model_sha256']==sha(directory/'model.txt') and meta['prediction_sha256']==sha(directory/'predictions.npz') and manifest['atom_manifest_sha256'][str(atom)]==sha(directory/'manifest.json')
    with np.load(directory/'predictions.npz',allow_pickle=False) as a:
     assert np.array_equal(a['oof_idx'],oofrows) and np.array_equal(a['valid_idx'],hold) and np.array_equal(a['oof_id'],ids[oofrows]) and np.array_equal(a['valid_id'],ids[hold]);prob(a['oof_proba'],len(local));prob(a['valid_proba'],len(hold));oof[local]=a['oof_proba'];valid+=a['valid_proba']/40;coverage[local]+=1
    model=lgb.Booster(model_file=str(directory/'model.txt'))
    assert model.feature_name()==mapping['final_features']
    for tree in model.dump_model()['tree_info']:leaf_count+=leaves(tree['tree_structure'],origins)
   assert np.all(coverage==1) and np.isfinite(oof).all();prob(valid,len(hold))
   with np.load(cache,allow_pickle=False) as a:
    assert np.array_equal(a['train_idx'],train) and np.array_equal(a['valid_idx'],hold) and np.array_equal(a['train_id'],ids[train]) and np.array_equal(a['valid_id'],ids[hold]) and np.array_equal(a['atom_fold'],atom_fold)
    np.testing.assert_array_equal(a['oof_proba'],oof);np.testing.assert_allclose(a['valid_proba'],valid,atol=1e-15,rtol=0)
   old_v85=ARCH/f'outer_{outer:02d}/v85/cache.npz';old_base=ARCH/f'assembled/outer_{outer:02d}/predictions.npz';old_manifest=json.loads((ARCH/f'assembled/outer_{outer:02d}/manifest.json').read_text())
   assert old_manifest['status']=='ASSEMBLED_UNSCORED' and old_manifest['prediction_sha256']==sha(old_base) and not old_manifest['outer_hold_labels_used']
   with np.load(old_v85,allow_pickle=False) as a:assert np.array_equal(a['valid_idx'],hold);v85=a['valid_proba']
   with np.load(old_base,allow_pickle=False) as a:assert np.array_equal(a['valid_idx'],hold) and np.array_equal(a['valid_id'],ids[hold]);ref=a['baseline_proba']
   co=.5*(v85+valid);pred=.5*(ref+co) if complete['candidate_selected_before_U_scoring']=='M' else co
   prob(ref,len(hold));prob(pred,len(hold));baseline[hold]=ref;candidate[hold]=pred;fold_id[hold]=outer;count[hold]+=1
   outer_reports.append({'outer':outer,'hold_rows':len(hold),'new_cache_sha256':sha(cache),'archived_v85_cache_sha256':sha(old_v85),'archived_v100_prediction_sha256':sha(old_base)})
 assert np.all(count==1) and np.isfinite(baseline).all() and np.isfinite(candidate).all()
 audit={'status':'PASS_UNSCORED','candidate_selected_before_scoring':complete['candidate_selected_before_U_scoring'],'contract_sha256':pre['contract_sha256'],'checked_atom_models':200,'leaf_paths_checked':leaf_count,'cross_group_paths':0,'outer_reports':outer_reports,'baseline_predictions_sha256':hashlib.sha256(baseline.tobytes()).hexdigest(),'candidate_predictions_sha256':hashlib.sha256(candidate.tobytes()).hexdigest()}
 (HERE/'verification.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
 # First score new outer-U labels only after all source, row, model, and prediction checks pass.
 y=pd.read_csv(PROJECT/'data/train.csv',usecols=['Will_Buy_EV']).Will_Buy_EV.eq('Yes').to_numpy(np.int8)
 old=json.loads((ARCH/'e2e_results.json').read_text());base=float(roc_auc_score(y,baseline));assert abs(base-old['baseline_auc'])<1e-12
 can=float(roc_auc_score(y,candidate));folds=[]
 for k in range(1,6):
  idx=fold_id==k;b=float(roc_auc_score(y[idx],baseline[idx]));c=float(roc_auc_score(y[idx],candidate[idx]));folds.append({'fold':k,'baseline_auc':b,'candidate_auc':c,'delta':c-b})
 passed=can>base and all(row['delta']>0 for row in folds)
 result={'status':'COMPLETE_E2E_CONFIRMATION','candidate':complete['candidate_selected_before_U_scoring'],'baseline_role':'archived V100 full-architecture E2E at 80% outer T, internal early stop; not online full-data score','baseline_auc':base,'candidate_auc':can,'delta':can-base,'folds':folds,'positive_folds':sum(row['delta']>0 for row in folds),'gate_passed':passed,'research_plus_0_0001':can-base>=.0001 and passed,'verification_sha256':sha(HERE/'verification.json'),'historically_exposed_data':True,'is_new_blind_test':False,'full_data_formal_gate':formal['gates'],'online_best_reference':{'submission_ref':56023943,'public_score':0.94635},'submission_allowed_from_this_result_alone':False}
 (HERE/'e2e_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':result['status'],'baseline':base,'candidate':can,'delta':can-base,'positive_folds':result['positive_folds'],'gate':passed,'checked_leaf_paths':leaf_count}))
if __name__=='__main__':main()
