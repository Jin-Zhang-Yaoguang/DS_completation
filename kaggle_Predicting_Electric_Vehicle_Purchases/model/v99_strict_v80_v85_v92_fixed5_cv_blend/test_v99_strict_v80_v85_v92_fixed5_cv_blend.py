from __future__ import annotations

import copy
import importlib.util
import inspect
from pathlib import Path

import numpy as np
import pytest


MODULE_PATH = Path(__file__).with_name(
    "v99_strict_v80_v85_v92_fixed5_cv_blend.py"
)
SPEC = importlib.util.spec_from_file_location("v99_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {MODULE_PATH}")
V99 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V99)


def synthetic_predictions() -> tuple[
    np.ndarray, dict[str, np.ndarray], dict[str, np.ndarray]
]:
    y = np.tile(np.array([0, 1], dtype=np.int8), 50)
    trend = np.linspace(0.01, 0.99, len(y))
    rng = np.random.default_rng(42)
    oof = {
        V99.MEMBER_IDS[0]: np.clip(0.18 + 0.60 * y + 0.04 * trend, 0, 1),
        V99.MEMBER_IDS[1]: np.clip(
            0.16 + 0.62 * y + 0.03 * trend[::-1], 0, 1
        ),
        V99.MEMBER_IDS[2]: np.clip(
            0.17 + 0.61 * y + 0.02 * rng.random(len(y)), 0, 1
        ),
    }
    test = {
        V99.MEMBER_IDS[0]: np.linspace(0.05, 0.95, 31),
        V99.MEMBER_IDS[1]: np.linspace(0.95, 0.05, 31),
        V99.MEMBER_IDS[2]: np.linspace(0.10, 0.90, 31) ** 1.1,
    }
    return y, oof, test


def test_config_freezes_new_question_and_cycle_position() -> None:
    config = V99.load_frozen_config()
    assert config["experiment_id"] == V99.EXPERIMENT_ID
    assert config["retry_of"] is None
    assert config["cycle_position"] == 16
    assert config["counts_toward_cycle_when_formally_closed"] is True
    assert tuple(item["experiment_id"] for item in config["members"]) == (
        V99.MEMBER_IDS
    )
    assert config["strict_baseline"]["experiment_id"] == V99.BASELINE_ID
    assert V99.BASELINE_ID not in V99.MEMBER_IDS


def test_config_rejects_parent_or_extra_member() -> None:
    config = V99.load_frozen_config()
    bad = copy.deepcopy(config)
    bad["members"].append(copy.deepcopy(bad["members"][0]))
    with pytest.raises(ValueError, match="恰好有三个"):
        V99.validate_static_config(bad)
    bad = copy.deepcopy(config)
    bad["members"][2]["prediction_parent"] = "forged_parent"
    with pytest.raises(ValueError, match="原子预测成员"):
        V99.validate_static_config(bad)


def test_frozen_weights_preserve_v90_ratio_and_add_exactly_five_percent_v92() -> None:
    for fold in range(1, 6):
        candidate, baseline = V99.frozen_weights_for_fold(fold)
        assert np.isclose(sum(candidate), 1.0)
        assert np.isclose(sum(baseline), 1.0)
        assert candidate[2] == 0.05
        assert baseline[2] == 0.0
        assert np.isclose(candidate[0], 0.95 * baseline[0])
        assert np.isclose(candidate[1], 0.95 * baseline[1])


def test_meta_cv_is_deterministic_and_exactly_covers_oof() -> None:
    y, oof, test = synthetic_predictions()
    first = V99.run_meta_cv(y, oof, test)
    second = V99.run_meta_cv(y, oof, test)
    for key in ("oof", "test", "baseline_oof", "baseline_test"):
        assert np.array_equal(first[key], second[key])
    assert np.all(first["coverage"] == 1)
    assert len(first["fold_rows"]) == 5
    assert all(row["weight_selection_performed"] is False for row in first["fold_rows"])


def test_every_mid_ecdf_state_is_fit_on_meta_train_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    y, oof, test = synthetic_predictions()
    original = V99.fit_mid_ecdf
    seen_lengths: list[int] = []

    def recording_fit(values: np.ndarray) -> np.ndarray:
        seen_lengths.append(len(values))
        return original(values)

    monkeypatch.setattr(V99, "fit_mid_ecdf", recording_fit)
    V99.run_meta_cv(y, oof, test)
    assert seen_lengths == [80] * 15


def test_baseline_reconstruction_fails_closed_on_drift() -> None:
    config = V99.load_frozen_config()
    y, oof, test = synthetic_predictions()
    meta = V99.run_meta_cv(y, oof, test)
    bad = meta["baseline_oof"].copy()
    bad[0] += 1e-6
    with pytest.raises(ValueError, match="v90 OOF"):
        V99.assert_baseline_reconstruction(
            config, y, meta, bad, meta["baseline_test"]
        )


def test_promotion_requires_all_three_frozen_gates() -> None:
    config = V99.load_frozen_config()
    assert V99.promotion_decision(0.0001, 5, 24, config) == "PROMOTE"
    assert V99.promotion_decision(0.000099999, 5, 24, config) == "REJECT"
    assert V99.promotion_decision(0.0002, 4, 24, config) == "REJECT"
    assert V99.promotion_decision(0.0002, 5, 23, config) == "REJECT"


def test_audit_is_hash_only(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_load(*args: object, **kwargs: object) -> None:
        raise AssertionError("audit must not parse prediction arrays")

    monkeypatch.setattr(V99.np, "load", forbidden_load)
    result = V99.audit()
    assert result["status"] == "AUDIT_OK_HASH_ONLY_NO_PREDICTION_ARRAYS_READ"
    assert result["formal_outputs_created"] is False


def test_formal_load_runs_all_source_verifiers_before_array_parse() -> None:
    source = inspect.getsource(V99.load_formal_inputs)
    assert source.index("verify_all_sources_before_prediction_load(config)") < (
        source.index("load_npy_from_sha_verified_bytes(")
    )
    assert source.count("load_npy_from_sha_verified_bytes(") == 4


def test_v92_summary_contract_is_exact() -> None:
    config = V99.load_frozen_config()
    source = config["members"][2]
    results = V99.json.loads(
        (
            V99.resolve_project_path(source["directory"]) / "cv_results.json"
        ).read_text(encoding="utf-8")
    )
    expected = V99.expected_v92_verification_summary(source, results)
    V99.validate_source_verifier_return(source, expected, results)
    bad = copy.deepcopy(expected)
    bad["oof_auc"] = 0.0
    with pytest.raises(ValueError, match="summary 字段漂移"):
        V99.validate_source_verifier_return(source, bad, results)


def test_smoke_uses_synthetic_predictions_and_no_weight_search() -> None:
    before = {
        name: (V99.OUT_DIR / name).exists() for name in V99.MATERIAL_ARTIFACTS
    }
    result = V99.smoke()
    after = {
        name: (V99.OUT_DIR / name).exists() for name in V99.MATERIAL_ARTIFACTS
    }
    assert result["status"] == "SMOKE_OK_SYNTHETIC_ONLY_NO_REAL_PREDICTIONS_LOADED"
    assert result["fixed_weight_candidate_count"] == 1
    assert result["fit_only_mid_ecdf"] is True
    assert before == after
