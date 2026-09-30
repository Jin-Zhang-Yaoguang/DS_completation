"""Independent clean-archive QA for V12A2 on already-exposed QA seeds."""

from __future__ import annotations

from contextlib import redirect_stderr
import hashlib
from io import StringIO
import json
from pathlib import Path
import random
import tarfile
from tempfile import TemporaryDirectory
from typing import Any

import numpy as np

from kaggle_Kaggriculture.model.v12a2_no_wool_throttle import main as source_main
from kaggle_Kaggriculture.model.v12a_terminal_branch_guard import (
    build_submission as parent_build,
)


HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / "submission.tar.gz"
MANIFEST = HERE / "submission_manifest.json"
OUTPUT = HERE / "package_qa_report.json"
SEEDS = (93451031, 93451032, 93451033)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TraceAgent:
    def __init__(self, handle: Any) -> None:
        self.handle = handle
        self.actions: list[dict[str, Any]] = []

    def __call__(self, obs: Any, configuration: Any = None) -> Any:
        action = self.handle(obs, configuration)
        self.actions.append(json.loads(json.dumps(action)))
        return action


def _run(factory: Any, seed: int, seat: int) -> dict[str, Any]:
    from kaggle_environments import make
    from kaggle_environments.envs.kaggriculture import kaggriculture as kg

    random.seed(seed * 104729 + seat * 1009)
    np.random.seed((seed + seat * 65537) % (2**32 - 1))
    traced = TraceAgent(factory())
    agents = [traced, kg.starter_agent] if seat == 0 else [kg.starter_agent, traced]
    stderr = StringIO()
    with redirect_stderr(stderr):
        steps = make(
            "kaggriculture", configuration={"seed": seed}, debug=False
        ).run(agents)
    final = steps[-1]
    diagnostics = traced.handle.diagnostics()
    action_bytes = json.dumps(
        traced.actions, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "steps": len(steps),
        "calls": len(traced.actions),
        "statuses": [str(state.status) for state in final],
        "rewards": [float(state.reward or 0.0) for state in final],
        "actions": traced.actions,
        "action_sha256": hashlib.sha256(action_bytes).hexdigest(),
        "stderr": stderr.getvalue(),
        "residual_fallbacks": diagnostics.get("residual_fallbacks"),
        "model_id": diagnostics.get("model_id"),
    }


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    with TemporaryDirectory(prefix="v12a2_package_qa_") as directory:
        extract = Path(directory) / "extract"
        extract.mkdir()
        with tarfile.open(ARCHIVE, "r:gz") as archive:
            members = archive.getmembers()
            archive.extractall(extract, filter="data")
        clean_main = parent_build._load_clean_main(extract / "main.py")
        games = []
        for seed in SEEDS:
            for seat in (0, 1):
                source = _run(source_main.make_agent, seed, seat)
                clean = _run(clean_main.make_agent, seed, seat)
                games.append(
                    {
                        "seed": seed,
                        "seat": seat,
                        "steps": clean["steps"],
                        "calls": clean["calls"],
                        "statuses": clean["statuses"],
                        "rewards": clean["rewards"],
                        "action_sha256": clean["action_sha256"],
                        "source_action_equal": clean["actions"] == source["actions"],
                        "source_reward_equal": clean["rewards"] == source["rewards"],
                        "stderr": clean["stderr"],
                        "source_stderr": source["stderr"],
                        "residual_fallbacks": clean["residual_fallbacks"],
                        "model_id": clean["model_id"],
                    }
                )
        extracted_files = {
            str(path.relative_to(extract)): {
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in extract.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        }
    expected_files = {
        str(item["path"]): {
            "size_bytes": int(item["size_bytes"]),
            "sha256": str(item["sha256"]),
        }
        for item in manifest["files"]
    }
    member_paths = [member.name for member in members]
    safe_members = all(
        not Path(name).is_absolute() and ".." not in Path(name).parts
        for name in member_paths
    )
    regular_only = all(member.isfile() for member in members)
    checks = {
        "archive_manifest_size_hash": (
            ARCHIVE.stat().st_size == int(manifest["archive_size_bytes"])
            and _sha256(ARCHIVE) == manifest["archive_sha256"]
        ),
        "manifest_file_records_match": extracted_files == expected_files,
        "safe_relative_regular_members_only": safe_members and regular_only,
        "no_duplicate_members": len(member_paths) == len(set(member_paths)),
        "source_wrapper_matches_packaged": (
            extracted_files["main.py"]["sha256"] == _sha256(HERE / "main.py")
        ),
        "parent_base_matches_packaged": (
            extracted_files["base_agent.py"]["sha256"]
            == _sha256(HERE.parent / "v12a_terminal_branch_guard" / "main.py")
        ),
        "three_exposed_qa_seeds_both_seats": len(games) == 6,
        "all_720_steps_719_calls_done_done": all(
            game["steps"] == 720
            and game["calls"] == 719
            and game["statuses"] == ["DONE", "DONE"]
            for game in games
        ),
        "zero_stderr_and_fallbacks": all(
            not game["stderr"]
            and not game["source_stderr"]
            and game["residual_fallbacks"] == 0
            for game in games
        ),
        "source_archive_exact_actions_rewards": all(
            game["source_action_equal"] and game["source_reward_equal"]
            for game in games
        ),
        "diagnostics_identify_a2": all(
            game["model_id"] == "v12a2_no_wool_throttle" for game in games
        ),
    }
    payload = {
        "schema": "v12a2-package-qa-1",
        "candidate": "v12a2_no_wool_throttle",
        "archive": {
            "path": str(ARCHIVE.resolve()),
            "size_bytes": ARCHIVE.stat().st_size,
            "sha256": _sha256(ARCHIVE),
        },
        "qa_seeds_are_previously_exposed": True,
        "formal_or_test_accessed": False,
        "games": games,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
    }
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    if payload["verdict"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
