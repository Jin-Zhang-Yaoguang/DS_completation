"""独立读取checkpoint，重算预测、行身份、五折差值和排序贡献。"""
import os
os.environ['OMP_NUM_THREADS']='4'
import hashlib,json
from pathlib import Path
import lightgbm as lgb
import numpy as np
import pandas as pd
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
P=Path(__file__).resolve().parent;R=P.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def auc_rank(y,p):
    ranks=rankdata(p,method='average');n=int(y.sum());return float((ranks[y==1].sum()-n*(n+1)/2)/(n*(len(y)-n)))
r=json.loads((P/'result.json').read_text());cfg=json.loads((P/'preregistration.json').read_text())
assert r['contract']['worker']==sha(P/'matrix_worker.py')
assert r['contract']['runner']==sha(P/'run.py') and r['contract']['config']==sha(P/'preregistration.json')
for name,digest in cfg['source_hashes'].items():assert sha(R/name)==digest,name
raw=pd.read_csv(R/'data/train.csv');y=raw.Will_Buy_EV.map({'No':0,'Yes':1}).to_numpy();ids=raw.id.to_numpy()
with np.load(P/'diagnostic_oof.npz') as z:
    np.testing.assert_array_equal(z['ids'],ids);pred=z['pred'].copy();fold=z['fold'].copy()
assert pred.shape==(len(y),3) and np.isfinite(pred).all() and ((pred>=0)&(pred<=1)).all()
assert sha(P/'diagnostic_oof.npz')==r['oof_sha256']
max_error=0.;folds=[]
for k,(fit,valid) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(np.zeros(len(y)),y),1):
    np.testing.assert_array_equal(np.flatnonzero(fold==k),valid)
    rec=json.loads((P/f'fold_{k}.json').read_text());assert sha(P/f'fold_{k}.npz')==rec['checkpoint_sha256']
    with np.load(P/f'fold_{k}.npz') as z:
        np.testing.assert_array_equal(z['ids'],ids[valid]);np.testing.assert_array_equal(z['pred'],pred[valid])
    with np.load(P/f'fold_{k}_query.npz') as z:
        xv=z['x'];scores=z['scores'];np.testing.assert_array_equal(z['valid'],valid)
    values=[]
    for arm in range(3):
        m=lgb.Booster(model_file=str(P/f'fold_{k}_arm_{arm}.txt'))
        x=xv if arm==0 else np.column_stack([xv,scores[:,arm-1]])
        pp=m.predict(x,num_threads=4);err=float(abs(pp-pred[valid,arm]).max());max_error=max(max_error,err);assert err<1e-14
        a=auc_rank(y[valid],pp);assert abs(a-rec['arms'][arm]['auc'])<1e-12;values.append(a)
    folds.append({'fold':k,'auc':values,'delta_primary':values[2]-values[0],'delta_mechanism':values[2]-values[1]})
aucs=[auc_rank(y,pred[:,j]) for j in range(3)];np.testing.assert_allclose(aucs,r['auc'],atol=1e-12,rtol=0)
primary=(raw.Environmental_Concern_Level.ge(4)&raw.Subsidy_Available.eq('Yes')&raw.Range_Anxiety_Level.eq('Low')).to_numpy()
parts=[]
for arm in range(3):
    d={};total=int((y==1).sum())*int((y==0).sum())
    for name,a,b in [('within_primary',primary,primary),('pos_primary_neg_other',primary,~primary),('pos_other_neg_primary',~primary,primary),('within_other',~primary,~primary)]:
        mask=((y==1)&a)|((y==0)&b);yy=y[mask];paircount=int(yy.sum())*int(len(yy)-yy.sum())
        d[name]=(1-auc_rank(yy,pred[mask,arm]))*paircount/total
        assert abs(d[name]-r['pair_error_mass'][arm][name])<1e-12
    parts.append(d)
wins=sum(x['delta_primary']>0 for x in folds);mwins=sum(x['delta_mechanism']>0 for x in folds)
gate=aucs[2]-aucs[0]>=cfg['gate']['primary_delta'] and wins==5 and aucs[2]>aucs[1] and mwins==5
assert gate==r['gate_passed'] and wins==r['positive_folds_primary'] and mwins==r['positive_folds_mechanism']
manifest={p.name:sha(p) for p in sorted(P.iterdir()) if p.is_file() and p.suffix in ('.json','.npz','.py','.txt') and p.name not in ('verification.json','train_log.txt','artifact_manifest.json')}
(P/'artifact_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
out={'status':'PASS','scope':'冻结来源、全量行身份、五折分区、15个树checkpoint预测重算、秩和AUC独立计算、四类配对贡献及门槛重算；不含重新训练矩阵模型和V100端到端验证','max_prediction_error':max_error,'auc':aucs,'delta_primary':aucs[2]-aucs[0],'delta_mechanism':aucs[2]-aucs[1],'positive_folds':[wins,mwins],'gate_passed':gate,'folds':folds,'pair_gain_candidate_minus_base':{k:parts[0][k]-parts[2][k] for k in parts[0]},'manifest_sha256':sha(P/'artifact_manifest.json'),'test_predictions':False,'submission_allowed':False}
(P/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n');print(json.dumps(out,ensure_ascii=False,indent=2))
