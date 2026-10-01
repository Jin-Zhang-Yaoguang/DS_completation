"""重新核对既有预测的配对差值，不重新训练或选模。"""
import os
os.environ['OPENBLAS_NUM_THREADS']='2'
from pathlib import Path
import sys,json,hashlib
import numpy as np,pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
P=Path(__file__).resolve().parent;R=P.parents[2];sys.path.insert(0,str(R/'model/research_runtime'))
from paired_auc import paired_auc
raw=pd.read_csv(R/'data/train.csv',usecols=['id','Will_Buy_EV']);ids=raw.id.to_numpy();y=raw.Will_Buy_EV.eq('Yes').to_numpy();fold=np.empty(len(y),int)
for k,(_,v) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(ids,y),1):fold[v]=k
v90=np.load(R/'model/v90_v89_member_verify_budget_retry/oof_proba.npy');v100=np.load(R/'model/v100_v90_ctboost_nested_cv_blend/oof_proba.npy')
sources=json.loads((R/'model/v100_v90_ctboost_nested_cv_blend/sources.json').read_text());assert hashlib.sha256((R/'data/train.csv').read_bytes()).hexdigest()==sources['source_sha256']['train.csv'];assert hashlib.sha256((R/'model/v90_v89_member_verify_budget_retry/oof_proba.npy').read_bytes()).hexdigest()==sources['source_sha256']['v90_oof']
a=np.load(R/'model/diagnostics/tabm_num_embeddings_20260906/diagnostic_oof.npz');b=np.load(R/'model/diagnostics/income_context_lowrank_20260906_retry1/diagnostic_oof.npz')
for z in [a,b]:np.testing.assert_array_equal(z['ids'],ids);np.testing.assert_array_equal(z['fold'],fold)
report={}
for name,base,cand in [('v90_to_v100',v90,v100),('tabm_plain_to_linear',a['pred'][:,0],a['pred'][:,1]),('v85_to_tabm_linear',b['pred'][:,0],a['pred'][:,1])]:
 out=paired_auc(y,base,cand,fold);assert abs(out['candidate_auc']-roc_auc_score(y,cand))<1e-12;report[name]=out
(P/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:{j:v[j] for j in ['delta','conditional_ci95','positive_folds']} for k,v in report.items()},ensure_ascii=False))
