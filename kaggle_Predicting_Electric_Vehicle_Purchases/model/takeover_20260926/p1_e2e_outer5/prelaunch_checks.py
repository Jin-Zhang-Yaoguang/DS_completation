"""R02 prelaunch checks without fitting real competition models or scoring U."""
import datetime,hashlib,importlib.util,json
from pathlib import Path
import numpy as np,pandas as pd
HERE=Path(__file__).resolve().parent

def module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj

def main():
    runner=module(HERE/'run.py','r02_prelaunch_runner');verify=module(HERE/'verify_score.py','r02_prelaunch_verify')
    base=runner.cpu.load_config()
    ids=pd.read_csv(runner.PROJECT/'data/train.csv',usecols=['id']).id.to_numpy(np.int64)
    with np.load(runner.ARCH/'splits.npz',allow_pickle=False) as z:splits={k:z[k] for k in z.files}
    ct=runner.ct_audit(splits,ids,base)
    rng=np.random.default_rng(19);n=500;q=37
    y=np.tile(np.array([0,1],dtype=np.int8),n//2);rng.shuffle(y)
    a=rng.uniform(.1,.9,n);b=rng.uniform(.1,.9,n);c=rng.uniform(.1,.9,n)
    ua=rng.uniform(.1,.9,q);ub=rng.uniform(.1,.9,q);uc=rng.uniform(.1,.9,q)
    v90_oof,v90_u,w90=verify.meta90(y,a,b,ua,ub)
    _,v100_u,w100=verify.meta100(y,v90_oof,c,v90_u,uc)
    source=runner.cpu.fit_v100_meta(y,a,b,c,ua,ub,uc,uc)
    error=float(np.max(np.abs(v100_u-source['refit_prediction'])))
    if error>1e-12 or w90!=source['v90_fold_weights'] or abs(w100-source['ct_final_weight'])>1e-15:raise ValueError('independent online meta formulas differ')
    d={'status':'PASS_UNSCORED','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'synthetic_seed':19,'synthetic_rows':n,'synthetic_query_rows':q,'online_meta_max_abs_error':error,'v90_weights_equal':True,'v100_weight_equal':True,'ct_audit':ct,'real_competition_models_fitted':0,'real_outer_U_scores_computed':0,'runner_sha256':runner.sha(HERE/'run.py'),'verifier_sha256':runner.sha(HERE/'verify_score.py'),'legacy_cpu_sha256':runner.sha(runner.LEGACY/'legacy_cpu.py')}
    runner.save(HERE/'prelaunch_checks.json',d)
    print(json.dumps({'status':d['status'],'online_meta_max_abs_error':error,'ct_caches':len(ct['outer_caches']),'model_state_bytes_archived':ct['model_state_bytes_archived']}))
if __name__=='__main__':main()
