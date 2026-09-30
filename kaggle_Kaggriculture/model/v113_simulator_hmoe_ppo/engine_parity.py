"""Exact replay parity gate for the V113 simulator training environment."""

from __future__ import annotations

import argparse
import copy
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import re
import tempfile
import time
from typing import Any


HEADER_BYTES = 32 * 1024
MODULE_RE = re.compile(rb'"module_version"\s*:\s*"([^"]+)"')
EPISODE_RE = re.compile(rb'"EpisodeId"\s*:\s*(\d+)')


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if hasattr(value, "toJSON"):
        return _plain(value.toJSON())
    if hasattr(value, "items"):
        return {str(key): _plain(item) for key, item in value.items()}
    return value


def _clean_observation(value: Any) -> Any:
    result = _plain(value)
    if isinstance(result, dict):
        # Wall-clock budget is runner state, not Kaggriculture transition state.
        result.pop("remainingOverageTime", None)
    return result


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _metadata(path: Path) -> tuple[str | None, int | None]:
    with path.open("rb") as source:
        header = source.read(HEADER_BYTES)
    module = MODULE_RE.search(header)
    episode = EPISODE_RE.search(header)
    return (
        module.group(1).decode("utf-8") if module else None,
        int(episode.group(1)) if episode else None,
    )


def discover(root: Path, module_version: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in root.glob("date=*/data/*.json"):
        version, episode_id = _metadata(path)
        if version != str(module_version):
            continue
        rows.append({
            "path": str(path.resolve()),
            "date": path.parents[1].name.removeprefix("date="),
            "episode_id": episode_id if episode_id is not None else int(path.stem),
            "module_version": version,
        })
    rows.sort(key=lambda row: (row["date"], int(row["episode_id"])))
    return rows


def select_samples(rows: list[dict[str, Any]], count: int, selection_seed: int) -> list[dict[str, Any]]:
    if count <= 0 or count > len(rows):
        raise ValueError(f"samples must be in 1..{len(rows)}")
    salt = f"v113-engine-parity|{int(selection_seed)}|"
    ranked = sorted(
        rows,
        key=lambda row: hashlib.sha256(
            (salt + row["date"] + "|" + str(row["episode_id"])).encode("utf-8")
        ).digest(),
    )
    selected = ranked[: int(count)]
    selected.sort(key=lambda row: (row["date"], int(row["episode_id"])))
    return selected


class _ActionStream:
    def __init__(self, actions: list[dict[str, Any]]) -> None:
        self.actions = actions

    def __call__(self, obs: Any, configuration: Any = None) -> dict[str, Any]:
        del configuration
        return copy.deepcopy(self.actions[int(obs.step)])


def replay_one(row: dict[str, Any]) -> dict[str, Any]:
    from kaggle_environments import make

    path = Path(row["path"])
    with path.open("r", encoding="utf-8") as source:
        replay = json.load(source)
    if replay.get("module_version") != row["module_version"]:
        raise RuntimeError("module version changed after discovery")
    steps = replay.get("steps") or []
    if len(steps) != 720:
        return {**row, "passed": False, "error": f"source_steps={len(steps)}"}
    actions = [
        [copy.deepcopy(pair[seat].get("action") or {}) for pair in steps[1:]]
        for seat in (0, 1)
    ]
    config = dict(replay.get("configuration") or {})
    config["seed"] = int((replay.get("info") or {})["seed"])
    env = make("kaggriculture", configuration=config, debug=False)
    env.run([_ActionStream(actions[0]), _ActionStream(actions[1])])

    mismatches: list[dict[str, Any]] = []
    if len(env.steps) != len(steps):
        mismatches.append({"kind": "step_count", "source": len(steps), "local": len(env.steps)})
    for step_index, (source_pair, local_pair) in enumerate(zip(steps, env.steps)):
        for seat in (0, 1):
            source_obs = _clean_observation(source_pair[seat].get("observation") or {})
            local_obs = _clean_observation(local_pair[seat].get("observation") or {})
            if source_obs != local_obs:
                mismatches.append({
                    "kind": "observation",
                    "step": step_index,
                    "seat": seat,
                    "source_hash": _digest(source_obs),
                    "local_hash": _digest(local_obs),
                })
                break
        if mismatches:
            break
    local_rewards = [float(state.reward or 0.0) for state in env.state]
    source_rewards = [float(value or 0.0) for value in (replay.get("rewards") or [])]
    local_statuses = [str(state.status) for state in env.state]
    source_statuses = [str(value) for value in (replay.get("statuses") or [])]
    if local_rewards != source_rewards:
        mismatches.append({"kind": "reward", "source": source_rewards, "local": local_rewards})
    if local_statuses != source_statuses:
        mismatches.append({"kind": "status", "source": source_statuses, "local": local_statuses})
    return {
        **row,
        "seed": int((replay.get("info") or {})["seed"]),
        "steps": len(env.steps),
        "source_rewards": source_rewards,
        "local_rewards": local_rewards,
        "source_statuses": source_statuses,
        "local_statuses": local_statuses,
        "mismatch_count": len(mismatches),
        "first_mismatches": mismatches[:3],
        "passed": not mismatches,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(root: Path, module_version: str, samples: int, workers: int, selection_seed: int) -> dict[str, Any]:
    import kaggle_environments
    from kaggle_environments.envs.kaggriculture import kaggriculture

    discovered = discover(root, module_version)
    selected = select_samples(discovered, samples, selection_seed)
    started = time.time()
    results: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=max(1, int(workers))) as pool:
        futures = [pool.submit(replay_one, row) for row in selected]
        for index, future in enumerate(as_completed(futures), 1):
            try:
                results.append(future.result())
            except Exception as exc:
                source_row = selected[futures.index(future)]
                results.append({**source_row, "passed": False, "error": repr(exc)})
            print(json.dumps({"phase": "ENV_PARITY", "completed": index, "samples": len(selected)}), flush=True)
    results.sort(key=lambda row: (row["date"], int(row["episode_id"])))
    passed = sum(bool(row.get("passed")) for row in results)
    rules_path = Path(kaggriculture.__file__).resolve()
    return {
        "schema": "kaggriculture-v113-engine-parity-v1",
        "model_id": "v113_simulator_hmoe_ppo",
        "gate": "ENV_PARITY",
        "selection_seed": int(selection_seed),
        "module_version_requested": str(module_version),
        "installed_kaggle_environments": kaggle_environments.__version__,
        "installed_rules": str(rules_path),
        "installed_rules_sha256": _sha256(rules_path),
        "available_matching_replays": len(discovered),
        "sampled": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "gate_passed": passed == len(results) and len(results) == int(samples),
        "elapsed_seconds": time.time() - started,
        "results": results,
    }


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2)
        sink.write("\n")
        temporary = Path(sink.name)
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episodes-root", type=Path, required=True)
    parser.add_argument("--module-version", default="1.32.7")
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--selection-seed", type=int, default=113001)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.episodes_root, args.module_version, args.samples, args.workers, args.selection_seed)
    atomic_json(args.output, report)
    print(json.dumps({key: report[key] for key in ("sampled", "passed", "failed", "gate_passed", "elapsed_seconds")}, ensure_ascii=False, indent=2))
    if not report["gate_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
