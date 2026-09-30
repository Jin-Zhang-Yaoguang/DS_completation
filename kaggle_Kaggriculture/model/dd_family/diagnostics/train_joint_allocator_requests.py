"""One supervised target per teacher purchase turn, split by source seed."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from sklearn.tree import DecisionTreeRegressor
from sklearn.metrics import mean_absolute_error,mean_squared_error
B=Path(__file__).resolve().parent;D=B/'ddar';sys.path.insert(0,str(D))
import action_space as a,joint_allocator as joint

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    X=[];Y=[];W=[];V=[];S=[];sources=[]
    for source in ['ddm','dde','ddo']:
        manifest=json.loads((B/source/'training_manifest.json').read_text())
        m=np.load(B/source/'data/market_tokens.npy',mmap_mode='r');q=np.load(B/source/'data/market_quantities.npy',mmap_mode='r')
        animal=np.isin(m,[a.MARKET_INDEX['BUY_ANIMAL:'+it] for it in a.ANIMALS]);count=0;pending_turns=0
        for k,row in enumerate(manifest['episodes']):
            raw=Path(row['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256'];rep=json.loads(raw);seat=row['seat']
            validation=int(hashlib.sha256(f"animal-allocation:{row['seed']}".encode()).hexdigest(),16)%5==0
            for t in np.flatnonzero(animal[:,k].any(1)):
                quantities=q[t,k];total=int(quantities[animal[t,k]].sum());assert total>0
                sheep=int(quantities[m[t,k]==a.MARKET_INDEX['BUY_ANIMAL:SHEEP']].sum())
                obs=dict(rep['steps'][int(t)][0]['observation']);obs.update(rep['steps'][int(t)][seat]['observation']);obs['step']=int(t);obs['player']=seat
                x=joint.features(obs,total);pending_turns+=int(np.any(x[-7:-1]>0))
                X.append(x);Y.append(sheep/total);W.append(total);V.append(validation);S.append(source);count+=1
            if (k+1)%40==0:print(source,k+1,flush=True)
        sources.append({'version':source,'episodes':len(manifest['episodes']),'purchase_turns':count,'with_unplaced_animals':pending_turns,'manifest_sha256':sha(B/source/'training_manifest.json')})
    X=np.asarray(X,np.float32);Y=np.asarray(Y);W=np.asarray(W);V=np.asarray(V);S=np.asarray(S)
    rows=[];best=None
    for depth in [3,4,5,6]:
        for leaf in [20,40,80]:
            model=DecisionTreeRegressor(max_depth=depth,min_samples_leaf=leaf,random_state=723)
            model.fit(X[~V],Y[~V],sample_weight=W[~V]);pred=model.predict(X[V]);score=mean_squared_error(Y[V],pred,sample_weight=W[V])
            row={'depth':depth,'min_leaf':leaf,'weighted_mse':score,'weighted_mae':mean_absolute_error(Y[V],pred,sample_weight=W[V])};rows.append(row)
            if best is None or score<best[0]:best=(score,model,row)
    model=best[1];tree=model.tree_
    export={'feature_global_indices':joint.IDX,'extra_features':['placed_goose/16','placed_cow/16','placed_sheep/16','shed_goose/16','shed_cow/16','shed_sheep/16','bag_goose/16','bag_cow/16','bag_sheep/16','planned_total/16'],'left':tree.children_left.tolist(),'right':tree.children_right.tolist(),'feature':tree.feature.tolist(),'threshold':tree.threshold.tolist(),'sheep_share':tree.value[:,0,0].tolist()}
    assert np.allclose([joint.predict(export,x) for x in X[V]],model.predict(X[V]),atol=1e-12)
    per_source={}
    for source in S.tolist():
        if source in per_source:continue
        mask=V&(S==source);per_source[source]={'validation_turns':int(mask.sum()),'weighted_mse':mean_squared_error(Y[mask],model.predict(X[mask]),sample_weight=W[mask])}
    mean=float(np.average(Y[~V],weights=W[~V]));baseline=mean_squared_error(Y[V],np.full(int(V.sum()),mean),sample_weight=W[V])
    report={'sources':sources,'samples':len(Y),'train_turns':int((~V).sum()),'validation_turns':int(V.sum()),'selection':best[2],'candidates':rows,'constant_baseline_mse':baseline,'per_source':per_source,'export_parity':True,'training_script_sha256':sha(Path(__file__)),'features_sha256':sha(D/'joint_allocator.py'),'split':'Source-seed hash shared by all teachers; validation selects hyperparameters, not an untouched test.','label':'Requested sheep count divided by all requested livestock within the same turn. Intent labels, not successful-fill labels.','scope':'Offline supervised regression; no y68 labels, seed features, future state or teacher identity.'}
    (D/'joint_animal_model.json').write_text(json.dumps(export,indent=2)+'\n');(D/'joint_animal_training.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
if __name__=='__main__':main()
