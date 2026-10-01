#!/usr/bin/env python3
"""CT outer caches. fit_outer accepts y_train only; never scores holdouts."""
from __future__ import annotations
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[key]='4'
import argparse
import gc
import hashlib
import json
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from ct_features import fit_features, transform_features, binary_target

ROOT=Path(__file__).resolve().parent

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def array_sha(a):
    return hashlib.sha256(np.asarray(a,dtype='<i8').tobytes()).hexdigest()

def atomic_json(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w') as f: json.dump(obj,f,indent=2,allow_nan=False);f.write('\n')
    os.replace(tmp,path)

def atomic_npz(path,**items):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    with tmp.open('wb') as f: np.savez_compressed(f,**items)
    os.replace(tmp,path)

def probability(x,n):
    x=np.asarray(x,dtype=np.float64)
    assert x.shape==(n,) and np.isfinite(x).all() and x.min()>=0 and x.max()<=1
    return x

def gpu_model(cfg):
    import ctboost
    return ctboost.CTBoostClassifier(iterations=cfg['iterations'],task_type='GPU',devices='0',random_seed=cfg['model_seed'],eval_metric='AUC',verbose=False,**cfg['params'])

def predict_fit(x,y,queries,original,cfg,factory):
    assert 'Will_Buy_EV' not in x
    assert all('Will_Buy_EV' not in q for q in queries)
    features,state=fit_features(x,y,original,seed=cfg['model_seed'])
    model=factory(cfg).fit(features,y)
    outputs=[probability(model.predict_proba(transform_features(q,state))[:,1],len(q)) for q in queries]
    if cfg.get('require_gpu',True):
        assert model.get_booster()._handle.export_state()['task_type']=='GPU'
    del features,state,model
    gc.collect()
    return outputs

def fit_outer(x_train,y_train,x_valid,original,train_idx,valid_idx,cfg,out,factory=gpu_model):
    # U labels are deliberately absent from this function and all callees.
    assert len(x_train)==len(y_train)==len(train_idx) and len(x_valid)==len(valid_idx)
    assert not np.intersect1d(train_idx,valid_idx).size
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    identity={'train_idx_sha256':array_sha(train_idx),'valid_idx_sha256':array_sha(valid_idx),
              'train_id_sha256':array_sha(x_train.id),'valid_id_sha256':array_sha(x_valid.id),
              'config_sha256':cfg['_config_sha256']}
    # Historical CT OOF was stored as float32; retain its exact meta-input precision.
    oof=np.full(len(x_train),np.nan,dtype=np.float32);fold_ids=np.full(len(x_train),-1,dtype=np.int8)
    mean=np.zeros(len(x_valid),dtype=np.float64);rows=[]
    folds=StratifiedKFold(cfg['inner_folds'],shuffle=True,random_state=cfg['inner_seed'])
    for atom,(fit,hold) in enumerate(folds.split(np.zeros(len(y_train)),y_train),1):
        cp=out/f'atom_{atom:02d}.npz';manifest=out/f'atom_{atom:02d}.json'
        if cp.exists() or manifest.exists():
            assert cp.exists() and manifest.exists(),'incomplete checkpoint pair'
            record=json.loads(manifest.read_text());assert record['identity']==identity and record['sha256']==sha(cp)
            with np.load(cp,allow_pickle=False) as z:
                assert np.array_equal(z['fit_idx'],train_idx[fit]) and np.array_equal(z['hold_idx'],train_idx[hold])
                assert np.array_equal(z['valid_idx'],valid_idx)
                a=probability(z['oof_proba'],len(hold));b=probability(z['valid_proba'],len(x_valid))
        else:
            tic=time.monotonic()
            a,b=predict_fit(x_train.iloc[fit],y_train[fit],[x_train.iloc[hold],x_valid],original,cfg,factory)
            atomic_npz(cp,fit_idx=train_idx[fit],hold_idx=train_idx[hold],valid_idx=valid_idx,oof_proba=a,valid_proba=b)
            record={'atom':atom,'seconds':time.monotonic()-tic,'identity':identity,'sha256':sha(cp)}
            atomic_json(manifest,record)
        oof[hold]=a;fold_ids[hold]=atom-1;mean+=b/cfg['inner_folds'];rows.append(record)
        print(json.dumps({'status':'CT_ATOM_COMPLETE','outer':out.name,**record}),flush=True)
    cp=out/'fullfit.npz';manifest=out/'fullfit.json'
    if cp.exists() or manifest.exists():
        assert cp.exists() and manifest.exists(),'incomplete fullfit checkpoint'
        record=json.loads(manifest.read_text());assert record['identity']==identity and record['sha256']==sha(cp)
        with np.load(cp,allow_pickle=False) as z:
            assert np.array_equal(z['valid_idx'],valid_idx)
            full=probability(z['valid_proba'],len(x_valid))
    else:
        tic=time.monotonic()
        full,=predict_fit(x_train,y_train,[x_valid],original,cfg,factory)
        atomic_npz(cp,valid_idx=valid_idx,valid_proba=full)
        record={'seconds':time.monotonic()-tic,'identity':identity,'sha256':sha(cp)}
        atomic_json(manifest,record)
    probability(oof,len(x_train));probability(mean,len(x_valid));assert (fold_ids>=0).all()
    cache=out/'cache.npz'
    atomic_npz(cache,train_idx=train_idx,valid_idx=valid_idx,train_id=x_train.id.to_numpy(),valid_id=x_valid.id.to_numpy(),
               oof_proba=oof,valid_proba_fullfit=full,valid_proba_foldmean=mean,atom_fold=fold_ids)
    summary={'status':'CT_CACHE_COMPLETE_UNSCORED','identity':identity,'cache_sha256':sha(cache),'atoms':rows,
             'fullfit':record,'atom_fold_sha256':array_sha(fold_ids),'validation_labels_used':False,
             'allowed_for_submission':False,'source_sha256':cfg['source_sha256']}
    atomic_json(out/'cache_manifest.json',summary)
    return summary

def run(input_root,output):
    import ctboost
    import sklearn
    cfg_path=ROOT/'frozen_config.json';cfg=json.loads(cfg_path.read_text())
    cfg['_config_sha256']=sha(cfg_path)
    for name,digest in cfg['code_sha256'].items(): assert sha(ROOT/name)==digest,('code drift',name)
    assert ctboost.__version__=='0.1.58' and ctboost.build_info()['cuda_enabled']
    expected=cfg['remote_versions'];actual={'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__}
    assert actual==expected,('remote runtime drift',actual,expected)
    base=Path(input_root)
    trains=list(base.glob('**/playground-series-s6e9/train.csv'))
    originals=list(base.glob('**/EV_Adoption_and_Range_Anxiety_Dataset.csv'))
    assert len(trains)==1 and len(originals)==1,(trains,originals)
    assert sha(trains[0])==cfg['source_sha256']['train.csv']
    assert sha(originals[0])==cfg['source_sha256']['original.csv']
    frame=pd.read_csv(trains[0]);y=binary_target(frame.Will_Buy_EV);x=frame.drop(columns='Will_Buy_EV')
    original=pd.read_csv(originals[0]);del frame
    outer_results=[]
    for outer,(train,valid) in enumerate(StratifiedKFold(cfg['outer_folds'],shuffle=True,random_state=cfg['outer_seed']).split(np.zeros(len(y)),y),1):
        outer_results.append(fit_outer(x.iloc[train],y[train],x.iloc[valid],original,train,valid,cfg,Path(output)/f'outer_{outer:02d}'))
    atomic_json(Path(output)/'GPU_COMPLETE.json',{'status':'CT_CACHE_COMPLETE_UNSCORED','config_sha256':cfg['_config_sha256'],
        'outer_results':outer_results,'versions':actual,'complete_v100_score':None,'submission_created':False})

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--input-root',default='/kaggle/input');ap.add_argument('--output',default='/kaggle/working/ct_cache')
    args=ap.parse_args()
    run(args.input_root,args.output)
