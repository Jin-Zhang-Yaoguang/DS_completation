#!/usr/bin/env python3
"""Verify V115 archive structure, source equality, raw load, and deterministic calls."""

from __future__ import annotations

import hashlib
import importlib.util
from io import BytesIO
import json
from pathlib import Path
import sys
import tarfile


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
sys.path.insert(0, str(sorted((CPPSIM / "build").glob("lib.*"))[-1]))
import kagsim  # type: ignore


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def load_bytes(data, name):
    namespace = {"__name__": name, "__file__": f"{name}.py"}
    exec(compile(data, f"{name}.py", "exec"), namespace)
    return namespace


def load_path(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def play(agent, opponent_path, seed, seat, capture=False):
    opponent = load_path(opponent_path, f"qa_opp_{seed}_{seat}_{id(agent)}")
    game = kagsim.Game(seed)
    actions_seen = []
    calls = violations = 0
    while not game.done:
        observations = [game.observe(0), game.observe(1)]
        actions = [None, None]
        actions[seat] = agent(observations[seat])
        actions[1 - seat] = opponent.agent(observations[1 - seat])
        expected = len(observations[seat]["farms"][seat].get("hands", []) or [])
        violations += int(len(actions[seat].get("market", []) or []) > 10 or len(actions[seat].get("hands", []) or []) != expected)
        if capture:
            actions_seen.append(actions[seat])
        game.step(actions[0], actions[1])
        calls += 1
    return {
        "rewards": [float(game.reward(0)), float(game.reward(1))],
        "calls": calls,
        "violations": violations,
        "actions": actions_seen,
    }


def main():
    archive_path = HERE / "submission.tar.gz"
    source_data = (HERE / "main.py").read_bytes()
    with tarfile.open(archive_path, "r:gz") as archive:
        names = archive.getnames()
        member = archive.getmember("main.py") if names == ["main.py"] else None
        archived_data = archive.extractfile(member).read() if member is not None else b""
    source_module = load_bytes(source_data, "v115_source_qa")
    archive_module = load_bytes(archived_data, "v115_archive_qa")
    opponent = MODEL / "v76_adjacent_safe_buy_lead/main.py"
    rows = []
    for seed in (115001, 115002):
        for seat in (0, 1):
            source = play(source_module["agent"], opponent, seed, seat, capture=True)
            archive = play(archive_module["agent"], opponent, seed, seat, capture=True)
            rows.append({
                "seed": seed,
                "seat": seat,
                "source_rewards": source["rewards"],
                "archive_rewards": archive["rewards"],
                "source_calls": source["calls"],
                "archive_calls": archive["calls"],
                "source_violations": source["violations"],
                "archive_violations": archive["violations"],
                "actions_exact": source["actions"] == archive["actions"],
            })
    passed = (
        names == ["main.py"]
        and source_data == archived_data
        and all(
            row["source_rewards"] == row["archive_rewards"]
            and row["source_calls"] == row["archive_calls"] == 719
            and row["source_violations"] == row["archive_violations"] == 0
            and row["actions_exact"]
            for row in rows
        )
    )
    payload = {
        "schema": "kaggriculture-v115-package-qa-v1",
        "engine": str(kagsim.ENGINE_VERSION),
        "archive_members": names,
        "source_sha256": sha_bytes(source_data),
        "archived_main_sha256": sha_bytes(archived_data),
        "source_archive_main_exact": source_data == archived_data,
        "raw_loader_callable": callable(archive_module.get("agent")),
        "games": len(rows),
        "rows": rows,
        "status": "PASS" if passed else "FAIL",
    }
    (HERE / "package_qa_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()

