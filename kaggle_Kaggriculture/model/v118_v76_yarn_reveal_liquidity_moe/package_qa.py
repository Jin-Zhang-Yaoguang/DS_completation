#!/usr/bin/env python3
"""Verify archive structure and exact source/package serving equivalence."""

from __future__ import annotations

import ast
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


SEEDS = (111406515, 200111900, 208899670, 306678837,
         322754288, 343166320, 347218322, 363531319)
OPPONENT = MODEL / "v76_adjacent_safe_buy_lead/main.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path, model_id: str):
    registry = Registry(path=HERE / "package_registry.json", models={}, raw={})
    return create_agent(registry, {
        "id": model_id, "kind": "python", "path": str(path), "entrypoint": "agent",
    })


def play_pair(source_path: Path, package_path: Path, seed: int, seat: int) -> dict:
    source_agent = load(source_path, f"source_{seed}_{seat}")
    package_agent = load(package_path, f"package_{seed}_{seat}")
    source_opp = load(OPPONENT, f"source_opp_{seed}_{seat}")
    package_opp = load(OPPONENT, f"package_opp_{seed}_{seat}")
    source_agents = [source_opp, source_opp]
    package_agents = [package_opp, package_opp]
    source_agents[seat] = source_agent
    package_agents[seat] = package_agent
    source_game, package_game = kagsim.Game(seed), kagsim.Game(seed)
    exact_actions, turns = True, 0
    while not source_game.done and not package_game.done:
        source_obs = [source_game.observe(0), source_game.observe(1)]
        package_obs = [package_game.observe(0), package_game.observe(1)]
        source_actions = [source_agents[i](source_obs[i]) for i in (0, 1)]
        package_actions = [package_agents[i](package_obs[i]) for i in (0, 1)]
        exact_actions = exact_actions and source_actions == package_actions
        source_game.step(*source_actions)
        package_game.step(*package_actions)
        turns += 1
    source_rewards = [float(source_game.reward(i)) for i in (0, 1)]
    package_rewards = [float(package_game.reward(i)) for i in (0, 1)]
    return {
        "seed": seed, "candidate_seat": seat, "turns": turns,
        "actions_exact": exact_actions, "source_rewards": source_rewards,
        "package_rewards": package_rewards,
        "rewards_exact": source_rewards == package_rewards,
    }


def main() -> int:
    archive_path = HERE / "submission.tar.gz"
    source_path = HERE / "main.py"
    with TemporaryDirectory(prefix="v118_package_qa_") as directory:
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
        rows = [
            play_pair(source_path, package_main, seed, seat)
            for seed in SEEDS for seat in (0, 1)
        ]
    result = {
        "schema": "kaggriculture-v118-package-qa-v1",
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
