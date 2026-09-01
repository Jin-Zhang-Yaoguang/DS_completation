#!/usr/bin/env python3
"""Verify V119 archive structure and exact source/package behavior."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
import sys
import tarfile
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
sys.path[:0] = [str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]

import kagsim  # type: ignore  # noqa: E402
from agent_factory import Registry, create_agent  # type: ignore  # noqa: E402


SEED = 1385806507
REPLAY = HERE / "evidence/episode-103982514-replay.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path, model_id: str):
    registry = Registry(path=HERE / "package_registry.json", models={}, raw={})
    return create_agent(registry, {
        "id": model_id, "kind": "python", "path": str(path), "entrypoint": "agent",
    })


def play(path: Path, candidate_seat: int, replay: dict, model_id: str) -> dict:
    candidate = load(path, model_id)
    opponent_tape = [copy.deepcopy(step[0].get("action") or {}) for step in replay["steps"][1:720]]
    game = kagsim.Game(SEED)
    actions = []
    while not game.done:
        step = int(game.observe(0)["step"])
        own_action = candidate(game.observe(candidate_seat))
        both = [None, None]
        both[candidate_seat] = own_action
        both[1 - candidate_seat] = copy.deepcopy(opponent_tape[step])
        game.step(*both)
        actions.append(own_action)
    return {
        "seat": candidate_seat,
        "turns": len(actions),
        "actions": actions,
        "rewards": [float(game.reward(0)), float(game.reward(1))],
    }


def main() -> int:
    archive_path = HERE / "submission.tar.gz"
    source_path = HERE / "main.py"
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    with TemporaryDirectory(prefix="v119_package_qa_") as directory:
        root = Path(directory)
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
            member_names = [member.name for member in members]
            safe_members = all(
                member.name == "main.py" and member.isfile()
                and not member.issym() and not member.islnk()
                for member in members
            )
            archive.extractall(root, filter="data")
        package_main = root / "main.py"
        bytes_exact = source_path.read_bytes() == package_main.read_bytes()
        tree = ast.parse(package_main.read_text(encoding="utf-8"))
        callables = [
            node.name for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        rows = []
        for seat in (0, 1):
            source = play(source_path, seat, replay, f"source_{seat}")
            package = play(package_main, seat, replay, f"package_{seat}")
            rows.append({
                "seat": seat,
                "turns": source["turns"],
                "actions_exact": source["actions"] == package["actions"],
                "rewards_exact": source["rewards"] == package["rewards"],
                "source_rewards": source["rewards"],
                "package_rewards": package["rewards"],
            })

    result = {
        "schema": "kaggriculture-v119-package-qa-v1",
        "engine": str(kagsim.ENGINE_VERSION),
        "archive_sha256": sha256(archive_path),
        "main_sha256": sha256(source_path),
        "archive_members": member_names,
        "only_top_level_main_py": member_names == ["main.py"] and safe_members,
        "archive_source_bytes_exact": bytes_exact,
        "selected_callable": callables[-1] if callables else None,
        "games": len(rows),
        "exact_action_games": sum(row["actions_exact"] for row in rows),
        "exact_reward_games": sum(row["rewards_exact"] for row in rows),
        "all_719_calls": all(row["turns"] == 719 for row in rows),
        "rows": rows,
    }
    result["gate"] = "PASS" if (
        result["engine"] == "1.32.7"
        and result["only_top_level_main_py"]
        and result["archive_source_bytes_exact"]
        and result["selected_callable"] == "agent"
        and result["exact_action_games"] == result["games"]
        and result["exact_reward_games"] == result["games"]
        and result["all_719_calls"]
    ) else "FAIL"
    (HERE / "package_qa_results.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: value for key, value in result.items() if key != "rows"},
                     ensure_ascii=False, indent=2))
    return 0 if result["gate"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
