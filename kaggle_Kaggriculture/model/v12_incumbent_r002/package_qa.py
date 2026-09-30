"""Independent clean-room package QA and registry-equivalence check for r002."""

from __future__ import annotations

import contextlib
import ast
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
from typing import Any, Callable

from kaggle_environments import make
from kaggle_environments.envs.kaggriculture import kaggriculture as kg

from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    create_agent as create_registered_agent,
    load_registry,
)


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent
ARCHIVE = HERE / "submission.tar.gz"
MANIFEST = HERE / "submission_manifest.json"
REPORT = HERE / "package_qa_report.json"
SOURCE_REGISTRY = (
    MODEL_ROOT
    / "v11_iterative_league"
    / "runs"
    / "round_002"
    / "strategy"
    / "registry_next.json"
)
SOURCE_MODEL_ID = "r002_learned_router_topday_animal_throttle"
SEEDS = (93451031, 93451032, 93451033)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical(action: Any) -> str:
    return json.dumps(action, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _action_sha256(actions: list[str]) -> str:
    digest = hashlib.sha256()
    for action in actions:
        digest.update(action.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _errors(diagnostics: Any) -> list[str]:
    result: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"runtime_errors", "prefix_errors"}:
                    if isinstance(child, dict):
                        for rows in child.values():
                            if rows:
                                result.extend(str(item) for item in rows)
                    elif child:
                        result.extend(str(item) for item in child)
                elif key in {"selected_fallbacks", "residual_fallbacks"} and child:
                    result.append(f"{key}={child}")
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(diagnostics)
    return result


class Capture:
    def __init__(self, agent: Callable[..., Any]) -> None:
        self.agent = agent
        self.actions: list[str] = []

    def __call__(self, obs: Any, configuration: Any = None) -> Any:
        action = self.agent(obs, configuration)
        self.actions.append(_canonical(action))
        return action


def _source_trajectory(seed: int, seat: int) -> dict[str, Any]:
    source = create_registered_agent(load_registry(SOURCE_REGISTRY), SOURCE_MODEL_ID)
    capture = Capture(source)
    agents = [capture, kg.starter_agent]
    if seat == 1:
        agents.reverse()
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        env = make("kaggriculture", configuration={"seed": int(seed)}, debug=True)
        steps = env.run(agents)
    diagnostics = source.diagnostics()
    return {
        "seed": int(seed),
        "seat": int(seat),
        "steps": len(steps),
        "calls": len(capture.actions),
        "statuses": [str(state.status) for state in steps[-1]],
        "rewards": [float(state.reward or 0.0) for state in steps[-1]],
        "actions": capture.actions,
        "action_sha256": _action_sha256(capture.actions),
        "stdout": stdout.getvalue(),
        "stderr": stderr.getvalue(),
        "runtime_errors": _errors(diagnostics),
    }


PACKAGE_RUNNER = r'''
import contextlib
import hashlib
import importlib.util
import inspect
import io
import json
from pathlib import Path
import sys

extract = Path(sys.argv[1]).resolve()
seed = int(sys.argv[2])
seat = int(sys.argv[3])
project_root = str(Path(sys.argv[4]).resolve())
project_importable_before = importlib.util.find_spec("kaggle_Kaggriculture") is not None

from kaggle_environments import make
from kaggle_environments.agent import get_last_callable
from kaggle_environments.envs.kaggriculture import kaggriculture as kg

def canonical(action):
    return json.dumps(action, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

class Capture:
    def __init__(self, agent):
        self.agent = agent
        self.actions = []
    def __call__(self, obs, configuration=None):
        action = self.agent(obs, configuration)
        self.actions.append(canonical(action))
        return action

def errors(diagnostics):
    result = []
    def visit(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"runtime_errors", "prefix_errors"}:
                    if isinstance(child, dict):
                        for rows in child.values():
                            if rows:
                                result.extend(str(item) for item in rows)
                    elif child:
                        result.extend(str(item) for item in child)
                elif key in {"selected_fallbacks", "residual_fallbacks"} and child:
                    result.append(f"{key}={child}")
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(diagnostics)
    return result

stdout = io.StringIO()
stderr = io.StringIO()
with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
    main_path = extract / "main.py"
    raw = main_path.read_text(encoding="utf-8")
    agent = get_last_callable(raw, path=str(main_path))
    agent_signature = inspect.signature(agent)
    agent_signature.bind(None)
    agent_signature.bind(None, None)
    capture = Capture(agent)
    agents = [capture, kg.starter_agent]
    if seat == 1:
        agents.reverse()
    env = make("kaggriculture", configuration={"seed": seed}, debug=True)
    steps = env.run(agents)

agent_globals = agent.__globals__
diagnostics = agent_globals["model_status"]()

digest = hashlib.sha256()
for action in capture.actions:
    digest.update(action.encode("utf-8"))
    digest.update(b"\n")
loaded = {}
source_tree_modules = []
for name, loaded_module in sorted(sys.modules.items()):
    path = getattr(loaded_module, "__file__", None)
    if not path:
        continue
    try:
        resolved = str(Path(path).resolve())
    except Exception:
        continue
    if resolved.startswith(str(extract)):
        loaded[name] = resolved
    elif resolved.startswith(project_root) and "/.venv/" not in resolved:
        source_tree_modules.append({"module": name, "path": resolved})
result = {
    "seed": seed,
    "seat": seat,
    "steps": len(steps),
    "calls": len(capture.actions),
    "statuses": [str(state.status) for state in steps[-1]],
    "rewards": [float(state.reward or 0.0) for state in steps[-1]],
    "actions": capture.actions,
    "action_sha256": digest.hexdigest(),
    "stdout": stdout.getvalue(),
    "stderr": stderr.getvalue(),
    "runtime_errors": errors(diagnostics),
    "raw_loader": "kaggle_environments.agent.get_last_callable",
    "raw_loader_globals_has_file": "__file__" in agent_globals,
    "resolved_bundle_directory": str(agent_globals["HERE"]),
    "expected_bundle_directory": str(extract),
    "resolved_bundle_directory_match": agent_globals["HERE"] == extract,
    "meaningful_action_calls": sum(
        action != '{"farmer":["PASS"],"hands":[],"market":[]}'
        for action in capture.actions
    ),
    "project_importable_before_package_load": project_importable_before,
    "source_tree_modules_loaded": source_tree_modules,
    "bundled_modules_loaded": loaded,
    "standard_agent_signature": str(agent_signature),
    "standard_agent_accepts_obs_only": True,
    "standard_agent_accepts_obs_and_configuration": True,
}
print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
'''


def _package_trajectory(extract: Path, seed: int, seat: int) -> dict[str, Any]:
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
            str(MODEL_ROOT.parent.parent),
        ],
        cwd=extract,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    if completed.stderr:
        raise RuntimeError(f"clean subprocess stderr: {completed.stderr}")
    return json.loads(completed.stdout)


def _archive_audit(extract: Path) -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    with tarfile.open(ARCHIVE, "r:gz") as archive:
        members = archive.getmembers()
    names = [member.name for member in members]
    unsafe = [
        member.name
        for member in members
        if not member.isfile()
        or Path(member.name).is_absolute()
        or ".." in Path(member.name).parts
    ]
    duplicates = sorted(name for name in set(names) if names.count(name) > 1)
    extracted = [
        {
            "path": str(path.relative_to(extract)),
            "size_bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path in sorted(extract.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    ]
    absolute_literals = []
    for path in sorted(extract.rglob("*")):
        if not path.is_file() or path.suffix in {".npz", ".pyc"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "/Users/" in text or str(MODEL_ROOT.parent.parent) in text:
            absolute_literals.append(str(path.relative_to(extract)))
    expected_files = manifest["files"]
    syntax = ast.parse((extract / "main.py").read_text(encoding="utf-8"))
    callable_definitions = [
        node.name
        for node in syntax.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    return {
        "path": ARCHIVE.name,
        "size_bytes": ARCHIVE.stat().st_size,
        "sha256": sha256(ARCHIVE),
        "manifest_size_match": ARCHIVE.stat().st_size
        == manifest["archive_size_bytes"],
        "manifest_sha256_match": sha256(ARCHIVE) == manifest["archive_sha256"],
        "manifest_file_records_match": extracted == expected_files,
        "source_main_matches_packaged_main": sha256(HERE / "main.py")
        == sha256(extract / "main.py"),
        "safe_relative_regular_members_only": not unsafe,
        "unsafe_members": unsafe,
        "duplicate_members": duplicates,
        "pycache_or_pyc_members": [
            name for name in names if "__pycache__" in name or name.endswith(".pyc")
        ],
        "embedded_absolute_path_literals": absolute_literals,
        "top_level_callable_definitions": callable_definitions,
        "agent_is_last_top_level_callable_definition": bool(callable_definitions)
        and callable_definitions[-1] == "agent",
        "files": extracted,
    }


def _normal_import_probe(extract: Path) -> dict[str, Any]:
    expected = extract.resolve()
    path = expected / "main.py"
    module_name = "_v12_r002_normal_import_probe"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot create normal import probe")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        return {
            "globals_has_file": "__file__" in vars(module),
            "globals_file": str(Path(vars(module)["__file__"]).resolve()),
            "resolved_bundle_directory": str(module.HERE),
            "expected_bundle_directory": str(expected),
            "resolved_bundle_directory_match": module.HERE == expected,
        }
    finally:
        sys.modules.pop(module_name, None)


def run() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    with TemporaryDirectory(prefix="kaggriculture_v12_r002_qa_") as directory:
        extract = Path(directory) / "extract"
        extract.mkdir()
        with tarfile.open(ARCHIVE, "r:gz") as archive:
            archive.extractall(extract, filter="data")
        archive_audit = _archive_audit(extract)
        normal_import = _normal_import_probe(extract)
        games: list[dict[str, Any]] = []
        isolation: dict[str, Any] | None = None
        for seed in SEEDS:
            for seat in (0, 1):
                source = _source_trajectory(seed, seat)
                package = _package_trajectory(extract, seed, seat)
                isolation = {
                    "project_importable_before_package_load": package[
                        "project_importable_before_package_load"
                    ],
                    "source_tree_modules_loaded": package["source_tree_modules_loaded"],
                    "bundled_modules_loaded": package["bundled_modules_loaded"],
                    "standard_agent_signature": package["standard_agent_signature"],
                    "standard_agent_accepts_obs_only": package[
                        "standard_agent_accepts_obs_only"
                    ],
                    "standard_agent_accepts_obs_and_configuration": package[
                        "standard_agent_accepts_obs_and_configuration"
                    ],
                    "raw_loader": package["raw_loader"],
                    "raw_loader_globals_has_file": package[
                        "raw_loader_globals_has_file"
                    ],
                    "resolved_bundle_directory": package[
                        "resolved_bundle_directory"
                    ],
                    "expected_bundle_directory": package[
                        "expected_bundle_directory"
                    ],
                    "resolved_bundle_directory_match": package[
                        "resolved_bundle_directory_match"
                    ],
                }
                action_equal = package["actions"] == source["actions"]
                reward_equal = package["rewards"] == source["rewards"]
                games.append(
                    {
                        "seed": seed,
                        "seat": seat,
                        "steps": package["steps"],
                        "calls": package["calls"],
                        "statuses": package["statuses"],
                        "rewards": package["rewards"],
                        "action_sha256": package["action_sha256"],
                        "source_action_sha256": source["action_sha256"],
                        "source_vs_archive_action_equal": action_equal,
                        "source_vs_archive_reward_equal": reward_equal,
                        "package_runtime_errors": package["runtime_errors"],
                        "source_runtime_errors": source["runtime_errors"],
                        "package_stdout": package["stdout"],
                        "package_stderr": package["stderr"],
                        "source_stdout": source["stdout"],
                        "source_stderr": source["stderr"],
                        "meaningful_action_calls": package[
                            "meaningful_action_calls"
                        ],
                    }
                )
        assert isolation is not None

    checks = {
        "archive_integrity": all(
            archive_audit[key]
            for key in (
                "manifest_size_match",
                "manifest_sha256_match",
                "manifest_file_records_match",
                "source_main_matches_packaged_main",
                "safe_relative_regular_members_only",
            )
        ),
        "clean_structure": not archive_audit["duplicate_members"]
        and not archive_audit["pycache_or_pyc_members"]
        and not archive_audit["embedded_absolute_path_literals"]
        and archive_audit["agent_is_last_top_level_callable_definition"],
        "isolated_bundled_runtime": not isolation[
            "project_importable_before_package_load"
        ]
        and not isolation["source_tree_modules_loaded"],
        "standard_agent_clean_import_and_call_contract": isolation[
            "standard_agent_accepts_obs_only"
        ]
        and isolation["standard_agent_accepts_obs_and_configuration"],
        "real_kaggle_get_last_callable_raw_loader": isolation["raw_loader"]
        == "kaggle_environments.agent.get_last_callable"
        and not isolation["raw_loader_globals_has_file"]
        and isolation["resolved_bundle_directory_match"],
        "normal_module_import_uses_file_path": normal_import[
            "globals_has_file"
        ]
        and normal_import["resolved_bundle_directory_match"],
        "three_exposed_development_seeds_both_seats": len(games) == 6
        and {row["seed"] for row in games} == set(SEEDS)
        and {row["seat"] for row in games} == {0, 1},
        "all_720_steps_719_calls_done_done": all(
            row["steps"] == 720
            and row["calls"] == 719
            and row["statuses"] == ["DONE", "DONE"]
            for row in games
        ),
        "zero_stdout_stderr_and_runtime_errors": all(
            not row["package_stdout"]
            and not row["package_stderr"]
            and not row["source_stdout"]
            and not row["source_stderr"]
            and not row["package_runtime_errors"]
            and not row["source_runtime_errors"]
            for row in games
        ),
        "non_noop_policy_actions": all(
            row["meaningful_action_calls"] > 0 for row in games
        ),
        "registry_source_vs_archive_stepwise_action_and_reward_equivalence": all(
            row["source_vs_archive_action_equal"]
            and row["source_vs_archive_reward_equal"]
            for row in games
        ),
        "source_policy_fingerprint_preserved": manifest["source_provenance"][
            "source_serving_sha256"
        ]
        == "38afb12bd5fbc987adf752acb437abe9330bd385233c22782b35353f77be2d74",
        "failed_archive_replaced_without_policy_change": manifest[
            "serving_repair"
        ]["failed_archive_sha256"]
        == "453df6eed29e5daa4160371ad31b3286c01ed7a7dbe2e7db735867ba236fe67d"
        and manifest["serving_repair"]["repaired_archive_sha256"]
        == archive_audit["sha256"]
        and not manifest["serving_repair"]["policy_changed"],
    }
    result = {
        "schema": "v12-independent-incumbent-package-qa-1",
        "candidate": "v12_incumbent_r002",
        "source_model_id": SOURCE_MODEL_ID,
        "scope": "packaging requalification only; policy unchanged; no formal/test access",
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "archive": archive_audit,
        "source_provenance": manifest["source_provenance"],
        "serving_repair": manifest["serving_repair"],
        "isolated_runtime": isolation,
        "normal_module_import": normal_import,
        "games": games,
        "checks": checks,
    }
    REPORT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["verdict"] != "PASS":
        raise SystemExit(1)
    return result


if __name__ == "__main__":
    run()
