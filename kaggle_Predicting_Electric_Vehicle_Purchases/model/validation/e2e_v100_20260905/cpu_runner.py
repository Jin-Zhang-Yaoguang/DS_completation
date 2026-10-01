#!/usr/bin/env python3
"""Checkpointed V100 E2E CPU cache; no historic OOF and no outer-hold scoring."""
from __future__ import annotations
import os
for _key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","VECLIB_MAXIMUM_THREADS","NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "8"
import argparse
import fcntl
import gc
import hashlib
import json
import resource
import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb
import sklearn
from sklearn.model_selection import StratifiedKFold, StratifiedShuffleSplit
from threadpoolctl import threadpool_limits
from feature_backends import Backend, load_backend, module_at

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2]
FAMILY_DIRS = {"v80":"v80_strict_v61_outer104395303_40f","v85":"v85_naji_v74_40f"}


def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()


def arr_sha(x):
    return hashlib.sha256(np.asarray(x,dtype="<i8").tobytes()).hexdigest()


def json_sha(x):
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()


def atomic_json(path,payload):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+f".tmp.{os.getpid()}")
    with temp.open("x",encoding="utf-8") as f:
        json.dump(payload,f,ensure_ascii=False,indent=2,allow_nan=False); f.write("\n"); f.flush(); os.fsync(f.fileno())
    os.replace(temp,path)


def atomic_npz(path,**arrays):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+f".tmp.{os.getpid()}")
    with temp.open("xb") as f:
        np.savez_compressed(f,**arrays); f.flush(); os.fsync(f.fileno())
    os.replace(temp,path)


def source_files():
    files=[Path(__file__),OUT/"feature_backends.py",OUT/"test_cpu_runner.py",OUT/"README.md",PROJECT/"data/train.csv",PROJECT/"data/test.csv",PROJECT/"data/original_dataset/EV_Adoption_and_Range_Anxiety_Dataset.csv"]
    for directory in FAMILY_DIRS.values():
        files += [PROJECT/f"model/{directory}/{directory}.py",PROJECT/f"model/{directory}/frozen_config.json"]
    for directory in ("v29_income_bin10_te_lgbm","v6_multiscale_te_lgbm","v68_naji_accelerated_probe","v90_v89_member_verify_budget_retry","v100_v90_ctboost_nested_cv_blend"):
        files.append(PROJECT/f"model/{directory}/{directory}.py")
    files.append(PROJECT/"model/diagnostics/ctboost_remote_probe_20260905/kernel/s6e9-ctboost-oof-audit.ipynb")
    return files


def freeze():
    if (OUT/"frozen_config.json").exists() or (OUT/"splits.npz").exists():
        raise FileExistsError("frozen state exists; do not overwrite")
    frame=pd.read_csv(PROJECT/"data/train.csv",usecols=["id","Will_Buy_EV"])
    y=frame.Will_Buy_EV.eq("Yes").to_numpy(np.int8)
    outer_ids=np.full(len(y),-1,dtype=np.int8); arrays={}
    plan=[]
    for outer,(train,hold) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42437).split(np.zeros(len(y)),y),1):
        outer_ids[hold]=outer
        arrays[f"outer_{outer:02d}_train_idx"]=train
        arrays[f"outer_{outer:02d}_valid_idx"]=hold
        row={"outer":outer,"train_idx_sha256":arr_sha(train),"valid_idx_sha256":arr_sha(hold),"train_id_sha256":arr_sha(frame.id.to_numpy()[train]),"valid_id_sha256":arr_sha(frame.id.to_numpy()[hold]),"atoms":{}}
        for family,n,seed in (("v80",40,104395303),("v85",40,42),("ct",5,42)):
            ids=np.full(len(train),-1,dtype=np.int8)
            for atom,(_,valid) in enumerate(StratifiedKFold(n,shuffle=True,random_state=seed).split(np.zeros(len(train)),y[train])):
                ids[valid]=atom
            arrays[f"outer_{outer:02d}_{family}_fold"]=ids
            row["atoms"][family]={"folds":n,"split_seed":seed,"fold_ids_sha256":arr_sha(ids)}
        plan.append(row)
    arrays["outer_fold"]=outer_ids
    atomic_npz(OUT/"splits.npz",**arrays)
    family_configs={}
    for family,directory in FAMILY_DIRS.items():
        old=json.loads((PROJECT/f"model/{directory}/frozen_config.json").read_text())
        params=old["lightgbm_params" if family=="v80" else "lightgbm_base_params"].copy()
        params["n_jobs"]=8
        family_configs[family]={"params":params,"early_stopping_rounds":old["early_stopping_rounds"],"te_seed_base":104395303 if family=="v80" else 42,"model_seed_base":104395303 if family=="v80" else 42,"seed_fields":[] if family=="v80" else old["lightgbm_fold_seed_fields"]}
    config={"experiment_id":"E2E_V100_20260905","status_at_freeze":"DESIGN_READY_NOT_STARTED","outer_folds":5,"outer_seed":42437,"historically_exposed_data":True,"is_new_blind_test":False,"cpu_seconds":43200,"threads":8,"memory_bytes":24*1024**3,"early_stop_fraction":.1,"early_stop_seed_base":424370000,"early_stop_family_offsets":{"v80":0,"v85":100},"families":family_configs,"outer_plan":plan,"splits_sha256":sha(OUT/"splits.npz"),"train_rows":len(frame),"train_id_sha256":arr_sha(frame.id.to_numpy()),"versions":{"python":sys.version.split()[0],"numpy":np.__version__,"pandas":pd.__version__,"sklearn":sklearn.__version__,"lightgbm":lgb.__version__},"sources":{str(path.relative_to(PROJECT)):sha(path) for path in source_files()},"submission_budget":0}
    atomic_json(OUT/"frozen_config.json",config)
    print(json.dumps({"status":"FROZEN_NOT_TRAINED","config_sha256":sha(OUT/"frozen_config.json"),"splits_sha256":config["splits_sha256"]}))


def load_config():
    c=json.loads((OUT/"frozen_config.json").read_text())
    if c["outer_seed"]!=42437 or c["threads"]!=8 or c["cpu_seconds"]!=43200: raise ValueError("contract drift")
    for name,digest in c["sources"].items():
        if sha(PROJECT/name)!=digest: raise ValueError("source drift: "+name)
    if sha(OUT/"splits.npz")!=c["splits_sha256"]: raise ValueError("split hash drift")
    current={"python":sys.version.split()[0],"numpy":np.__version__,"pandas":pd.__version__,"sklearn":sklearn.__version__,"lightgbm":lgb.__version__}
    if current!=c["versions"]: raise ValueError("runtime version drift")
    return c


class Budget:
    def __init__(self,config):
        self.config=config; self.path=OUT/"cpu_budget.json"; self.started=time.monotonic()
        prior=json.loads(self.path.read_text()) if self.path.exists() else {"spent_seconds":0.}
        self.prior=float(prior["spent_seconds"])
        self.check()
    def check(self):
        spent=self.prior+time.monotonic()-self.started
        rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        rss=int(rss if sys.platform=="darwin" else rss*1024)
        atomic_json(self.path,{"spent_seconds":spent,"peak_rss_bytes":rss,"pid":os.getpid(),"updated_unix":time.time()})
        if spent>self.config["cpu_seconds"]: raise TimeoutError("cumulative CPU-run wall budget exceeded")
        if rss>self.config["memory_bytes"]: raise MemoryError("peak RSS budget exceeded")
    def callback(self,env):
        if env.iteration%50==0: self.check()


def atom_params(family,contract,atom):
    params=contract["params"].copy()
    for name in contract["seed_fields"]: params[name]=contract["model_seed_base"]+atom
    return params


def fit_atom(backend,fit_rows,fit_y,query_rows,params,te_seed,es_seed,patience,budget=None,selected_iteration=None):
    """No query labels in this API. Early stopping is wholly inside fit_rows."""
    fit_rows=np.asarray(fit_rows,dtype=np.int64); fit_y=np.asarray(fit_y,dtype=np.int8)
    query_rows=np.asarray(query_rows,dtype=np.int64)
    if np.intersect1d(fit_rows,query_rows).size or len(fit_rows)!=len(fit_y): raise ValueError("invalid atom scope")
    s,e=next(StratifiedShuffleSplit(1,test_size=.1,random_state=es_seed).split(np.zeros(len(fit_y)),fit_y))
    scope={"fit_idx_sha256":arr_sha(fit_rows),"query_idx_sha256":arr_sha(query_rows),"fit_y_sha256":arr_sha(fit_y),"early_fit_idx_sha256":arr_sha(fit_rows[s]),"early_valid_idx_sha256":arr_sha(fit_rows[e]),"te_seed":te_seed,"early_stop_seed":es_seed,"query_labels_available":False}
    callbacks=[] if budget is None else [budget.callback]
    if selected_iteration is None:
        xs,xe,names=backend.encode(fit_rows[s],fit_y[s],fit_rows[e],te_seed)
        early=lgb.LGBMClassifier(**params)
        early.fit(xs,fit_y[s],eval_set=[(xe,fit_y[e])],eval_metric="auc",feature_name=names,callbacks=[lgb.early_stopping(patience,verbose=False),lgb.log_evaluation(0),*callbacks])
        selected_iteration=int(early.best_iteration_ or params["n_estimators"])
        del early,xs,xe; gc.collect()
    if budget: budget.check()
    xf,xq,names=backend.encode(fit_rows,fit_y,query_rows,te_seed)
    refit=params.copy(); refit["n_estimators"]=int(selected_iteration)
    model=lgb.LGBMClassifier(**refit)
    model.fit(xf,fit_y,feature_name=names,callbacks=[lgb.log_evaluation(0),*callbacks])
    prediction=model.predict_proba(xq)[:,1]
    if not np.isfinite(prediction).all() or np.any((prediction<0)|(prediction>1)): raise ValueError("invalid predictions")
    scope.update({"selected_iteration":int(selected_iteration),"feature_names":names,"feature_names_sha256":json_sha(names),"params_sha256":json_sha(refit),"final_fit_eval_set_used":False})
    return prediction,scope,model


def verify_atom(directory,config_sha,expected=None):
    meta=json.loads((directory/"manifest.json").read_text())
    if meta["config_sha256"]!=config_sha: raise ValueError("checkpoint config mismatch")
    if sha(directory/"predictions.npz")!=meta["prediction_sha256"]: raise ValueError("checkpoint prediction hash mismatch")
    if sha(directory/"model.txt")!=meta["model_sha256"]: raise ValueError("checkpoint model hash mismatch")
    if expected is not None and any(meta[k]!=v for k,v in expected.items()): raise ValueError("checkpoint scope mismatch")
    with np.load(directory/"predictions.npz",allow_pickle=False) as a:
        for key in ("oof_proba","valid_proba"):
            if not np.isfinite(a[key]).all() or np.any((a[key]<0)|(a[key]>1)): raise ValueError("invalid checkpoint probability")
    return meta


def cpu(outer,family,max_atoms=None,_lock_held=False):
    config=load_config(); config_sha=sha(OUT/"frozen_config.json")
    OUT.mkdir(parents=True,exist_ok=True)
    with (OUT/"cpu.lock").open("a") as lock:
        if not _lock_held:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        budget=Budget(config)
        try:
            with threadpool_limits(limits=8):
                with np.load(OUT/"splits.npz",allow_pickle=False) as a:
                    train=a[f"outer_{outer:02d}_train_idx"]; hold=a[f"outer_{outer:02d}_valid_idx"]; folds=a[f"outer_{outer:02d}_{family}_fold"]
                labels=pd.read_csv(PROJECT/"data/train.csv",usecols=["Will_Buy_EV"]).Will_Buy_EV.eq("Yes").to_numpy(np.int8)[train]
                ids=pd.read_csv(PROJECT/"data/train.csv",usecols=["id"]).id.to_numpy()
                backend=load_backend(family); budget.check()
                contract=config["families"][family]
                trained=0
                for atom in range(1,41):
                    fit_local=np.flatnonzero(folds!=atom-1); valid_local=np.flatnonzero(folds==atom-1)
                    fit_rows=train[fit_local]; oof_rows=train[valid_local]
                    query=np.concatenate([oof_rows,hold])
                    directory=OUT/f"outer_{outer:02d}"/family/f"atom_{atom:02d}"
                    expected={"outer":outer,"family":family,"atom":atom,"fit_idx_sha256":arr_sha(fit_rows),"query_idx_sha256":arr_sha(query),"fit_y_sha256":arr_sha(labels[fit_local])}
                    if (directory/"manifest.json").exists():
                        verify_atom(directory,config_sha,expected)
                        print(f"RESUME outer={outer} family={family} atom={atom}",flush=True)
                        continue
                    if max_atoms is not None and trained>=max_atoms: break
                    directory.mkdir(parents=True,exist_ok=True)
                    start=time.monotonic()
                    prediction,scope,model=fit_atom(backend,fit_rows,labels[fit_local],query,atom_params(family,contract,atom),contract["te_seed_base"]+atom,config["early_stop_seed_base"]+outer*1000+config["early_stop_family_offsets"][family]+atom,contract["early_stopping_rounds"],budget)
                    model_temp=directory/f"model.tmp.{os.getpid()}.txt"
                    model.booster_.save_model(str(model_temp)); os.replace(model_temp,directory/"model.txt")
                    atomic_npz(directory/"predictions.npz",oof_idx=oof_rows,valid_idx=hold,oof_id=ids[oof_rows],valid_id=ids[hold],oof_proba=prediction[:len(oof_rows)],valid_proba=prediction[len(oof_rows):])
                    atomic_json(directory/"manifest.json",{**expected,**scope,"status":"COMPLETE","config_sha256":config_sha,"prediction_sha256":sha(directory/"predictions.npz"),"model_sha256":sha(directory/"model.txt"),"elapsed_seconds":time.monotonic()-start,"outer_hold_labels_used":False})
                    del model,prediction; gc.collect(); trained+=1; budget.check()
                    print(f"COMPLETE outer={outer} family={family} atom={atom} seconds={time.monotonic()-start:.2f}",flush=True)
                assemble_cpu(outer,family,allow_partial=True)
        except Exception as error:
            atomic_json(OUT/f"failure_{time.time_ns()}.json",{"outer":outer,"family":family,"type":type(error).__name__,"error":str(error),"config_sha256":config_sha})
            raise
        finally:
            budget.check()


def assemble_cpu(outer,family,allow_partial=False):
    config=load_config(); config_sha=sha(OUT/"frozen_config.json")
    with np.load(OUT/"splits.npz",allow_pickle=False) as a:
        train=a[f"outer_{outer:02d}_train_idx"]; hold=a[f"outer_{outer:02d}_valid_idx"]; folds=a[f"outer_{outer:02d}_{family}_fold"]
    ids=pd.read_csv(PROJECT/"data/train.csv",usecols=["id"]).id.to_numpy()
    oof=np.full(len(train),np.nan); valid=np.zeros(len(hold)); coverage=np.zeros(len(train),dtype=np.int8); hashes={}
    directory=OUT/f"outer_{outer:02d}"/family
    for atom in range(1,41):
        part=directory/f"atom_{atom:02d}"
        if not (part/"manifest.json").exists():
            if allow_partial: return {"status":"PARTIAL","completed_atoms":len(hashes)}
            raise FileNotFoundError(f"missing atom {atom}")
        verify_atom(part,config_sha)
        local=np.flatnonzero(folds==atom-1)
        with np.load(part/"predictions.npz",allow_pickle=False) as a:
            if not np.array_equal(a["oof_idx"],train[local]) or not np.array_equal(a["valid_idx"],hold): raise ValueError("atom indices do not match frozen partition")
            if not np.array_equal(a["oof_id"],ids[train[local]]) or not np.array_equal(a["valid_id"],ids[hold]): raise ValueError("atom ID mismatch")
            oof[local]=a["oof_proba"]; coverage[local]+=1; valid+=a["valid_proba"]/40
        hashes[str(atom)]=sha(part/"manifest.json")
    if not np.all(coverage==1) or not np.isfinite(oof).all(): raise ValueError("OOF coverage incomplete")
    output=directory/"cache.npz"
    payload=dict(train_idx=train,valid_idx=hold,train_id=ids[train],valid_id=ids[hold],oof_proba=oof,valid_proba=valid,atom_fold=folds)
    if output.exists():
        with np.load(output,allow_pickle=False) as a:
            if set(a.files)!=set(payload) or any(not np.array_equal(a[k],v) for k,v in payload.items()): raise ValueError("existing cache reconstruction mismatch")
    else: atomic_npz(output,**payload)
    result={"status":"CPU_CACHE_COMPLETE","outer":outer,"family":family,"config_sha256":config_sha,"input_sha256":config["sources"]["data/train.csv"],"splits_sha256":config["splits_sha256"],"cache_sha256":sha(output),"train_idx_sha256":arr_sha(train),"valid_idx_sha256":arr_sha(hold),"train_id_sha256":arr_sha(ids[train]),"valid_id_sha256":arr_sha(ids[hold]),"atom_manifest_sha256":hashes,"ctboost_complete":False,"complete_v100_scored":False}
    atomic_json(directory/"cache_manifest.json",result)
    return result


def fit_v100_meta(y_train,v80_oof,v85_oof,ct_oof,v80_valid,v85_valid,ct_valid_fullfit,ct_valid_foldmean):
    """Pure fitting on T labels; caller keeps U labels outside this function."""
    r90=module_at(PROJECT/"model/v90_v89_member_verify_budget_retry/v90_v89_member_verify_budget_retry.py","e2e_meta90")
    r100=module_at(PROJECT/"model/v100_v90_ctboost_nested_cv_blend/v100_v90_ctboost_nested_cv_blend.py","e2e_meta100")
    layer1=r90.run_meta_cv(y_train,v80_oof,v85_oof,v80_valid,v85_valid)
    layer2=r100.nested_blend(y_train,layer1["oof"],ct_oof,layer1["test"],ct_valid_fullfit)
    s90=r100.fit_mid_ecdf(layer1["oof"]); sct=r100.fit_mid_ecdf(ct_oof)
    w=layer2["final_ctboost_weight"]
    b=(1-w)*r100.transform_mid_ecdf(s90,layer1["test"])+w*r100.transform_mid_ecdf(sct,ct_valid_foldmean)
    return {"refit_prediction":layer2["test"],"foldmean_prediction":b,"v90_fold_weights":[r["selected_v85_weight"] for r in layer1["fold_rows"]],"ct_final_weight":w,"outer_hold_labels_used":False}


def cpu_all():
    config=load_config()
    with (OUT/"cpu.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        atomic_json(OUT/"supervisor_state.json",{"status":"RUNNING","pid":os.getpid(),"config_sha256":sha(OUT/"frozen_config.json"),"started_unix":time.time(),"outer_folds":5,"atomic_fits_expected":400,"threads":8,"cpu_seconds":config["cpu_seconds"]})
        print(f"SUPERVISOR_STARTED pid={os.getpid()} config={sha(OUT/'frozen_config.json')} expected_atoms=400",flush=True)
        for outer in range(1,6):
            for family in ("v80","v85"):
                print(f"FAMILY_STARTED outer={outer} family={family}",flush=True)
                cpu(outer,family,_lock_held=True)
        atomic_json(OUT/"supervisor_state.json",{"status":"CPU_CACHE_COMPLETE","pid":os.getpid(),"config_sha256":sha(OUT/"frozen_config.json"),"finished_unix":time.time(),"completed_atoms":400,"complete_v100_scored":False})
        print("CPU_CACHE_COMPLETE atoms=400; CTBoost and E2E scoring remain separate",flush=True)


def main():
    p=argparse.ArgumentParser(); p.add_argument("mode",choices=["freeze","preflight","cpu","cpu-all","assemble-cpu"])
    p.add_argument("--outer",type=int,choices=range(1,6)); p.add_argument("--family",choices=["v80","v85"]); p.add_argument("--max-atoms",type=int)
    a=p.parse_args()
    if a.mode=="freeze": freeze()
    elif a.mode=="preflight":
        c=load_config(); print(json.dumps({"status":"PREFLIGHT_PASS_NOT_TRAINED","sources":len(c["sources"]),"outer_seed":c["outer_seed"],"cpu_seconds":c["cpu_seconds"]}))
    elif a.mode=="cpu-all": cpu_all()
    else:
        if a.outer is None or a.family is None: p.error("--outer and --family required")
        if a.mode=="cpu": cpu(a.outer,a.family,a.max_atoms)
        else: print(json.dumps(assemble_cpu(a.outer,a.family)))


if __name__=="__main__": main()
