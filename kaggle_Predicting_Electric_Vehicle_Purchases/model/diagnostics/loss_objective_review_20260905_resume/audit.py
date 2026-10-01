#!/usr/bin/env python3
"""只读既有OOF的损失机制审查；不拟合模型、不生成新预测。"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "2"

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2]
MODEL = PROJECT / "model"
SPECIALIST = MODEL / "diagnostics/high_intent_specialist_20260905_resume"
V66 = MODEL / "v66_xgb_pairwise_rank_probe"
V67 = MODEL / "v67_auc_class_weight_probe"
GAMMA = 2.0
CLIP = 1e-12


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_json(path, payload):
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("x") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    os.replace(temporary, path)


def analyze():
    started = time.monotonic()
    artifact = SPECIALIST / "diagnostic_predictions.npz"
    previous_evidence = json.loads((SPECIALIST / "evidence.json").read_text())
    assert previous_evidence["status"] == "COMPLETE_DIAGNOSTIC"
    assert sha(artifact) == previous_evidence["artifacts_sha256"]["diagnostic_predictions.npz"]
    frozen = json.loads((SPECIALIST / "frozen_config.json").read_text())
    assert sha(PROJECT / "data/train.csv") == frozen["source_sha256"]["data/train.csv"]
    z = np.load(artifact, allow_pickle=False)
    train = pd.read_csv(PROJECT / "data/train.csv")
    y = z["target"]
    primary = z["primary_slice"]
    original_p = z["global_prediction"]
    assert np.array_equal(y, train.Will_Buy_EV.eq("Yes").to_numpy(np.int8))
    expected_primary = (train.Environmental_Concern_Level.ge(4) & train.Subsidy_Available.eq("Yes") & train.Range_Anxiety_Level.eq("Low")).to_numpy()
    assert np.array_equal(primary, expected_primary)
    assert original_p.shape == y.shape and np.isfinite(original_p).all()
    assert original_p.min() >= 0 and original_p.max() <= 1
    p = np.clip(original_p, CLIP, 1 - CLIP)
    pt = np.where(y == 1, p, 1 - p)
    gradient_bce = 1 - pt
    hessian_bce = p * (1 - p)
    gradient_focal = (1 - pt) ** GAMMA * ((1 - pt) - GAMMA * pt * np.log(pt))
    assert np.isfinite(gradient_focal).all() and (gradient_focal >= 0).all()
    # gamma=0在相同预测点必须退化为BCE的绝对logit梯度。
    assert np.array_equal((1 - pt) ** 0 * ((1 - pt) - 0 * pt * np.log(pt)), gradient_bce)
    scopes = {
        "all_negative": y == 0,
        "easy_negative_pt_ge_0_9": (y == 0) & (pt >= .9),
        "very_easy_negative_pt_ge_0_99": (y == 0) & (pt >= .99),
        "primary_high_intent": primary,
        "correct_confident_pt_ge_0_9": pt >= .9,
        "hard_pt_le_0_5": pt <= .5,
    }
    rows = {}
    for name, mask in scopes.items():
        rows[name] = {
            "rows": int(mask.sum()), "row_share": float(mask.mean()),
            "bce_abs_logit_gradient_share": float(gradient_bce[mask].sum() / gradient_bce.sum()),
            "bce_logit_hessian_share": float(hessian_bce[mask].sum() / hessian_bce.sum()),
            "focal_gamma2_abs_logit_gradient_share": float(gradient_focal[mask].sum() / gradient_focal.sum()),
        }
    bins = []
    for lower, upper in [(0., .1), (.1, .5), (.5, .9), (.9, 1.)]:
        mask = (pt > lower) & (pt <= upper)
        bins.append({"pt_lower_exclusive": lower, "pt_upper_inclusive": upper,
            "rows": int(mask.sum()),
            "bce_abs_logit_gradient_share": float(gradient_bce[mask].sum() / gradient_bce.sum()),
            "focal_gamma2_abs_logit_gradient_share": float(gradient_focal[mask].sum() / gradient_focal.sum())})
    assert sum(row["rows"] for row in bins) == len(y)
    for field in ["bce_abs_logit_gradient_share", "focal_gamma2_abs_logit_gradient_share"]:
        assert abs(sum(row[field] for row in bins) - 1.) < 1e-12
    v67_result = json.loads((V67 / "probe_results.json").read_text())
    v66_files = sorted(p.name for p in V66.iterdir() if p.is_file())
    v66_output_artifacts = [name for name in v66_files if name == "probe_results.json" or name.endswith((".npy", ".npz"))]
    focal_python_matches = []
    focal_scan_count = 0
    for path in MODEL.rglob("*.py"):
        if OUT in path.parents or "__pycache__" in path.parts:
            continue
        focal_scan_count += 1
        for line_no, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            if "focal" in line.lower():
                focal_python_matches.append({"path": str(path.relative_to(PROJECT)), "line": line_no, "text": line.strip()[:250]})
    source_paths = [Path(__file__), artifact, SPECIALIST/"evidence.json", SPECIALIST/"frozen_config.json",
        SPECIALIST/"independent_postrun_audit.json", PROJECT/"data/train.csv",
        V66/"v66_xgb_pairwise_rank_probe.py", V66/"train_log.txt",
        V67/"v67_auc_class_weight_probe.py", V67/"probe_results.json"]
    return {
        "experiment_id": "LOSS_OBJECTIVE_REVIEW_20260905_RESUME", "status": "COMPLETE_READ_ONLY_AUDIT",
        "decision": "NO_GO_NEW_FOCAL_OR_FIXED_CLASS_WEIGHT_TRAINING",
        "evidence_type": "STATIC_GRADIENT_DIAGNOSTIC_ON_EXISTING_CROSSFITTED_PREDICTIONS",
        "input_sha256": {str(path.relative_to(PROJECT)): sha(path) for path in source_paths},
        "input": {"prediction_array": "global_prediction", "target_array": "target", "primary_array": "primary_slice",
            "rows": len(y), "gamma": GAMMA, "clip": CLIP, "clipped_prediction_rows": int((p != original_p).sum())},
        "formulas": {
            "pt": "p if y=1 else 1-p",
            "bce_abs_logit_gradient": "1-pt",
            "bce_logit_hessian": "p*(1-p)",
            "focal_loss": "-((1-pt)**gamma)*log(pt), no extra class alpha",
            "focal_abs_logit_gradient": "((1-pt)**gamma)*((1-pt)-gamma*pt*log(pt))",
            "reported_share": "sum(quantity on scope) / sum(quantity on all rows)"},
        "scope_rows": rows, "pt_bins": bins,
        "history": {
            "v67_class_weights": {"screened_folds": v67_result["screened_folds"], "seed": v67_result["seed"], "summary": v67_result["summary"],
                "boundary": "Only two development folds using legacy v6 inner-prior TE; not strict five-fold evidence and not a definitive universal rejection of class weighting."},
            "v66_pairwise": {"files": v66_files, "present_result_or_prediction_artifacts": v66_output_artifacts,
                "train_log_lines": (V66/"train_log.txt").read_text().splitlines(),
                "status": "NO_USABLE_COMPLETED_RESULT" if not v66_output_artifacts else "REQUIRES_REVIEW",
                "correction": "Do not say pairwise completed and failed to improve. Present files show only startup/iteration0; no usable completed result. Planned validation-weight search would also not be unbiased."},
            "focal_code_search": {"scope": "model/**/*.py excluding this review directory and __pycache__; textual audit only", "files_scanned": focal_scan_count, "matches": focal_python_matches,
                "interpretation": "No focal objective implementation identified in prior reviewed modeling files; absence of a keyword alone is not proof of every conceivable equivalent objective."}},
        "local_specialist_attribution": {key: previous_evidence[key] for key in ["global_delta_b_minus_a", "primary_auc_delta_b_minus_a", "pair_contribution_b_minus_a", "cross_group_net_gain"]},
        "reasoning": [
            "Easy negatives are numerous but carry only about 6.5% of remaining BCE absolute gradient at fixed OOF predictions; this does not support the overwhelming-easy-negatives mechanism.",
            "The primary slice already carries about 65% of BCE gradient/Hessian, and gamma2 focal barely changes its aggregate gradient share. Focal mainly emphasizes incorrectly predicted points without evidence that they are learnable or repair cross-group ordering.",
            "A strictly increasing transform of final probabilities preserves AUC exactly. A monotone reshaping of each loss can alter optimization and must not be confused with prediction postprocessing.",
            "Fixed class reweighting changes probability estimates; finite-capacity ranking could change but the legacy v67 screen gives no stable new mechanism signal.",
            "Pairwise remains unconfirmed, not a demonstrated failure; local error cancellation alone does not establish a sufficient new reason to launch it now."],
        "external_primary_sources": [
            {"title": "Focal Loss for Dense Object Detection", "url": "https://arxiv.org/abs/1708.02002", "supports": "Focal downweights well-classified examples to address easy-negative dominance in dense detection."},
            {"title": "On Focal Loss for Class-Posterior Probability Estimation: A Theoretical Perspective", "url": "https://arxiv.org/abs/2011.09172", "supports": "Focal is classification-calibrated but not strictly proper for posterior estimation."},
            {"title": "LightGBM 4.6.0 Parameters - scale_pos_weight", "url": "https://lightgbm.readthedocs.io/en/v4.6.0/Parameters.html#scale_pos_weight", "supports": "Fixed positive class weighting can distort individual class probability estimates."},
            {"title": "XGBoost Learning to Rank - Loss", "url": "https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html#loss", "supports": "rank:pairwise is RankNet/pairwise logistic, not NDCG-scaled loss; pairs are sampled within query."}],
        "future_cost_if_new_evidence_emerges": {"proposal_only_not_authorization": True, "max_wall_seconds": 1200, "threads": 4, "memory_gib": 8,
            "requirements": ["analytic gradient/Hessian and finite-difference checks", "gamma=0 equivalence with BCE", "fixed gamma and no alpha sweep", "five-fold paired control plus exact cross-group accounting"],
            "cost_boundary": "Budget cap is untested for a custom objective, not a runtime guarantee."},
        "limitations": [
            "Static gradient/Hessian evaluation on converged OOF probabilities is not the actual per-iteration training trajectory or split allocation.",
            "These OOF predictions have already been used for development; this review is not independent confirmation.",
            "Overlapping scopes are not additive; only pt_bins form a disjoint exhaustive partition.",
            "No new model, weight fitting, test prediction or submission was performed."],
        "validation": {"canonical_target_and_primary_mask": "PASS", "prediction_sha_matches_prior_evidence": "PASS", "gamma0_equals_bce_gradient": "PASS", "pt_bin_row_and_gradient_share_conservation": "PASS"},
        "runtime": {"elapsed_seconds": time.monotonic()-started, "numpy":np.__version__, "threads":2},
        "allowed_for_fusion": False, "allowed_for_submission": False,
    }


def readme(e):
    labels = {"all_negative":"全部负样本", "easy_negative_pt_ge_0_9":"容易负样本，pt≥0.9", "very_easy_negative_pt_ge_0_99":"极容易负样本，pt≥0.99", "primary_high_intent":"固定高意向主切片", "correct_confident_pt_ge_0_9":"正确且较确信，pt≥0.9", "hard_pt_le_0_5":"难点，pt≤0.5"}
    lines = ["# 损失目标只读审查", "", "**NO_GO：不新开 Focal loss 或固定类别权重训练。** Pairwise 历史证据纠正为未完成、没有可用结论；也不据此硬开新分支。", "", "下表在已完成局部专家诊断的全局A五折OOF固定预测点计算，pt为真实类别的预测概率。不是训练轨迹，不声称还原各轮梯度或树分裂。", "", "| 范围 | 行占比 | BCE绝对logit梯度占比 | BCE Hessian占比 | Focal γ=2绝对logit梯度占比 |", "|---|---:|---:|---:|---:|"]
    for key,row in e["scope_rows"].items():
        lines.append(f"| {labels[key]} | {row['row_share']:.2%} | {row['bce_abs_logit_gradient_share']:.2%} | {row['bce_logit_hessian_share']:.2%} | {row['focal_gamma2_abs_logit_gradient_share']:.3%} |")
    lines.extend(["", "主切片已占BCE梯度/Hessian约65%；Focal主要把注意力进一步移向难点，没有证据这些点可学习或能修复跨组排序。局部专家的组内收益对总体AUC只贡献 +0.0000060151，跨组抵消 -0.0000011261，不能推出应当换损失。", "", "v67确实测试了scale_pos_weight=1.5/2/3/4.726，但只有旧非严格TE的2折。最好均值 +0.0000206304、1/2折胜；平衡权重4.726为 -0.0000428175、0/2折胜。v66只找到脚本、两行启动/iteration0日志，没有结果JSON或预测文件；不能再写成完整pairwise实验无增益。源码路径和SHA、搜索范围与结果均在evidence.json。", "", "严格递增的最终概率变换保持AUC不变；逐样本loss的单调重塑可能改变有限模型的优化，两者不能混淆。当前结论是缺乏针对本数据的机制依据，不是声称Focal在任何问题都不可能有效。", "", "外部依据仅使用论文与官方文档："])
    for source in e["external_primary_sources"]:
        lines.append(f"- [{source['title']}]({source['url']})：{source['supports']}")
    lines.extend(["", "重算：`/opt/anaconda3/bin/python audit.py --verify`，从本目录运行即可。程序核对输入SHA和原始train标签/固定门控，计算完整梯度表；不训练、不改预测。`evidence.json`保存公式、全部输入SHA、历史纠正、资源代价与限制。", "", "未来只有出现新机制证据时才考虑固定gamma的严格五折A/B：需梯度/Hessian有限差分检查、gamma=0等价校验和精确跨组贡献检查；可预先封顶1200秒、4线程、8GiB，该上限未经自定义损失实测，当前不构成开跑授权。", ""])
    return "\n".join(lines)


if __name__ == "__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--verify",action="store_true");args=parser.parse_args()
    result=analyze()
    if args.verify:
        saved=json.loads((OUT/"evidence.json").read_text())
        for key in ["input_sha256", "input", "formulas", "scope_rows", "pt_bins", "local_specialist_attribution", "validation"]:
            assert result[key]==saved[key],key
        print(json.dumps({"status":"RECOMPUTE_PASS","evidence_sha256":sha(OUT/"evidence.json"),"rows":result["input"]["rows"]},ensure_ascii=False))
    else:
        assert not (OUT/"evidence.json").exists(), "历史证据不覆盖"
        atomic_json(OUT/"evidence.json",result)
        (OUT/"README.md").write_text(readme(result))
        print(json.dumps({"status":result["status"],"decision":result["decision"],"evidence_sha256":sha(OUT/"evidence.json"),"runtime":result["runtime"]},ensure_ascii=False))
