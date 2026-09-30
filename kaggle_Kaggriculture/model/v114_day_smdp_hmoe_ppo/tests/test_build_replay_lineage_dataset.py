from __future__ import annotations

import importlib.util
from pathlib import Path


MODULE = Path(__file__).resolve().parents[1] / "build_replay_lineage_dataset.py"
SPEC = importlib.util.spec_from_file_location("build_replay_lineage_dataset", MODULE)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(mod)


def test_causal_phase_labels_cover_boundaries():
    assert mod.causal_phase_labels(0) == (4, 4)
    assert mod.causal_phase_labels(71) == (4, 4)
    assert mod.causal_phase_labels(72) == (2, 4)
    assert mod.causal_phase_labels(215) == (2, 4)
    assert mod.causal_phase_labels(216) == (0, 4)
    assert mod.causal_phase_labels(479) == (0, 4)
    assert mod.causal_phase_labels(480) == (1, 3)
    assert mod.causal_phase_labels(670) == (1, 3)
    assert mod.causal_phase_labels(671) == (5, 5)
    assert mod.causal_phase_labels(718) == (5, 5)


def test_split_is_deterministic_and_bounded():
    values = [mod.split_id(identity) for identity in range(1000, 1100)]
    assert values == [mod.split_id(identity) for identity in range(1000, 1100)]
    assert set(values) == {0, 1, 2}


def test_episode_filename_contract():
    assert mod.episode_id(Path("episode-12345-replay.json")) == 12345
