"""Synthetic contract tests; no real CT training or competition predictions."""
import ast
import hashlib
import json
import tempfile
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
import cache_runner as runner

def test():
    rng=np.random.default_rng(7423);n=500
    x=pd.DataFrame({'id':np.arange(n),'Annual_Income_USD':rng.integers(20000,160000,n),
        'Daily_Commute_km':rng.integers(0,120,n),'Environmental_Concern_Level':rng.integers(1,6,n),
        'Subsidy_Available':rng.choice(['Yes','No'],n),'Range_Anxiety_Level':rng.choice(['Low','High'],n)})
    y=rng.integers(0,2,n,dtype=np.int8)
    original=x.iloc[:200].copy();original['Will_Buy_EV']=y[:200]
    cfg={'model_seed':20260904,'inner_folds':5,'inner_seed':42,'require_gpu':False,
         '_config_sha256':'synthetic','source_sha256':{}}
    traces=[]
    class Fake:
        def fit(self,a,b):
            traces.append(hashlib.sha256(a.to_numpy().tobytes()+np.asarray(b).tobytes()).hexdigest())
            self.center=np.nanmean(a.to_numpy(),axis=0);self.scale=np.nanstd(a.to_numpy(),axis=0)+1
            self.model=LogisticRegression(max_iter=50).fit(np.nan_to_num((a.to_numpy()-self.center)/self.scale),b)
            return self
        def predict_proba(self,a):
            return self.model.predict_proba(np.nan_to_num((a.to_numpy()-self.center)/self.scale))
    factory=lambda _:Fake()
    with tempfile.TemporaryDirectory() as td:
        out=Path(td)/'one';train=np.arange(400);valid=np.arange(400,n)
        a=runner.fit_outer(x.iloc[train],y[train],x.iloc[valid],original,train,valid,cfg,out,factory)
        trace_a=list(traces);traces.clear()
        # Same fit-side data, arbitrary different U feature values: fitted states remain identical.
        changed=x.iloc[valid].copy();changed['Annual_Income_USD']+=9999
        runner.fit_outer(x.iloc[train],y[train],changed,original,train,valid,cfg,Path(td)/'two',factory)
        assert traces==trace_a
        traces.clear()
        runner.fit_outer(x.iloc[train],y[train],x.iloc[valid],original,train,valid,cfg,out,factory)
        assert not traces,'resume must not fit any model'
        cache=np.load(out/'cache.npz');assert (np.bincount(cache['atom_fold'])==80).all()
        assert np.array_equal(cache['train_idx'],train) and np.array_equal(cache['valid_id'],x.id.to_numpy()[valid])
        broken=out/'atom_01.npz'
        broken.write_bytes(broken.read_bytes()+b'corruption')
        try:runner.fit_outer(x.iloc[train],y[train],x.iloc[valid],original,train,valid,cfg,out,factory)
        except AssertionError:pass
        else:raise AssertionError('checkpoint corruption accepted')
        try:runner.predict_fit(x.iloc[train],y[train],[original],original,cfg,factory)
        except AssertionError:pass
        else:raise AssertionError('query containing label column accepted')
    fn=ast.parse((Path(__file__).parent/'cache_runner.py').read_text())
    fit=next(f for f in fn.body if isinstance(f,ast.FunctionDef) and f.name=='fit_outer')
    assert [a.arg for a in fit.args.args]==['x_train','y_train','x_valid','original','train_idx','valid_idx','cfg','out','factory']
    assert 'roc_auc_score' not in (Path(__file__).parent/'cache_runner.py').read_text()
    evidence={'status':'SYNTHETIC_CONTRACT_PASS','fit_calls':6,'query_feature_changes_leave_training_identical':True,
              'no_query_target_argument':True,'target_column_query_rejected':True,'resume_without_refit':True,
              'checkpoint_corruption_rejected':True,'fold_and_id_alignment':True,'scores_not_computed':True,
              'real_ct_training':False,'code_sha256':{name:runner.sha(Path(__file__).parent/name) for name in ['cache_runner.py','ct_features.py','self_test.py']}}
    runner.atomic_json(Path(__file__).parent/'self_test_results.json',evidence)
    print(json.dumps(evidence,indent=2))

if __name__=='__main__':test()
