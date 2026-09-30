"""Independent clean-package QA for the final V12B-v2 archive.

Only previously exposed V12B-v1 QA seeds are used.  Each packaged run is
executed in a fresh subprocess whose cwd is the extracted archive and whose
PYTHONPATH is empty.  Its full action trace is then compared with a fresh
instance loaded from the V10 registry.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
from typing import Any

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as kg

from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    create_agent,
    load_registry,
)


HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / "submission.tar.gz"
MANIFEST = HERE / "submission_manifest.json"
REGISTRY = HERE / "registry_entry.json"
OUTPUT = HERE / "package_qa_v2_report.json"
MODEL_ID = "v12b_v2_winrisk_feedback_gate"
SEEDS = (93451031, 93451032, 93451033)
EXPECTED_MEMBERS = ("main.py", "parent_agent.py")
EXPECTED_PARENT_SHA256 = "ed2e443f6ae3683da9f34c55920bc8aa06a81e22e3b905df92389597e8adc327"
PARENT_SOURCE = HERE.parent / "v8_kawa_lead2_slot" / "main.py"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def action_sha256(actions: list[Any]) -> str:
    payload = json.dumps(
        actions,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def inspect_archive() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    duplicates: list[str] = []
    names: list[str] = []
    unsafe: list[str] = []
    non_regular: list[str] = []
    with tarfile.open(ARCHIVE, "r:gz") as archive:
        seen: set[str] = set()
        for member in archive.getmembers():
            name = member.name
            names.append(name)
            if name in seen:
                duplicates.append(name)
            seen.add(name)
            pure = PurePosixPath(name)
            if pure.is_absolute() or ".." in pure.parts:
                unsafe.append(name)
            if not member.isfile():
                non_regular.append(name)
    members = sorted(names)
    return {
        "path": ARCHIVE.name,
        "size_bytes": ARCHIVE.stat().st_size,
        "sha256": sha256(ARCHIVE),
        "manifest_size_match": manifest.get("size_bytes") == ARCHIVE.stat().st_size,
        "manifest_sha256_match": manifest.get("sha256") == sha256(ARCHIVE),
        "manifest_members_match": sorted(manifest.get("files") or []) == list(EXPECTED_MEMBERS),
        "members": members,
        "safe_relative_regular_members_only": not unsafe and not non_regular,
        "duplicate_members": duplicates,
        "unsafe_members": unsafe,
        "non_regular_members": non_regular,
        "extra_or_missing_members": sorted(set(members).symmetric_difference(EXPECTED_MEMBERS)),
        "pycache_or_pyc_members": [
            name for name in names if "__pycache__" in name or name.endswith(".pyc")
        ],
    }


CLEAN_RUNNER = r'''import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as kg


def digest(actions):
    payload = json.dumps(actions, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


root = Path.cwd()
project_importable_before = importlib.util.find_spec("kaggle_Kaggriculture") is not None
spec = importlib.util.spec_from_file_location("main", root / "main.py")
module = importlib.util.module_from_spec(spec)
sys.modules["main"] = module
spec.loader.exec_module(module)
actions = []


def tracked(obs, configuration=None):
    action = module.agent(obs, configuration)
    actions.append(action)
    return action


seed = int(sys.argv[1])
seat = int(sys.argv[2])
agents = [tracked, kg.starter_agent]
if seat == 1:
    agents.reverse()
env = make("kaggriculture", configuration={"seed": seed}, debug=True)
steps = env.run(agents)
loaded_local = sorted(
    str(Path(value.__file__).resolve().relative_to(root))
    for value in list(sys.modules.values())
    if getattr(value, "__file__", None)
    and Path(value.__file__).resolve().is_relative_to(root)
)
print(json.dumps({
    "seed": seed,
    "seat": seat,
    "steps": len(steps),
    "calls": len(actions),
    "statuses": [str(state.status) for state in steps[-1]],
    "rewards": [float(state.reward or 0) for state in steps[-1]],
    "action_sha256": digest(actions),
    "runtime_errors": module.model_status().get("errors", []),
    "project_source_importable_before_package_load": project_importable_before,
    "bundled_modules_loaded": loaded_local,
}, ensure_ascii=False))
'''


def clean_game(extracted: Path, seed: int, seat: int) -> tuple[dict[str, Any], str]:
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment["PYTHONPYCACHEPREFIX"] = "/tmp/v12b-v2-package-qa-pycache"
    process = subprocess.run(
        [sys.executable, "-c", CLEAN_RUNNER, str(seed), str(seat)],
        cwd=extracted,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(
            f"clean package failed seed={seed} seat={seat}: {process.stderr}"
        )
    lines = [line for line in process.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"clean package emitted no result seed={seed} seat={seat}")
    return json.loads(lines[-1]), process.stderr


def registry_game(seed: int, seat: int) -> dict[str, Any]:
    registry = load_registry(REGISTRY)
    candidate = create_agent(registry, MODEL_ID)
    actions: list[Any] = []

    def tracked(obs: Any, configuration: Any = None):
        action = candidate(obs, configuration)
        actions.append(action)
        return action

    agents = [tracked, kg.starter_agent]
    if seat == 1:
        agents.reverse()
    env = make("kaggriculture", configuration={"seed": seed}, debug=True)
    steps = env.run(agents)
    diagnostics = candidate.diagnostics().get("model_status", {})
    return {
        "steps": len(steps),
        "calls": len(actions),
        "statuses": [str(state.status) for state in steps[-1]],
        "rewards": [float(state.reward or 0) for state in steps[-1]],
        "action_sha256": action_sha256(actions),
        "runtime_errors": diagnostics.get("errors", []),
    }


def main() -> None:
    archive = inspect_archive()
    games: list[dict[str, Any]] = []
    with TemporaryDirectory(prefix="v12b_v2_package_qa_") as directory:
        extracted = Path(directory)
        with tarfile.open(ARCHIVE, "r:gz") as source:
            source.extractall(extracted, filter="data")
        packaged_main = extracted / "main.py"
        packaged_parent = extracted / "parent_agent.py"
        archive.update(
            source_main_matches_packaged_main=sha256(HERE / "main.py") == sha256(packaged_main),
            packaged_parent_matches_declared_sha256=sha256(packaged_parent) == EXPECTED_PARENT_SHA256,
        )
        for seed in SEEDS:
            for seat in (0, 1):
                clean, stderr = clean_game(extracted, seed, seat)
                registry = registry_game(seed, seat)
                games.append(
                    {
                        **clean,
                        "registry_action_equal": clean["action_sha256"] == registry["action_sha256"],
                        "registry_reward_equal": clean["rewards"] == registry["rewards"],
                        "registry_steps_equal": clean["steps"] == registry["steps"],
                        "registry_calls_equal": clean["calls"] == registry["calls"],
                        "stderr": stderr,
                        "registry_runtime_errors": registry["runtime_errors"],
                    }
                )

    checks = {
        "archive_integrity": archive["manifest_size_match"] and archive["manifest_sha256_match"],
        "clean_structure": (
            archive["members"] == list(EXPECTED_MEMBERS)
            and archive["safe_relative_regular_members_only"]
            and not archive["duplicate_members"]
            and not archive["pycache_or_pyc_members"]
        ),
        "isolated_bundled_parent_runtime": all(
            not row["project_source_importable_before_package_load"]
            and row["bundled_modules_loaded"] == ["main.py", "parent_agent.py"]
            for row in games
        ),
        "three_exposed_qa_seeds_both_seats": len(games) == len(SEEDS) * 2,
        "all_720_steps_719_calls_done_done": all(
            row["steps"] == 720
            and row["calls"] == 719
            and row["statuses"] == ["DONE", "DONE"]
            for row in games
        ),
        "zero_stderr_and_runtime_errors": all(
            not row["stderr"]
            and not row["runtime_errors"]
            and not row["registry_runtime_errors"]
            for row in games
        ),
        "package_registry_stepwise_action_and_reward_equivalence": all(
            row["registry_action_equal"]
            and row["registry_reward_equal"]
            and row["registry_steps_equal"]
            and row["registry_calls_equal"]
            for row in games
        ),
    }
    payload = {
        "schema": "v12b-v2-independent-package-qa-1",
        "candidate": MODEL_ID,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "data_scope": "previously exposed V12B-v1 package-QA seeds only",
        "formal_panel_accessed": False,
        "new_seed_draw": False,
        "seeds": list(SEEDS),
        "archive": archive,
        "files": [
            {
                "path": name,
                "size_bytes": (
                    (HERE / "main.py").stat().st_size
                    if name == "main.py"
                    else PARENT_SOURCE.stat().st_size
                ),
                "sha256": (
                    sha256(HERE / "main.py")
                    if name == "main.py"
                    else EXPECTED_PARENT_SHA256
                ),
            }
            for name in EXPECTED_MEMBERS
        ],
        "games": games,
        "checks": checks,
    }
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"verdict": payload["verdict"], "checks": checks}, ensure_ascii=False, indent=2))
    if payload["verdict"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
