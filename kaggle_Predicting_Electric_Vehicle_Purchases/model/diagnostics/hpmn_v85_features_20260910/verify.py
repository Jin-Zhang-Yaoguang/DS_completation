"""Independent OOF/rank/AUC check and full saved-model validation replay."""
from pathlib import Path
import gc,hashlib,importlib.util,json,warnings
import numpy as np
import pandas as pd
import torch
from scipy.stats import rankdata
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

P=Path(__file__).resolve().parent;R=P.parents[2]
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('hpmn_replay_runner',P/'run.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
m=runner.module('hpmn_replay_public',R/'model/diagnostics/hpmn_source_audit_20260910/public_components.py')
backend=runner.module('hpmn_verify_backend',R/'model/validation/e2e_v100_20260905/feature_backends.py').load_backend('v85')
torch.set_num_threads(4);m.DEVICE=torch.device('mps')
raw=pd.read_csv(R/'data/train.csv',usecols=['id','Will_Buy_EV'])
y=raw.Will_Buy_EV.eq('Yes').to_numpy();ids=raw.id.to_numpy()
z=np.load(P/'diagnostic_oof.npz')
np.testing.assert_array_equal(z['ids'],ids)
reference=np.load(runner.REF/'diagnostic_oof.npz')
np.testing.assert_array_equal(z['baseline'],reference['pred'][:,0])
for key in ['pred','baseline','transformed_baseline','blend','equal']:
    assert z[key].shape==(len(y),) and np.isfinite(z[key]).all()
    assert ((z[key]>=0)&(z[key]<=1)).all()
replays=[]
for f,(fit,valid) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(ids,y),1):
    d=P/f'fold_{f}';record=json.loads((d/'result.json').read_text())
    np.testing.assert_array_equal(z['fold'][valid],f)
    np.testing.assert_array_equal(np.load(d/'fit_rows.npy'),fit)
    np.testing.assert_array_equal(np.load(d/'valid_rows.npy'),valid)
    meta=json.loads((d/'input.json').read_text())
    assert meta['fit_labels_sha']==hashlib.sha256(y[fit].astype('int8').tobytes()).hexdigest()
    for name,h in meta['files'].items():assert sha(d/name)==h
    assert sha(d/'model.pt')==record['model_sha']
    assert sha(d/'prediction.npy')==record['prediction_sha']
    np.testing.assert_array_equal(z['pred'][valid],np.load(d/'prediction.npy'))
    scaler=np.load(d/'preprocess.npz')
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        fit_features,valid_features,names=backend.encode(fit,y[fit].astype('int8'),valid,42+f)
    fit_features=fit_features.astype('float32')
    mean=fit_features.mean(axis=0,dtype=np.float64).astype('float32')
    std=fit_features.std(axis=0,dtype=np.float64).astype('float32')
    std=np.where(np.isfinite(std)&(std>1e-7),std,1).astype('float32')
    np.testing.assert_array_equal(mean,scaler['mean'])
    np.testing.assert_array_equal(std,scaler['std'])
    fit_features=np.clip((fit_features-mean)/std,-8,8).astype('float32')
    assert hashlib.sha256(fit_features.tobytes()).hexdigest()==meta['fit_features_sha']
    assert names==meta['feature_names']
    cache=np.load(runner.REF/f'fold_{f}_query.npz')
    np.testing.assert_array_equal(valid_features,cache['x'])
    del fit_features,valid_features
    expected=np.clip((cache['x'].astype('float32')-scaler['mean'])/scaler['std'],-8,8).astype('float32')
    xv=np.load(d/'valid_features.npy');np.testing.assert_array_equal(expected,xv)
    saved=torch.load(d/'model.pt',map_location='cpu',weights_only=True)
    model=m.HierarchicalMatcher(148).to(m.DEVICE)
    model.load_state_dict(saved['state']);model.set_mask_temperature(saved['temperature'])
    replay=runner.predict(model,xv,m.DEVICE)
    np.testing.assert_array_equal(replay,z['pred'][valid])
    assert abs(roc_auc_score(y[valid],replay)-record['auc'])<1e-12
    assert saved['epoch']==record['best_epoch']
    history=json.loads((d/'history.json').read_text())
    assert abs(max(e['auc'] for e in history)-record['auc'])<1e-12
    def transform(a,q):
        s=np.sort(a)
        return (np.searchsorted(s,q,'left')+np.searchsorted(s,q,'right'))/(2*len(s))
    b=transform(z['baseline'][fit],z['baseline'][valid]);h=transform(z['pred'][fit],z['pred'][valid])
    np.testing.assert_allclose(z['transformed_baseline'][valid],b,atol=1e-15,rtol=0)
    np.testing.assert_allclose(z['blend'][valid],.9*b+.1*h,atol=1e-15,rtol=0)
    np.testing.assert_allclose(z['equal'][valid],.5*b+.5*h,atol=1e-15,rtol=0)
    replays.append({'fold':f,'max_abs':float(abs(replay-z['pred'][valid]).max()),'rows':len(valid)})
    del model,saved,xv,expected,cache;gc.collect();torch.mps.empty_cache()
result=json.loads((P/'result.json').read_text());checks={}
for label,keys in [('standalone',('baseline','pred')),('fixed_10pct',('transformed_baseline','blend')),('equal_weight_control',('transformed_baseline','equal'))]:
    auc=[float(roc_auc_score(y,z[k])) for k in keys];parts=[];pos=int(y.sum());neg=int((~y).sum())
    for k in keys:
        v=np.r_[z[k][y],z[k][~y]];r=rankdata(v)
        parts.append(((r[:pos]-rankdata(v[:pos]))/neg,1-(r[pos:]-rankdata(v[pos:]))/pos))
    se=float(np.sqrt(np.var(parts[1][0]-parts[0][0],ddof=1)/pos+np.var(parts[1][1]-parts[0][1],ddof=1)/neg))
    assert abs(auc[1]-auc[0]-result[label]['delta'])<1e-12
    assert abs(se-result[label]['conditional_standard_error'])<1e-12
    wins=sum(roc_auc_score(y[z['fold']==f],z[keys[1]][z['fold']==f])>roc_auc_score(y[z['fold']==f],z[keys[0]][z['fold']==f]) for f in range(1,6))
    assert wins==result[label]['positive_folds']
    checks[label]={'auc':auc,'delta':auc[1]-auc[0],'positive_folds':int(wins),'independent_midrank_se':se}
followup=checks['standalone']['auc'][1]>=.9452 and checks['fixed_10pct']['delta']>0 and checks['fixed_10pct']['positive_folds']==5
promotion=checks['fixed_10pct']['delta']>=.0001 and checks['fixed_10pct']['positive_folds']==5
assert followup==result['followup_gate_passed'] and promotion==result['research_promotion_gate_passed']
out={'status':'PASS','checks':checks,'replays':replays,'followup_gate_passed':followup,'research_promotion_gate_passed':promotion,
     'oof_sha':sha(P/'diagnostic_oof.npz'),'verifier_sha':sha(__file__),'submission_allowed':False}
(P/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False))
