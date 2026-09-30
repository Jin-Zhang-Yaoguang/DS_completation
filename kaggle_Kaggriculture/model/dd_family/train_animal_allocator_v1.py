"""Episode-held-out supervised animal allocation from public teacher observations."""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import balanced_accuracy_score,accuracy_score
B=Path(__file__).resolve().parent;D=B/'ddw';sys.path.insert(0,str(D));import action_space as a
IDX=[0,4,16,*range(33,60)]
X=[];Y=[];W=[];V=[];sources=[]
for source in ['ddm','dde','ddo']:
 d=B/source/'data';g=np.load(d/'global.npy',mmap_mode='r');board=np.load(d/'board.npy',mmap_mode='r');m=np.load(d/'market_tokens.npy',mmap_mode='r');q=np.load(d/'market_quantities.npy',mmap_mode='r');count=0
 for t,k,slot in zip(*np.where(np.isin(m,[a.MARKET_INDEX['BUY_ANIMAL:'+item] for item in a.ANIMALS]))):
  xx=np.concatenate([g[t,k,IDX].astype(np.float32),board[t,k].reshape(100,21)[:,10:13].sum(0).astype(np.float32)/16])
  X.append(xx);Y.append(int(m[t,k,slot]==a.MARKET_INDEX['BUY_ANIMAL:SHEEP']));W.append(float(q[t,k,slot]));V.append(int(hashlib.sha256(f'{source}:{k}'.encode()).hexdigest(),16)%5==0);count+=1
 sources.append({'version':source,'episodes':g.shape[1],'purchase_orders':count})
X=np.asarray(X,np.float32);Y=np.asarray(Y);W=np.asarray(W);V=np.asarray(V);rows=[];best=None
for depth in [3,4,5]:
 for leaf in [20,40]:
  model=DecisionTreeClassifier(max_depth=depth,min_samples_leaf=leaf,class_weight='balanced',random_state=723)
  model.fit(X[~V],Y[~V],sample_weight=W[~V]);pred=model.predict(X[V]);score=balanced_accuracy_score(Y[V],pred,sample_weight=W[V]);rows.append({'depth':depth,'min_leaf':leaf,'balanced_accuracy':score,'accuracy':accuracy_score(Y[V],pred,sample_weight=W[V])})
  if best is None or score>best[0]:best=(score,model,rows[-1])
model=best[1];tree=model.tree_;v=tree.value[:,0,:];prob=v[:,1]/v.sum(1)
export={'feature_global_indices':IDX,'extra_features':['own_goose_count/16','own_cow_count/16','own_sheep_count/16'],'left':tree.children_left.tolist(),'right':tree.children_right.tolist(),'feature':tree.feature.tolist(),'threshold':tree.threshold.tolist(),'prob_sheep':prob.tolist(),'decision_threshold':0.5}
pred=[]
for x in X[V]:
 node=0
 while export['left'][node]>=0:node=export['left'][node] if x[export['feature'][node]]<=export['threshold'][node] else export['right'][node]
 pred.append(export['prob_sheep'][node])
assert np.allclose(pred,model.predict_proba(X[V])[:,1],atol=1e-12)
(D/'animal_model.json').write_text(json.dumps(export,indent=2)+'\n')
report={'sources':sources,'samples':len(Y),'train_orders':int((~V).sum()),'validation_orders':int(V.sum()),'selection':best[2],'candidates':rows,'export_probability_parity':True,'scope':'supervised binary allocation; no online RL; no y68 labels; no trajectory ID or future market input'}
(D/'animal_training.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
