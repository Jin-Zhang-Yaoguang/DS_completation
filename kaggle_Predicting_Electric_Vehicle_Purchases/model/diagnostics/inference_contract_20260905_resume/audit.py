#!/usr/bin/env python3
"""Only inspect frozen predictions; never train, persist predictions, or submit."""
from __future__ import annotations

import os
for _key in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_key] = "2"

import argparse
import hashlib
import json
import resource
import signal
import sys
import time
from pathlib import Path

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2]
NAMES = {
    "v80": "v80_strict_v61_outer104395303_40f",
    "v85": "v85_naji_v74_40f",
    "v90": "v90_v89_member_verify_budget_retry",
    "v100": "v100_v90_ctboost_nested_cv_blend",
}
Q = [0, .0001, .001, .01, .05, .1, .25, .5, .75, .9, .95, .99, .999, .9999, 1]


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_new(path, value):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")


def paths():
    found = {"train": "data/train.csv", "test": "data/test.csv"}
    for name, directory in NAMES.items():
        for tag, file in (("oof", "oof_proba.npy"), ("test", "test_proba.npy"), ("cv", "cv_results.json"), ("sources", "sources.json"), ("runner", directory + ".py")):
            found[f"{name}_{tag}"] = f"model/{directory}/{file}"
    ct = "model/diagnostics/ctboost_remote_probe_20260905"
    found.update({"ct_oof": ct + "/remote_output/oof.npz", "ct_test": ct + "/remote_output/submission.csv", "ct_summary": ct + "/remote_output/run_summary.json", "ct_notebook": ct + "/kernel/s6e9-ctboost-oof-audit.ipynb"})
    return found


def freeze():
    write_new(OUT / "frozen_config.json", {
        "experiment_id": "INFERENCE_CONTRACT_AUDIT_20260905_RESUME",
        "runner_sha256": digest(__file__), "preregistration_sha256": digest(OUT / "README.md"),
        "inputs": {k: {"path": v, "sha256": digest(PROJECT / v)} for k, v in paths().items()},
        "wall_seconds": 120, "threads": 2, "peak_rss_limit_bytes": 4 * 1024**3,
        "quantiles": Q, "predictions_saved": False, "test_used_for_selection": False,
        "confirmation_evidence": False, "counts_toward_cycle": False,
    })


def run():
    started = time.monotonic()
    config = json.loads((OUT / "frozen_config.json").read_text())
    assert config["runner_sha256"] == digest(__file__)
    assert config["preregistration_sha256"] == digest(OUT / "README.md")
    write_new(OUT / "RUN_STARTED.json", {"pid": os.getpid(), "started_unix": time.time(), "frozen_config_sha256": digest(OUT / "frozen_config.json")})
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("120 second wall budget")))
    signal.alarm(120)
    stage = "imports"
    evidence = {"experiment_id": config["experiment_id"], "config_sha256": digest(OUT / "frozen_config.json"), "source_sha256": {}, "warnings": [], "selection_using_test": False, "model_training_performed": False, "predictions_saved": False}
    try:
        import numpy as np
        import pandas as pd
        import scipy
        import sklearn
        from scipy.stats import ks_2samp, rankdata
        from sklearn.model_selection import StratifiedKFold
        from sklearn.metrics import roc_auc_score
        from threadpoolctl import threadpool_limits, threadpool_info
        thread_limit = threadpool_limits(limits=2)

        def check(label):
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            rss = int(rss if sys.platform == "darwin" else rss * 1024)
            if rss > config["peak_rss_limit_bytes"]:
                raise MemoryError(f"RSS budget exceeded at {label}: {rss}")
            if time.monotonic() - started > 120:
                raise TimeoutError(label)
            return rss

        def ecdf(state, x):
            return (np.searchsorted(state, x, "left") + np.searchsorted(state, x, "right")) / (2. * len(state))

        def percentile(x):
            return rankdata(x, method="average") / len(x)

        def diff(a, b):
            pa, pb = percentile(a), percentile(b)
            displacement = np.abs(pa - pb)
            corr = float(np.corrcoef(pa, pb)[0, 1])
            d99 = float(np.quantile(displacement, .99))
            return {"max_abs": float(np.max(np.abs(a-b))), "mean_abs": float(np.mean(np.abs(a-b))), "rms": float(np.sqrt(np.mean((a-b)**2))), "spearman": corr, "rank_abs_mean": float(displacement.mean()), "rank_abs_p99": d99, "rank_abs_max": float(displacement.max()), "material_by_frozen_threshold": bool(corr < .99999 or d99 > .001)}

        def profile(x):
            s = np.sort(x)
            gap = np.diff(s)
            return {"rows": len(x), "mean": float(x.mean()), "std": float(x.std()), "quantiles": np.quantile(x, Q).tolist(), "unique_fraction": float(np.count_nonzero(gap) + 1) / len(x), "gap_quantiles_p50_p90_p99_max": np.quantile(gap, [.5, .9, .99, 1]).tolist(), "zero_fraction": float(np.mean(x == 0)), "one_fraction": float(np.mean(x == 1))}

        stage = "source_hashes"
        for name, record in config["inputs"].items():
            actual = digest(PROJECT / record["path"])
            if actual != record["sha256"]:
                raise ValueError(f"source changed: {name}")
            evidence["source_sha256"][name] = actual
        train = pd.read_csv(PROJECT / "data/train.csv", usecols=["id", "Will_Buy_EV"])
        test = pd.read_csv(PROJECT / "data/test.csv", usecols=["id"])
        y = train.Will_Buy_EV.eq("Yes").to_numpy(np.int8)
        evidence["row_identity"] = {"train_rows": len(train), "test_rows": len(test), "train_ids_sha256_newline": hashlib.sha256(("\n".join(map(str, train.id)) + "\n").encode()).hexdigest(), "test_ids_sha256_newline": hashlib.sha256(("\n".join(map(str, test.id)) + "\n").encode()).hexdigest(), "scope": "CTBoost explicit id/target/fold checked; local arrays frozen against source metadata, no historical model rerun"}
        p = {}
        results = {}
        for name, directory in NAMES.items():
            p[name] = {split: np.load(PROJECT / f"model/{directory}/{file}", allow_pickle=False).astype(np.float64, copy=False) for split, file in (("oof", "oof_proba.npy"), ("test", "test_proba.npy"))}
            results[name] = json.loads((PROJECT / f"model/{directory}/cv_results.json").read_text())
            source = json.loads((PROJECT / f"model/{directory}/sources.json").read_text())
            if name != "v100":
                identity = source["row_identity"]
                assert identity["train_rows"] == len(train) and identity["test_rows"] == len(test)
                assert identity["train_id_sha256"] == evidence["row_identity"]["train_ids_sha256_newline"]
                assert identity["test_id_sha256"] == evidence["row_identity"]["test_ids_sha256_newline"]
                for split in ("oof", "test"):
                    key = split + "_proba" + (".npy" if name == "v90" else "")
                    assert source["outputs"][key]["sha256"] == evidence["source_sha256"][name + "_" + split]
            else:
                for split in ("oof", "test"):
                    assert results[name]["artifact_sha256"][split+"_proba.npy"] == evidence["source_sha256"][name+"_"+split]
        ct = np.load(PROJECT / paths()["ct_oof"], allow_pickle=False)
        assert np.array_equal(ct["id"], train.id.to_numpy())
        assert np.array_equal(ct["target"], y)
        ct_test = pd.read_csv(PROJECT / paths()["ct_test"])
        assert np.array_equal(ct_test.id.to_numpy(), test.id.to_numpy())
        p["ct"] = {"oof": ct["prediction"].astype(np.float64), "test": ct_test.Will_Buy_EV.to_numpy(np.float64)}
        folds = list(StratifiedKFold(5, shuffle=True, random_state=42).split(np.zeros(len(y)), y))
        fold_id = np.full(len(y), -1)
        for fold, (_, hold) in enumerate(folds):
            fold_id[hold] = fold
        assert np.array_equal(ct["fold"], fold_id)
        for name, pair in p.items():
            for split, values in pair.items():
                assert values.shape == (len(train) if split == "oof" else len(test),)
                assert np.isfinite(values).all() and np.all((values >= 0) & (values <= 1))
        check("inputs")
        stage = "profiles"
        evidence["profiles"] = {}
        for name, pair in p.items():
            state = np.sort(pair["oof"])
            rank_test = ecdf(state, pair["test"])
            evidence["profiles"][name] = {
                "oof": profile(pair["oof"]), "test": profile(pair["test"]),
                "test_minus_oof_mean": float(pair["test"].mean()-pair["oof"].mean()),
                "test_to_oof_std_ratio": float(pair["test"].std()/pair["oof"].std()),
                "ks_effect": float(ks_2samp(pair["oof"], pair["test"], method="asymp").statistic),
                "test_in_oof_ecdf": profile(rank_test),
                "test_below_oof_min_fraction": float(np.mean(pair["test"] < state[0])),
                "test_above_oof_max_fraction": float(np.mean(pair["test"] > state[-1])),
            }
            check(name)
        evidence["atomic_rank_disagreement"] = {}
        for a, b in (("v80", "v85"), ("v80", "ct"), ("v85", "ct"), ("v90", "ct")):
            evidence["atomic_rank_disagreement"][a+"_vs_"+b] = {split: diff(p[a][split], p[b][split]) for split in ("oof", "test")}

        stage = "v90_contract"
        v90_rows = results["v90"]["meta_fold_rows"]
        v100_rows = results["v100"]["meta_fold_rows"]
        rebuilt90 = np.zeros(len(test)); global90 = np.zeros(len(test)); rebuilt90_oof = np.zeros(len(y))
        full80, full85 = np.sort(p["v80"]["oof"]), np.sort(p["v85"]["oof"])
        t80, t85 = ecdf(full80, p["v80"]["test"]), ecdf(full85, p["v85"]["test"])
        rebuilt100_foldmean = np.zeros(len(test))
        for fold, (fit, hold) in enumerate(folds):
            s80, s85 = np.sort(p["v80"]["oof"][fit]), np.sort(p["v85"]["oof"][fit])
            w = v90_rows[fold]["selected_v85_weight"]
            rebuilt90 += ((1-w)*ecdf(s80,p["v80"]["test"]) + w*ecdf(s85,p["v85"]["test"])) / 5
            global90 += ((1-w)*t80+w*t85) / 5
            rebuilt90_oof[hold] = (1-w)*ecdf(s80,p["v80"]["oof"][hold])+w*ecdf(s85,p["v85"]["oof"][hold])
            s90, sct = np.sort(p["v90"]["oof"][fit]), np.sort(p["ct"]["oof"][fit])
            wc = v100_rows[fold]["selected_ctboost_weight"]
            rebuilt100_foldmean += ((1-wc)*ecdf(s90,p["v90"]["test"])+wc*ecdf(sct,p["ct"]["test"])) / 5
        if not np.allclose(rebuilt90, p["v90"]["test"], atol=1e-12, rtol=0) or not np.allclose(rebuilt90_oof, p["v90"]["oof"], atol=1e-12, rtol=0):
            raise AssertionError("V90 reconstruction failed")
        a, b = ecdf(full80,p["v80"]["oof"]), ecdf(full85,p["v85"]["oof"])
        grid = [round(i*.05,2) for i in range(21)]
        scores = [float(roc_auc_score(y,(1-w)*a+w*b)) for w in grid]
        best = max(scores)
        full_weight = min((w for w,s in zip(grid,scores) if abs(s-best)<=1e-15),key=lambda w:(abs(w-.5),w))
        fullfit90 = (1-full_weight)*t80+full_weight*t85
        evidence["v90_contract"] = {"stored_fold_weights": [r["selected_v85_weight"] for r in v90_rows], "rebuild_test_max_abs": float(np.max(np.abs(rebuilt90-p["v90"]["test"]))), "rebuild_oof_max_abs": float(np.max(np.abs(rebuilt90_oof-p["v90"]["oof"]))), "ecdf_only_same_weights": diff(rebuilt90,global90), "full_fit_weight_from_train_only": full_weight, "full_fit_train_auc_apparent_only": best, "full_fit_contract_vs_canonical": diff(rebuilt90,fullfit90), "auc_used_for_test_selection": False}
        stage = "v100_contract"
        s90, sct = np.sort(p["v90"]["oof"]), np.sort(p["ct"]["oof"])
        z90,zct = ecdf(s90,p["v90"]["test"]),ecdf(sct,p["ct"]["test"])
        wc = results["v100"]["evaluation"]["final_ctboost_weight"]
        rebuilt100 = (1-wc)*z90+wc*zct
        if not np.allclose(rebuilt100,p["v100"]["test"],atol=1e-12,rtol=0):
            raise AssertionError("V100 reconstruction failed")
        mean_wc = float(np.mean([r["selected_ctboost_weight"] for r in v100_rows]))
        full_ecdf_meanw = (1-mean_wc)*z90+mean_wc*zct
        evidence["v100_contract"] = {"stored_final_weight": wc, "stored_fold_weights": [r["selected_ctboost_weight"] for r in v100_rows], "rebuild_test_max_abs": float(np.max(np.abs(rebuilt100-p["v100"]["test"]))), "foldmean_ecdf_and_foldweights_vs_canonical": diff(rebuilt100,rebuilt100_foldmean), "ecdf_only_same_mean_foldweight": diff(rebuilt100_foldmean,full_ecdf_meanw), "weight_only_global_ecdf": diff(rebuilt100,full_ecdf_meanw)}
        evidence["ctboost_identification_limit"] = {"oof_fit_fraction": .8, "test_fit_fraction": 1., "test_models_averaged": 1, "available_fold_test_predictions": False, "full_refit_harm_identified": False, "reason": "train/test population and training-size effects are confounded; no matched heldout fold-average/full-fit comparison exists"}
        evidence["status"] = "COMPLETE"
        evidence["versions"] = {"python":sys.version.split()[0], "numpy":np.__version__, "pandas":pd.__version__, "scipy":scipy.__version__, "sklearn":sklearn.__version__}
        evidence["threadpools"] = threadpool_info()
        evidence["peak_rss_bytes"] = check("complete")
        evidence["elapsed_seconds"] = time.monotonic()-started
        write_new(OUT / "evidence.json", evidence)
        print(json.dumps({"status": evidence["status"], "elapsed_seconds": evidence["elapsed_seconds"], "peak_rss_bytes": evidence["peak_rss_bytes"], "evidence_sha256": digest(OUT/"evidence.json")}, ensure_ascii=False))
    except Exception as error:
        evidence.update({"status":"FAILED", "stage":stage, "error_type":type(error).__name__, "error":str(error), "elapsed_seconds":time.monotonic()-started})
        write_new(OUT / "failure.json",evidence)
        raise
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",choices=["freeze","run"])
    arguments=parser.parse_args()
    freeze() if arguments.mode=="freeze" else run()
