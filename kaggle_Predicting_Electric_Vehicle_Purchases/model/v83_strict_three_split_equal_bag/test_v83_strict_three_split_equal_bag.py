from __future__ import annotations

import copy
import importlib.util
import inspect
from pathlib import Path

import numpy as np
import pytest


MODULE_PATH = Path(__file__).with_name("v83_strict_three_split_equal_bag.py")
SPEC = importlib.util.spec_from_file_location("v83_under_test", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot import {MODULE_PATH}")
V83 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V83)


def _member_predictions(
    base: np.ndarray,
    second: np.ndarray,
    third: np.ndarray,
) -> dict[str, np.ndarray]:
    return dict(zip(V83.EXPECTED_MEMBER_IDS, (base, second, third), strict=True))


def _valid_complete_result(
    config: dict[str, object], recomputed: dict[str, float]
) -> dict[str, object]:
    peak_bytes = 256 * 1024**2
    return {
        "research_cycle": "C01",
        "cycle_position": 4,
        "experiment_type": "SMALL_BLEND",
        "counts_toward_cycle": True,
        "cycle_count_update_required": True,
        "canonical_base": V83.EXPECTED_MEMBER_IDS[0],
        "members": list(V83.EXPECTED_MEMBER_IDS),
        "member_weights": {name: 1.0 / 3.0 for name in V83.EXPECTED_MEMBER_IDS},
        "formal_trigger_verified": True,
        "member_verifiers": {name: "PASSED" for name in V83.EXPECTED_MEMBER_IDS},
        "base": V83.EXPECTED_MEMBER_IDS[0],
        "submission_budget": 0,
        "oof_auc": recomputed["oof_auc"],
        "base_oof_auc": recomputed["canonical_v80_oof_auc"],
        "oof_delta_vs_base": recomputed["oof_delta_vs_canonical_v80"],
        "artifact_validation": V83.expected_artifact_validation(100, 40),
        "resource_budget": {
            "time_budget_seconds": config["time_budget_seconds"],
            "memory_budget_gib": config["memory_budget_gib"],
            "cpu_threads": config["cpu_threads"],
        },
        "elapsed_seconds": 10.0,
        "peak_rss_bytes": peak_bytes,
        "peak_rss_gib": peak_bytes / 1024**3,
    }


def test_frozen_config_is_exact_three_atomic_siblings() -> None:
    config = V83.load_frozen_config()

    assert tuple(member["experiment_id"] for member in config["members"]) == (
        V83.EXPECTED_MEMBER_IDS
    )
    assert all(member["role"] == "ATOMIC_SIBLING" for member in config["members"])
    assert config["canonical_base"] == V83.EXPECTED_MEMBER_IDS[0]
    assert config["research_cycle"] == "C01"
    assert config["cycle_position"] == 4
    assert config["experiment_type"] == "SMALL_BLEND"
    assert config["formal_trigger"]["all_frozen_verifiers_must_pass"] is True


def test_frozen_method_has_no_data_driven_choice_or_transform() -> None:
    method = V83.load_frozen_config()["method"]

    assert method == {
        "prediction_space": "RAW_PROBABILITY",
        "operator": "FIXED_ARITHMETIC_MEAN",
        "weights": [1.0 / 3.0] * 3,
        "member_selection": "NONE",
        "weight_fitting": "NONE",
        "rank_or_ecdf": "NONE",
        "calibration_transform": "NONE",
        "oof_and_test_use_identical_operator": True,
    }


def test_static_config_rejects_forbidden_prediction_member() -> None:
    config = copy.deepcopy(V83.load_frozen_config())
    config["members"][2]["experiment_id"] = next(iter(V83.FORBIDDEN_MEMBER_IDS))

    with pytest.raises(ValueError, match="冻结成员或顺序错误"):
        V83.validate_static_config(config)


def test_fixed_equal_mean_is_exact_raw_probability_operator() -> None:
    first = np.array([0.0, 0.3, 0.9], dtype=np.float64)
    second = np.array([0.3, 0.6, 0.3], dtype=np.float64)
    third = np.array([0.6, 0.0, 0.6], dtype=np.float64)

    actual = V83.fixed_equal_mean([first, second, third])
    expected = np.add.reduce([first, second, third], dtype=np.float64) / 3.0

    assert np.array_equal(actual, expected)


@pytest.mark.parametrize(
    "arrays, message",
    [
        ([np.array([0.1]), np.array([0.2])], "恰好接收三个"),
        (
            [np.array([0.1]), np.array([0.2, 0.3]), np.array([0.4])],
            "shape 不一致",
        ),
        (
            [np.array([0.1]), np.array([np.nan]), np.array([0.4])],
            "NaN/Inf",
        ),
        (
            [np.array([0.1]), np.array([1.1]), np.array([0.4])],
            "概率超出",
        ),
    ],
)
def test_fixed_equal_mean_rejects_invalid_inputs(
    arrays: list[np.ndarray], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        V83.fixed_equal_mean(arrays)


def test_evaluation_gate_passes_only_full_oof_and_all_five_buckets() -> None:
    config = V83.load_frozen_config()
    y = np.tile(np.array([0, 1], dtype=np.int8), 500)
    base = np.linspace(0.1, 0.9, len(y), dtype=np.float64)
    strong_one = 0.1 + 0.75 * y + np.linspace(0.0, 0.01, len(y))
    strong_two = 0.12 + 0.73 * y + np.linspace(0.01, 0.0, len(y))
    member_oof = _member_predictions(base, strong_one, strong_two)
    member_test = _member_predictions(
        base[::-1].copy(), strong_one[::-1].copy(), strong_two[::-1].copy()
    )
    bag_oof = V83.fixed_equal_mean(list(member_oof.values()))
    bag_test = V83.fixed_equal_mean(list(member_test.values()))

    result = V83.evaluate_predictions(
        config, y, member_oof, member_test, bag_oof, bag_test
    )

    assert result["promotion_gate"]["full_oof_delta_passes"] is True
    assert result["promotion_gate"]["all_meta_bucket_deltas_strictly_positive"] is True
    assert result["promotion_gate"]["meta_buckets_won"] == 5
    assert result["promotion_gate"]["passes"] is True
    assert result["decision"] == "PROMOTE"
    assert result["oof_delta_vs_best_input"] <= 0.0
    assert set(result["calibration"]) == {*V83.EXPECTED_MEMBER_IDS, V83.EXPERIMENT_ID}


def test_evaluation_rejects_zero_delta_even_with_identical_operator() -> None:
    config = V83.load_frozen_config()
    y = np.tile(np.array([0, 1], dtype=np.int8), 100)
    base = np.linspace(0.1, 0.9, len(y), dtype=np.float64)
    member_oof = _member_predictions(base, base.copy(), base.copy())
    member_test = _member_predictions(base.copy(), base.copy(), base.copy())
    bag_oof = V83.fixed_equal_mean(list(member_oof.values()))
    bag_test = V83.fixed_equal_mean(list(member_test.values()))

    result = V83.evaluate_predictions(
        config, y, member_oof, member_test, bag_oof, bag_test
    )

    assert result["promotion_gate"]["full_oof_delta_passes"] is False
    assert result["promotion_gate"]["all_meta_bucket_deltas_strictly_positive"] is False
    assert result["promotion_gate"]["passes"] is False
    assert result["decision"] == "REJECT"


def test_member_result_rejects_failed_robustness_gate() -> None:
    member = V83.load_frozen_config()["members"][1]
    result = {
        "experiment_id": member["experiment_id"],
        "status": "COMPLETE",
        "decision": "ROBUSTNESS_REPLICATION_PASSED",
        "artifact_validation": {
            "oof_exactly_once_coverage": True,
            "probabilities_finite_and_in_range": True,
            "submission_id_matches_test": True,
            "strict_prior_self_check": True,
            "checkpoint_reconstruction_required": True,
        },
        "split_seed_robustness_gate": {"passes": False},
    }

    with pytest.raises(ValueError, match="robustness gate 未通过"):
        V83.validate_member_result(member, result)


def test_lineage_contains_only_three_allowed_prediction_parents() -> None:
    config = V83.load_frozen_config()
    lineage = V83.lineage_payload(config)

    assert [edge["source"] for edge in lineage["prediction_edges"]] == list(
        V83.EXPECTED_MEMBER_IDS
    )
    assert all(edge["weight"] == 1.0 / 3.0 for edge in lineage["prediction_edges"])
    assert not (
        {edge["source"] for edge in lineage["prediction_edges"]}
        & V83.FORBIDDEN_MEMBER_IDS
    )
    assert lineage["no_parent_ensemble_member"] is True


def test_candidate_json_is_immutable(tmp_path: Path) -> None:
    path = tmp_path / "candidate_snapshot.json"
    payload = {"members": list(V83.EXPECTED_MEMBER_IDS)}

    V83.write_immutable_json(path, payload)
    V83.write_immutable_json(path, payload)

    with pytest.raises(ValueError, match="不可变 JSON"):
        V83.write_immutable_json(path, {"members": ["changed"]})


def test_audit_does_not_create_formal_outputs() -> None:
    paths = V83.formal_output_paths()
    before = {name: path.exists() for name, path in paths.items()}

    result = V83.audit()

    after = {name: path.exists() for name, path in paths.items()}
    assert before == after
    assert result["status"] == "AUDIT_OK_NO_REAL_MEMBER_OUTPUTS_READ"
    assert result["formal_outputs_created"] is False


@pytest.mark.parametrize(
    "field, changed",
    [
        ("oof_auc", 0.8),
        ("base", "not-v80"),
        ("base_oof_auc", 0.7),
        ("oof_delta_vs_base", 0.1),
    ],
)
def test_complete_contract_rejects_stale_top_level_metrics(
    field: str, changed: object
) -> None:
    config = V83.load_frozen_config()
    recomputed = {
        "oof_auc": 0.9463,
        "canonical_v80_oof_auc": 0.9462,
        "oof_delta_vs_canonical_v80": 0.0001,
    }
    result = _valid_complete_result(config, recomputed)
    result[field] = changed

    with pytest.raises(ValueError):
        V83.validate_completed_result_contract(result, recomputed, config, 100, 40)


def test_complete_contract_checks_every_artifact_validation_field() -> None:
    config = V83.load_frozen_config()
    recomputed = {
        "oof_auc": 0.9463,
        "canonical_v80_oof_auc": 0.9462,
        "oof_delta_vs_canonical_v80": 0.0001,
    }
    result = _valid_complete_result(config, recomputed)
    result["artifact_validation"] = copy.deepcopy(result["artifact_validation"])
    result["artifact_validation"].pop("blend_reconstruction_required")

    with pytest.raises(ValueError, match="artifact_validation"):
        V83.validate_completed_result_contract(result, recomputed, config, 100, 40)


@pytest.mark.parametrize(
    "usage, error",
    [
        (
            {
                "elapsed_seconds": 900.000001,
                "peak_rss_bytes": 1024,
                "peak_rss_gib": 1024 / 1024**3,
            },
            V83.ResourceBudgetExceeded,
        ),
        (
            {
                "elapsed_seconds": 10.0,
                "peak_rss_bytes": 4 * 1024**3 + 1,
                "peak_rss_gib": (4 * 1024**3 + 1) / 1024**3,
            },
            V83.ResourceBudgetExceeded,
        ),
        (
            {
                "elapsed_seconds": 10.0,
                "peak_rss_bytes": 1024,
                "peak_rss_gib": 2.0,
            },
            ValueError,
        ),
    ],
)
def test_resource_contract_rejects_over_budget_or_inconsistent_values(
    usage: dict[str, float | int], error: type[Exception]
) -> None:
    with pytest.raises(error):
        V83.validate_resource_values(usage, V83.load_frozen_config(), "TEST")


def test_sources_header_requires_exact_schema_and_experiment() -> None:
    valid = {
        "schema_version": 1,
        "experiment_id": V83.EXPERIMENT_ID,
        "immutable": True,
    }
    V83.validate_sources_header(valid)

    for field, changed in (
        ("schema_version", 2),
        ("experiment_id", "wrong"),
        ("immutable", False),
    ):
        invalid = {**valid, field: changed}
        with pytest.raises(ValueError):
            V83.validate_sources_header(invalid)


def test_formal_complete_commit_occurs_after_final_verify_and_has_failed_fallback() -> None:
    source = inspect.getsource(V83.run_formal)
    verify_position = source.index("_verify_complete(")
    stage_position = source.index("_atomic_bytes(pending_results_path")
    commit_position = source.index("os.replace(pending_results_path, results_path)")

    assert verify_position < stage_position < commit_position
    assert "MEMBERS_AND_DATA_LOADED" in source
    assert "ALL_NON_RESULT_OUTPUTS_WRITTEN" in source
    assert "FINAL_REBUILD_VERIFY" in source
    assert "FORMAL_SCOPE_COMPLETE" in source
    assert "atomic_write_json(results_path, failure)" in source
