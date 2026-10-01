from pathlib import Path
import hashlib,json,time
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import roc_auc_score
P=Path(__file__).resolve().parent;R=P.parents[1];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
c=json.loads((P/'preregistration.json').read_text());started=json.loads((P/'RUN_STARTED.json').read_text());progress=json.loads((P/'progress.json').read_text());failure=json.loads((P/'failure.json').read_text())
assert 'np.array_equal(oof,reference' in failure['traceback'] and failure['traceback'].rstrip().endswith('AssertionError')
assert sha(P/'rebuild.py')==started['code_sha256'];assert sha(P/'preregistration.json')==started['prereg_sha256'];assert len(progress['folds'])==5
for name,digest in c['source_hashes'].items():assert sha(R/name)==digest,name
train=pd.read_csv(R/'data/train.csv',usecols=['id','Will_Buy_EV']);test=pd.read_csv(R/'data/test.csv',usecols=['id']);sample=pd.read_csv(R/'data/sample_submission.csv');y=train.Will_Buy_EV.map({'Yes':1,'No':0}).to_numpy();ref=np.load(R/'model/diagnostics/original_prior_reliability_20260905/diagnostic_oof.npz',allow_pickle=False)
assert np.array_equal(train.id,ref['ids']) and np.array_equal(sample.id,test.id)
oof=np.full(len(train),np.nan);pred=np.zeros(len(test));files={};diffs=[]
for fold,(_,valid) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(np.zeros(len(y)),y),1):
 f=P/f'fold_{fold}.npz';a=np.load(f,allow_pickle=False);assert np.array_equal(a['valid_rows'],valid);assert np.array_equal(a['valid_ids'],train.id.to_numpy()[valid]);assert np.array_equal(a['test_ids'],test.id)
 for key,rows in [('valid_proba',len(valid)),('test_proba',len(test))]:assert a[key].shape==(rows,) and np.isfinite(a[key]).all() and ((a[key]>=0)&(a[key]<=1)).all()
 diff=float(np.max(np.abs(a['valid_proba']-ref['b'][valid])));assert diff<=c['require_reference_reproduction_max_abs'];diffs.append(diff)
 assert roc_auc_score(y[valid],a['valid_proba'])==progress['folds'][fold-1]['auc'];assert (P/f'fold_{fold}.txt').is_file()
 oof[valid]=a['valid_proba'];pred+=a['test_proba']/5;files[f.name]=sha(f);files[f'fold_{fold}.txt']=sha(P/f'fold_{fold}.txt')
assert np.isfinite(oof).all();auc=roc_auc_score(y,oof);assert abs(auc-c['reference_oof_auc'])<1e-12
np.save(P/'oof_proba.npy',oof);np.save(P/'test_proba.npy',pred);sample['Will_Buy_EV']=pred;sample.to_csv(P/'submission.csv',index=False)
check=pd.read_csv(P/'submission.csv');assert list(check)==['id','Will_Buy_EV'];assert len(check)==286571 and check.id.is_unique and np.array_equal(check.id,test.id);np.testing.assert_allclose(check.Will_Buy_EV,pred,atol=1e-15,rtol=0)
result={'status':'READY_EXPLORATORY_SUBMISSION','oof_auc':auc,'reference_max_abs':max(diffs),'tolerance':c['require_reference_reproduction_max_abs'],'failure_resolution':'Original model training completed; overly strict final bit-equality assertion replaced in separate assembler by pre-registered 1e-12 tolerance. No retraining or change of predictions.','failure_preserved_sha256':sha(P/'failure.json'),'model_checkpoint_sha256':files,'submission_sha256':sha(P/'submission.csv'),'rows':len(check),'training_elapsed_seconds_to_last_checkpoint':progress['elapsed_seconds'],'code_sha256':sha(P/'rebuild.py'),'assembler_sha256':sha(Path(__file__)),'superiority_to_v100_proven':False,'research_promotion':False,'user_authorized_exploratory_submission':True,'submission_budget':1}
(P/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='model_checkpoint_sha256'},ensure_ascii=False,indent=2))
