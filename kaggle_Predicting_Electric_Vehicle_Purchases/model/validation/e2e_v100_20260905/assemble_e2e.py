#!/usr/bin/env python3
"""Pre-registered complete-cache assembly. See ASSEMBLY_PREREGISTRATION.md.

No partial outer scores. Meta receives T labels only. The independent score
entrypoint is gated by all 15 caches plus independent two-layer reconstruction.
"""
from __future__ import annotations
import os
for _key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","VECLIB_MAXIMUM_THREADS","NUMEXPR_NUM_THREADS"):
    os.environ[_key]="2"
import argparse
import json
import resource
import time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from threadpoolctl import threadpool_limits
import cpu_runner as cpu
for _key in ("OMP_NUM_THREADS","OPENBLAS_NUM_THREADS","MKL_NUM_THREADS","VECLIB_MAXIMUM_THREADS","NUMEXPR_NUM_THREADS","BLIS_NUM_THREADS"):
    os.environ[_key]="2"

OUT=Path(__file__).resolve().parent
PROJECT=OUT.parents[2]
GPU=OUT/"gpu/remote_output/ct_cache"
GPU_SOURCE=OUT/"gpu/revision_01"
ASSEMBLED=OUT/"assembled"
SHARED=PROJECT/"model/research_runtime/paired_auc.py"


def required_files():
    files=[GPU/"GPU_COMPLETE.json",OUT/"gpu/remote_output/GPU_RUN_RESULT.json",OUT/"supervisor_state.json",OUT/"cpu_budget.json"]
    for outer in range(1,6):
        for family in ("v80","v85"):
            directory=OUT/f"outer_{outer:02d}"/family
            files += [directory/"cache.npz",directory/"cache_manifest.json"]
        files += [GPU/f"outer_{outer:02d}/cache.npz",GPU/f"outer_{outer:02d}/cache_manifest.json"]
    return files


def missing_files():
    return [str(p.relative_to(OUT)) for p in required_files() if not p.is_file()]


def insist_complete():
    missing=missing_files()
    if missing: raise FileNotFoundError("NOT_READY: "+", ".join(missing))


def freeze():
    dest=OUT/"assembly_config.json"
    if dest.exists(): raise FileExistsError("assembly contract already frozen")
    sources=[Path(__file__),OUT/"test_assemble_e2e.py",OUT/"ASSEMBLY_PREREGISTRATION.md",OUT/"cpu_runner.py",OUT/"frozen_config.json",OUT/"splits.npz",GPU_SOURCE/"frozen_config.json",GPU_SOURCE/"bundle_manifest.json",GPU_SOURCE/"kernel/kernel-metadata.json",OUT/"gpu/PUSH_RECEIPT.json",SHARED]
    cpu.load_config()
    config={"experiment_id":"E2E_V100_COMPLETE_ASSEMBLY_20260905","sources":{str(p.relative_to(PROJECT)):cpu.sha(p) for p in sources},"research_delta":.0001,"required_positive_folds":5,"submission_rebuild_delta_strictly_above":0.,"is_new_blind_test":False,"wall_budget_seconds":1800,"peak_rss_bytes":16*1024**3,"threads":2,"actual_test_predictions_generated":False,"submission_budget":0}
    cpu.atomic_json(dest,config)
    return {"status":"ASSEMBLY_FROZEN_UNSCORED","sha256":cpu.sha(dest)}


def config():
    c=json.loads((OUT/"assembly_config.json").read_text())
    for name,digest in c["sources"].items():
        if cpu.sha(PROJECT/name)!=digest: raise ValueError("assembly source drift: "+name)
    if c["research_delta"]!=.0001 or c["required_positive_folds"]!=5: raise ValueError("score gate drift")
    cpu.load_config()
    return c


def guard(started,c):
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if rss>c["peak_rss_bytes"]: raise MemoryError("assembly RSS budget")
    if time.monotonic()-started>c["wall_budget_seconds"]: raise TimeoutError("assembly wall budget")


def read_npz(path):
    with np.load(path,allow_pickle=False) as a: return {k:a[k] for k in a.files}


def probability(x,n,dtype=None):
    x=np.asarray(x)
    if x.shape!=(n,) or not np.isfinite(x).all() or np.any((x<0)|(x>1)): raise ValueError("invalid probability vector")
    if dtype is not None and x.dtype!=np.dtype(dtype): raise ValueError("prediction precision mismatch")


def validate_arrays(a,train,hold,official_ids,folds,ct=False):
    prediction_keys={"oof_proba","valid_proba_fullfit","valid_proba_foldmean"} if ct else {"oof_proba","valid_proba"}
    if set(a)!={"train_idx","valid_idx","train_id","valid_id","atom_fold"}|prediction_keys: raise ValueError("cache schema mismatch")
    expected={"train_idx":train,"valid_idx":hold,"train_id":official_ids[train],"valid_id":official_ids[hold],"atom_fold":folds}
    for name,value in expected.items():
        if a[name].dtype.kind not in "iu" or not np.array_equal(a[name],value): raise ValueError("cache identity mismatch: "+name)
    probability(a["oof_proba"],len(train),"float32" if ct else "float64")
    for name in prediction_keys-{"oof_proba"}: probability(a[name],len(hold),"float64")


def check_cpu(directory,outer,family,train,hold,ids,folds,config_sha,input_sha,splits_sha):
    a=read_npz(directory/"cache.npz"); m=json.loads((directory/"cache_manifest.json").read_text())
    if m["status"]!="CPU_CACHE_COMPLETE" or m["outer"]!=outer or m["family"]!=family: raise ValueError("CPU cache status mismatch")
    if m["config_sha256"]!=config_sha or m["input_sha256"]!=input_sha or m["splits_sha256"]!=splits_sha: raise ValueError("CPU source mismatch")
    if m["cache_sha256"]!=cpu.sha(directory/"cache.npz"): raise ValueError("CPU cache SHA mismatch")
    validate_arrays(a,train,hold,ids,folds)
    for name,values in (("train_idx",train),("valid_idx",hold),("train_id",ids[train]),("valid_id",ids[hold])):
        if m[name+"_sha256"]!=cpu.arr_sha(values): raise ValueError("CPU manifest identity mismatch")
    oof=np.full(len(train),np.nan); valid=np.zeros(len(hold)); coverage=np.zeros(len(train),dtype=np.int8)
    for atom in range(1,41):
        part=directory/f"atom_{atom:02d}"
        if cpu.sha(part/"manifest.json")!=m["atom_manifest_sha256"][str(atom)]: raise ValueError("CPU atom manifest changed")
        local=np.flatnonzero(folds==atom-1); fit=np.flatnonzero(folds!=atom-1)
        expected={"outer":outer,"family":family,"atom":atom,"fit_idx_sha256":cpu.arr_sha(train[fit]),"query_idx_sha256":cpu.arr_sha(np.concatenate([train[local],hold]))}
        record=cpu.verify_atom(part,config_sha,expected)
        if record["query_labels_available"] or record["final_fit_eval_set_used"] or record["outer_hold_labels_used"]: raise ValueError("CPU label boundary flags failed")
        z=read_npz(part/"predictions.npz")
        if set(z)!={"oof_idx","valid_idx","oof_id","valid_id","oof_proba","valid_proba"}: raise ValueError("CPU atom schema mismatch")
        for key,expect in (("oof_idx",train[local]),("valid_idx",hold),("oof_id",ids[train[local]]),("valid_id",ids[hold])):
            if not np.array_equal(z[key],expect): raise ValueError("CPU atom identity mismatch")
        probability(z["oof_proba"],len(local),"float64"); probability(z["valid_proba"],len(hold),"float64")
        oof[local]=z["oof_proba"]; coverage[local]+=1; valid+=z["valid_proba"]/40
    if not np.all(coverage==1) or not np.array_equal(oof,a["oof_proba"]) or not np.array_equal(valid,a["valid_proba"]): raise ValueError("CPU cache reconstruction mismatch")
    return a


def check_ct(directory,train,hold,ids,folds,gpu_config,gpu_sha):
    a=read_npz(directory/"cache.npz"); m=json.loads((directory/"cache_manifest.json").read_text())
    if m["status"]!="CT_CACHE_COMPLETE_UNSCORED" or m["validation_labels_used"] or m["allowed_for_submission"]: raise ValueError("CT status/boundary mismatch")
    identity={"train_idx_sha256":cpu.arr_sha(train),"valid_idx_sha256":cpu.arr_sha(hold),"train_id_sha256":cpu.arr_sha(ids[train]),"valid_id_sha256":cpu.arr_sha(ids[hold]),"config_sha256":gpu_sha}
    if m["identity"]!=identity or m["source_sha256"]!=gpu_config["source_sha256"]: raise ValueError("CT source identity mismatch")
    if m["cache_sha256"]!=cpu.sha(directory/"cache.npz") or m["atom_fold_sha256"]!=cpu.arr_sha(folds): raise ValueError("CT cache SHA mismatch")
    validate_arrays(a,train,hold,ids,folds,ct=True)
    oof=np.full(len(train),np.nan,dtype=np.float32); valid=np.zeros(len(hold)); coverage=np.zeros(len(train),dtype=np.int8)
    if len(m["atoms"])!=5: raise ValueError("CT atom count mismatch")
    for atom in range(1,6):
        record=json.loads((directory/f"atom_{atom:02d}.json").read_text())
        if record!=m["atoms"][atom-1] or record.get("atom")!=atom or record["identity"]!=identity or record["sha256"]!=cpu.sha(directory/f"atom_{atom:02d}.npz"): raise ValueError("CT atom source mismatch")
        z=read_npz(directory/f"atom_{atom:02d}.npz"); local=np.flatnonzero(folds==atom-1); fit=np.flatnonzero(folds!=atom-1)
        if set(z)!={"fit_idx","hold_idx","valid_idx","oof_proba","valid_proba"}: raise ValueError("CT atom schema mismatch")
        for key,expect in (("fit_idx",train[fit]),("hold_idx",train[local]),("valid_idx",hold)):
            if not np.array_equal(z[key],expect): raise ValueError("CT atom indices mismatch")
        probability(z["oof_proba"],len(local)); probability(z["valid_proba"],len(hold))
        oof[local]=z["oof_proba"]; coverage[local]+=1; valid+=z["valid_proba"]/5
    record=json.loads((directory/"fullfit.json").read_text()); full=read_npz(directory/"fullfit.npz")
    if record!=m["fullfit"] or record["identity"]!=identity or record["sha256"]!=cpu.sha(directory/"fullfit.npz"): raise ValueError("CT fullfit SHA mismatch")
    if set(full)!={"valid_idx","valid_proba"} or not np.array_equal(full["valid_idx"],hold): raise ValueError("CT fullfit indices mismatch")
    probability(full["valid_proba"],len(hold))
    if not np.all(coverage==1) or not np.array_equal(oof,a["oof_proba"]) or not np.array_equal(valid,a["valid_proba_foldmean"]) or not np.array_equal(full["valid_proba"],a["valid_proba_fullfit"]): raise ValueError("CT cache reconstruction mismatch")
    return a


def load_checked_outer(outer,cpu_config,gpu_config,ids,splits):
    train=splits[f"outer_{outer:02d}_train_idx"]; hold=splits[f"outer_{outer:02d}_valid_idx"]
    pairs={}
    for family in ("v80","v85"):
        pairs[family]=check_cpu(OUT/f"outer_{outer:02d}"/family,outer,family,train,hold,ids,splits[f"outer_{outer:02d}_{family}_fold"],cpu.sha(OUT/"frozen_config.json"),cpu_config["sources"]["data/train.csv"],cpu_config["splits_sha256"])
    pairs["ct"]=check_ct(GPU/f"outer_{outer:02d}",train,hold,ids,splits[f"outer_{outer:02d}_ct_fold"],gpu_config,cpu.sha(GPU_SOURCE/"frozen_config.json"))
    return pairs,train,hold


def require_supervisors(state,budget,gpu_result,cpu_config_sha):
    if state.get("status")!="CPU_CACHE_COMPLETE" or state.get("completed_atoms")!=400 or state.get("config_sha256")!=cpu_config_sha or state.get("complete_v100_scored") is not False: raise ValueError("CPU supervisor not successfully complete")
    if state.get("pid")!=budget.get("pid"): raise ValueError("CPU budget belongs to another supervisor")
    spent=budget.get("spent_seconds",float("nan")); peak=budget.get("peak_rss_bytes",float("nan"))
    if not np.isfinite(spent) or not 0<=spent<=43200 or not np.isfinite(peak) or not 0<peak<=24*1024**3: raise ValueError("CPU final budget failed")
    seconds=gpu_result.get("seconds",float("nan")); gp=gpu_result.get("peak_process_tree_rss",float("nan"))
    if gpu_result.get("status")!="GPU_CACHE_RUN_COMPLETE" or not np.isfinite(seconds) or not 0<=seconds<7200 or not np.isfinite(gp) or not 0<gp<=24*1024**3: raise ValueError("GPU supervisor failed or exceeded final budget")
    checks=gpu_result.get("resource_checks",[])
    if not checks or checks[-1].get("phase")!="BEFORE_COMPLETE" or checks[-1].get("seconds")!=seconds: raise ValueError("GPU final boundary check missing")
    expected={"START","BEFORE_bootstrap.py","AFTER_EXIT_bootstrap.py","AFTER_CLEANUP_bootstrap.py","BEFORE_cache_runner.py","AFTER_EXIT_cache_runner.py","AFTER_CLEANUP_cache_runner.py","BEFORE_COMPLETE"}
    if not expected.issubset({row.get("phase") for row in checks}): raise ValueError("GPU stage budget checks incomplete")
    for row in checks:
        if not 0<=row["seconds"]<=seconds or not 0<row["rss_bytes"]<=row["peak_process_tree_rss"]<=gp: raise ValueError("GPU stage budget check inconsistent")


def inputs():
    insist_complete()
    cc=cpu.load_config(); gc=json.loads((GPU_SOURCE/"frozen_config.json").read_text())
    require_supervisors(json.loads((OUT/"supervisor_state.json").read_text()),json.loads((OUT/"cpu_budget.json").read_text()),json.loads((OUT/"gpu/remote_output/GPU_RUN_RESULT.json").read_text()),cpu.sha(OUT/"frozen_config.json"))
    receipt=json.loads((OUT/"gpu/PUSH_RECEIPT.json").read_text())
    metadata=json.loads((GPU_SOURCE/"kernel/kernel-metadata.json").read_text())
    if receipt["returncode"]!=0 or receipt["status"]!="PUSH_RETURNED" or receipt["kernel"]!=metadata["id"] or "Kernel version 1 successfully pushed." not in receipt["stdout"]: raise ValueError("GPU push receipt invalid")
    if receipt["config_sha256"]!=cpu.sha(GPU_SOURCE/"frozen_config.json") or receipt["bundle_manifest_sha256"]!=cpu.sha(GPU_SOURCE/"bundle_manifest.json"): raise ValueError("GPU receipt source mismatch")
    for name,digest in gc["code_sha256"].items():
        if cpu.sha(GPU_SOURCE/name)!=digest: raise ValueError("GPU code source drift")
    done=json.loads((GPU/"GPU_COMPLETE.json").read_text())
    if done["status"]!="CT_CACHE_COMPLETE_UNSCORED" or done["config_sha256"]!=cpu.sha(GPU_SOURCE/"frozen_config.json") or len(done["outer_results"])!=5 or done["submission_created"]: raise ValueError("GPU global completion invalid")
    if gc["source_sha256"]["train.csv"]!=cc["sources"]["data/train.csv"] or gc["outer_seed"]!=42437: raise ValueError("GPU/CPU inputs differ")
    if gc["source_sha256"]["original.csv"]!=cc["sources"]["data/original_dataset/EV_Adoption_and_Range_Anxiety_Dataset.csv"] or gc["source_sha256"]["historical_ct_notebook"]!=cc["sources"]["model/diagnostics/ctboost_remote_probe_20260905/kernel/s6e9-ctboost-oof-audit.ipynb"]: raise ValueError("GPU/CPU original or CT recipe source differs")
    ids=pd.read_csv(PROJECT/"data/train.csv",usecols=["id"]).id.to_numpy()
    splits=read_npz(OUT/"splits.npz")
    return cc,gc,ids,splits


def audit_all():
    c=config(); started=time.monotonic(); cc,gc,ids,splits=inputs()
    for outer in range(1,6):
        load_checked_outer(outer,cc,gc,ids,splits); guard(started,c)
    snapshot={"status":"ALL_15_CACHES_REBUILT_UNSCORED","assembly_config_sha256":cpu.sha(OUT/"assembly_config.json"),"files":{str(p.relative_to(OUT)):cpu.sha(p) for p in required_files()},"outer_labels_scored":False}
    dest=OUT/"cache_snapshot.json"
    if dest.exists() and json.loads(dest.read_text())!=snapshot: raise ValueError("frozen cache snapshot changed")
    if not dest.exists(): cpu.atomic_json(dest,snapshot)
    return snapshot


def check_snapshot():
    snap=json.loads((OUT/"cache_snapshot.json").read_text())
    if snap["assembly_config_sha256"]!=cpu.sha(OUT/"assembly_config.json"): raise ValueError("snapshot contract drift")
    for name,digest in snap["files"].items():
        if cpu.sha(OUT/name)!=digest: raise ValueError("cache snapshot source drift")
    return cpu.sha(OUT/"cache_snapshot.json")


def training_labels(rows):
    return pd.read_csv(PROJECT/"data/train.csv",usecols=["Will_Buy_EV"]).Will_Buy_EV.eq("Yes").to_numpy(np.int8)[rows]


def meta_inputs(y,pairs):
    return (y,pairs["v80"]["oof_proba"],pairs["v85"]["oof_proba"],pairs["ct"]["oof_proba"].astype(np.float64),pairs["v80"]["valid_proba"],pairs["v85"]["valid_proba"],pairs["ct"]["valid_proba_fullfit"],pairs["ct"]["valid_proba_foldmean"])


def independent_meta(y,a,b,ct,qa,qb,qct_full,qct_mean):
    """Independent numerical implementation; never calls original meta methods."""
    def apply(sorted_fit,query):
        return (np.searchsorted(sorted_fit,query,"left")+np.searchsorted(sorted_fit,query,"right"))/(2.*len(sorted_fit))
    q=np.zeros(len(y)); query=np.zeros(len(qa)); weights=[]
    grid=[round(i*.05,2) for i in range(21)]
    for fit,hold in StratifiedKFold(5,shuffle=True,random_state=42).split(np.zeros(len(y)),y):
        sa,sb=np.sort(a[fit]),np.sort(b[fit])
        af,bf=apply(sa,a[fit]),apply(sb,b[fit])
        scores=[float(roc_auc_score(y[fit],(1-w)*af+w*bf)) for w in grid]
        best=max(scores)
        w=min([w for w,s in zip(grid,scores) if abs(s-best)<=1e-15],key=lambda w:(abs(w-.5),w))
        weights.append(w)
        q[hold]=(1-w)*apply(sa,a[hold])+w*apply(sb,b[hold])
        query+=((1-w)*apply(sa,qa)+w*apply(sb,qb))/5
    sq,sc=np.sort(q),np.sort(ct)
    qrank,crank=apply(sq,q),apply(sc,ct)
    grid=np.arange(0.,.5000001,.025)
    scores=[float(roc_auc_score(y,(1-w)*qrank+w*crank)) for w in grid]
    ix=max(range(len(grid)),key=lambda i:(scores[i],-grid[i])); w=float(grid[ix])
    base=(1-w)*apply(sq,query)
    return {"refit_prediction":base+w*apply(sc,qct_full),"foldmean_prediction":base+w*apply(sc,qct_mean),"v90_fold_weights":weights,"ct_final_weight":w,"outer_hold_labels_used":False}


def assemble():
    c=config(); started=time.monotonic(); audit_all(); snapshot=check_snapshot()
    cc,gc,ids,splits=inputs()
    for outer in range(1,6):
        pairs,train,hold=load_checked_outer(outer,cc,gc,ids,splits)
        result=cpu.fit_v100_meta(*meta_inputs(training_labels(train),pairs))
        directory=ASSEMBLED/f"outer_{outer:02d}"; path=directory/"predictions.npz"
        arrays={"valid_idx":hold,"valid_id":ids[hold],"baseline_proba":result["refit_prediction"],"candidate_proba":result["foldmean_prediction"]}
        if path.exists():
            prior=read_npz(path)
            if set(prior)!=set(arrays) or any(not np.array_equal(prior[k],v) for k,v in arrays.items()): raise ValueError("existing assembled prediction mismatch")
        else: cpu.atomic_npz(path,**arrays)
        cpu.atomic_json(directory/"manifest.json",{"status":"ASSEMBLED_UNSCORED","outer":outer,"assembly_config_sha256":cpu.sha(OUT/"assembly_config.json"),"cache_snapshot_sha256":snapshot,"prediction_sha256":cpu.sha(path),"v90_fold_weights":result["v90_fold_weights"],"ct_final_weight":result["ct_final_weight"],"outer_hold_labels_used":False})
        guard(started,c)
    check_snapshot()
    return {"status":"ALL_OUTER_PREDICTIONS_ASSEMBLED_UNSCORED","outer_folds":5}


def verify_all():
    c=config(); started=time.monotonic(); audit_all(); snapshot=check_snapshot()
    cc,gc,ids,splits=inputs(); rows=[]
    for outer in range(1,6):
        directory=ASSEMBLED/f"outer_{outer:02d}"; path=directory/"predictions.npz"
        prior=read_npz(path); manifest=json.loads((directory/"manifest.json").read_text())
        if manifest["assembly_config_sha256"]!=cpu.sha(OUT/"assembly_config.json") or manifest["cache_snapshot_sha256"]!=snapshot or manifest["prediction_sha256"]!=cpu.sha(path) or manifest["outer_hold_labels_used"]: raise ValueError("assembled source mismatch")
        pairs,train,hold=load_checked_outer(outer,cc,gc,ids,splits)
        if set(prior)!={"valid_idx","valid_id","baseline_proba","candidate_proba"} or not np.array_equal(prior["valid_idx"],hold) or not np.array_equal(prior["valid_id"],ids[hold]): raise ValueError("assembled identity mismatch")
        expected=independent_meta(*meta_inputs(training_labels(train),pairs))
        for field in ("v90_fold_weights","ct_final_weight"):
            if manifest[field]!=expected[field]: raise ValueError("independent meta weights differ")
        errors={}
        for field,rebuild in (("baseline_proba","refit_prediction"),("candidate_proba","foldmean_prediction")):
            probability(prior[field],len(hold)); errors[field]=float(np.max(np.abs(prior[field]-expected[rebuild])))
            if errors[field]>1e-12: raise ValueError("independent meta reconstruction differs")
        rows.append({"outer":outer,"max_abs_errors":errors,"prediction_sha256":cpu.sha(path),"manifest_sha256":cpu.sha(directory/"manifest.json")}); guard(started,c)
    check_snapshot()
    result={"status":"INDEPENDENT_RECONSTRUCTION_PASS_UNSCORED","assembly_config_sha256":cpu.sha(OUT/"assembly_config.json"),"cache_snapshot_sha256":snapshot,"outer_rows":rows,"outer_labels_scored":False,"elapsed_seconds":time.monotonic()-started}
    cpu.atomic_json(OUT/"independent_reconstruction.json",result)
    return result


def score_vectors(y,baseline,candidate,folds,independent_pass):
    if not independent_pass: raise ValueError("independent verification required")
    if set(np.unique(folds))!={1,2,3,4,5}: raise ValueError("all five outer folds required")
    shared=cpu.module_at(SHARED,"e2e_shared_paired_auc")
    report=shared.paired_auc(y,baseline,candidate,folds)
    for field,pred in (("baseline_auc",baseline),("candidate_auc",candidate)):
        if abs(report[field]-roc_auc_score(y,pred))>1e-12: raise ValueError("independent sklearn AUC mismatch")
    for row in report["folds"]:
        selected=folds==row["fold"]
        for field,pred in (("baseline_auc",baseline),("candidate_auc",candidate)):
            if abs(row[field]-roc_auc_score(y[selected],pred[selected]))>1e-12: raise ValueError("fold sklearn AUC mismatch")
    report.update({"research_promotion_gate_passed":bool(report["delta"]>=.0001 and report["positive_folds"]==5),"submission_candidate_rebuild_gate_passed":bool(report["delta"]>0 and report["positive_folds"]==5),"allowed_for_submission":False,"actual_test_predictions_generated":False,"independent_reconstruction_passed":True,"is_new_blind_test":False})
    return report


def score():
    if (OUT/"e2e_results.json").exists(): raise FileExistsError("results already exist; preserve original score evidence")
    c=config(); started=time.monotonic(); verification=verify_all()
    insist_complete(); check_snapshot()
    ids=pd.read_csv(PROJECT/"data/train.csv",usecols=["id"]).id.to_numpy()
    baseline=np.full(len(ids),np.nan); candidate=np.full(len(ids),np.nan); coverage=np.zeros(len(ids),dtype=np.int8)
    with np.load(OUT/"splits.npz",allow_pickle=False) as a: folds=a["outer_fold"]
    for row in verification["outer_rows"]:
        path=ASSEMBLED/f"outer_{row['outer']:02d}/predictions.npz"
        if cpu.sha(path)!=row["prediction_sha256"]: raise ValueError("prediction changed after verification")
        a=read_npz(path); idx=a["valid_idx"]
        if not np.array_equal(a["valid_id"],ids[idx]): raise ValueError("score ID mismatch")
        baseline[idx]=a["baseline_proba"]; candidate[idx]=a["candidate_proba"]; coverage[idx]+=1
    if not np.all(coverage==1): raise ValueError("global OOF coverage invalid")
    # First use of all U labels for the endpoint is here, after complete verification.
    y=pd.read_csv(PROJECT/"data/train.csv",usecols=["Will_Buy_EV"]).Will_Buy_EV.eq("Yes").to_numpy(np.int8)
    result=score_vectors(y,baseline,candidate,folds,True)
    result.update({"status":"COMPLETE_E2E_CONFIRMATION_ONLY","baseline":"V100_E2E_CT_FULLREFIT","candidate":"V100_E2E_CT_FOLDMEAN","assembly_config_sha256":cpu.sha(OUT/"assembly_config.json"),"independent_reconstruction_sha256":cpu.sha(OUT/"independent_reconstruction.json"),"cache_snapshot_sha256":cpu.sha(OUT/"cache_snapshot.json")})
    guard(started,c)
    if (OUT/"e2e_results.json").exists(): raise FileExistsError("results already exist; preserve original score evidence")
    cpu.atomic_json(OUT/"e2e_results.json",result)
    return result


def main():
    p=argparse.ArgumentParser(); p.add_argument("mode",choices=["freeze","status","audit","assemble","verify","score"]); args=p.parse_args()
    if args.mode=="status": print(json.dumps({"status":"NOT_READY" if missing_files() else "FILES_PRESENT_AUDIT_REQUIRED","missing":missing_files(),"partial_scores_computed":False})); return
    with threadpool_limits(limits=2):
        result={"freeze":freeze,"audit":audit_all,"assemble":assemble,"verify":verify_all,"score":score}[args.mode]()
    print(json.dumps(result,ensure_ascii=False))


if __name__=="__main__": main()
