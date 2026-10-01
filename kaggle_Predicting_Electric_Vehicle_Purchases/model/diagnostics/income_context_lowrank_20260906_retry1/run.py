"""收入与人群低秩条件估计：固定三臂、嵌套五折诊断。"""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'): os.environ[k]='8'
import argparse,fcntl,gc,hashlib,importlib.util,json,resource,signal,time,traceback,warnings
from pathlib import Path
import numpy as np
import pandas as pd
import subprocess,sys
import lightgbm as lgb
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
CFG=json.loads((HERE/'preregistration.json').read_text())

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(name,obj):
    p=HERE/name;t=p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n');t.replace(p)
def save_npz(path,**arrays):
    t=path.with_suffix('.tmp')
    with t.open('wb') as f: np.savez_compressed(f,**arrays)
    t.replace(path)
def module(path,name):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m


def pair_parts(y,p,g):
    den=int((y==1).sum())*int((y==0).sum());ans={}
    for name,a,b in [('within_primary',g,g),('pos_primary_neg_other',g,~g),('pos_other_neg_primary',~g,g),('within_other',~g,~g)]:
        pos=p[(y==1)&a];neg=np.sort(p[(y==0)&b]);errors=(len(neg)-.5*(np.searchsorted(neg,pos,'left')+np.searchsorted(neg,pos,'right'))).sum()
        ans[name]=float(errors/den)
    assert abs(1-sum(ans.values())-roc_auc_score(y,p))<1e-12
    return ans

def smoke():
    worker=module(HERE/'matrix_worker.py','worker_smoke')
    rng=np.random.default_rng(128);inc=rng.integers(0,12,400);ctx=rng.integers(0,4,400);y=((inc%2)==(ctx%2)).astype('int8')
    z,d=worker.matrix_fit(inc,ctx,y,13,5,4,516)
    assert roc_auc_score(y,z[inc,ctx])>.95
    write('smoke.json',{'status':'PASS','synthetic_only':True,'code_sha256':sha(__file__),'worker_sha256':sha(HERE/'matrix_worker.py')})

def run():
    lock=(HERE/'run.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert json.loads((HERE/'smoke.json').read_text())['code_sha256']==sha(__file__)
    assert json.loads((HERE/'smoke.json').read_text())['worker_sha256']==sha(HERE/'matrix_worker.py')
    hashes={p:sha(ROOT/p) for p in CFG['source_hashes']};assert hashes==CFG['source_hashes']
    contract={'runner':sha(__file__),'config':sha(HERE/'preregistration.json'),'worker':sha(HERE/'matrix_worker.py'),'source':hashes}
    if (HERE/'contract.json').exists(): assert json.loads((HERE/'contract.json').read_text())==contract
    else: write('contract.json',contract)
    if (HERE/'result.json').exists(): raise RuntimeError('已有完整结果，不重复训练')
    previous=json.loads((HERE/'progress.json').read_text()).get('elapsed_seconds',0) if (HERE/'progress.json').exists() else json.loads((HERE/'retry_note.json').read_text())['spent_attempt_seconds']
    if (HERE/'RUN_STARTED.json').exists():
        prior=json.loads((HERE/'RUN_STARTED.json').read_text())
        previous=max(previous,time.time()-prior['started_unix']+prior['resumed_elapsed'])
    start=time.monotonic()
    def guard():
        assert time.monotonic()-start+previous<CFG['budget_seconds'],'wall budget'
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss<CFG['memory_gib']*1024**3,'RSS budget'
    signal.signal(signal.SIGALRM,lambda *_:(_ for _ in ()).throw(TimeoutError('wall budget')))
    signal.alarm(max(1,int(CFG['budget_seconds']-previous)))
    write('RUN_STARTED.json',{'pid':os.getpid(),'started_unix':time.time(),'resumed_elapsed':previous,'contract':contract})
    raw=pd.read_csv(ROOT/'data/train.csv');y=raw.Will_Buy_EV.map({'No':0,'Yes':1}).to_numpy('int8');ids=raw.id.to_numpy()
    inc,iv=pd.factorize(raw[CFG['income']],sort=True)
    ctx,cv=pd.factorize(pd.MultiIndex.from_frame(raw[CFG['context']]),sort=True)
    ni,nc=len(iv),len(cv);assert min(inc.min(),ctx.min())>=0
    primary=(raw.Environmental_Concern_Level.ge(4)&raw.Subsidy_Available.eq('Yes')&raw.Range_Anxiety_Level.eq('Low')).to_numpy()
    backend=module(ROOT/'model/validation/e2e_v100_20260905/feature_backends.py','lr_backend').load_backend('v85')
    params=json.loads((ROOT/'model/v85_naji_v74_40f/frozen_config.json').read_text())['lightgbm_base_params']
    oof=np.full((len(y),3),np.nan);foldids=np.zeros(len(y),dtype='int8');rows=[]
    for fold,(fit,valid) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(np.zeros(len(y)),y),1):
        checkpoint=HERE/f'fold_{fold}.npz';summary=HERE/f'fold_{fold}.json'
        if checkpoint.exists() and summary.exists():
            row=json.loads(summary.read_text());assert row['checkpoint_sha256']==sha(checkpoint) and row['contract']==contract
            with np.load(checkpoint) as z:
                np.testing.assert_array_equal(z['ids'],ids[valid]);np.testing.assert_array_equal(z['valid'],valid);oof[valid]=z['pred']
            rows.append(row);foldids[valid]=fold;continue
        guard();print('FOLD_START',fold,'income',ni,'context',nc,flush=True)
        # 子进程只接收拟合标签，不接收外层验证标签；算法、种子和折数不变。
        inp=HERE/f'fold_{fold}_worker_input.npz';out=HERE/f'fold_{fold}_matrix.npz'
        if not out.exists():
            save_npz(inp,inc=inc[fit],ctx=ctx[fit],y=y[fit],query_inc=inc[valid],query_ctx=ctx[valid],ni=ni,nc=nc,fold=fold)
            remaining=CFG['budget_seconds']-previous-(time.monotonic()-start)
            env=dict(os.environ,MF_SECONDS=str(remaining),MF_MEMORY=str(CFG['memory_gib']*1024**3-resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))
            subprocess.run([sys.executable,str(HERE/'matrix_worker.py'),str(inp),str(out)],env=env,check=True,timeout=remaining)
        with np.load(out) as z:sf=z['fit_scores'];sv=z['query_scores']
        logs=json.loads(out.with_suffix('.json').read_text())['logs']
        assert sf.shape==(len(fit),2) and sv.shape==(len(valid),2) and np.isfinite(sf).all()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore');xf,xv,names=backend.encode(fit,y[fit],valid,42+fold)
        arms=[]
        for arm in range(3):
            xx=xf if arm==0 else np.column_stack([xf,sf[:,arm-1]])
            vv=xv if arm==0 else np.column_stack([xv,sv[:,arm-1]])
            seed=42+fold;model=lgb.LGBMClassifier(**params,**{k:seed for k in ['random_state','bagging_seed','feature_fraction_seed','data_random_seed']})
            def callback(env):
                if env.iteration%25==0:guard()
            callback.order=5
            model.fit(xx,y[fit],eval_set=[(vv,y[valid])],callbacks=[lgb.early_stopping(350,verbose=False),callback])
            p=model.predict_proba(vv)[:,1];assert np.isfinite(p).all() and ((p>=0)&(p<=1)).all();oof[valid,arm]=p
            model.booster_.save_model(str(HERE/f'fold_{fold}_arm_{arm}.txt'))
            arms.append({'arm':arm,'auc':float(roc_auc_score(y[valid],p)),'best_iteration':model.best_iteration_,'features':xx.shape[1]})
            print('ARM_COMPLETE',fold,arms[-1],flush=True);del model,xx,vv;guard()
        # 保留查询特征用于独立checkpoint复算；不保存可提交测试预测。
        save_npz(HERE/f'fold_{fold}_query.npz',x=xv,scores=sv,valid=valid)
        save_npz(checkpoint,ids=ids[valid],valid=valid,pred=oof[valid])
        row={'fold':fold,'arms':arms,'delta_primary':arms[2]['auc']-arms[0]['auc'],'delta_mechanism':arms[2]['auc']-arms[1]['auc'],'matrix_diagnostics':logs,'contract':contract,'checkpoint_sha256':sha(checkpoint)}
        write(summary.name,row);rows.append(row);foldids[valid]=fold
        write('progress.json',{'folds':rows,'elapsed_seconds':previous+time.monotonic()-start});print('FOLD_COMPLETE',fold,row['delta_primary'],row['delta_mechanism'],flush=True)
        del xf,xv,sf,sv;gc.collect()
    guard();assert np.isfinite(oof).all() and (foldids>0).all()
    auc=[float(roc_auc_score(y,oof[:,j])) for j in range(3)];parts=[pair_parts(y,oof[:,j],primary) for j in range(3)]
    wins=sum(r['delta_primary']>0 for r in rows);mwins=sum(r['delta_mechanism']>0 for r in rows)
    save_npz(HERE/'diagnostic_oof.npz',ids=ids,fold=foldids,pred=oof)
    write('result.json',{'status':'COMPLETE_DIAGNOSTIC','auc':auc,'delta_primary':auc[2]-auc[0],'delta_mechanism':auc[2]-auc[1],'positive_folds_primary':wins,'positive_folds_mechanism':mwins,'gate_passed':auc[2]-auc[0]>=.0001 and wins==5 and auc[2]>auc[1] and mwins==5,'pair_error_mass':parts,'folds':rows,'elapsed_seconds':previous+time.monotonic()-start,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'contract':contract,'oof_sha256':sha(HERE/'diagnostic_oof.npz'),'test_predictions_generated':False,'submission_allowed':False,'counts_toward_cycle':False})
    signal.alarm(0)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--smoke',action='store_true');args=ap.parse_args()
    try:smoke() if args.smoke else run()
    except BaseException:
        write('failure.json',{'status':'FAILED','traceback':traceback.format_exc()});raise
