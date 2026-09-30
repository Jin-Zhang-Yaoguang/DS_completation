from __future__ import annotations

from copy import deepcopy

import pytest

from kaggle_Kaggriculture.model.v10_replay_lolo_router.report_frozen_test import (
    _validate_complete_matrix,
)


def _rows(models: list[str]) -> list[dict]:
    rows = []
    for left_index, left in enumerate(models):
        for right in models[left_index + 1 :]:
            for seed in (101, 202):
                for seat in (0, 1):
                    rows.append(
                        {
                            "pair_id": f"{left}__vs__{right}",
                            "model_a": left,
                            "model_b": right,
                            "model_a_seat": seat,
                            "source": {
                                "date": "2026-08-18",
                                "episode_id": f"episode-{seed}",
                                "seed": seed,
                            },
                            "done": True,
                            "error": None,
                        }
                    )
    return rows


def test_complete_matrix_requires_every_pair_shared_sources_and_both_seats() -> None:
    models = ["a", "b", "c"]
    report = _validate_complete_matrix(_rows(models), models, games_per_pair=4)
    assert report == {
        "pairs": 3,
        "games": 12,
        "unique_seed_clusters": 2,
        "dual_seat_balanced": True,
        "common_seed_panel": True,
    }


@pytest.mark.parametrize("mutation", ["missing", "bad_seat", "different_source"])
def test_complete_matrix_rejects_incomplete_or_incomparable_panels(mutation: str) -> None:
    models = ["a", "b", "c"]
    rows = _rows(models)
    if mutation == "missing":
        rows.pop()
    elif mutation == "bad_seat":
        rows[-1]["model_a_seat"] = 0
    else:
        changed = deepcopy(rows[-1]["source"])
        changed.update(seed=303, episode_id="episode-303")
        rows[-1]["source"] = changed
    with pytest.raises(ValueError):
        _validate_complete_matrix(rows, models, games_per_pair=4)
