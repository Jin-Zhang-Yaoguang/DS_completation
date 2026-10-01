"""Frozen matched V85 A/B diagnostic for source-group tree constraints."""
from __future__ import annotations
import os
for _key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[_key]='6'
import argparse,contextlib,datetime,fcntl,hashlib,importlib.util,json,platform,resource,signal,sys,time,traceback,warnings,gc
from pathlib import Path
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
TOP=HERE.parent
PREREG=HERE/'preregistration.json'
FREEZE=HERE/'freeze_manifest.json'
MAP=HERE/'feature_origin_map.json'
STATUS=TOP/'status.json'
BACKEND=ROOT/'model/validation/e2e_v100_20260905/feature_backends.py'

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def write_json(path,obj):
    tmp=path.with_name(path.name+'.tmp')
    with tmp.open('w') as f:
        json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    tmp.replace(path)
def log(s):
    line=f'{now()} {s}'
    print(line,flush=True)
    with (HERE/'train_log.txt').open('a') as f:f.write(line+'\n')
def rss():
    raw=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(raw if platform.system()=='Darwin' else raw*1024)
def check_budget(start):
    elapsed=time.monotonic()-start
    if elapsed>=3600:raise TimeoutError(f'P1 wall budget exceeded: {elapsed:.1f}s')
    if rss()>16*1024**3:raise MemoryError(f'P1 RSS budget exceeded: {rss()}')
def check_probs(p,n):
    if p.shape!=(n,) or not np.isfinite(p).all() or ((p<0)|(p>1)).any():raise ValueError('invalid probabilities')
def load_backend():
    spec=importlib.util.spec_from_file_location('takeover_v85_backend',BACKEND)
    mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore');return mod.load_backend('v85')
def preflight():
    prereg=json.loads(PREREG.read_text());freeze=json.loads(FREEZE.read_text());mapping=json.loads(MAP.read_text())
    for rel,rec in freeze['source_files'].items():
        path=ROOT/rel
        if not path.is_file() or sha(path)!=rec['sha256']:raise ValueError(f'frozen source changed: {rel}')
    if sha(MAP)!=freeze['feature_origin_map_sha256']:raise ValueError('feature mapping changed')
    if sha(HERE/'fold_assignments_5f_seed42.npy')!=freeze['fold_arrays_sha256']['5']:raise ValueError('fold array changed')
    backend=load_backend()
    static_hash=hashlib.sha256(pd.util.hash_pandas_object(backend.static,index=False).to_numpy(np.uint64).tobytes()).hexdigest()
    if static_hash!=freeze['pre_te_train_values_sha256']:raise ValueError(f'V85 pre-TE input mismatch: {static_hash}')
    names=mapping['final_features'];groups=mapping['groups_zero_based']
    expected=[c for c in backend.static if c not in backend.te_columns]+[f'{c}_TE_{tag}' for tag in ('auto','10') for c in backend.te_columns]
    if names!=expected or len(names)!=148:raise ValueError('148-column final feature schema changed')
    if len(groups)!=12 or sorted(i for g in groups for i in g)!=list(range(148)) or not all(groups):raise ValueError('groups do not exactly partition 148 columns')
    if prereg['outer_cv']!={'n_splits':5,'shuffle':True,'random_state':42}:raise ValueError('prereg CV mismatch')
    if lgb.__version__!='4.6.0':raise ValueError('LightGBM version mismatch')
    train=pd.read_csv(ROOT/'data/train.csv',usecols=['id','Will_Buy_EV'])
    y=train.Will_Buy_EV.eq('Yes').to_numpy(np.int8);ids=train.id.to_numpy(np.int64)
    if hashlib.sha256(y.tobytes()).hexdigest()!=freeze['labels_sha256']:raise ValueError('labels changed')
    if hashlib.sha256(ids.tobytes()).hexdigest()!=freeze['raw_train_ids_sha256']:raise ValueError('row IDs changed')
    folds=list(StratifiedKFold(n_splits=5,shuffle=True,random_state=42).split(np.zeros(len(y)),y))
    assignments=np.zeros(len(y),dtype=np.int16)
    for k,(_,va) in enumerate(folds,1):assignments[va]=k
    if not np.array_equal(assignments,np.load(HERE/'fold_assignments_5f_seed42.npy')):raise ValueError('fold identities changed')
    # Runtime proof that the installed LightGBM accepts and retains this constraint type.
    toy=np.random.RandomState(42).normal(size=(100,3));labels=(toy[:,0]+toy[:,1]>0).astype(int)
    test=lgb.LGBMClassifier(n_estimators=3,min_child_samples=2,verbosity=-1,n_jobs=1,interaction_constraints=[[0,1],[2]])
    test.fit(toy,labels,feature_name=['f0','f1','f2'])
    if test.booster_.params.get('interaction_constraints')!=[[0,1],[2]]:raise ValueError('LightGBM constraint not active')
    contract={'prereg_sha256':sha(PREREG),'freeze_sha256':sha(FREEZE),'feature_map_sha256':sha(MAP),'runner_sha256':sha(Path(__file__)),'backend_sha256':sha(BACKEND),'lightgbm_version':lgb.__version__}
    contract_sha=hashlib.sha256(json.dumps(contract,sort_keys=True).encode()).hexdigest()
    write_json(HERE/'preflight.json',{'status':'PASS','at_utc':now(),'contract':contract,'contract_sha256':contract_sha,'train_rows':len(y),'final_columns':148,'group_sizes':mapping['group_sizes'],'static_input_sha256':static_hash})
    return backend,y,ids,folds,names,groups,contract_sha

def save_ckpt(path,fold,arm,valid,pred,auc,best_iter,contract_sha,model_path):
    tmp=path.with_suffix('.tmp.npz')
    with tmp.open('wb') as f:
        np.savez_compressed(f,fold=np.array(fold),arm=np.array(arm),valid_idx=valid.astype(np.int64),valid_pred=pred.astype(np.float64),fold_auc=np.array(auc),best_iteration=np.array(best_iter),contract_sha256=np.array(contract_sha),model_sha256=np.array(sha(model_path)))
        f.flush();os.fsync(f.fileno())
    tmp.replace(path)
def load_ckpt(path,fold,arm,valid,contract_sha):
    with np.load(path,allow_pickle=False) as d:
        if int(d['fold'])!=fold or str(d['arm'])!=arm or str(d['contract_sha256'])!=contract_sha or not np.array_equal(d['valid_idx'],valid):raise ValueError('checkpoint identity mismatch')
        pred=d['valid_pred'].astype(np.float64);check_probs(pred,len(valid))
        model_path=HERE/f'fold_{fold:02d}_{arm}.txt'
        if not model_path.is_file() or sha(model_path)!=str(d['model_sha256']):raise ValueError('model checkpoint mismatch')
        return pred,float(d['fold_auc']),int(d['best_iteration'])
def update_status(phase,fold=None,arm=None,**kwargs):
    d=json.loads(STATUS.read_text());d.update({'updated_at_utc':now(),'phase':phase,'current_experiment':'p1_source_group_constraints_5f','checkpoint':{'fold':fold,'arm':arm} if fold else None,'process':{'pid':os.getpid(),'active':phase=='P1_RUNNING'}});d.update(kwargs);write_json(STATUS,d)
def run():
    start=time.monotonic();backend,y,ids,folds,names,groups,contract_sha=preflight()
    params=json.loads((ROOT/'model/v85_naji_v74_40f/frozen_config.json').read_text())['lightgbm_base_params'].copy()
    if params.get('n_jobs')!=8:raise ValueError('V85 base threads drifted')
    params['n_jobs']=6
    lock=HERE/'run.lock'
    with lock.open('a+') as handle:
        try:fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:raise RuntimeError('P1 diagnostic instance already running')
        handle.seek(0);handle.truncate();handle.write(json.dumps({'pid':os.getpid(),'contract_sha256':contract_sha,'at_utc':now()}));handle.flush();os.fsync(handle.fileno())
        if (HERE/'result.json').exists():raise RuntimeError('result already exists; refuse duplicate run')
        write_json(HERE/'RUN_STARTED.json',{'pid':os.getpid(),'started_at_utc':now(),'contract_sha256':contract_sha,'resume':bool(list(HERE.glob('fold_??_?.npz')))} )
        update_status('P1_RUNNING',process={'pid':os.getpid(),'active':True,'contract_sha256':contract_sha},next_action='Wait for paired 5-fold checkpoint and gate')
        log(f'P1 start pid={os.getpid()} contract={contract_sha} threads=6')
        oof=np.full((len(y),2),np.nan,dtype=np.float64);fold_rows=[]
        for fold,(fit,valid) in enumerate(folds,1):
            check_budget(start)
            paths={arm:HERE/f'fold_{fold:02d}_{arm}.npz' for arm in ('A','B')}
            if all(path.exists() for path in paths.values()):
                vals={arm:load_ckpt(paths[arm],fold,arm,valid,contract_sha) for arm in ('A','B')}
                log(f'fold={fold} resumed both arms')
            else:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    xf,xv,computed_names=backend.encode(fit,y[fit],valid,42+fold)
                if names!=computed_names or xf.shape[1]!=148 or xv.shape[1]!=148:raise ValueError('encoded column contract changed')
                vals={}
                for arm in ('A','B'):
                    path=paths[arm]
                    if path.exists():
                        vals[arm]=load_ckpt(path,fold,arm,valid,contract_sha);continue
                    check_budget(start)
                    fold_params=params.copy();seed=42+fold
                    for key in ('random_state','bagging_seed','feature_fraction_seed','data_random_seed'):fold_params[key]=seed
                    if arm=='B':fold_params['interaction_constraints']=groups
                    model=lgb.LGBMClassifier(**fold_params)
                    tic=time.monotonic()
                    model.fit(xf,y[fit],eval_set=[(xv,y[valid])],eval_metric='auc',feature_name=names,callbacks=[lgb.early_stopping(350,verbose=False),lgb.log_evaluation(period=0)])
                    active=model.booster_.params.get('interaction_constraints')
                    if arm=='B' and active!=groups:raise ValueError('B constraint was not retained')
                    if arm=='A' and active is not None:raise ValueError('A unexpectedly constrained')
                    if model.booster_.feature_name()!=names:raise ValueError('model feature names mismatch')
                    best=int(model.best_iteration_ or params['n_estimators'])
                    pred=model.predict_proba(xv,num_iteration=best)[:,1].astype(np.float64);check_probs(pred,len(valid))
                    auc=float(roc_auc_score(y[valid],pred))
                    model_path=HERE/f'fold_{fold:02d}_{arm}.txt';tmp=model_path.with_suffix('.tmp.txt');model.booster_.save_model(str(tmp));tmp.replace(model_path)
                    save_ckpt(path,fold,arm,valid,pred,auc,best,contract_sha,model_path)
                    vals[arm]=(pred,auc,best)
                    log(f'fold={fold} arm={arm} auc={auc:.9f} best={best} elapsed={time.monotonic()-tic:.1f}s rss_gib={rss()/1024**3:.2f}')
                    update_status('P1_RUNNING',fold=fold,arm=arm)
                    del model;gc.collect()
                del xf,xv;gc.collect()
            a,auc_a,iter_a=vals['A'];b,auc_b,iter_b=vals['B'];oof[valid,0]=a;oof[valid,1]=b
            blended=.5*(a+b);auc_blend=float(roc_auc_score(y[valid],blended))
            fold_rows.append({'fold':fold,'valid_rows':len(valid),'a_auc':auc_a,'b_auc':auc_b,'blend_auc':auc_blend,'b_minus_a':auc_b-auc_a,'blend_minus_a':auc_blend-auc_a,'a_best_iteration':iter_a,'b_best_iteration':iter_b})
            write_json(HERE/'progress.json',{'contract_sha256':contract_sha,'updated_at_utc':now(),'completed_folds':fold,'folds':fold_rows,'elapsed_seconds':time.monotonic()-start,'peak_rss_bytes':rss()})
            update_status('P1_RUNNING',fold=fold,arm='COMPLETE')
        if not np.isfinite(oof).all():raise ValueError('OOF incomplete')
        a_auc=float(roc_auc_score(y,oof[:,0]));b_auc=float(roc_auc_score(y,oof[:,1]));blend_auc=float(roc_auc_score(y,.5*(oof[:,0]+oof[:,1])))
        a_reference=0.9460627523329033
        if abs(a_auc-a_reference)>0.00005:raise ValueError(f'A control diverges from V85 five-fold reference: {a_auc}, expected {a_reference}')
        d_b=b_auc-a_auc;d_blend=blend_auc-a_auc
        wins_b=sum(r['b_minus_a']>0 for r in fold_rows);wins_blend=sum(r['blend_minus_a']>0 for r in fold_rows)
        gate_b=d_b>0 and wins_b==5;gate_blend=d_blend>0 and wins_blend==5
        np.save(HERE/'oof_a.npy',oof[:,0]);np.save(HERE/'oof_b.npy',oof[:,1]);np.save(HERE/'oof_fixed_blend.npy',.5*(oof[:,0]+oof[:,1]))
        check_budget(start)
        result={'status':'COMPLETE_DIAGNOSTIC','completed_at_utc':now(),'experiment_id':'P1_SOURCE_GROUP_CONSTRAINTS_5F_20260926','evidence_level':'outer-validation early-stopped matched development diagnostic','folds':fold_rows,'pooled_oof_auc':{'A':a_auc,'B':b_auc,'fixed_blend':blend_auc},'pooled_delta_vs_a':{'B':d_b,'fixed_blend':d_blend},'positive_folds':{'B':wins_b,'fixed_blend':wins_blend},'diagnostic_gate':{'B':gate_b,'fixed_blend':gate_blend,'any_pass':gate_b or gate_blend},'research_plus_0_0001_gate':{'B':d_b>=.0001 and wins_b==5,'fixed_blend':d_blend>=.0001 and wins_blend==5},'a_reference_5f_auc':a_reference,'a_reference_delta':a_auc-a_reference,'elapsed_seconds':time.monotonic()-start,'peak_rss_bytes':rss(),'contract_sha256':contract_sha,'oof_sha256':{k:sha(HERE/f'oof_{k}.npy') for k in ['a','b','fixed_blend']},'test_predictions_generated':False,'submission_allowed_from_diagnostic':False}
        write_json(HERE/'result.json',result)
        log(f"P1 complete A={a_auc:.9f} B={b_auc:.9f} blend={blend_auc:.9f} dB={d_b:+.9f} dBlend={d_blend:+.9f} wins={wins_b}/{wins_blend} gate={gate_b or gate_blend}")
        update_status('P1_DIAGNOSTIC_COMPLETE',process={'pid':os.getpid(),'active':False},checkpoint={'fold':5,'arm':'COMPLETE'},oof=result['pooled_oof_auc'],p1_diagnostic_gate=result['diagnostic_gate'],next_action='Independent result verification; formal 40-fold if pass, otherwise P2')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');args=ap.parse_args()
    if args.preflight:
        *_,contract=preflight();print(json.dumps({'status':'PASS','contract_sha256':contract}));return
    try:run()
    except BaseException:
        error={'status':'FAILED','at_utc':now(),'traceback':traceback.format_exc(),'pid':os.getpid()}
        write_json(HERE/'failure.json',error)
        update_status('P1_FAILED',process={'pid':os.getpid(),'active':False},blocker=str(error['traceback'][-2000:]),next_action='Audit failure and resume only under same frozen contract')
        raise
if __name__=='__main__':main()
