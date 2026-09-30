"""Independent Kaggle raw-loader red-team for a clean submission archive.

This verifier deliberately does not use a candidate's own package-QA loader.
It executes the extracted ``main.py`` through Kaggle's installed
``get_last_callable`` contract in an isolated subprocess, then compares it
step-for-step with the development source factory on already-exposed QA seeds.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
from typing import Any, Callable

import numpy as np
from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as kg


QA_SEEDS = (93451031, 93451032, 93451033)
PYTHON311 = Path("/opt/anaconda3/envs/quant_xbx/bin/python3.11")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(action: Any) -> str:
    return json.dumps(
        action, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )


def _action_hash(actions: list[str]) -> str:
    digest = hashlib.sha256()
    for action in actions:
        digest.update(action.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


class _Capture:
    def __init__(self, handle: Callable[..., Any]) -> None:
        self.handle = handle
        self.actions: list[str] = []

    def __call__(self, obs: Any, configuration: Any = None) -> Any:
        action = self.handle(obs, configuration)
        self.actions.append(_canonical(action))
        return action


def _load_source(path: Path, project_root: Path) -> Any:
    name = f"raw_loader_redteam_source_{hashlib.sha256(str(path).encode()).hexdigest()[:12]}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load source module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(project_root))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def _source_trajectory(
    source_main: Path, project_root: Path, seed: int, seat: int
) -> dict[str, Any]:
    # Keep the repository root available for lazy imports performed by the
    # development factory after module execution. The clean-package subprocess
    # below remains isolated and explicitly verifies that it cannot do this.
    sys.path.insert(0, str(project_root))
    try:
        module = _load_source(source_main, project_root)
        factory = getattr(module, "make_agent")
        random.seed(seed * 104729 + seat * 1009)
        np.random.seed((seed + seat * 65537) % (2**32 - 1))
        capture = _Capture(factory())
        agents: list[Callable[..., Any]] = [capture, kg.starter_agent]
        if seat == 1:
            agents.reverse()
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            steps = make(
                "kaggriculture", configuration={"seed": seed}, debug=True
            ).run(agents)
    finally:
        sys.path.pop(0)
    return {
        "steps": len(steps),
        "calls": len(capture.actions),
        "statuses": [str(state.status) for state in steps[-1]],
        "rewards": [float(state.reward or 0.0) for state in steps[-1]],
        "actions": capture.actions,
        "action_sha256": _action_hash(capture.actions),
        "stdout": stdout.getvalue(),
        "stderr": stderr.getvalue(),
    }


PACKAGE_RUNNER = r'''
import ast
import contextlib
import hashlib
import importlib.util
import inspect
import io
import json
from pathlib import Path
import random
import sys

import numpy as np
from kaggle_environments import make
from kaggle_environments.agent import get_last_callable, read_file
from kaggle_environments.envs.kaggriculture import kaggriculture as kg

extract = Path(sys.argv[1]).resolve()
seed = int(sys.argv[2])
seat = int(sys.argv[3])
project_root = Path(sys.argv[4]).resolve()
main_path = extract / "main.py"
project_importable_before = importlib.util.find_spec("kaggle_Kaggriculture") is not None

def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def valid_schema(action):
    if not isinstance(action, dict) or set(action) != {"farmer", "hands", "market"}:
        return False
    if not all(isinstance(action[key], list) for key in ("farmer", "hands", "market")):
        return False
    if not action["farmer"] or not isinstance(action["farmer"][0], str):
        return False
    return all(isinstance(row, list) for row in action["hands"] + action["market"])

class Capture:
    def __init__(self, handle):
        self.handle = handle
        self.actions = []
        self.schema_valid = []
    def __call__(self, obs, configuration=None):
        # Kaggle build_agent injects this immediately before invoking the
        # callable selected by get_last_callable.
        try:
            configuration["__raw_path__"] = str(main_path)
        except Exception:
            pass
        # Match build_agent.callable_agent: trim positional arguments to the
        # selected function's declared co_argcount (why model_status() became
        # a silently accepted zero-argument online policy in 55713093).
        args = [obs, configuration]
        if hasattr(self.handle, "__code__") and hasattr(
            self.handle.__code__, "co_argcount"
        ):
            args = args[: self.handle.__code__.co_argcount]
        action = self.handle(*args)
        self.actions.append(canonical(action))
        self.schema_valid.append(valid_schema(action))
        return action

stdout = io.StringIO()
stderr = io.StringIO()
with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
    raw = read_file(main_path)
    selected = get_last_callable(raw, path=str(main_path))
    selected_signature = inspect.signature(selected)
    random.seed(seed * 104729 + seat * 1009)
    np.random.seed((seed + seat * 65537) % (2**32 - 1))
    capture = Capture(selected)
    agents = [capture, kg.starter_agent]
    if seat == 1:
        agents.reverse()
    steps = make("kaggriculture", configuration={"seed": seed}, debug=True).run(agents)

loaded_from_bundle = []
loaded_from_project = []
for name, module in sorted(sys.modules.items()):
    value = getattr(module, "__file__", None)
    if not value:
        continue
    try:
        path = Path(value).resolve()
    except Exception:
        continue
    row = {"module": name, "path": str(path)}
    if path == extract or extract in path.parents:
        loaded_from_bundle.append(row)
    elif path == project_root or project_root in path.parents:
        if "/.venv/" not in str(path):
            loaded_from_project.append(row)

tree = ast.parse(read_file(main_path), filename=str(main_path))
top_callables = [
    node.name for node in tree.body
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
]
noop = '{"farmer":["PASS"],"hands":[],"market":[]}'
digest = hashlib.sha256()
for action in capture.actions:
    digest.update(action.encode("utf-8"))
    digest.update(b"\n")

result = {
    "seed": seed,
    "seat": seat,
    "steps": len(steps),
    "calls": len(capture.actions),
    "statuses": [str(state.status) for state in steps[-1]],
    "rewards": [float(state.reward or 0.0) for state in steps[-1]],
    "actions": capture.actions,
    "action_sha256": digest.hexdigest(),
    "first_action": json.loads(capture.actions[0]),
    "schema_valid_calls": sum(capture.schema_valid),
    "invalid_schema_calls": [i for i, valid in enumerate(capture.schema_valid) if not valid],
    "meaningful_action_calls": sum(
        valid and action != noop
        for action, valid in zip(capture.actions, capture.schema_valid)
    ),
    "stdout": stdout.getvalue(),
    "stderr": stderr.getvalue(),
    "loader": "kaggle_environments.agent.get_last_callable(read_file(main.py), path=main.py)",
    "selected_callable_name": getattr(selected, "__name__", None),
    "selected_callable_qualname": getattr(selected, "__qualname__", None),
    "selected_signature": str(selected_signature),
    "selected_globals_has_file": "__file__" in selected.__globals__,
    "top_level_callables": top_callables,
    "last_top_level_callable": top_callables[-1] if top_callables else None,
    "project_importable_before": project_importable_before,
    "loaded_from_bundle": loaded_from_bundle,
    "loaded_from_project": loaded_from_project,
}
print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
'''


def _package_trajectory(
    extract: Path, seed: int, seat: int, project_root: Path
) -> dict[str, Any]:
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            PACKAGE_RUNNER,
            str(extract),
            str(seed),
            str(seat),
            str(project_root),
        ],
        cwd=extract,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "isolated raw-loader failed: "
            f"rc={completed.returncode}\nstdout={completed.stdout}\nstderr={completed.stderr}"
        )
    if completed.stderr:
        raise RuntimeError(f"isolated process stderr: {completed.stderr}")
    return json.loads(completed.stdout)


def _python311_compile(extract: Path) -> dict[str, Any]:
    files = sorted(extract.rglob("*.py"))
    if not PYTHON311.is_file():
        return {
            "available": False,
            "executable": str(PYTHON311),
            "files": len(files),
            "passed": False,
            "reason": "python3.11 executable not found",
        }
    cache = extract.parent / "python311-pycache"
    environment = dict(os.environ)
    environment["PYTHONPYCACHEPREFIX"] = str(cache)
    completed = subprocess.run(
        [str(PYTHON311), "-m", "py_compile", *map(str, files)],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "available": True,
        "executable": str(PYTHON311),
        "version": subprocess.run(
            [str(PYTHON311), "--version"], capture_output=True, text=True, check=True
        ).stdout.strip(),
        "files": len(files),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "passed": completed.returncode == 0,
    }


def _safe_extract(archive_path: Path, extract: Path) -> dict[str, Any]:
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        unsafe = [
            member.name
            for member in members
            if not member.isfile()
            or Path(member.name).is_absolute()
            or ".." in Path(member.name).parts
        ]
        if unsafe or len(names) != len(set(names)):
            raise RuntimeError(
                f"unsafe or duplicate archive members: unsafe={unsafe} names={names}"
            )
        archive.extractall(extract, filter="data")
    return {
        "members": len(members),
        "safe_regular_relative_unique": True,
        "names": names,
    }


def verify(
    candidate: str,
    archive_path: Path,
    source_main: Path,
    project_root: Path,
) -> dict[str, Any]:
    archive_path = archive_path.resolve()
    source_main = source_main.resolve()
    project_root = project_root.resolve()
    with TemporaryDirectory(prefix=f"raw_loader_redteam_{candidate}_") as directory:
        extract = Path(directory).resolve() / "clean"
        extract.mkdir()
        structure = _safe_extract(archive_path, extract)
        packaged_main = extract / "main.py"
        python311 = _python311_compile(extract)
        games: list[dict[str, Any]] = []
        loader_identity: dict[str, Any] | None = None
        for seed in QA_SEEDS:
            for seat in (0, 1):
                source = _source_trajectory(source_main, project_root, seed, seat)
                package = _package_trajectory(extract, seed, seat, project_root)
                loader_identity = {
                    key: package[key]
                    for key in (
                        "loader",
                        "selected_callable_name",
                        "selected_callable_qualname",
                        "selected_signature",
                        "selected_globals_has_file",
                        "top_level_callables",
                        "last_top_level_callable",
                        "project_importable_before",
                        "loaded_from_bundle",
                        "loaded_from_project",
                    )
                }
                games.append(
                    {
                        "seed": seed,
                        "seat": seat,
                        "steps": package["steps"],
                        "calls": package["calls"],
                        "statuses": package["statuses"],
                        "rewards": package["rewards"],
                        "first_action": package["first_action"],
                        "schema_valid_calls": package["schema_valid_calls"],
                        "invalid_schema_calls": package["invalid_schema_calls"],
                        "meaningful_action_calls": package["meaningful_action_calls"],
                        "package_action_sha256": package["action_sha256"],
                        "source_action_sha256": source["action_sha256"],
                        "source_action_equal": package["actions"] == source["actions"],
                        "source_reward_equal": package["rewards"] == source["rewards"],
                        "package_stdout": package["stdout"],
                        "package_stderr": package["stderr"],
                        "source_stdout": source["stdout"],
                        "source_stderr": source["stderr"],
                    }
                )
        assert loader_identity is not None
        source_main_hash = _sha256(source_main)
        packaged_main_hash = _sha256(packaged_main)

    checks = {
        "archive_safe": structure["safe_regular_relative_unique"],
        "source_main_matches_package": source_main_hash == packaged_main_hash,
        "python311_all_files_compile": python311["passed"],
        "real_raw_loader_used": loader_identity["loader"].startswith(
            "kaggle_environments.agent.get_last_callable"
        ),
        "last_callable_is_agent": loader_identity["selected_callable_name"] == "agent"
        and loader_identity["last_top_level_callable"] == "agent",
        "raw_exec_globals_has_no_file": not loader_identity["selected_globals_has_file"],
        "clean_runtime_has_no_project_import": not loader_identity[
            "project_importable_before"
        ]
        and not loader_identity["loaded_from_project"],
        "all_720_states_719_calls_done_done": all(
            row["steps"] == 720
            and row["calls"] == 719
            and row["statuses"] == ["DONE", "DONE"]
            for row in games
        ),
        "all_raw_actions_have_exact_schema": all(
            row["schema_valid_calls"] == 719 and not row["invalid_schema_calls"]
            for row in games
        ),
        "every_game_has_non_noop_actions": all(
            row["meaningful_action_calls"] > 0 for row in games
        ),
        "zero_stdout_stderr": all(
            not row["package_stdout"]
            and not row["package_stderr"]
            and not row["source_stdout"]
            and not row["source_stderr"]
            for row in games
        ),
        "source_stepwise_actions_and_rewards_equal": all(
            row["source_action_equal"] and row["source_reward_equal"]
            for row in games
        ),
    }
    return {
        "schema": "kaggriculture-v12-raw-loader-redteam-1",
        "candidate": candidate,
        "scope": "packaging/runtime red-team only; no policy change, formal panel, or submission",
        "verdict": "GO" if all(checks.values()) else "NO-GO",
        "archive": {
            "path": str(archive_path),
            "size_bytes": archive_path.stat().st_size,
            "sha256": _sha256(archive_path),
            **structure,
        },
        "source_main": {
            "path": str(source_main),
            "sha256": source_main_hash,
            "packaged_sha256": packaged_main_hash,
        },
        "python311": python311,
        "loader_identity": loader_identity,
        "qa_seeds_previously_exposed": list(QA_SEEDS),
        "games": games,
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--source-main", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(
        args.candidate, args.archive, args.source_main, args.project_root
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["verdict"] != "GO":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
