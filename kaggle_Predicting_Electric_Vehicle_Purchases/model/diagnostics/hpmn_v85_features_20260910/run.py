"""Frozen HPMN predictor diagnostic using the existing strict V85 representation."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:
    os.environ[name]='4'
from pathlib import Path
import fcntl,gc,hashlib,importlib.util,json,random,resource,signal,sys,time,traceback,warnings
import numpy as np
import pandas as pd
import lightgbm as lgb
import torch
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

P=Path(__file__).resolve().parent
R=P.parents[2]
C=json.loads((P/'preregistration.json').read_text())
REF=R/'model/diagnostics/income_context_lowrank_20260906_retry1'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def write(path,value):
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False))
    temp.replace(path)

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    obj=importlib.util.module_from_spec(spec)
    sys.modules[name]=obj
    spec.loader.exec_module(obj)
    return obj

def predict(model,x,device):
    model.eval()
    out=[]
    with torch.no_grad():
        for i in range(0,len(x),8192):
            out.append(model(torch.from_numpy(x[i:i+8192]).to(device)).sigmoid().cpu().numpy())
    return np.concatenate(out).astype('float64')

def main():
    lock=(P/'run.lock').open('w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert not (P/'result.json').exists(),'Closed experiment must not be rerun'
    previous=json.loads((R/'model/diagnostics/income_support_geometry_20260910/verification.json').read_text())
    assert previous['status']=='PASS' and not previous['gate_passed']
    for path,digest in C['source_hashes'].items():
        assert sha(R/path)==digest,path
    contract={'runner':sha(__file__),'preregistration':sha(P/'preregistration.json'),'sources':C['source_hashes']}
    if (P/'contract.json').exists():
        assert contract==json.loads((P/'contract.json').read_text())
    else:
        write(P/'contract.json',contract)
    if (P/'RUN_STARTED.json').exists():
        started=json.loads((P/'RUN_STARTED.json').read_text())['started']
    else:
        started=time.time()
        write(P/'RUN_STARTED.json',{'pid':os.getpid(),'started':started})
    def guard():
        assert time.time()-started<C['budget']['wall_seconds'],'wall budget'
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<C['budget']['memory_gib']*1024**3,'memory budget'
    signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError('wall budget')))
    signal.alarm(max(1,int(C['budget']['wall_seconds']-(time.time()-started))))
    torch.set_num_threads(4)
    assert torch.backends.mps.is_available()
    device=torch.device('mps')
    m=module('hpmn_frozen_public',R/'model/diagnostics/hpmn_source_audit_20260910/public_components.py')
    m.DEVICE=device
    for key,value in C['model'].items():
        if key!='all_other_architecture_and_regularization':
            assert getattr(m,key)==value,(key,getattr(m,key),value)
    backend=module('hpmn_v85_backend',R/'model/validation/e2e_v100_20260905/feature_backends.py').load_backend('v85')
    rank=module('hpmn_rank',R/'model/v100_v90_ctboost_nested_cv_blend/v100_v90_ctboost_nested_cv_blend.py')
    sys.path.insert(0,str(R/'model/research_runtime'))
    from paired_auc import paired_auc
    raw=pd.read_csv(R/'data/train.csv',usecols=['id','Will_Buy_EV'])
    ids=raw.id.to_numpy();y=raw.Will_Buy_EV.eq('Yes').to_numpy('int8')
    ref=np.load(REF/'diagnostic_oof.npz')
    np.testing.assert_array_equal(ref['ids'],ids)
    baseline=ref['pred'][:,0].copy()
    pred=np.full(len(y),np.nan);folds=np.zeros(len(y),int);fold_results=[]
    splits=list(StratifiedKFold(5,shuffle=True,random_state=42).split(ids,y))
    for fold,(fit,valid) in enumerate(splits,1):
        guard()
        np.testing.assert_array_equal(ref['fold'][valid],fold)
        d=P/f'fold_{fold}';d.mkdir(exist_ok=True)
        if (d/'result.json').exists():
            record=json.loads((d/'result.json').read_text())
            assert sha(d/'prediction.npy')==record['prediction_sha']
            assert sha(d/'model.pt')==record['model_sha']
            np.testing.assert_array_equal(np.load(d/'valid_rows.npy'),valid)
            pred[valid]=np.load(d/'prediction.npy');folds[valid]=fold;fold_results.append(record)
            continue
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            xf,xv,names=backend.encode(fit,y[fit],valid,42+fold)
        assert xf.shape[1]==148 and xv.dtype==np.float64
        cache=np.load(REF/f'fold_{fold}_query.npz')
        np.testing.assert_array_equal(cache['valid'],valid)
        np.testing.assert_array_equal(cache['x'],xv)
        booster=lgb.Booster(model_file=str(REF/f'fold_{fold}_arm_0.txt'))
        base_replay=booster.predict(xv,num_threads=4)
        np.testing.assert_allclose(base_replay,baseline[valid],rtol=0,atol=1e-12)
        del booster,cache
        xf=xf.astype('float32');xv=xv.astype('float32')
        mean=xf.mean(axis=0,dtype=np.float64).astype('float32')
        std=xf.std(axis=0,dtype=np.float64).astype('float32')
        std=np.where(np.isfinite(std)&(std>1e-7),std,1).astype('float32')
        assert np.isfinite(mean).all()
        xf=np.clip((xf-mean)/std,-8,8).astype('float32')
        xv=np.clip((xv-mean)/std,-8,8).astype('float32')
        assert np.isfinite(xf).all() and np.isfinite(xv).all()
        np.savez(d/'preprocess.npz',mean=mean,std=std)
        np.save(d/'valid_features.npy',xv)
        np.save(d/'valid_rows.npy',valid);np.save(d/'fit_rows.npy',fit)
        write(d/'input.json',{'feature_names':names,'fit_features_sha':hashlib.sha256(xf.tobytes()).hexdigest(),
             'fit_labels_sha':hashlib.sha256(y[fit].tobytes()).hexdigest(),
             'files':{name:sha(d/name) for name in ['preprocess.npz','valid_features.npy','valid_rows.npy','fit_rows.npy']}})
        seed=42+fold
        random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
        model=m.HierarchicalMatcher(148).to(device)
        model.initialize_centers(xf,seed=seed+8100)
        loader=torch.utils.data.DataLoader(m.BinaryDataset(xf,y[fit]),batch_size=m.BATCH_SIZE,shuffle=True,num_workers=0,pin_memory=False,drop_last=False)
        optimizer=torch.optim.AdamW(model.parameters(),lr=m.LR,weight_decay=m.WEIGHT_DECAY)
        scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,T_max=m.MAX_EPOCHS,eta_min=m.LR*.12)
        best_auc=-np.inf;best_epoch=0;history=[];fold_start=time.time()
        for epoch in range(1,m.MAX_EPOCHS+1):
            guard();temperature=m.MASK_TEMP_START*(m.MASK_TEMP_END/m.MASK_TEMP_START)**((epoch-1)/(m.MAX_EPOCHS-1))
            model.set_mask_temperature(temperature);model.train()
            loss_sum=0.;n_seen=0
            for batch,(xb,yb) in enumerate(loader):
                if batch%32==0:guard()
                xb=xb.to(device);yb=yb.to(device)
                optimizer.zero_grad(set_to_none=True)
                data_loss=torch.nn.functional.binary_cross_entropy_with_logits(model(xb),yb)
                loss=data_loss+model.regularization()
                assert bool(torch.isfinite(loss))
                loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),m.GRAD_CLIP);optimizer.step()
                loss_sum+=float(data_loss.detach().cpu())*len(xb);n_seen+=len(xb)
            scheduler.step()
            q=predict(model,xv,device)
            score=float(roc_auc_score(y[valid],q))
            if score>best_auc:
                best_auc=score;best_epoch=epoch
                torch.save({'state':{k:v.detach().cpu() for k,v in model.state_dict().items()},'temperature':temperature,'epoch':epoch},d/'model.pt')
            entry={'epoch':epoch,'auc':score,'loss':loss_sum/n_seen,'seconds':time.time()-fold_start,'best_epoch':best_epoch}
            history.append(entry);write(d/'history.json',history)
            print('EPOCH',fold,json.dumps(entry),flush=True)
            if epoch-best_epoch>=m.PATIENCE:break
        saved=torch.load(d/'model.pt',map_location='cpu',weights_only=True)
        model.load_state_dict(saved['state']);model.set_mask_temperature(saved['temperature'])
        q=predict(model,xv,device)
        assert abs(roc_auc_score(y[valid],q)-best_auc)<1e-12
        other=m.HierarchicalMatcher(148).to(device)
        other.load_state_dict(saved['state']);other.set_mask_temperature(saved['temperature'])
        replay=predict(other,xv,device)
        np.testing.assert_array_equal(q,replay)
        np.save(d/'prediction.npy',q)
        record={'fold':fold,'auc':best_auc,'best_epoch':best_epoch,'epochs':len(history),
                'baseline_auc':float(roc_auc_score(y[valid],baseline[valid])),
                'model_sha':sha(d/'model.pt'),'prediction_sha':sha(d/'prediction.npy'),
                'baseline_replay_max_abs':float(abs(base_replay-baseline[valid]).max()),
                'candidate_reload_max_abs':float(abs(q-replay).max()),'seconds':time.time()-fold_start}
        write(d/'result.json',record)
        pred[valid]=q;folds[valid]=fold;fold_results.append(record)
        np.savez_compressed(P/'checkpoint_oof.npz',ids=ids,fold=folds,pred=pred)
        del model,other,optimizer,scheduler,loader,xf,xv,saved
        gc.collect();torch.mps.empty_cache()
    transformed_base=np.full(len(y),np.nan)
    blend=np.full(len(y),np.nan);equal=np.full(len(y),np.nan)
    for fit,valid in splits:
        b=rank.transform_mid_ecdf(rank.fit_mid_ecdf(baseline[fit]),baseline[valid])
        h=rank.transform_mid_ecdf(rank.fit_mid_ecdf(pred[fit]),pred[valid])
        transformed_base[valid]=b;blend[valid]=.9*b+.1*h;equal[valid]=.5*b+.5*h
    standalone=paired_auc(y,baseline,pred,folds)
    mixed=paired_auc(y,transformed_base,blend,folds)
    control=paired_auc(y,transformed_base,equal,folds)
    followup=standalone['candidate_auc']>=.9452 and mixed['delta']>0 and mixed['positive_folds']==5
    result={'status':'COMPLETE_DIAGNOSTIC','standalone':standalone,'fixed_10pct':mixed,'equal_weight_control':control,
            'followup_gate_passed':followup,'research_promotion_gate_passed':mixed['delta']>=.0001 and mixed['positive_folds']==5,
            'scope':'Outer-validation epoch selection and last-layer fit-only ranks: development evidence, not end-to-end unbiased.',
            'test_generated':False,'submission_allowed':False,'counts_toward_cycle':False,
            'fold_results':fold_results,'seconds':time.time()-started,'peak_memory_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    np.savez_compressed(P/'diagnostic_oof.npz',ids=ids,fold=folds,pred=pred,baseline=baseline,transformed_baseline=transformed_base,blend=blend,equal=equal)
    write(P/'result.json',result);signal.alarm(0)
    print('RESULT',json.dumps(result),flush=True)

if __name__=='__main__':
    try:
        main()
    except BaseException:
        write(P/'failure.json',{'traceback':traceback.format_exc(),'time':time.time()})
        raise
