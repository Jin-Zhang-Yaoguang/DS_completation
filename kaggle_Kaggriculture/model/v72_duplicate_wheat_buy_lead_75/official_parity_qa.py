#!/usr/bin/env python3
"""Recompute 16 frozen V72 Confirmation sources in official Python 1.32.7."""

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
DATA = PROJECT / "model_data/loop_evaluations/v72_duplicate_wheat_buy_lead_75"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path.insert(0, str(FACTORY))

from agent_factory import Registry, create_agent  # type: ignore
from kaggle_environments import make
from kaggle_environments.agent import get_last_callable

OPPONENTS = {
    "v19": MODEL / "v19_hierarchical_moe/main.py",
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
    "v32": MODEL / "v32_clone_horizon_preempt/main.py",
    "v33": MODEL / "v33_demand_gap_horizon4/main.py",
    "v34": MODEL / "v34_demand_boundary_preempt/main.py",
    "v37": MODEL / "v37_preterminal_boundary_preempt/main.py",
    "v46": MODEL / "v46_full_terminal_front_run/main.py",
    "v51": MODEL / "v51_post_action_terminal_sell/main.py",
    "v52": MODEL / "v52_terminal_route_acceleration/main.py",
    "v53": MODEL / "v53_terminal_access_flush/main.py",
    "v54": MODEL / "v54_terminal_water_bypass/main.py",
    "v66": MODEL / "v66_margin_gated_sell_bubble/main.py",
    "v70": MODEL / "v70_duplicate_wheat_buy_lead/main.py",
    "v71": MODEL / "v71_duplicate_wheat_buy_lead_50/main.py",
}
PARENT = MODEL / "v71_duplicate_wheat_buy_lead_50/main.py"
SOURCE_MANIFEST = DATA / "confirmation_source_manifest.json"
CPP_GAMES = DATA / "confirmation_games.jsonl"
PARITY_MANIFEST = DATA / "official_parity_source_manifest.json"
PACKAGE_SOURCE = DATA / "official_parity_package_main.py"
EXPECTED_ARCHIVE_SHA = "aaa1628aa9416e88e6f1bd8bc9812c373a12a172bd0e69c4f797e97fcbad6979"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def freeze_sources() -> list[dict]:
    if PARITY_MANIFEST.exists():
        return json.loads(PARITY_MANIFEST.read_text(encoding="utf-8"))["sources"]
    sources = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))["sources"]
    groups: dict[str, list[dict]] = {}
    for row in sources:
        groups.setdefault(str(row["first_shop"]), []).append(row)
    selected = []
    for shop in sorted(groups):
        groups[shop].sort(key=lambda row: hashlib.sha256(
            f"v72-official-parity-v1:{row['episode_id']}:{row['seed']}".encode()).hexdigest())
        selected.extend(groups[shop][:2])
    if len(selected) != 16:
        raise RuntimeError("official parity must freeze exactly two sources per first-shop regime")
    PARITY_MANIFEST.write_text(json.dumps({
        "schema": "kaggriculture-v72-official-parity-sources-v1",
        "selection": "two hash-ranked Confirmation sources per first-shop regime",
        "source_count": len(selected), "sources": selected,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return selected


def raw_candidate():
    return get_last_callable(PACKAGE_SOURCE.read_text(encoding="utf-8"), path=str(PACKAGE_SOURCE))


def loaded(path: Path, model_id: str):
    registry = Registry(path=HERE / "official_parity_registry.json", models={}, raw={})
    return create_agent(registry, {"id": model_id, "kind": "python", "path": str(path), "entrypoint": "agent"})


def policy(mode: str, family: str, source_id: str, seat: int):
    if mode == "candidate":
        return raw_candidate()
    return loaded(PARENT, f"parent_{family}_{source_id}_{seat}_{os.getpid()}_{random.random()}")


def opponent(mode: str, family: str, source_id: str, seat: int):
    return loaded(OPPONENTS[family], f"opp_{mode}_{family}_{source_id}_{seat}_{os.getpid()}_{random.random()}")


def run(task: dict) -> dict:
    mode, family, source_id, seed, seat = task["mode"], task["family"], task["source_id"], task["seed"], task["seat"]
    try:
        own, rival = policy(mode, family, source_id, seat), opponent(mode, family, source_id, seat)
        agents = [None, None]
        agents[seat], agents[1 - seat] = own, rival
        calls = [0, 0]
        wrapped = []
        for index, agent in enumerate(agents):
            def call(obs, config=None, agent=agent, index=index):
                calls[index] += 1
                return agent(obs, config)
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


def main() -> None:
    if sha256(HERE / "submission.tar.gz") != EXPECTED_ARCHIVE_SHA:
        raise RuntimeError("archive drift before official parity")
    with tarfile.open(HERE / "submission.tar.gz", "r:gz") as archive:
        PACKAGE_SOURCE.write_bytes(archive.extractfile("main.py").read())
    sources = freeze_sources()
    source_ids = {str(row["episode_id"]) for row in sources}
    cpp = {}
    for line in CPP_GAMES.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if str(row["source_id"]) in source_ids:
            cpp[(row["mode"], row["family"], str(row["source_id"]), int(row["seat"]))] = row
    tasks = []
    for source in sources:
        for mode in ("candidate", "parent"):
            for family in OPPONENTS:
                for seat in (0, 1):
                    row = cpp[(mode, family, str(source["episode_id"]), seat)]
                    tasks.append({"mode": mode, "family": family, "source_id": str(source["episode_id"]),
                                  "seed": int(source["seed"]), "seat": seat, "date": source["date"],
                                  "first_shop": source["first_shop"],
                                  "cpp_rewards": [float(row["own"]), float(row["opponent"])] if seat == 0
                                  else [float(row["opponent"]), float(row["own"])]})
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(12, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(run, tasks, chunksize=1))
    result = {"schema": "kaggriculture-v72-official-parity-v1",
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
        and result["calls_719_games"] == result["games"]
        and result["error_count"] == 0 and result["raw_loader_selected_callable"] == "agent") else "FAIL"
    (DATA / "official_parity_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "official_parity_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
