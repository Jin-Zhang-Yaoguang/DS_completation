"""Independent reconstruction of saved P1 diagnostic and tree path constraints."""
import hashlib,json
from pathlib import Path
import lightgbm as lgb
import numpy as np,pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def count_paths(tree,index_origin):
 count=0
 stack=[(tree,set())]
 while stack:
  node,origins=stack.pop()
  if 'split_feature' not in node:
   count+=1;continue
  next_origins=origins|{index_origin[node['split_feature']]}
  if len(next_origins)>1:raise ValueError(f'tree path crossed source groups: {next_origins}')
  stack.append((node['left_child'],next_origins));stack.append((node['right_child'],next_origins))
 return count

def main():
 result=json.loads((HERE/'result.json').read_text());mapping=json.loads((HERE/'feature_origin_map.json').read_text());freeze=json.loads((HERE/'freeze_manifest.json').read_text())
 y=pd.read_csv(ROOT/'data/train.csv',usecols=['Will_Buy_EV']).Will_Buy_EV.eq('Yes').to_numpy(np.int8)
 assert hashlib.sha256(y.tobytes()).hexdigest()==freeze['labels_sha256']
 folds=list(StratifiedKFold(5,shuffle=True,random_state=42).split(np.zeros(len(y)),y));out=np.full((len(y),2),np.nan);folds_rebuilt=[];checked_tree_paths=0
 origins=[mapping['feature_to_origin'][name] for name in mapping['final_features']]
 for fold,(_,valid) in enumerate(folds,1):
  row={'fold':fold}
  for j,arm in enumerate(('A','B')):
   ck=HERE/f'fold_{fold:02d}_{arm}.npz';mp=HERE/f'fold_{fold:02d}_{arm}.txt'
   with np.load(ck,allow_pickle=False) as d:
    assert np.array_equal(d['valid_idx'],valid)
    assert sha(mp)==str(d['model_sha256'])
    assert str(d['contract_sha256'])==result['contract_sha256']
    pred=d['valid_pred'];assert pred.shape==(len(valid),) and np.isfinite(pred).all()
    out[valid,j]=pred;auc=float(roc_auc_score(y[valid],pred));assert abs(auc-float(d['fold_auc']))<1e-12
    row[arm]=auc
   if arm=='B':
    booster=lgb.Booster(model_file=str(mp))
    assert booster.feature_name()==mapping['final_features']
    for tree in booster.dump_model()['tree_info']:
     checked_tree_paths+=count_paths(tree['tree_structure'],origins)
  row['blend']=float(roc_auc_score(y[valid],.5*(out[valid,0]+out[valid,1])));folds_rebuilt.append(row)
 assert np.isfinite(out).all()
 aucs={'A':float(roc_auc_score(y,out[:,0])),'B':float(roc_auc_score(y,out[:,1])),'fixed_blend':float(roc_auc_score(y,.5*(out[:,0]+out[:,1])))}
 for key,value in aucs.items():
  assert abs(value-result['pooled_oof_auc'][key])<1e-12
  saved=np.load(HERE/f'oof_{key.lower()}.npy');expected=out[:,0] if key=='A' else out[:,1] if key=='B' else .5*(out[:,0]+out[:,1]);np.testing.assert_array_equal(saved,expected)
 for x,r in zip(folds_rebuilt,result['folds']):
  assert x['fold']==r['fold']
  for key,col in [('A','a_auc'),('B','b_auc'),('blend','blend_auc')]:assert abs(x[key]-r[col])<1e-12
 decision=any(aucs[key]>aucs['A'] and sum(x[key]>x['A'] for x in folds_rebuilt)==5 for key in ('B','blend'))
 assert decision==result['diagnostic_gate']['any_pass']
 report={'status':'PASS','recomputed_pooled_auc':aucs,'decision':decision,'folds':folds_rebuilt,'B_leaf_paths_checked':checked_tree_paths,'cross_group_paths':0,'saved_result_sha256':sha(HERE/'result.json')}
 (HERE/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':'PASS','auc':aucs,'paths_checked':checked_tree_paths,'gate':decision}))
if __name__=='__main__':main()
