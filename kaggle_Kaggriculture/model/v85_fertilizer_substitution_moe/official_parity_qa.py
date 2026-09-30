#!/usr/bin/env python3
"""Recompute 16 frozen V85 Confirmation sources in official Python 1.32.7."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import tarfile


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
PROJECT = MODEL.parent
DATA = PROJECT / "model_data/loop_evaluations/v85_fertilizer_substitution_moe"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path.insert(0, str(FACTORY))
from agent_factory import Registry, create_agent  # type: ignore
from kaggle_environments import make
from kaggle_environments.agent import get_last_callable


OPPONENTS = {
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
    "v32": MODEL / "v32_clone_horizon_preempt/main.py",
    "v54": MODEL / "v54_terminal_water_bypass/main.py",
    "v66": MODEL / "v66_margin_gated_sell_bubble/main.py",
    "v76": MODEL / "v76_adjacent_safe_buy_lead/main.py",
}
PARENT = MODEL / "v76_adjacent_safe_buy_lead/main.py"
SOURCE_MANIFEST = DATA / "confirmation_source_manifest.json"
CPP_GAMES = DATA / "confirmation_games.jsonl"
PARITY_MANIFEST = DATA / "official_parity_source_manifest.json"
PACKAGE_DIR = DATA / "official_parity_package"
PACKAGE_SOURCE = PACKAGE_DIR / "main.py"
EXPECTED_ARCHIVE_SHA = "c2e822ec1d56f76f2edb857b2877041a38257f876cbe14de7d2c4cbd153fe51f"


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def freeze_sources():
    if PARITY_MANIFEST.exists():
        return json.loads(PARITY_MANIFEST.read_text(encoding="utf-8"))["sources"]
    sources = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))["sources"]
    groups = {}
    for row in sources:
        groups.setdefault(str(row["first_shop"]), []).append(row)
    selected = []
    for shop in sorted(groups):
        groups[shop].sort(key=lambda row: hashlib.sha256(
            f"v85-official-parity-v1:{row['episode_id']}:{row['seed']}".encode()).hexdigest())
        selected.extend(groups[shop][:2])
    if len(selected) != 16:
        raise RuntimeError("official parity requires two sources per shop regime")
    PARITY_MANIFEST.write_text(json.dumps({
        "schema": "kaggriculture-v85-official-parity-sources-v1",
        "selection": "two hash-ranked Confirmation sources per first-shop regime",
        "source_count": len(selected), "sources": selected,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return selected


def raw_candidate():
    return get_last_callable(PACKAGE_SOURCE.read_text(encoding="utf-8"), path=str(PACKAGE_SOURCE))


def loaded(path: Path, model_id: str):
    registry = Registry(path=HERE / "official_parity_registry.json", models={}, raw={})
    return create_agent(registry, {"id": model_id, "kind": "python", "path": str(path), "entrypoint": "agent"})


def policy(mode, family, source_id, seat):
    if mode == "candidate":
        return raw_candidate()
    return loaded(PARENT, f"parent_{family}_{source_id}_{seat}_{os.getpid()}_{random.random()}")


def opponent(mode, family, source_id, seat):
    return loaded(OPPONENTS[family], f"opp_{mode}_{family}_{source_id}_{seat}_{os.getpid()}_{random.random()}")


def run(task):
    mode, family, source_id, seed, seat = task["mode"], task["family"], task["source_id"], task["seed"], task["seat"]
    try:
        own, rival = policy(mode, family, source_id, seat), opponent(mode, family, source_id, seat)
        agents = [None, None]
        agents[seat], agents[1 - seat] = own, rival
        calls = [0, 0]
        wrapped = []
        for index, current in enumerate(agents):
            def call(obs, config=None, current=current, index=index):
                calls[index] += 1
                return current(obs, config)
            wrapped.append(call)
        env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": int(seed)}, debug=False)
        env.run(wrapped)
        rewards = [float(state.reward or 0) for state in env.state]
        statuses = [str(state.status) for state in env.state]
        cpp_margin = float(task["cpp_rewards"][seat]) - float(task["cpp_rewards"][1 - seat])
        official_margin = rewards[seat] - rewards[1 - seat]
        return {**task, "official_rewards": rewards, "official_statuses": statuses,
                "official_calls": calls, "exact_rewards": rewards == task["cpp_rewards"],
                "same_margin_direction": (cpp_margin > 0) == (official_margin > 0)
                and (cpp_margin < 0) == (official_margin < 0), "error": None}
    except Exception as exc:
        return {**task, "error": f"{type(exc).__name__}: {exc}",
                "exact_rewards": False, "same_margin_direction": False}


def main():
    if sha256(HERE / "submission.tar.gz") != EXPECTED_ARCHIVE_SHA:
        raise RuntimeError("archive drift before official parity")
    PACKAGE_DIR.mkdir(parents=True, exist_ok=True)
    with tarfile.open(HERE / "submission.tar.gz", "r:gz") as archive:
        for name in ("main.py", "parent_v76.py"):
            (PACKAGE_DIR / name).write_bytes(archive.extractfile(name).read())
    sources = freeze_sources()
    source_ids = {str(row["episode_id"]) for row in sources}
    cpp = {}
    for line in CPP_GAMES.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if str(row["source_id"]) in source_ids:
            cpp[row["mode"], row["family"], str(row["source_id"]), int(row["seat"])] = row
    tasks = []
    for source in sources:
        for mode in ("candidate", "parent"):
            for family in OPPONENTS:
                for seat in (0, 1):
                    row = cpp[mode, family, str(source["episode_id"]), seat]
                    rewards = ([float(row["own"]), float(row["opponent"])] if seat == 0
                               else [float(row["opponent"]), float(row["own"])])
                    tasks.append({"mode": mode, "family": family, "source_id": str(source["episode_id"]),
                                  "seed": int(source["seed"]), "seat": seat, "date": source["date"],
                                  "first_shop": source["first_shop"], "cpp_rewards": rewards})
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(12, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(run, tasks, chunksize=1))
    result = {"schema": "kaggriculture-v85-official-parity-v1",
              "official_engine": "kaggle_environments 1.32.7", "source_count": len(sources),
              "games": len(rows), "exact_reward_games": sum(row["exact_rewards"] for row in rows),
              "same_margin_direction_games": sum(row["same_margin_direction"] for row in rows),
              "done_done_games": sum(row.get("official_statuses") == ["DONE", "DONE"] for row in rows),
              "calls_719_games": sum(row.get("official_calls") == [719, 719] for row in rows),
              "error_count": sum(bool(row.get("error")) for row in rows),
              "raw_loader_selected_callable": getattr(raw_candidate(), "__name__", None), "rows": rows}
    result["gate"] = "PASS" if (result["exact_reward_games"] == result["games"]
        and result["same_margin_direction_games"] == result["games"]
        and result["done_done_games"] == result["games"]
        and result["calls_719_games"] == result["games"] and result["error_count"] == 0
        and result["raw_loader_selected_callable"] == "agent") else "FAIL"
    (DATA / "official_parity_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "official_parity_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
