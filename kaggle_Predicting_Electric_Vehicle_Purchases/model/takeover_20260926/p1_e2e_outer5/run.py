"""R02: faithful old-online V100 and P1 grouped V85 on the same five T/U splits.

This process never scores outer U.  Historical new-CPU A/B predictions are not read.
"""
from __future__ import annotations
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','BLIS_NUM_THREADS'):
    os.environ[key]='8'
import argparse,datetime,fcntl,gc,hashlib,json,platform,resource,sys,time,traceback
from pathlib import Path
import lightgbm as lgb,numpy as np,pandas as pd
from threadpoolctl import threadpool_limits

HERE=Path(__file__).resolve().parent;TOP=HERE.parent;PROJECT=HERE.parents[2]
ARCH=PROJECT/'model/validation/e2e_v100_20260905'
LEGACY=PROJECT/'model/validation/e2e_legacy_comparison_20260905'
FORMAL=TOP/'p1_source_group_constraints_40f';DIAG=TOP/'p1_source_group_constraints_5f'
GPU_SOURCE=ARCH/'gpu/revision_01';GPU=ARCH/'gpu/remote_output/ct_cache'
sys.path[:0]=[str(ARCH),str(LEGACY)]
import cpu_runner as cpu
import legacy_cpu as old
import assemble_e2e as assembly

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(path):return cpu.sha(path)
def save(path,value):cpu.atomic_json(path,value)
def log(s):
    line=f'{now()} {s}';print(line,flush=True)
    with (HERE/'train_log.txt').open('a') as f:f.write(line+'\n')
def peak():
    r=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(r if platform.system()=='Darwin' else r*1024)
def valid(p,n):
    if p.shape!=(n,) or not np.isfinite(p).all() or ((p<0)|(p>1)).any():raise ValueError('invalid probability array')
def status(phase,outer=None,family=None,atom=None,**extra):
    path=TOP/'status.json';s=json.loads(path.read_text());s.update({'phase':phase,'current_experiment':'p1_e2e_outer5_r02','updated_at_utc':now(),'process':{'pid':os.getpid(),'active':phase=='P1_E2E_R02_RUNNING'},'checkpoint':{'outer':outer,'family':family,'atom':atom} if outer else None});s.update(extra);save(path,s)

class Budget:
    def __init__(self):
        prior=json.loads((HERE/'budget.json').read_text()) if (HERE/'budget.json').exists() else {'spent_seconds':0.,'peak_rss_bytes':0}
        self.prior=float(prior['spent_seconds']);self.peak=int(prior['peak_rss_bytes']);self.start=time.monotonic();self.check()
    def check(self):
        spent=self.prior+time.monotonic()-self.start;self.peak=max(self.peak,peak())
        save(HERE/'budget.json',{'spent_seconds':spent,'peak_rss_bytes':self.peak,'pid':os.getpid(),'updated_at_utc':now()})
        if spent>43200:raise TimeoutError('R02 12-hour cumulative CPU budget exceeded')
        if self.peak>24*1024**3:raise MemoryError('R02 24-GiB peak RSS budget exceeded')

def ct_audit(splits,ids,base):
    cfg=json.loads((GPU_SOURCE/'frozen_config.json').read_text());complete=json.loads((ARCH/'gpu/remote_output/GPU_RUN_RESULT.json').read_text());done=json.loads((GPU/'GPU_COMPLETE.json').read_text());receipt=json.loads((ARCH/'gpu/PUSH_RECEIPT.json').read_text())
    if cfg['outer_seed']!=42437 or cfg['inner_seed']!=42 or cfg['iterations']!=1426 or cfg['model_seed']!=20260904:raise ValueError('CT recipe drift')
    if cfg['source_sha256']['train.csv']!=base['sources']['data/train.csv'] or cfg['source_sha256']['original.csv']!=base['sources']['data/original_dataset/EV_Adoption_and_Range_Anxiety_Dataset.csv']:raise ValueError('CT data source drift')
    if cfg['source_sha256']['historical_ct_notebook']!=base['sources']['model/diagnostics/ctboost_remote_probe_20260905/kernel/s6e9-ctboost-oof-audit.ipynb']:raise ValueError('CT historical recipe drift')
    for name,digest in cfg['code_sha256'].items():
        if sha(GPU_SOURCE/name)!=digest:raise ValueError(f'CT implementation drift: {name}')
    if complete['status']!='GPU_CACHE_RUN_COMPLETE' or done['status']!='CT_CACHE_COMPLETE_UNSCORED' or done['config_sha256']!=sha(GPU_SOURCE/'frozen_config.json') or done['submission_created']:raise ValueError('CT GPU completion invalid')
    if receipt['status']!='PUSH_RETURNED' or receipt['returncode']!=0 or receipt['config_sha256']!=sha(GPU_SOURCE/'frozen_config.json'):raise ValueError('CT GPU push provenance invalid')
    checks=[]
    for outer in range(1,6):
        train=splits[f'outer_{outer:02d}_train_idx'];hold=splits[f'outer_{outer:02d}_valid_idx'];fold=splits[f'outer_{outer:02d}_ct_fold']
        cache=GPU/f'outer_{outer:02d}';assembly.check_ct(cache,train,hold,ids,fold,cfg,sha(GPU_SOURCE/'frozen_config.json'))
        checks.append({'outer':outer,'cache_sha256':sha(cache/'cache.npz'),'manifest_sha256':sha(cache/'cache_manifest.json')})
    return {'status':'PASS_PREDICTION_PROVENANCE_ONLY','config_sha256':sha(GPU_SOURCE/'frozen_config.json'),'gpu_result_sha256':sha(ARCH/'gpu/remote_output/GPU_RUN_RESULT.json'),'gpu_complete_sha256':sha(GPU/'GPU_COMPLETE.json'),'outer_caches':checks,'model_state_bytes_archived':False}

def preflight():
    pr=json.loads((HERE/'conditional_preregistration.json').read_text())
    if pr['experiment_id']!='P1_ONLINE_RECIPE_E2E_OUTER5_R02_20260926' or pr['outer_candidate']['M_U']!='0.5 * (faithful_legacy_V100_U + C_U)':raise ValueError('R02 protocol absent or M formula drift')
    prelaunch=json.loads((HERE/'prelaunch_checks.json').read_text())
    if prelaunch['status']!='PASS_UNSCORED' or prelaunch['real_competition_models_fitted']!=0 or prelaunch['real_outer_U_scores_computed']!=0 or prelaunch['online_meta_max_abs_error']>1e-12 or len(prelaunch['ct_audit']['outer_caches'])!=5 or prelaunch['runner_sha256']!=sha(Path(__file__)) or prelaunch['verifier_sha256']!=sha(HERE/'verify_score.py') or prelaunch['legacy_cpu_sha256']!=sha(LEGACY/'legacy_cpu.py'):raise ValueError('R02 prelaunch audit missing or stale')
    f=json.loads((FORMAL/'cv_results.json').read_text());v=json.loads((FORMAL/'verification.json').read_text())
    if f['status']!='COMPLETE' or v['status']!='PASS' or sha(FORMAL/'cv_results.json')!=v['result_sha256'] or not any(f['gates'].values()) or f['selected_c']!='fixed_v85_b_50_50':raise ValueError('formal P1 fixed-blend gate not verified')
    selected='M' if f['gates']['m'] else 'C'
    mapping=json.loads((DIAG/'feature_origin_map.json').read_text());frozen=json.loads((DIAG/'freeze_manifest.json').read_text())
    if sha(DIAG/'feature_origin_map.json')!=frozen['feature_origin_map_sha256']:raise ValueError('group map drift')
    for rel,record in frozen['source_files'].items():
        if sha(PROJECT/rel)!=record['sha256']:raise ValueError(f'frozen source drift: {rel}')
    base=cpu.load_config()
    if sha(ARCH/'splits.npz')!=base['splits_sha256']:raise ValueError('outer splits drift')
    frame=pd.read_csv(PROJECT/'data/train.csv',usecols=['id','Will_Buy_EV']);ids=frame.id.to_numpy(np.int64);y=frame.Will_Buy_EV.eq('Yes').to_numpy(np.int8)
    if cpu.arr_sha(ids)!=base['train_id_sha256'] or hashlib.sha256(y.tobytes()).hexdigest()!=frozen['labels_sha256']:raise ValueError('label/ID drift')
    with np.load(ARCH/'splits.npz',allow_pickle=False) as z:splits={name:z[name] for name in z.files}
    for outer in range(1,6):
        train=splits[f'outer_{outer:02d}_train_idx'];hold=splits[f'outer_{outer:02d}_valid_idx']
        if np.intersect1d(train,hold).size or len(train)+len(hold)!=len(y):raise ValueError('T/U overlap or coverage')
        for family in ('v80','v85','ct'):
            folds=splits[f'outer_{outer:02d}_{family}_fold'];n=5 if family=='ct' else 40
            if len(folds)!=len(train) or not np.array_equal(np.unique(folds),np.arange(n)):raise ValueError('inner fold drift')
            if cpu.arr_sha(folds)!=base['outer_plan'][outer-1]['atoms'][family]['fold_ids_sha256']:raise ValueError('inner fold SHA drift')
    ct=ct_audit(splits,ids,base)
    groups=mapping['groups_zero_based'];names=mapping['final_features']
    if sorted(i for group in groups for i in group)!=list(range(148)) or len(groups)!=12 or len(names)!=148:raise ValueError('group partition drift')
    if lgb.__version__!='4.6.0':raise ValueError('LightGBM version drift')
    contract={'prereg_sha256':sha(HERE/'conditional_preregistration.json'),'protocol_review_sha256':sha(HERE/'PROTOCOL_REVIEW_R02.md'),'prelaunch_checks_sha256':sha(HERE/'prelaunch_checks.json'),'runner_sha256':sha(Path(__file__)),'verifier_sha256':sha(HERE/'verify_score.py'),'formal_result_sha256':sha(FORMAL/'cv_results.json'),'formal_verification_sha256':sha(FORMAL/'verification.json'),'group_map_sha256':sha(DIAG/'feature_origin_map.json'),'frozen_source_sha256':sha(DIAG/'freeze_manifest.json'),'legacy_adapter_sha256':sha(LEGACY/'legacy_cpu.py'),'cpu_runner_sha256':sha(ARCH/'cpu_runner.py'),'feature_backend_sha256':sha(ARCH/'feature_backends.py'),'splits_sha256':sha(ARCH/'splits.npz'),'ct_gpu_complete_sha256':ct['gpu_complete_sha256'],'selected_before_U_scoring':selected}
    digest=cpu.json_sha(contract)
    record={'status':'PASS_R02_UNSCORED','checked_at_utc':now(),'contract':contract,'contract_sha256':digest,'selected_before_U_scoring':selected,'ct_audit':ct,'baseline_role':'FAITHFUL_ONLINE_V100_ALGORITHM','archived_new_cpu_A_score_used':False,'old_AB_gate_inherited':False}
    if (HERE/'preflight.json').exists() and json.loads((HERE/'preflight.json').read_text())['contract_sha256']!=digest:raise ValueError('preflight contract changed')
    save(HERE/'preflight.json',record)
    return y,ids,splits,base,groups,names,selected,digest

def atom_paths(outer,family,atom):return HERE/f'outer_{outer:02d}'/family/f'atom_{atom:02d}'
def check_atom(path,expected,contract,hold,oofrows,ids):
    manifest=path/'manifest.json';archive=path/'predictions.npz';model=path/'model.txt'
    if not manifest.exists():
        if path.exists():raise ValueError(f'partial atom requires review: {path}')
        return None
    m=json.loads(manifest.read_text())
    if m['status']!='COMPLETE_UNSCORED' or m['contract_sha256']!=contract or any(m.get(k)!=v for k,v in expected.items()) or m['prediction_sha256']!=sha(archive) or m['model_sha256']!=sha(model):raise ValueError(f'atom checkpoint mismatch: {path}')
    if m['outer_hold_labels_used'] or not m['atom_hold_labels_used_for_early_stopping'] or m['refit_performed']:raise ValueError('legacy F/H scope drift')
    with np.load(archive,allow_pickle=False) as z:
        for key,arr in [('oof_idx',oofrows),('valid_idx',hold),('oof_id',ids[oofrows]),('valid_id',ids[hold])]:
            if not np.array_equal(z[key],arr):raise ValueError('atom row identity drift')
        valid(z['oof_proba'],len(oofrows));valid(z['valid_proba'],len(hold))
    return m

def run():
    y,ids,splits,base,groups,names,selected,digest=preflight()
    with (HERE/'run.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (HERE/'cache_complete.json').exists():raise RuntimeError('R02 cache already complete')
        budget=Budget();save(HERE/'RUN_STARTED.json',{'at_utc':now(),'pid':os.getpid(),'contract_sha256':digest,'selected_before_U_scoring':selected})
        status('P1_E2E_R02_RUNNING',next_action='Train 600 faithful F/H CPU atoms; no outer U score')
        count=0
        with threadpool_limits(limits=8):
            for outer in range(1,6):
                train=splits[f'outer_{outer:02d}_train_idx'];hold=splits[f'outer_{outer:02d}_valid_idx']
                for family in ('v80','v85','grouped_v85'):
                    source='v85' if family=='grouped_v85' else family
                    fold=splits[f'outer_{outer:02d}_{source}_fold'];backend=cpu.load_backend(source)
                    config=base['families'][source];oof=np.full(len(train),np.nan);u=np.zeros(len(hold));coverage=np.zeros(len(train),np.int8)
                    for atom in range(1,41):
                        fit_local=np.flatnonzero(fold!=atom-1);h_local=np.flatnonzero(fold==atom-1)
                        fit=train[fit_local];h=train[h_local];path=atom_paths(outer,family,atom)
                        expected={'outer':outer,'family':family,'atom':atom,'fit_idx_sha256':cpu.arr_sha(fit),'early_stop_hold_idx_sha256':cpu.arr_sha(h),'outer_valid_idx_sha256':cpu.arr_sha(hold),'fit_y_sha256':cpu.arr_sha(y[fit]),'early_stop_hold_y_sha256':cpu.arr_sha(y[h]),'te_seed':config['te_seed_base']+atom}
                        m=check_atom(path,expected,digest,hold,h,ids) if path.exists() else None
                        if m is None:
                            budget.check();path.mkdir(parents=True,exist_ok=False);tic=time.monotonic()
                            params=cpu.atom_params(source,config,atom);params['n_jobs']=8
                            if family=='grouped_v85':params['interaction_constraints']=groups
                            pred,scope,model=old.fit_legacy_atom(backend,fit,y[fit],h,y[h],hold,params,config['te_seed_base']+atom,config['early_stopping_rounds'])
                            if scope['refit_performed'] or scope['outer_hold_labels_used'] or scope['training_fit_count']!=1:raise ValueError('legacy single fit scope invalid')
                            if family=='grouped_v85' and (model.booster_.params.get('interaction_constraints')!=groups or model.booster_.feature_name()!=names):raise ValueError('grouped constraint inactive')
                            if family!='grouped_v85' and model.booster_.params.get('interaction_constraints'):raise ValueError('control received constraints')
                            valid(pred,len(h)+len(hold));tmp=path/'model.tmp.txt';model.booster_.save_model(str(tmp));tmp.replace(path/'model.txt')
                            cpu.atomic_npz(path/'predictions.npz',oof_idx=h,valid_idx=hold,oof_id=ids[h],valid_id=ids[hold],oof_proba=pred[:len(h)],valid_proba=pred[len(h):])
                            m={**expected,**scope,'status':'COMPLETE_UNSCORED','contract_sha256':digest,'family':family,'outer':outer,'atom':atom,'oof_id_sha256':cpu.arr_sha(ids[h]),'valid_id_sha256':cpu.arr_sha(ids[hold]),'model_sha256':sha(path/'model.txt'),'prediction_sha256':sha(path/'predictions.npz'),'elapsed_seconds':time.monotonic()-tic,'outer_hold_labels_used':False}
                            save(path/'manifest.json',m);check_atom(path,expected,digest,hold,h,ids)
                            log(f'outer={outer}/5 family={family} atom={atom}/40 seconds={m["elapsed_seconds"]:.1f} best={m["selected_iteration"]} rss_gib={peak()/1024**3:.2f}')
                            del model,pred;gc.collect()
                        with np.load(path/'predictions.npz',allow_pickle=False) as z:
                            oof[h_local]=z['oof_proba'];u+=z['valid_proba']/40;coverage[h_local]+=1
                        count+=1;budget.check();save(HERE/'progress.json',{'completed_atoms':count,'total_atoms':600,'outer':outer,'family':family,'atom':atom,'spent_seconds':json.loads((HERE/'budget.json').read_text())['spent_seconds'],'contract_sha256':digest,'updated_at_utc':now()});status('P1_E2E_R02_RUNNING',outer,family,atom)
                    if not np.all(coverage==1) or not np.isfinite(oof).all():raise ValueError('family OOF coverage invalid')
                    valid(u,len(hold));directory=HERE/f'outer_{outer:02d}'/family
                    data={'train_idx':train,'valid_idx':hold,'train_id':ids[train],'valid_id':ids[hold],'atom_fold':fold,'oof_proba':oof,'valid_proba':u}
                    if (directory/'cache.npz').exists():
                        with np.load(directory/'cache.npz',allow_pickle=False) as z:
                            if set(z.files)!=set(data) or any(not np.array_equal(z[k],v) for k,v in data.items()):raise ValueError('existing cache mismatch')
                    else:cpu.atomic_npz(directory/'cache.npz',**data)
                    save(directory/'cache_manifest.json',{'status':'CACHE_COMPLETE_UNSCORED','contract_sha256':digest,'outer':outer,'family':family,'cache_sha256':sha(directory/'cache.npz'),'atom_manifest_sha256':{str(a):sha(atom_paths(outer,family,a)/'manifest.json') for a in range(1,41)},'outer_U_labels_used':False})
                    del backend,oof,u;gc.collect();log(f'outer={outer}/5 family={family} cache complete, U unscored')
        if count!=600:raise ValueError('missing R02 atoms')
        budget.check();save(HERE/'cache_complete.json',{'status':'COMPLETE_UNSCORED','contract_sha256':digest,'atoms':600,'ct_caches':5,'candidate_selected_before_U_scoring':selected,'completed_at_utc':now(),'budget':json.loads((HERE/'budget.json').read_text()),'archived_new_cpu_A_score_used':False})
        status('P1_E2E_R02_CACHE_COMPLETE',process={'pid':os.getpid(),'active':False},next_action='Independent R02 source/model/meta reconstruction before first outer U score')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--preflight',action='store_true');args=parser.parse_args()
    try:
        if args.preflight:
            *_,selected,digest=preflight();print(json.dumps({'status':'PASS_R02_UNSCORED','selected':selected,'contract_sha256':digest}));return
        run()
    except BaseException:
        detail={'status':'FAILED','at_utc':now(),'traceback':traceback.format_exc()};save(HERE/'failure.json',detail)
        status('P1_E2E_R02_FAILED',process={'pid':os.getpid(),'active':False},blocker=detail['traceback'][-3000:],next_action='Audit checkpoint and preserve R02 contract before resume')
        raise
if __name__=='__main__':main()
