"""Independent P3 full-row and meta-formula reconstruction."""
import hashlib,importlib.util,json,sys
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(s):return np.load(ROOT/s,allow_pickle=False).astype(float)
pre=json.loads((HERE/'preregistration.json').read_text());frozen=json.loads((HERE/'source_freeze.json').read_text());r=json.loads((HERE/'development_result.json').read_text())
assert r['preregistration_sha256']==sha(HERE/'preregistration.json') and r['source_freeze_sha256']==sha(HERE/'source_freeze.json')
for rel,row in frozen['files'].items():assert sha(ROOT/rel)==row['sha256'],rel
source=ROOT/'model/takeover_20260926/p1_e2e_outer5/verify_score.py';spec=importlib.util.spec_from_file_location('p3_independent_meta',source);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
y=pd.read_csv(ROOT/'data/train.csv',usecols=['Will_Buy_EV']).Will_Buy_EV.eq('Yes').to_numpy(np.int8)
a='model/v80_strict_v61_outer104395303_40f/';b='model/v85_naji_v74_40f/';p1='model/takeover_20260926/p1_source_group_constraints_40f/'
v80=load(a+'oof_proba.npy');v80t=load(a+'test_proba.npy');v85=load(b+'oof_proba.npy');v85t=load(b+'test_proba.npy');group=load(p1+'oof_proba.npy');groupt=load(p1+'test_proba.npy');c=.5*(v85+group);ct=.5*(v85t+groupt)
np.testing.assert_allclose(c,load(p1+'c_oof.npy'),atol=1e-15,rtol=0);np.testing.assert_allclose(ct,load(p1+'c_test.npy'),atol=1e-15,rtol=0)
with np.load(ROOT/'model/diagnostics/ctboost_remote_probe_20260905/remote_output/oof.npz',allow_pickle=False) as z:cto=z['prediction'].astype(float)
ctt=pd.read_csv(ROOT/'model/diagnostics/ctboost_remote_probe_20260905/remote_output/submission.csv').Will_Buy_EV.to_numpy(float)
v90,v90t,w90=m.meta90(y,v80,c,v80t,ct);v100,v100t,w100=m.meta100(y,v90,cto,v90t,ctt)
for name,array in [('p3_v90_oof.npy',v90),('p3_v90_test.npy',v90t),('p3_v100_oof.npy',v100),('p3_v100_test.npy',v100t)]:np.testing.assert_allclose(array,np.load(HERE/name,allow_pickle=False),atol=1e-15,rtol=0)
old=load('model/v100_v90_ctboost_nested_cv_blend/oof_proba.npy');auc=float(roc_auc_score(y,v100));oldauc=float(roc_auc_score(y,old));assert abs(auc-r['candidate_auc'])<1e-12 and abs(oldauc-r['baseline_auc'])<1e-12
blocks=[]
for k,(_,u) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(np.zeros(len(y)),y)):
 delta=float(roc_auc_score(y[u],v100[u])-roc_auc_score(y[u],old[u]));assert abs(delta-r['folds'][k]['delta'])<1e-12;blocks.append(delta)
assert w90==r['v90_weights'] and abs(w100-r['v100_final_ct_weight'])<1e-15
assert auc>oldauc and all(x>0 for x in blocks)
out={'status':'PASS','candidate_auc':auc,'baseline_auc':oldauc,'delta':auc-oldauc,'positive_blocks':5,'v90_weights':w90,'v100_full_T_ct_weight':w100,'candidate_oof_sha256':sha(HERE/'p3_v100_oof.npy'),'candidate_test_sha256':sha(HERE/'p3_v100_test.npy'),'verifier_sha256':sha(Path(__file__)),'independent_meta_source_sha256':sha(source),'pre_registration_sha256':sha(HERE/'preregistration.json'),'development_result_sha256':sha(HERE/'development_result.json'),'limit':'Same 40-fold development base predictions; independent formula implementation but not independent data'}
p=HERE/'independent_verification.json'
if p.exists():raise RuntimeError('verification already exists')
p.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
