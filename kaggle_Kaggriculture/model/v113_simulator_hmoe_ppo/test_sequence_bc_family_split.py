"""Tests for seed-grouped and family-isolated BC splits."""

import numpy as np

from train_sequence_action_bc import grouped_split


def test_grouped_split_respects_eligible_family_rows():
    data = {"episode": np.asarray([10, 10, 11, 11, 12, 12, 13, 13])}
    eligible = np.asarray([0, 1, 2, 3, 4, 5])
    train, validation, validation_episodes = grouped_split(data, 7, 0.34, eligible)
    assert set(train).isdisjoint(validation)
    assert set(train) | set(validation) == set(eligible)
    assert not set(data["episode"][train]) & set(data["episode"][validation])
    assert set(validation_episodes) == set(data["episode"][validation])
