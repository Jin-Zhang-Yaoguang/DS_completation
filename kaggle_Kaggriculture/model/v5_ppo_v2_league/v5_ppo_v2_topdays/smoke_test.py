"""Fast unit and integration checks for the v3 hierarchical agent."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

import numpy as np
from kaggle_environments import make

import base_agent
import main
from build_submission import build
from model_jax import initial_params, export_numpy, parity_error


HERE = Path(__file__).resolve().parent


def _valid(action, obs):
    assert set(action) == {"farmer", "hands", "market"}
    assert isinstance(action["farmer"], list) and action["farmer"]
    assert len(action["market"]) <= 10
    json.dumps(action, allow_nan=False)
    player = int(obs.get("player", 0) or 0)
    assert len(action["hands"]) == len(obs["farms"][player].get("hands", []) or [])


def unit_tests(weights):
    assert main.FEATURE_DIM == 180
    assert main.HEAD_SIZES == (2, 3, 3, 3, 3, 3)
    assert np.array_equal(main.DEFAULT_MACRO, [0, 1, 1, 1, 0, 0])
    assert main.macro_action_mask(0, 0).tolist() == [False, True, False, False, False, True]
    assert not main.macro_action_mask(1, 0).any()
    assert main.macro_action_mask(7, 0)[0]
    env = make("kaggriculture", configuration={"seed": 731}, debug=False)
    env.reset(2)
    obs = env.state[0].observation
    obs.step = 0
    feature = main.encode_observation(obs)
    assert feature.shape == (180,) and np.isfinite(feature).all()
    assert np.max(np.abs(feature)) <= 5.0
    assert main.opponent_family_distance(obs) == 0

    policy = main.NumpyPolicy(weights)
    hidden = np.zeros(main.HIDDEN_SIZE, dtype=np.float32)
    forced, logp, value, next_hidden, logits = policy.act(feature, hidden, stochastic=False, route_enabled=False)
    assert forced.shape == (6,) and forced[0] == 0
    assert math.isfinite(logp) and math.isfinite(value) and np.isfinite(next_hidden).all()
    assert [len(head) for head in logits] == list(main.HEAD_SIZES)

    with tempfile.TemporaryDirectory(prefix="kaggriculture-v3-corrupt-") as temporary:
        arrays = dict(np.load(weights, allow_pickle=False))
        arrays["enc_w"] = np.asarray(arrays["enc_w"]).copy()
        arrays["enc_w"][0, 0] = np.nan
        corrupt = Path(temporary) / "policy_weights.npz"
        np.savez_compressed(corrupt, **arrays)
        try:
            main.NumpyPolicy(corrupt)
        except ValueError as error:
            assert "invalid policy arrays" in str(error)
        else:
            raise AssertionError("non-finite policy was accepted")

    saved = base_agent._projected_shed
    try:
        base_agent._projected_shed = lambda _obs, _action: {"WHEAT": 10, "CARROT": 2}
        raw = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "WHEAT", 10], ["SELL", "CARROT", 2]]}
        macro = np.asarray([0, 2, 1, 1, 0, 2], dtype=np.int16)
        adjusted = main.apply_macro(obs, raw, macro, 100)
        assert adjusted["market"] == [["SELL", "WHEAT", 7], ["SELL", "CARROT", 2]], adjusted
        assert main.apply_macro(obs, raw, macro, 715) is raw
        assert main.apply_macro(obs, raw, main.DEFAULT_MACRO, 100) is raw
    finally:
        base_agent._projected_shed = saved

    class ResetProbe:
        def __init__(self):
            self.inputs = []

        def act(self, features, hidden, **kwargs):
            self.inputs.append(np.asarray(hidden).copy())
            logits = [np.zeros(size, dtype=np.float32) for size in main.HEAD_SIZES]
            return main.DEFAULT_MACRO.copy(), 0.0, 0.0, np.ones_like(hidden), logits

    old_policy, old_error = main._POLICY, main._POLICY_ERROR
    probe = ResetProbe()
    try:
        main._POLICY, main._POLICY_ERROR = probe, None
        main.agent(obs)
        main.agent(obs)
        assert len(probe.inputs) == 2
        assert np.all(probe.inputs[0] == 0) and np.all(probe.inputs[1] == 0)
    finally:
        main._POLICY, main._POLICY_ERROR = old_policy, old_error
        main._reset_game(0)

    # A corrupt/missing policy must permanently fall back for the game.
    old_file, old_policy, old_error = main.MODEL_FILE, main._POLICY, main._POLICY_ERROR
    try:
        main.MODEL_FILE = HERE / "definitely-missing-policy.npz"
        main._POLICY = main._POLICY_ERROR = None
        fallback = main.agent(obs)
        _valid(fallback, obs)
        assert main._GAME[0]["fallback"] and main._POLICY_ERROR
    finally:
        main.MODEL_FILE, main._POLICY, main._POLICY_ERROR = old_file, old_policy, old_error
        main._reset_game(0)


def run_match(weights, opponent, seat, seed):
    main.MODEL_FILE = Path(weights)
    main._POLICY = main._POLICY_ERROR = None
    calls = 0

    def candidate(obs, configuration=None):
        nonlocal calls
        result = main.agent(obs)
        _valid(result, obs)
        calls += 1
        return result

    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
    agents = [candidate, opponent] if seat == 0 else [opponent, candidate]
    steps = env.run(agents)
    assert len(steps) == 720 and calls == 719
    final = steps[-1]
    assert [str(state.status) for state in final] == ["DONE", "DONE"]
    rewards = [float(state.reward or 0.0) for state in final]
    assert all(math.isfinite(value) for value in rewards)
    return {
        "seat": seat, "seed": seed, "reward": rewards[seat],
        "opponent_reward": rewards[1 - seat],
        "neural_enabled": main._GAME[seat].get("neural_enabled"),
        "family_distance": main._GAME[seat].get("family_distance"),
    }


def run(weights):
    weights = Path(weights)
    unit_tests(weights)
    parity = parity_error(initial_params(19), _temporary_export())
    assert parity <= 1e-5, parity
    matches = []
    for opponent, base_seed in (("starter", 9100), ("random", 9200)):
        for seat in (0, 1):
            matches.append(run_match(weights, opponent, seat, base_seed + seat))
    assert all(match["neural_enabled"] is False for match in matches)
    family = run_match(weights, base_agent.agent, 0, 9250)
    assert family["neural_enabled"] is True and family["family_distance"] <= main.FAMILY_DISTANCE_LIMIT
    matches.append(family)
    with tempfile.TemporaryDirectory(prefix="kaggriculture-v3-archive-") as temporary:
        temporary = Path(temporary)
        archive = build(temporary / "submission.tar.gz", weights)
        with tarfile.open(archive["archive"], "r:gz") as source:
            for name in source.getnames():
                member = source.extractfile(name)
                assert member is not None
                (temporary / name).write_bytes(member.read())
        # Run from only the unpacked directory. This catches accidental imports
        # from the development tree and Kaggle's file-loader __file__ behavior.
        code = (
            "from kaggle_environments import make; "
            "e=make('kaggriculture',configuration={'seed':9300},debug=False); "
            "s=e.run(['main.py','starter']); "
            "assert len(s)==720; assert [str(x.status) for x in s[-1]]==['DONE','DONE']; "
            "print([float(x.reward or 0) for x in s[-1]])"
        )
        clean = subprocess.run(
            [sys.executable, "-c", code], cwd=temporary,
            text=True, capture_output=True, timeout=60,
        )
        assert clean.returncode == 0, clean.stderr
        archive["clean_match"] = clean.stdout.strip().splitlines()[-1]
    return {"ok": True, "parity_max_abs_error": parity, "matches": matches, "archive": archive}


def _temporary_export():
    path = Path(tempfile.mkdtemp(prefix="kaggriculture-v3-parity-")) / "weights.npz"
    export_numpy(initial_params(19), path)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, default=HERE / "policy_weights.npz")
    print(json.dumps(run(parser.parse_args().weights), ensure_ascii=False, indent=2))
