from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np


SOURCE = Path(__file__).with_name("probe.py")
SPEC = importlib.util.spec_from_file_location("split_replica_probe", SOURCE)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_ecdf_ties() -> None:
    state = MODULE.fit_mid_ecdf(np.array([1.0, 2.0, 2.0, 4.0]))
    actual = MODULE.transform_mid_ecdf(state, np.array([0.0, 2.0, 3.0, 5.0]))
    np.testing.assert_allclose(actual, [0.0, 0.5, 0.75, 1.0])


def test_reversed_candidate_gets_zero_weight() -> None:
    rng = np.random.default_rng(7)
    y = np.tile(np.array([0, 1], dtype=np.int8), 250)
    core = y + rng.normal(0, 0.7, len(y))
    result = MODULE.nested_meta(y, core, -core)
    assert all(row["selected_family_weight"] == 0.0 for row in result["rows"])
    assert result["positive_folds"] == 0


def test_member_set_excludes_v80() -> None:
    assert len(MODULE.MEMBERS) == 3
    assert all(
        path.parent.name != "v80_strict_v61_outer104395303_40f"
        for path in MODULE.MEMBERS.values()
    )
