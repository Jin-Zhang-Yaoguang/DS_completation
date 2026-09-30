from pathlib import Path
import concurrent.futures,json,sys,time
import numpy as np
from sklearn.tree import DecisionTreeClassifier
B=Path(__file__).resolve().parent;D=B/'ddj';sys.path.insert(0,str(D));import tree_features as F
SOURCE=B.parent/'v126_majkel_neural_bc/data'
def load(split):
    return {name:np.load(SOURCE/split/f'{name}.npy',mmap_mode='r') for name in ['global','board','units','step','unit_tokens','unit_quantities','market_tokens','market_quantities','unit_mask']}
def export(tree):
    t=tree.tree_;classes=tree.classes_
    return {'feature':t.feature.astype(np.int16),'threshold':t.threshold.astype(np.float32),
            'left':t.children_left.astype(np.int32),'right':t.children_right.astype(np.int32),
            'label':classes[t.value[:,0,:].argmax(1)].astype(np.int32)}
def job(task):
    kind,i=task;start=time.perf_counter();tr=load('train');va=load('validation')
    cx={}
    for split,x in [('train',tr),('validation',va)]:
        c=np.load(D/f'cache_{split}.npy',mmap_mode='r')
        if kind=='unit':
            X=F.local(c,x['units'],i);y=x['unit_tokens'][:,i].astype(np.int32)*102+x['unit_quantities'][:,i];mask=x['unit_mask'][:,i]>0
        else:
            u=x['unit_tokens'].astype(np.int32)*102+x['unit_quantities'];m=x['market_tokens'].astype(np.int32)*102+x['market_quantities']
            prefix=np.zeros((len(c),20),np.float32)
            if i:prefix[:,:i*2]=np.stack([x['market_tokens'][:,:i],x['market_quantities'][:,:i]],axis=-1).reshape(len(c),-1)
            X=F.market(c,u,prefix);y=m[:,i];mask=np.ones(len(c),bool)
        cx[split]=(X[mask],np.asarray(y[mask]))
    X,y=cx['train'];V,z=cx['validation']
    if not len(X):
        X=np.zeros((1,cx['train'][0].shape[1]),np.float32);y=np.zeros(1,np.int32)
    tree=DecisionTreeClassifier(max_depth=26,min_samples_leaf=2,max_leaf_nodes=10000,random_state=1971+i)
    tree.fit(X,y)
    result={'head':f'{kind}_{i}','train_samples':len(y),'validation_samples':len(z),'nodes':tree.tree_.node_count,
            'train_accuracy':float(tree.score(X,y)),
            'validation_accuracy':float(tree.score(V,z)) if len(z) else None,'elapsed':time.perf_counter()-start}
    np.savez_compressed(D/f'{kind}_{i}.npz',**export(tree));print(json.dumps(result),flush=True);return result
def main():
    for split in ['train','validation']:
        x=load(split);out=D/f'cache_{split}.npy'
        if not out.exists():
            c=F.common(x['global'],x['board'],x['units'],x['step']);np.save(out,c);print('cached',split,c.shape,flush=True)
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as pool:results=list(pool.map(job,[('unit',i) for i in range(16)]+[('market',i) for i in range(10)]))
    (D/'training_report.json').write_text(json.dumps({'algorithm':'supervised decision trees, joint token/quantity labels, autoregressive market prefix',
        'selection':'fixed hyperparameters; validation only reported, test untouched','heads':results},indent=2)+'\n')
    for split in ['train','validation']:(D/f'cache_{split}.npy').unlink()
if __name__=='__main__':main()
