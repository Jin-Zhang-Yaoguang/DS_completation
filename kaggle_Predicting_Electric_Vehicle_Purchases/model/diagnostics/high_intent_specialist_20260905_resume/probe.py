#!/usr/bin/env python3
"""固定高意向切片专家：严格五折配对诊断，禁止入池或提交。"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import resource
import signal
import sys
import time
from pathlib import Path

for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "4"

import lightgbm as lgb
import numpy as np
import sklearn
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2]
MODEL = PROJECT / "model"
V96 = MODEL / "v96_strict_v80_outer42_matched_control_40f"
V96_RUNNER = V96 / "v96_strict_v80_outer42_matched_control_40f.py"
V100 = MODEL / "v100_v90_ctboost_nested_cv_blend"
ALPHA = 0.25
TIME_LIMIT = 1200
MEMORY_LIMIT = 8 * 1024**3
EXPERIMENT_ID = "HIGH_INTENT_SPECIALIST_20260905_RESUME"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, obj):
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("x") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    os.replace(tmp, path)


def atomic_npz(path, **arrays):
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with tmp.open("xb") as f:
        np.savez_compressed(f, **arrays)
    os.replace(tmp, path)


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    obj = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj


def gate(frame):
    return (frame.Environmental_Concern_Level.ge(4) & frame.Subsidy_Available.eq("Yes")
            & frame.Range_Anxiety_Level.eq("Low")).to_numpy(dtype=bool)


def candidate_prediction(global_prediction, expert_prediction, primary):
    result = np.array(global_prediction, dtype=np.float64, copy=True)
    assert len(expert_prediction) == int(primary.sum())
    result[primary] = (1 - ALPHA) * result[primary] + ALPHA * expert_prediction
    assert np.array_equal(result[~primary], global_prediction[~primary])
    return result


def error_count(pos, neg):
    ordered = np.sort(neg)
    return float((len(neg) - (np.searchsorted(ordered,pos,"left") + np.searchsorted(ordered,pos,"right")) * 0.5).sum())


def contributions(y, pred, primary):
    positive, negative = y == 1, y == 0
    denominator = int(positive.sum()) * int(negative.sum())
    parts = {}
    for name, pmask, nmask in (
        ("primary_within", primary, primary),
        ("positive_primary_negative_other", primary, ~primary),
        ("positive_other_negative_primary", ~primary, primary),
        ("other_within", ~primary, ~primary),
    ):
        p, n = pred[positive & pmask], pred[negative & nmask]
        pairs = len(p) * len(n)
        mistakes = error_count(p,n)
        parts[name] = {"pairs": pairs, "errors": mistakes, "global_error_mass": mistakes/denominator,
                       "conditional_auc": 1-mistakes/pairs if pairs else None}
    auc = 1 - sum(x["errors"] for x in parts.values()) / denominator
    assert abs(auc-roc_auc_score(y,pred)) < 1e-12
    return {"auc": auc, "parts": parts}


def contract():
    cfg = json.loads((V96 / "frozen_config.json").read_text())
    params = dict(cfg["lightgbm_params"])
    params["n_jobs"] = 4
    paths = [Path(__file__), OUT/"preregistration.json", V96_RUNNER, V96/"frozen_config.json",
        MODEL/"v29_income_bin10_te_lgbm/v29_income_bin10_te_lgbm.py",
        MODEL/"v6_multiscale_te_lgbm/v6_multiscale_te_lgbm.py",
        PROJECT/"data/train.csv", PROJECT/"data/test.csv", PROJECT/"data/sample_submission.csv",
        V100/"cv_results.json", V100/"sources.json", V100/"oof_proba.npy",
        MODEL/"research_runtime/paired_auc.py"]
    hashes = {str(p.relative_to(PROJECT)): sha(p) for p in paths}
    cv100 = json.loads((V100/"cv_results.json").read_text())
    assert hashes[str((V100/"oof_proba.npy").relative_to(PROJECT))] == cv100["artifact_sha256"]["oof_proba.npy"]
    data_source = json.loads((V100/"sources.json").read_text())["source_sha256"]
    for filename in ["train.csv","test.csv","sample_submission.csv"]:
        assert hashes["data/"+filename] == data_source[filename]
    assert lgb.__version__ == cfg["required_lightgbm_version"]
    assert cfg["expected_total_features"] == 113 and cfg["n_inner_folds"] == 5
    assert cfg["early_stopping_rounds"] == 500
    return {"experiment_id": EXPERIMENT_ID, "alpha": ALPHA, "outer_folds":5,"outer_seed":42,
        "params_both_models": params, "early_stopping_rounds":500,
        "inner_te_seed_base": cfg["inner_te_seed_base"], "smooths":cfg["smooths"],
        "feature_count":113, "source_sha256":hashes,
        "runtime":{"python":sys.version.split()[0],"numpy":np.__version__,"sklearn":sklearn.__version__,"lightgbm":lgb.__version__},
        "budget":{"wall_seconds_total":TIME_LIMIT,"cpu_threads":4,"memory_bytes":MEMORY_LIMIT},
        "allowed_for_fusion":False,"allowed_for_submission":False,"test_predictions":False,
        "gate":{"delta":0.0001,"positive_folds":4,"primary_auc_positive":True}}


def smoke():
    source = module(V96_RUNNER,"specialist_smoke_source")
    source.strict_prior_self_check()
    rng = np.random.default_rng(87123)
    x = rng.normal(size=(400,113)).astype(np.float32)
    y = ((x[:,0] + 0.4*x[:,1]) > 0).astype(np.int8)
    primary = np.arange(400)%2 == 0
    fit, valid = np.arange(300), np.arange(300,400)
    params = dict(n_estimators=5,num_leaves=7,min_child_samples=2,n_jobs=4,verbosity=-1,random_state=42)
    a = lgb.LGBMClassifier(**params).fit(x[fit],y[fit])
    expert = lgb.LGBMClassifier(**params).fit(x[fit][primary[fit]],y[fit][primary[fit]])
    pa = a.predict_proba(x[valid])[:,1]
    pe = expert.predict_proba(x[valid][primary[valid]])[:,1]
    pb = candidate_prediction(pa,pe,primary[valid])
    assert np.array_equal(pb[~primary[valid]],pa[~primary[valid]])
    assert np.allclose(pb[primary[valid]],0.75*pa[primary[valid]]+0.25*pe,rtol=0,atol=0)
    contributions(y[valid],pb,primary[valid])
    tiny_y=np.array([1,0,1,0,1,0]); tiny_p=np.array([.8,.8,.2,.1,.3,.9]);tiny_gate=np.array([1,1,1,0,0,0],dtype=bool)
    parts=contributions(tiny_y,tiny_p,tiny_gate)
    brute=np.mean([float(p>n)+.5*float(p==n) for p in tiny_p[tiny_y==1] for n in tiny_p[tiny_y==0]])
    assert abs(parts["auc"]-brute)<1e-12
    payload={"status":"SMOKE_PASS_SYNTHETIC_ONLY","strict_inner_prior":"PASS","113_feature_subset_fit":"PASS",
        "outside_gate_bitwise_identity":"PASS","fixed_alpha":"PASS","pair_mass_ties_and_conservation":"PASS",
        "real_data_training":False,"runner_sha256":sha(Path(__file__))}
    atomic_json(OUT/"smoke_results.json",payload)
    return payload


def freeze():
    assert not (OUT/"frozen_config.json").exists(), "已冻结，不覆盖"
    s=json.loads((OUT/"smoke_results.json").read_text())
    assert s["status"]=="SMOKE_PASS_SYNTHETIC_ONLY" and s["runner_sha256"]==sha(Path(__file__))
    c=contract()
    atomic_json(OUT/"frozen_config.json",c)
    return {"status":"FROZEN_NOT_STARTED","config_sha256":sha(OUT/"frozen_config.json"),"runner_sha256":sha(Path(__file__))}


def resources(started):
    mem=int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*(1 if sys.platform=="darwin" else 1024)
    elapsed=time.time()-started
    return {"elapsed_seconds_total":elapsed,"peak_rss_bytes":mem,"threads":4}


def guard(started):
    r=resources(started)
    if r["elapsed_seconds_total"]>=TIME_LIMIT or r["peak_rss_bytes"]>=MEMORY_LIMIT:
        raise RuntimeError("RESOURCE_BUDGET: "+json.dumps(r))
    return r


def training_guard(started):
    def callback(env):
        if env.iteration%25==0:
            guard(started)
    callback.order=5
    callback.before_iteration=True
    return callback


def build_fold(source,recipe,cfg,frame,keys_train,keys_test,y,fit_idx,valid_idx,fold):
    inner=list(StratifiedKFold(5,shuffle=True,random_state=cfg["inner_te_seed_base"]+fold).split(np.zeros(len(fit_idx)),y[fit_idx]))
    fit_te,valid_te=[],[]
    for key in recipe.base.TE_KEYS:
        a,b,_=source.strict_encode_key(keys_train[key],keys_test[key],y,fit_idx,valid_idx,inner,tuple(cfg["smooths"]))
        fit_te.append(a);valid_te.append(b)
    fit=np.column_stack([frame.iloc[fit_idx].to_numpy(np.float32),*fit_te])
    valid=np.column_stack([frame.iloc[valid_idx].to_numpy(np.float32),*valid_te])
    assert fit.shape[1]==valid.shape[1]==113
    return fit,valid


def finish_report(y,primary,a,b,fold_ids,rows,resource_state,cfg_hash):
    v100=np.load(V100/"oof_proba.npy",allow_pickle=False).astype(np.float64)
    exact={name:contributions(y,p,primary) for name,p in [("a_global",a),("b_specialist_mix",b),("v100_development",v100)]}
    delta=exact["b_specialist_mix"]["auc"]-exact["a_global"]["auc"]
    primary_delta=exact["b_specialist_mix"]["parts"]["primary_within"]["conditional_auc"]-exact["a_global"]["parts"]["primary_within"]["conditional_auc"]
    wins=sum(r["global_delta_b_minus_a"]>0 for r in rows)
    gain={key:exact["a_global"]["parts"][key]["global_error_mass"]-exact["b_specialist_mix"]["parts"][key]["global_error_mass"] for key in exact["a_global"]["parts"]}
    assert abs(sum(gain.values())-delta)<1e-12
    passed=delta>=0.0001 and wins>=4 and primary_delta>0
    diagnostic=OUT/"diagnostic_predictions.npz"
    atomic_npz(diagnostic,target=y,primary_slice=primary,fold=fold_ids,global_prediction=a,candidate_prediction=b,
        evidence_type=np.array("DIAGNOSTIC_ONLY_NOT_ELIGIBLE_FOR_FUSION_OR_SUBMISSION"),frozen_config_sha256=np.array(cfg_hash))
    checkpoint_hashes={str(p.relative_to(OUT)):sha(p) for p in sorted((OUT/"checkpoints").glob("fold_*.npz"))}
    paired=module(MODEL/"research_runtime/paired_auc.py","specialist_paired_auc")
    uncertainty={"b_vs_a_global":paired.paired_auc(y,a,b,fold_ids),
        "b_vs_a_primary":paired.paired_auc(y[primary],a[primary],b[primary],fold_ids[primary]),
        "b_vs_v100_development_only":paired.paired_auc(y,v100,b,fold_ids)}
    evidence={"experiment_id":EXPERIMENT_ID,"status":"COMPLETE_DIAGNOSTIC","decision":"GO_FOR_NEW_PREREGISTRATION_ONLY" if passed else "NO_GO",
        "frozen_config_sha256":cfg_hash,"completed_folds":5,"global_delta_b_minus_a":delta,"positive_folds":wins,
        "primary_auc_delta_b_minus_a":primary_delta,"pair_contribution_b_minus_a":gain,
        "cross_group_net_gain":gain["positive_primary_negative_other"]+gain["positive_other_negative_primary"],
        "exact":exact,"fold_results":rows,"resource":resource_state,"conditional_paired_auc":uncertainty,
        "validation":{"outside_primary_bitwise_identity":bool(np.array_equal(a[~primary],b[~primary])),"oof_coverage":"PASS","pair_conservation_vs_auc":"PASS","source_frozen_contract":"PASS"},
        "artifacts_sha256":{"diagnostic_predictions.npz":sha(diagnostic),**checkpoint_hashes},
        "allowed_for_fusion":False,"allowed_for_submission":False,"test_predictions":False,
        "comparison_limit":"v100为历史开发OOF、训练量不同；其差异只作同掩码诊断，不用于alpha或参数选择。"}
    atomic_json(OUT/"evidence.json",evidence)
    lines=["# 固定高意向局部专家诊断","",f"决策：**{evidence['decision']}**。五折配对总体增量 `{delta:+.10f}`，正向折 `{wins}/5`；主切片组内增量 `{primary_delta:+.10f}`。所有预测只供诊断，不可入池或提交。","",
        "| 模型 | 总体 AUC | 主切片组内 AUC |","|---|---:|---:|"]
    for name,x in exact.items():
        lines.append(f"| {name} | {x['auc']:.10f} | {x['parts']['primary_within']['conditional_auc']:.10f} |")
    lines.extend(["","| 正负对范围 | 对总体 AUC 增量的贡献 |","|---|---:|"])
    for name,value in gain.items():lines.append(f"| {name} | {value:+.10f} |")
    lines.extend(["",f"跨组两方向合计 `{evidence['cross_group_net_gain']:+.10f}`；区域外预测逐元素不变。资源：{resource_state['elapsed_seconds_total']:.1f}秒，peak RSS {resource_state['peak_rss_bytes']/1024**3:.3f}GiB，4线程。","",
        f"总体B-A条件配对SE `{uncertainty['b_vs_a_global']['conditional_standard_error']:.10f}`，95%区间 `{uncertainty['b_vs_a_global']['conditional_ci95']}`。它仅描述给定预测的样本不确定性，不包括OOF训练重叠、早停、选模或历史开发，不能替代独立确认或改变预注册门槛。","",
        "预注册机制只改变专家训练支持；A和专家共用113特征与完整outer-fit内严格TE。固定主切片为环保等级>=4、有补贴、低里程焦虑；其中B=0.75*A+0.25*expert，区域外B=A。专家早停在同outer-valid的主切片上进行，故不能分离局部训练支持与局部早停各自贡献；也未证明相对于等计算全局bagging的优越性。","",
        "v100为历史开发OOF、训练量不同，仅提供同掩码比较。本诊断不得调alpha、追加树参数搜索或直接提交。若NO_GO，保留失败方向；若GO，也只允许另立完整验证预注册。",""])
    (OUT/"README.md").write_text("\n".join(lines))
    return evidence


def run(resume=False):
    lock=(OUT/"run.lock").open("a+")
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert not (OUT/"evidence.json").exists(), "最终证据已存在，禁止同配置重跑"
    cfg=json.loads((OUT/"frozen_config.json").read_text())
    assert cfg==contract(), "冻结合同漂移"
    cfg_hash=sha(OUT/"frozen_config.json")
    marker=OUT/"RUN_STARTED.json"
    if marker.exists():
        assert resume, "已有运行标记，需显式resume且不得重复实例"
        state=json.loads(marker.read_text());assert state["frozen_config_sha256"]==cfg_hash
    else:
        assert not resume
        state={"pid":os.getpid(),"started_unix":time.time(),"frozen_config_sha256":cfg_hash}
        atomic_json(marker,state)
    started=state["started_unix"]
    (OUT/"checkpoints").mkdir(exist_ok=True)
    rows=[]
    try:
        guard(started)
        signal.signal(signal.SIGALRM,lambda *_: (_ for _ in ()).throw(TimeoutError("1200秒总预算达到")))
        signal.alarm(max(1,int(TIME_LIMIT-(time.time()-started))))
        source=module(V96_RUNNER,"specialist_v96_source")
        source.strict_prior_self_check()
        recipe=source.load_recipe()
        train,test,_=recipe.base.load_data()
        y=train.Will_Buy_EV.eq("Yes").to_numpy(np.int8)
        primary=gate(train)
        static,_,keys_train,keys_test=recipe.base.build_static_features(train,test)
        assert static.shape==(len(y),62)
        a=np.full(len(y),np.nan);b=np.full(len(y),np.nan);fold_ids=np.full(len(y),-1,dtype=np.int8)
        for fold,(fit_idx,valid_idx) in enumerate(StratifiedKFold(5,shuffle=True,random_state=42).split(static,y),1):
            checkpoint=OUT/"checkpoints"/f"fold_{fold:02d}.npz"
            pf,pv=primary[fit_idx],primary[valid_idx]
            if checkpoint.exists():
                z=np.load(checkpoint,allow_pickle=False)
                assert str(z["frozen_config_sha256"])==cfg_hash and np.array_equal(z["valid_idx"],valid_idx)
                assert np.array_equal(z["target"],y[valid_idx]) and np.array_equal(z["primary_slice"],pv)
                pa,pe,pb=z["global_prediction"],z["expert_prediction_on_primary"],z["candidate_prediction"]
                assert np.array_equal(pb,candidate_prediction(pa,pe,pv))
                row=json.loads(str(z["fold_metadata_json"]))
            else:
                guard(started)
                x_fit,x_valid=build_fold(source,recipe,cfg,static,keys_train,keys_test,y,fit_idx,valid_idx,fold)
                row={"fold":fold,"fit_rows":len(fit_idx),"valid_rows":len(valid_idx),"expert_fit_rows":int(pf.sum()),"expert_valid_rows":int(pv.sum()),"inner_te_seed":cfg["inner_te_seed_base"]+fold}
                outputs={}
                for name,xx,yy,xv,yv in [("global",x_fit,y[fit_idx],x_valid,y[valid_idx]),
                                       ("expert",x_fit[pf],y[fit_idx][pf],x_valid[pv],y[valid_idx][pv])]:
                    guard(started)
                    model=lgb.LGBMClassifier(**cfg["params_both_models"])
                    model.fit(xx,yy,eval_set=[(xv,yv)],eval_metric="auc",callbacks=[training_guard(started),lgb.early_stopping(500,verbose=False),lgb.log_evaluation(0)])
                    outputs[name]=model.predict_proba(xv,num_iteration=model.best_iteration_)[:,1]
                    row[f"{name}_best_iteration"]=int(model.best_iteration_)
                    del model
                pa,pe=outputs["global"],outputs["expert"]
                pb=candidate_prediction(pa,pe,pv)
                for p in [pa,pe,pb]:assert np.isfinite(p).all() and p.min()>=0 and p.max()<=1
                row.update({"global_auc_a":float(roc_auc_score(y[valid_idx],pa)),"global_auc_b":float(roc_auc_score(y[valid_idx],pb)),
                    "primary_auc_a":float(roc_auc_score(y[valid_idx][pv],pa[pv])),"primary_auc_b":float(roc_auc_score(y[valid_idx][pv],pb[pv])),
                    "expert_primary_auc":float(roc_auc_score(y[valid_idx][pv],pe))})
                row["global_delta_b_minus_a"]=row["global_auc_b"]-row["global_auc_a"]
                row["primary_delta_b_minus_a"]=row["primary_auc_b"]-row["primary_auc_a"]
                row["resource"]=guard(started)
                atomic_npz(checkpoint,valid_idx=valid_idx,target=y[valid_idx],primary_slice=pv,
                    global_prediction=pa,expert_prediction_on_primary=pe,candidate_prediction=pb,
                    fold_metadata_json=np.array(json.dumps(row)),frozen_config_sha256=np.array(cfg_hash),
                    evidence_type=np.array("DIAGNOSTIC_ONLY_NOT_ELIGIBLE_FOR_FUSION_OR_SUBMISSION"))
                del x_fit,x_valid,outputs
            a[valid_idx]=pa;b[valid_idx]=pb;fold_ids[valid_idx]=fold-1;rows.append(row)
            print(json.dumps(row,ensure_ascii=False),flush=True)
            guard(started)
        assert np.isfinite(a).all() and np.isfinite(b).all() and (fold_ids>=0).all()
        assert cfg==contract(), "运行中来源变更"
        result=finish_report(y,primary,a,b,fold_ids,rows,guard(started),cfg_hash)
        guard(started)
        signal.alarm(0)
        return {k:v for k,v in result.items() if k not in ["fold_results","exact","artifacts_sha256"]}
    except BaseException as error:
        signal.alarm(0)
        failure={"experiment_id":EXPERIMENT_ID,"status":"FAILED_DIAGNOSTIC","error_type":type(error).__name__,"error":str(error),
            "frozen_config_sha256":cfg_hash,"completed_folds":len(rows),"fold_results":rows,"resource":resources(started),
            "checkpoint_paths":[str(p.relative_to(OUT)) for p in sorted((OUT/"checkpoints").glob("fold_*.npz"))],
            "allowed_for_fusion":False,"allowed_for_submission":False,"diagnostic_arrays_invalid_for_formal_use":True}
        atomic_json(OUT/"evidence.json",failure)
        (OUT/"README.md").write_text(f"# 固定高意向局部专家诊断\n\n状态：FAILED_DIAGNOSTIC。{type(error).__name__}: {error}\n\n已保留 {len(rows)} 折记录及checkpoint，所有预测仅作失败诊断，禁止入池或提交。详见 evidence.json。\n")
        raise
    finally:
        fcntl.flock(lock,fcntl.LOCK_UN);lock.close()


def verify():
    cfg=json.loads((OUT/"frozen_config.json").read_text());assert cfg==contract()
    e=json.loads((OUT/"evidence.json").read_text());assert e["status"]=="COMPLETE_DIAGNOSTIC"
    for name,digest in e["artifacts_sha256"].items():assert sha(OUT/name)==digest,name
    z=np.load(OUT/"diagnostic_predictions.npz",allow_pickle=False)
    assert str(z["frozen_config_sha256"])==sha(OUT/"frozen_config.json")
    assert np.array_equal(z["global_prediction"][~z["primary_slice"]],z["candidate_prediction"][~z["primary_slice"]])
    for name,key in [("a_global","global_prediction"),("b_specialist_mix","candidate_prediction")]:
        assert abs(roc_auc_score(z["target"],z[key])-e["exact"][name]["auc"])<1e-12
    return {"status":"VERIFY_PASS","decision":e["decision"],"evidence_sha256":sha(OUT/"evidence.json")}


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("command",choices=["audit","smoke","freeze","run","verify"]);parser.add_argument("--resume",action="store_true")
    args=parser.parse_args()
    result={"audit":contract,"smoke":smoke,"freeze":freeze,"run":lambda:run(args.resume),"verify":verify}[args.command]()
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
