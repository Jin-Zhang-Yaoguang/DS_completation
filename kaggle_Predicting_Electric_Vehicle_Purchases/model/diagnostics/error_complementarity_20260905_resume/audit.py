#!/usr/bin/env python3
"""已有 OOF 的固定切片错序审计；不训练、不调权、不产生候选预测。"""
from __future__ import annotations

import hashlib
import json
import os
import resource
import signal
import sys
import time
from pathlib import Path

for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "2"

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2]
STARTED = time.monotonic()
MODELS = ("v80", "v85", "ctboost", "v90", "v100")


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def budget():
    seconds = time.monotonic() - STARTED
    memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform != "darwin":
        memory *= 1024
    assert seconds <= 120 and memory < 4 * 1024**3, (seconds, memory)
    return {"elapsed_seconds": seconds, "peak_rss_bytes": memory, "threads": 2}


def atomic_json(path, obj):
    temp = path.with_suffix(".tmp")
    with temp.open("x") as stream:
        json.dump(obj, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    os.replace(temp, path)


def pair_errors(positive, negative):
    """逐正样本的错序负样本数，等分数计半错。"""
    neg = np.sort(negative)
    left = np.searchsorted(neg, positive, side="left")
    right = np.searchsorted(neg, positive, side="right")
    return len(neg) - (left + right) * 0.5


def exact_metrics(y, pred, partitions):
    positive = y == 1
    negative = ~positive
    npos, nneg = int(positive.sum()), int(negative.sum())
    denominator = npos * nneg
    ep = pair_errors(pred[positive], pred[negative])
    sorted_pos = np.sort(pred[positive])
    en = (np.searchsorted(sorted_pos, pred[negative], side="left")
          + np.searchsorted(sorted_pos, pred[negative], side="right")) * 0.5
    total_errors = float(ep.sum())
    assert abs(total_errors - en.sum()) < 0.01
    auc = 1 - total_errors / denominator
    assert abs(auc - roc_auc_score(y, pred)) < 1e-12
    result = {"auc": auc, "pair_error_count": total_errors, "total_pairs": denominator,
              "partitions": {}}
    for partition, labels in partitions.items():
        rows = {}
        inside_errors = 0.0
        inside_pairs = 0
        for label in np.unique(labels):
            in_group = labels == label
            gp, gn = in_group[positive], in_group[negative]
            a, b = int(gp.sum()), int(gn.sum())
            local_pairs = a * b
            local_errors = float(pair_errors(pred[positive][gp], pred[negative][gn]).sum()) if local_pairs else 0.0
            pos_inside_errors = float(ep[gp].sum()) - local_errors
            neg_inside_errors = float(en[gn].sum()) - local_errors
            row = {
                "rows": a + b, "positive_rows": a, "negative_rows": b,
                "within_auc": 1 - local_errors / local_pairs if local_pairs else None,
                "within_pairs": local_pairs,
                "within_pair_error_count": local_errors,
                "within_global_error_mass": local_errors / denominator,
                "within_share_of_global_errors": local_errors / total_errors,
                "positive_inside_negative_outside_global_error_mass": pos_inside_errors / denominator,
                "positive_outside_negative_inside_global_error_mass": neg_inside_errors / denominator,
                "cross_global_error_mass": (pos_inside_errors + neg_inside_errors) / denominator,
            }
            rows[str(label)] = row
            inside_errors += local_errors
            inside_pairs += local_pairs
        result["partitions"][partition] = {
            "groups": rows,
            "within_global_error_mass": inside_errors / denominator,
            "across_global_error_mass": (total_errors - inside_errors) / denominator,
            "within_pair_fraction": inside_pairs / denominator,
            "within_share_of_global_errors": inside_errors / total_errors,
        }
    return result


def sampled_complementarity(y, predictions, mask, seed):
    positive = np.flatnonzero((y == 1) & mask)
    negative = np.flatnonzero((y == 0) & mask)
    rng = np.random.default_rng(seed)
    a = rng.choice(positive, size=250000, replace=True)
    b = rng.choice(negative, size=250000, replace=True)
    errors = {}
    for name, pred in predictions.items():
        errors[name] = (pred[a] < pred[b]).astype(float) + 0.5 * (pred[a] == pred[b])
    base = errors["v100"]
    rows = {}
    for name, error in errors.items():
        repaired = np.maximum(base - error, 0)
        broken = np.maximum(error - base, 0)
        rows[name] = {
            "sample_auc": 1 - float(error.mean()),
            "repair_pair_mass_vs_v100": float(repaired.mean()),
            "break_pair_mass_vs_v100": float(broken.mean()),
            "net_auc_gain_vs_v100": float((base - error).mean()),
            "fraction_v100_error_mass_repaired": float(repaired.sum() / base.sum()),
            "shared_error_mass": float(np.minimum(base, error).mean()),
        }
    return {"pairs": len(a), "seed": seed, "sampling": "uniform labelled positive-negative pairs with replacement; diagnostic Monte Carlo only", "models": rows}


def main():
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("120秒预算已到")))
    signal.alarm(120)
    assert not (OUT / "evidence.json").exists(), "历史证据不覆盖"
    prereg = json.loads((OUT / "preregistration.json").read_text())
    train_path = PROJECT / "data/train.csv"
    train = pd.read_csv(train_path)
    y = train.Will_Buy_EV.eq("Yes").to_numpy(dtype=np.int8)
    folds = np.full(len(y), -1, dtype=np.int8)
    for i, (_, idx) in enumerate(StratifiedKFold(5, shuffle=True, random_state=42).split(np.zeros(len(y)), y)):
        folds[idx] = i
    manifest = {"train.csv": sha(train_path), "preregistration.json": sha(OUT / "preregistration.json"), "audit.py": sha(Path(__file__))}
    predictions = {}
    for name in ("v80", "v85", "v90", "v100"):
        directory = next((PROJECT / "model").glob(name + "_*"))
        cv_path = directory / "cv_results.json"
        cv = json.loads(cv_path.read_text())
        path = directory / "oof_proba.npy"
        actual_hash = sha(path)
        expected = cv["artifact_sha256"].get("oof_proba.npy", cv["artifact_sha256"].get("oof_proba"))
        assert actual_hash == expected, (name, "OOF哈希不符")
        predictions[name] = np.load(path).astype(np.float64)
        manifest[name] = {"path": str(path.relative_to(PROJECT)), "oof_sha256": actual_hash, "cv_sha256": sha(cv_path), "source_expected_auc": cv["oof_auc"]}
    ct_path = PROJECT / "model/diagnostics/ctboost_remote_probe_20260905/remote_output/oof.npz"
    ct = np.load(ct_path)
    expected_ct_hash = json.loads((PROJECT / "model/v100_v90_ctboost_nested_cv_blend/sources.json").read_text())["source_sha256"]["ct_oof"]
    assert sha(ct_path) == expected_ct_hash
    assert np.array_equal(ct["id"], train.id.to_numpy())
    assert np.array_equal(ct["target"], y)
    assert np.array_equal(ct["fold"], folds)
    predictions["ctboost"] = ct["prediction"].astype(np.float64)
    manifest["ctboost"] = {"path": str(ct_path.relative_to(PROJECT)), "oof_sha256": sha(ct_path), "row_id_target_fold_check": "PASS"}
    predictions = {name: predictions[name] for name in MODELS}
    for name, pred in predictions.items():
        assert pred.shape == y.shape and np.isfinite(pred).all() and pred.min() >= 0 and pred.max() <= 1, name
    env = train.Environmental_Concern_Level
    primary = env.isin([4, 5]) & train.Subsidy_Available.eq("Yes") & train.Range_Anxiety_Level.eq("Low")
    frequency = train.Annual_Income_USD.map(train.Annual_Income_USD.value_counts())
    partitions = {
        "primary": np.where(primary, "primary", "other"),
        "income_equals_30000": np.where(train.Annual_Income_USD.eq(30000), "30000", "other"),
        "income_frequency": pd.cut(frequency, bins=[0,9,99,499,np.inf], labels=["1-9", "10-99", "100-499", "500+"]).astype(str).to_numpy(),
        "environment_by_subsidy": (env.astype(str) + "|" + train.Subsidy_Available).to_numpy(),
        "anxiety_by_home_charging": (train.Range_Anxiety_Level + "|" + train.Home_Charging_Possible).to_numpy(),
    }
    scopes = {}
    for scope_index in range(6):
        scope = "pooled" if scope_index == 0 else f"seed42_bucket_{scope_index}"
        take = np.ones(len(y), dtype=bool) if scope_index == 0 else folds == scope_index - 1
        yy = y[take]
        pp = {name: value[take] for name, value in predictions.items()}
        gg = {name: value[take] for name, value in partitions.items()}
        exact = {name: exact_metrics(yy, pred, gg) for name, pred in pp.items()}
        scopes[scope] = {"rows": int(take.sum()), "exact": exact,
            "sampled_pairs": {
                "whole": sampled_complementarity(yy, pp, np.ones(len(yy), dtype=bool), 424242 + scope_index * 10),
                "primary": sampled_complementarity(yy, pp, primary.to_numpy()[take], 424243 + scope_index * 10),
            }}
        print(scope, {k: round(v["auc"], 10) for k,v in exact.items()}, flush=True)
        budget()
    pooled = scopes["pooled"]["exact"]
    primary100 = pooled["v100"]["partitions"]["primary"]["groups"]["primary"]
    summary = {}
    for name in MODELS:
        local = pooled[name]["partitions"]["primary"]["groups"]["primary"]
        local_deltas = []
        for i in range(1,6):
            e = scopes[f"seed42_bucket_{i}"]["exact"]
            local_deltas.append(e[name]["partitions"]["primary"]["groups"]["primary"]["within_auc"] - e["v100"]["partitions"]["primary"]["groups"]["primary"]["within_auc"])
        summary[name] = {
            "global_auc": pooled[name]["auc"],
            "primary_within_auc": local["within_auc"],
            "primary_within_delta_vs_v100": local["within_auc"] - primary100["within_auc"],
            "primary_global_weighted_gain_vs_v100": primary100["within_global_error_mass"] - local["within_global_error_mass"],
            "primary_bucket_deltas_vs_v100": local_deltas,
            "primary_positive_buckets_vs_v100": sum(d > 0 for d in local_deltas),
            "local_expert_signal_gate": name in ("v80","v85","ctboost") and local["within_auc"] - primary100["within_auc"] >= 0.0001 and sum(d > 0 for d in local_deltas) >= 4,
        }
    local_go = any(r["local_expert_signal_gate"] for r in summary.values())
    representation_priority = primary100["within_share_of_global_errors"] >= 0.25
    resource_state = budget()
    evidence = {
        "experiment_id": prereg["experiment_id"], "status": "COMPLETE",
        "evidence_type": prereg["evidence_type"], "sources": manifest,
        "validation": {"source_oof_hashes": "PASS", "ct_row_ids_targets_and_seed42_folds": "PASS", "exact_auc_vs_sklearn": "PASS", "pair_error_conservation": "PASS", "new_weights_or_predictions": False},
        "summary": summary,
        "primary_v100": primary100,
        "decision": {"local_expert_from_existing_predictions": "GO_FOR_NEW_PREREGISTRATION_ONLY" if local_go else "NO_GO", "new_representation_diagnostic_priority": representation_priority, "no_model_promotion_or_submission": True},
        "scopes": scopes, "resource": resource_state,
        "limitations": ["这是已反复使用OOF上的诊断，不能把后续切片或模型选择视为新验证。", "5个seed42桶用于同一行子集比较，各基模型原有外层训练折并不相同。", "组内AUC不能代替总体AUC；跨组顺序可能抵消局部增益。", "抽样互补统计存在Monte Carlo误差；精确净增量以exact字段为准。", "有错误可修不等于能在不看标签时识别这些错误，必须另立严格训练验证。"]}
    atomic_json(OUT / "evidence.json", evidence)
    lines = ["# 固定切片错序与互补性审计", "", "本报告只分析已有 OOF，不训练、不调权、不产生新预测。预注册见 `preregistration.json`；可复跑程序为 `audit.py`，完整分桶及贡献见 `evidence.json`。", "", "| 模型 | 全体 AUC | 主切片组内 AUC | 相对 v100 主切片增量 | 正向桶 |", "|---|---:|---:|---:|---:|"]
    for name,r in summary.items():
        lines.append(f"| {name} | {r['global_auc']:.10f} | {r['primary_within_auc']:.10f} | {r['primary_within_delta_vs_v100']:+.10f} | {r['primary_positive_buckets_vs_v100']}/5 |")
    lines.extend(["", f"主切片为环保等级 4/5、有补贴、低里程焦虑，共 {primary100['rows']:,} 行，正样本 {primary100['positive_rows']:,}。v100 在该切片组内错序占全体正负对错序的 {primary100['within_share_of_global_errors']:.2%}，全体 AUC 错序质量贡献 {primary100['within_global_error_mass']:.8f}。", "", f"既有原子预测直接支持局部专家的门槛：{'通过，只可另立新预注册' if local_go else 'NO_GO，不能据此创建局部换权候选'}。新表示诊断优先级：{'有：主切片错序集中超过预注册 25%' if representation_priority else '无：主切片未达到错序集中门槛'}。", "", "`within_global_error_mass` 是该组内错序对数除以全体正负对数；两类 cross 字段分别计算正样本在组内、负样本在组外以及相反方向，因此能检查局部排序与跨组排序的取舍。多分组的 within/across 总质量严格守恒；二值切片的跨组对在两个组说明中重复出现，不得再把组说明相加。", "", "下一项可证伪假设：若预注册主切片确有错序集中，则用同一全局严格模型作控制，仅改变该区间的收入值表示或专家容量，并以连续、折内校准的残差输出保留跨组排序；必须在全新的嵌套验证内检验总体 AUC 与跨组净贡献，不能直接依据本报告切换原子预测或调局部权重。若没有浓度和一致局部信号，则关闭局部专家方向。", "", f"校验：来源 OOF SHA、CTBoost ID/目标/seed42 fold、概率合法性、精确 AUC 对照和错序贡献守恒均通过。耗时 {resource_state['elapsed_seconds']:.2f} 秒，peak RSS {resource_state['peak_rss_bytes']/1024**3:.3f} GiB，2线程；未修改注册表或历史文件。", "", "局限：这些数据已用于历史选模，本诊断不能变成新的无偏 CV 结论；5个seed42桶不是所有模型相同训练折。抽样修复/破坏率只描述互补性，不能证明推理时能够识别哪对样本应由哪个模型负责。", ""])
    (OUT / "README.md").write_text("\n".join(lines))
    print(json.dumps({"summary": summary, "primary_v100": primary100, "decision": evidence['decision'], "resource": resource_state}, ensure_ascii=False, indent=2), flush=True)
    signal.alarm(0)


if __name__ == "__main__":
    main()
