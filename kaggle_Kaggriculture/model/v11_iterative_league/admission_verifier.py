#!/usr/bin/env python3
"""Independent closed-loop admission verifier for one V11 candidate.

The optimizer's smoke report is provenance input only.  This module reloads
the admitted registry and independently reruns candidate and direct-parent
controls on six explicit development sources in both seats before the pool
state can be changed.
"""

from __future__ import annotations

from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import random
from typing import Any, Mapping, Sequence

import numpy as np

from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    create_agent,
    load_registry,
)


SCHEMA = "kaggriculture-v11-independent-admission-1"


def _canonical_action(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_action(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonical_action(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    return value


def _sha(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


class _Recorder:
    def __init__(self, agent: Any) -> None:
        self.agent = agent
        self.actions: list[Any] = []

    def __call__(self, obs: Any, configuration: Any = None):
        action = self.agent(obs, configuration)
        self.actions.append(_canonical_action(action))
        return action


def _trajectory(
    registry_path: str,
    target_id: str,
    opponent_id: str,
    target_seat: int,
    seed: int,
) -> dict[str, Any]:
    from kaggle_environments import make

    rng_seed = (int(seed) * 2 + int(target_seat) + 0x11C0DE) % (2**32)
    random.seed(rng_seed)
    np.random.seed(rng_seed)
    registry = load_registry(Path(registry_path))
    target = _Recorder(create_agent(registry, target_id))
    opponent = create_agent(registry, opponent_id)
    agents = [target, opponent] if int(target_seat) == 0 else [opponent, target]
    stderr = io.StringIO()
    random.seed(rng_seed)
    np.random.seed(rng_seed)
    with redirect_stderr(stderr):
        env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
        env.run(agents)
    return {
        "statuses": [str(state.status) for state in env.state],
        "steps": len(env.steps),
        "actions": target.actions,
        "stderr": stderr.getvalue(),
    }


def _normalise_sources(
    sources: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    seen = set()
    for raw in sources:
        split = str(raw.get("split") or "").lower()
        split = "validation" if split == "val" else split
        row = {
            "date": str(raw.get("date") or raw.get("source_date") or "")[:10],
            "episode_id": str(raw.get("episode_id") or ""),
            "seed": int(raw.get("seed") or 0),
            "split": split,
        }
        key = (row["date"], row["episode_id"], row["seed"])
        if split not in {"train", "validation"}:
            raise ValueError("independent admission source must be train/validation")
        if not row["date"] or not row["seed"] or key in seen:
            raise ValueError("independent admission needs six explicit unique sources")
        seen.add(key)
        result.append(row)
    if len(result) != 6:
        raise ValueError("independent admission requires exactly six sources")
    return result


def verify_candidate(
    registry_path: Path,
    candidate_id: str,
    parent_id: str,
    sources: Sequence[Mapping[str, Any]],
    *,
    workers: int = 1,
) -> dict[str, Any]:
    """Rerun 12 candidate + 12 direct-parent control trajectories."""

    registry_path = registry_path.expanduser().resolve()
    registry = load_registry(registry_path)
    registry.require(candidate_id)
    registry.require(parent_id)
    source_rows = _normalise_sources(sources)
    jobs = []
    for index, source in enumerate(source_rows):
        for seat in (0, 1):
            jobs.extend(
                [
                    (index, seat, "candidate", candidate_id, int(source["seed"])),
                    (index, seat, "control", parent_id, int(source["seed"])),
                ]
            )
    results: dict[tuple[int, int, str], dict[str, Any]] = {}
    if int(workers) <= 1:
        for index, seat, kind, target, seed in jobs:
            results[(index, seat, kind)] = _trajectory(
                str(registry_path), target, parent_id, seat, seed
            )
    else:
        with ProcessPoolExecutor(max_workers=min(int(workers), len(jobs))) as pool:
            futures = {
                pool.submit(
                    _trajectory,
                    str(registry_path),
                    target,
                    parent_id,
                    seat,
                    seed,
                ): (index, seat, kind)
                for index, seat, kind, target, seed in jobs
            }
            for future in as_completed(futures):
                results[futures[future]] = future.result()

    changed_games = 0
    changed_steps = 0
    components: Counter[str] = Counter()
    trajectories = []
    all_done = True
    all_720 = True
    zero_stderr = True
    for index, source in enumerate(source_rows):
        for seat in (0, 1):
            candidate = results[(index, seat, "candidate")]
            control = results[(index, seat, "control")]
            local = Counter()
            local_steps = 0
            for left, right in zip(candidate["actions"], control["actions"]):
                changed = False
                if isinstance(left, Mapping) and isinstance(right, Mapping):
                    for component in ("market", "farmer", "hands"):
                        if left.get(component) != right.get(component):
                            local[component] += 1
                            changed = True
                elif left != right:
                    local["whole_action"] += 1
                    changed = True
                local_steps += int(changed)
            length_delta = abs(len(candidate["actions"]) - len(control["actions"]))
            local_steps += length_delta
            local["trajectory_length"] += length_delta
            changed_games += int(local_steps > 0)
            changed_steps += local_steps
            components.update(local)
            candidate_done = candidate["statuses"] == ["DONE", "DONE"]
            control_done = control["statuses"] == ["DONE", "DONE"]
            all_done = all_done and candidate_done and control_done
            all_720 = (
                all_720
                and candidate["steps"] == 720
                and control["steps"] == 720
            )
            zero_stderr = zero_stderr and not candidate["stderr"] and not control["stderr"]
            trajectories.append(
                {
                    **source,
                    "target_seat": seat,
                    "candidate_done": candidate_done,
                    "control_done": control_done,
                    "candidate_steps": candidate["steps"],
                    "control_steps": control["steps"],
                    "candidate_action_sha256": _sha(candidate["actions"]),
                    "control_action_sha256": _sha(control["actions"]),
                    "changed_steps": local_steps,
                    "stderr_bytes": len(candidate["stderr"].encode("utf-8"))
                    + len(control["stderr"].encode("utf-8")),
                }
            )
    passed = all_done and all_720 and zero_stderr and changed_games > 0 and changed_steps > 0
    return {
        "schema": SCHEMA,
        "registry": str(registry_path),
        "registry_file_sha256": hashlib.sha256(registry_path.read_bytes()).hexdigest(),
        "candidate_id": str(candidate_id),
        "parent_id": str(parent_id),
        "development_sources": source_rows,
        "development_sources_sha256": _sha(source_rows),
        "seeds": 6,
        "seat_assignments": 2,
        "candidate_games": 12,
        "parent_control_games": 12,
        "all_done": all_done,
        "all_720_steps": all_720,
        "zero_stderr": zero_stderr,
        "changed_games": changed_games,
        "changed_steps": changed_steps,
        "component_changed_steps": dict(sorted(components.items())),
        "real_action_difference": changed_games > 0 and changed_steps > 0,
        "passed": passed,
        "trajectories": trajectories,
    }

