"""Fit separate sale-event and positive sale-fraction trees from actual fills."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from sklearn.tree import DecisionTreeClassifier,DecisionTreeRegressor
from sklearn.metrics import log_loss,mean_squared_error
B=Path(__file__).resolve().parent;D=B/'ddat';sys.path.insert(0,str(D));import sale_policy as policy

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def export(model,classifier=False):
    t=model.tree_;values=t.value[:,0,:]
    v=values[:,1]/values.sum(1) if classifier else values[:,0]
    return {'left':t.children_left.tolist(),'right':t.children_right.tolist(),'feature':t.feature.tolist(),'threshold':t.threshold.tolist(),'value':v.tolist()}

def main():
    manifest=json.loads((B/'executed_sale_labels/manifest.json').read_text());assert manifest['episodes']==415
    samples={item:[] for item in policy.ITEMS}
    for row in manifest['rows']:
        p=B/'executed_sale_labels'/row['source']/f"{row['prototype']:03}.npz";assert sha(p)==row['label_sha256'];z=np.load(p)
        valid=int(hashlib.sha256(f"sale-timing:{row['seed']}".encode()).hexdigest(),16)%5==0
        for j,item in enumerate(policy.ITEMS):
            idx=z['eligible'][:,j];n=z['available'][idx,j];y=z['filled'][idx,j]
            samples[item].append((z['features'][idx,j],y/n,n,np.full(len(n),valid,dtype=bool)))
    models={};report={}
    for item,parts in samples.items():
        X,Y,W,V=[np.concatenate([p[j] for p in parts]) for j in range(4)];Z=Y>0;trials=[];best=None
        for depth in [5,7,9]:
            for leaf in [25,100,250]:
                clf=DecisionTreeClassifier(max_depth=depth,min_samples_leaf=leaf,random_state=731)
                clf.fit(X[~V],Z[~V],sample_weight=W[~V]);pred=np.clip(clf.predict_proba(X[V])[:,1],1e-5,1-1e-5);loss=log_loss(Z[V],pred,sample_weight=W[V])
                row={'depth':depth,'min_leaf':leaf,'weighted_log_loss':loss};trials.append(row)
                if best is None or loss<best[0]:best=(loss,clf,row)
        chosen=best;best=None;fractions=[]
        for depth in [3,5,7]:
            for leaf in [10,40]:
                reg=DecisionTreeRegressor(max_depth=depth,min_samples_leaf=leaf,random_state=731)
                reg.fit(X[(~V)&Z],Y[(~V)&Z],sample_weight=W[(~V)&Z]);mask=V&Z;loss=mean_squared_error(Y[mask],reg.predict(X[mask]),sample_weight=W[mask]);row={'depth':depth,'min_leaf':leaf,'weighted_mse':loss};fractions.append(row)
                if best is None or loss<best[0]:best=(loss,reg,row)
        decision=export(chosen[1],True);fraction=export(best[1]);models[item]={'decision':decision,'fraction':fraction,'threshold':0.5}
        assert np.allclose([policy.predict(decision,x) for x in X[V]],chosen[1].predict_proba(X[V])[:,1],atol=1e-12)
        assert np.allclose([policy.predict(fraction,x) for x in X[V]],best[1].predict(X[V]),atol=1e-12)
        pred=chosen[1].predict_proba(X[V])[:,1]>=0.5
        report[item]={'samples':len(Y),'train':int((~V).sum()),'validation':int(V.sum()),'sale_samples':int(Z.sum()),'decision_selection':chosen[2],'decision_trials':trials,'fraction_selection':best[2],'fraction_trials':fractions,'validation_precision':float(np.sum(pred&Z[V])/max(1,pred.sum())),'validation_recall':float(np.sum(pred&Z[V])/Z[V].sum()),'export_parity':True}
        print(item,report[item]['decision_selection'],report[item]['validation_precision'],report[item]['validation_recall'],flush=True)
    (D/'sale_model.json').write_text(json.dumps({'features':policy.FEATURES,'items':models},indent=2)+'\n')
    (D/'sale_training.json').write_text(json.dumps({'source_manifest_sha256':sha(B/'executed_sale_labels/manifest.json'),'training_script_sha256':sha(Path(__file__)),'feature_sha256':sha(D/'sale_policy.py'),'split':'Source seed grouped across all three teacher pools; internal validation selects depth/leaf size. No independent test claim.','labels':'Actual sale event and sold/available fraction; no sell requests used as filled labels; only decision-time stock unchanged by current unit actions.','scope':'Offline supervised behavior cloning. No y68 labels, future observations or opponent private state.','items':report},indent=2)+'\n')
if __name__=='__main__':main()
