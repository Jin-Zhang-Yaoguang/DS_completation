"""Distill conditional exogenous flow distributions from public replays."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import mean_squared_error
B=Path(__file__).resolve().parent;D=B/'ddau';sys.path.insert(0,str(D));import sale_policy as policy

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    manifest=json.loads((B/'sale_flow_labels/manifest.json').read_text());parts={(i,h):[] for i in range(3) for h in range(3)}
    for row in manifest['rows']:
        s=row['source'];k=row['prototype'];fp=B/'executed_sale_labels'/s/f'{k:03}.npz';tp=B/'sale_flow_labels'/s/f'{k:03}.npz'
        assert sha(fp)==row['feature_data_sha256'] and sha(tp)==row['target_sha256'];f=np.load(fp);target=np.load(tp)
        v=int(hashlib.sha256(f"sale-timing:{row['seed']}".encode()).hexdigest(),16)%5==0
        for i in range(3):
            for h in range(3):
                mask=target['valid'][:,i,h];n=int(mask.sum());parts[i,h].append((f['features'][mask,i],target['target'][mask,i,h],f['available'][mask,i],np.full(n,v,dtype=bool)))
    models={};report={}
    for (i,hi),rows in parts.items():
        item=policy.ITEMS[i];h=manifest['horizons'][hi];X,Y,W,V=[np.concatenate([r[j] for r in rows]) for j in range(4)];trials=[];best=None
        for depth in [4,6,8]:
            for leaf in [50,200]:
                model=DecisionTreeRegressor(max_depth=depth,min_samples_leaf=leaf,random_state=941)
                model.fit(X[~V],Y[~V],sample_weight=W[~V]);mse=mean_squared_error(Y[V],model.predict(X[V]),sample_weight=W[V]);trial={'depth':depth,'min_leaf':leaf,'weighted_mse':mse};trials.append(trial)
                if best is None or mse<best[0]:best=(mse,model,trial)
        model=best[1];tree=model.tree_;export={'left':tree.children_left.tolist(),'right':tree.children_right.tolist(),'feature':tree.feature.tolist(),'threshold':tree.threshold.tolist(),'value':tree.value[:,0,0].tolist(),'flow_quantiles':[None]*tree.node_count}
        leaves=model.apply(X[~V]);yt=Y[~V];wt=W[~V]
        for leaf in np.unique(leaves):
            mask=leaves==leaf;order=np.argsort(yt[mask]);values=yt[mask][order];weights=wt[mask][order];cdf=(np.cumsum(weights)-0.5*weights)/weights.sum()
            export['flow_quantiles'][int(leaf)]=np.interp([.1,.3,.5,.7,.9],cdf,values).tolist()
        assert np.allclose([policy.predict(export,x) for x in X[V]],model.predict(X[V]),atol=1e-12)
        models.setdefault(item,{})[str(h)]=export
        baseline=mean_squared_error(Y[V],np.full(int(V.sum()),np.average(Y[~V],weights=W[~V])),sample_weight=W[V])
        record={'samples':len(Y),'train':int((~V).sum()),'validation':int(V.sum()),'selection':best[2],'trials':trials,'constant_baseline_mse':baseline,'export_parity':True};report.setdefault(item,{})[str(h)]=record
        print(item,h,best[2],'constant',baseline,flush=True)
    result={'features':policy.FEATURES,'horizons':manifest['horizons'],'risk_penalty':0.25,'min_gain_fraction':0.002,'items':models}
    (D/'flow_model.json').write_text(json.dumps(result,indent=2)+'\n')
    (D/'flow_training.json').write_text(json.dumps({'source_manifest_sha256':sha(B/'sale_flow_labels/manifest.json'),'training_script_sha256':sha(Path(__file__)),'split':'Same source-seed grouping as ddat, internal validation only.','label':'Future inventory minus current inventory minus own actual sales; ambiguous $1 clipping windows excluded. Features contain no future observations.','limitations':'Observed opponent flow can react to teacher market actions; removing self inventory contribution is not a full counterfactual simulation. Conditional leaf quantiles are forecasts, not guaranteed bounds.','items':report},indent=2)+'\n')
if __name__=='__main__':main()
