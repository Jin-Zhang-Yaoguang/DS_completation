import numpy as np

from collect_router_ppo import sample_expert


def test_sample_expert_excludes_unqualified_animal_branch():
    rng = np.random.default_rng(113)
    logits = np.asarray([0.0, 0.0, 0.0, 0.0, 0.0, 100.0])
    sampled = [sample_expert(logits, 1.0, rng)[0] for _ in range(100)]
    assert set(sampled) <= {0, 1, 2, 3, 4}


def test_sample_expert_respects_dominant_crop_logit():
    rng = np.random.default_rng(114)
    expert, logprob = sample_expert(np.asarray([-20.0, -20.0, -20.0, -20.0, 20.0, 50.0]), 1.0, rng)
    assert expert == 4
    assert logprob > -1e-6
