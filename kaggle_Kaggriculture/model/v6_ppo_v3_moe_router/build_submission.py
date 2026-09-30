"""Build and clean-verify the pure-NumPy PPO v3 Kaggle archive."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
V1_SOURCE = HERE.parent / "v1_adaptive_market" / "main.py"
FILES = ("main.py", "catalog.py", "experts.py", "action_compiler.py", "features.py", "router_numpy.py")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path: Path):
    spec = importlib.util.spec_from_file_location("ppo_v3_clean_main", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    old = list(sys.path)
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path[:] = old
    return module


def _smoke(directory: Path):
    from kaggle_environments import make
    from kaggle_environments.envs.kaggriculture import kaggriculture as kg

    module = _load(directory / "main.py")
    env = make("kaggriculture", configuration={"seed": 98600000}, debug=False)
    env.reset(2)
    for step in range(719):
        for state in env.state:
            state.observation.step = step
        env.step([module.agent(env.state[0].observation), kg.starter_agent(env.state[1].observation)])
    if [str(state.status) for state in env.state] != ["DONE", "DONE"]:
        raise RuntimeError("clean archive smoke did not reach DONE/DONE")
    return [float(state.reward or 0.0) for state in env.state]


def build(weights: Path, output: Path):
    weights = weights.resolve()
    if not weights.exists():
        raise FileNotFoundError(weights)
    if not V1_SOURCE.exists():
        raise FileNotFoundError(V1_SOURCE)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ppo_v3_submission_") as temp:
        root = Path(temp) / "package"
        root.mkdir()
        for name in FILES:
            shutil.copy2(HERE / name, root / name)
        shutil.copy2(V1_SOURCE, root / "v1_agent.py")
        shutil.copy2(weights, root / "router_weights.npz")
        rewards = _smoke(root)
        members = [*FILES, "v1_agent.py", "router_weights.npz"]
        with tarfile.open(output, "w:gz") as archive:
            # The smoke import can create __pycache__.  Archive only the
            # explicit serving contract so a submission is deterministic and
            # never accidentally includes local interpreter artifacts.
            for name in sorted(members):
                archive.add(root / name, arcname=name)
    return {"archive": str(output), "sha256": _sha256(output), "clean_smoke_rewards": rewards, "members": members}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=HERE / "submission.tar.gz")
    args = parser.parse_args()
    import json
    print(json.dumps(build(args.weights, args.output), ensure_ascii=False, indent=2))
