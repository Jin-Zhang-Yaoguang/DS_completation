#!/usr/bin/env python3
"""Fail-closed fidelity pilot for the public Kaggriculture C++ simulator.

This script is infrastructure-only.  It never reads V15 source reservations,
hidden panels, evaluator-private mappings, or strategy-generator outputs.

Gates:

1. Pin the public repository commit and official engine version/source hashes.
2. Build the Python binding in an isolated temporary target.
3. Require every trace to contain exactly ``turns + 1`` truth states, then run
   the repository's bundled C++ golden, Python L0 golden and L1 tests.
4. Export a fresh official-engine starter-vs-starter trace, prove truncation is
   rejected, and demand stepwise money/market equality through the public C++
   validator only after the structural gate passes.
5. Compare full official agent-callback observations, emitted actions,
   rewards and final banks against L1 for:
      * a deterministic built-in callback on both seats;
      * the frozen local A2 archive in seat 0 and seat 1 versus starter.

The result is JSON. Any missing check, exception, mismatch, unpinned source,
or incomplete episode makes ``overall_pass`` false and exits non-zero.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


EXPECTED_CPPSIM_COMMIT = "812e50c58543e436828465f89e4cf808a388874f"
EXPECTED_ENGINE_VERSION = "1.32.7"
EXPECTED_CORE_SHA256 = "0922c4599a1b6e0d8c3dadf06ae5297f98138d859d686f00daee6f36e6d45d0e"
EXPECTED_KAGGRICULTURE_SHA256 = (
    "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"
)
PASS_ACTION = {"farmer": ["PASS"], "hands": [], "market": []}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def plain(value: Any) -> Any:
    """Normalise Struct/dict/list/scalars to JSON-compatible plain values."""

    return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":")))


def canonical_action(value: Any) -> dict[str, list[Any]]:
    source = plain(value or {}) if isinstance(value, Mapping) else {}
    return {
        "farmer": list(source.get("farmer") or ["PASS"]),
        "hands": [list(item or ["PASS"]) for item in source.get("hands", [])],
        "market": [list(item) for item in source.get("market", [])],
    }


def first_diff(left: Any, right: Any, path: str = "$.") -> str | None:
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left) | set(right)):
            if key not in left:
                return f"{path}{key}: missing in official"
            if key not in right:
                return f"{path}{key}: missing in kagsim"
            found = first_diff(left[key], right[key], f"{path}{key}.")
            if found:
                return found
        return None
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return f"{path[:-1]}: length {len(left)} != {len(right)}"
        for index, (a, b) in enumerate(zip(left, right)):
            found = first_diff(a, b, f"{path[:-1]}[{index}].")
            if found:
                return found
        return None
    if left != right:
        return f"{path[:-1]}: {left!r} != {right!r}"
    return None


def run_command(
    command: list[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
    timeout: int = 300,
) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=dict(env) if env is not None else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return {
        "command": command,
        "cwd": str(cwd),
        "returncode": completed.returncode,
        "duration_seconds": round(time.perf_counter() - started, 6),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "pass": completed.returncode == 0,
    }


def command_json(command_result: Mapping[str, Any], label: str) -> dict[str, Any]:
    """Parse a JSON-only command response or fail closed."""

    try:
        value = json.loads(str(command_result.get("stdout", "")))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{label} emitted invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label} JSON root is not an object")
    return value


def import_path(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_extract(archive: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=False)
    root = destination.resolve()
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            target = (destination / member.name).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"unsafe tar member: {member.name}")
            if member.issym() or member.islnk():
                raise RuntimeError(f"links are not allowed in agent archive: {member.name}")
        tar.extractall(destination, filter="data")
    main = destination / "main.py"
    if not main.is_file():
        raise RuntimeError(f"archive lacks root main.py: {archive}")
    return main


def modules_loaded_from(root: Path) -> set[str]:
    resolved = root.resolve()
    found: set[str] = set()
    for name, module in list(sys.modules.items()):
        raw = getattr(module, "__file__", None)
        if not raw:
            continue
        try:
            path = Path(raw).resolve()
        except (OSError, RuntimeError):
            continue
        if path == resolved or resolved in path.parents:
            found.add(name)
    return found


def purge_modules(names: Iterable[str]) -> None:
    for name in sorted(set(names), key=lambda item: item.count("."), reverse=True):
        sys.modules.pop(name, None)


class CallbackRecorder:
    """Record the exact observation and action crossing an official callback."""

    def __init__(self, policy: Callable[[Any, Any], Any], name: str) -> None:
        self.policy = policy
        self.name = name
        self.observations: list[Any] = []
        self.actions: list[dict[str, list[Any]]] = []
        self.errors: list[str] = []

    def __call__(self, observation: Any, configuration: Any = None) -> Any:
        self.observations.append(plain(observation))
        try:
            action = self.policy(observation, configuration)
            if isinstance(action, BaseException):
                raise action
            normalised = canonical_action(action)
            self.actions.append(normalised)
            return normalised
        except BaseException as exc:  # fail closed and retain evidence
            self.errors.append(f"{type(exc).__name__}: {exc}")
            raise


def agent_act_policy(agent: Any) -> Callable[[Any, Any], Any]:
    def invoke(observation: Any, _configuration: Any = None) -> Any:
        action, log = agent.act(observation)
        if log.get("stderr"):
            raise RuntimeError(f"agent stderr: {log['stderr']}")
        if isinstance(action, BaseException):
            raise action
        return action

    return invoke


def official_rewards(env: Any) -> list[float]:
    return [float(state.reward or 0.0) for state in env.steps[-1]]


def official_statuses(env: Any) -> list[str]:
    return [str(state.status) for state in env.steps[-1]]


def check_recorded_actions(env: Any, recorders: list[CallbackRecorder]) -> str | None:
    expected_turns = len(env.steps) - 1
    for seat, recorder in enumerate(recorders):
        if len(recorder.actions) != expected_turns:
            return (
                f"seat {seat}: callback actions {len(recorder.actions)} "
                f"!= acting turns {expected_turns}"
            )
        stored = [canonical_action(step[seat].action) for step in env.steps[1:]]
        found = first_diff(recorder.actions, stored)
        if found:
            return f"seat {seat}: callback action != recorded action: {found}"
    return None


def run_l1_replay(
    *,
    kagsim: Any,
    seed: int,
    official_env: Any,
    official_recorders: list[CallbackRecorder],
    replay_policies: list[Callable[[Any, Any], Any]],
    configuration: Any,
) -> dict[str, Any]:
    from kaggle_environments.utils import structify

    result: dict[str, Any] = {
        "seed": seed,
        "turns_expected": len(official_env.steps) - 1,
        "observation_blocks_compared": 0,
        "actions_compared": 0,
        "first_difference": None,
        "official_statuses": official_statuses(official_env),
        "official_rewards": official_rewards(official_env),
        "kagsim_rewards": None,
        "kagsim_done": False,
        "pass": False,
    }
    if result["official_statuses"] != ["DONE", "DONE"]:
        result["first_difference"] = "official episode did not finish DONE/DONE"
        return result
    action_error = check_recorded_actions(official_env, official_recorders)
    if action_error:
        result["first_difference"] = action_error
        return result

    game = kagsim.Game(seed)
    for turn in range(result["turns_expected"]):
        actions: list[dict[str, list[Any]]] = []
        for seat in (0, 1):
            observed = plain(game.observe(seat))
            expected_observation = official_recorders[seat].observations[turn]
            found = first_diff(expected_observation, observed)
            if found:
                result["first_difference"] = (
                    f"turn {turn} seat {seat} observation: {found}"
                )
                return result
            result["observation_blocks_compared"] += 1
            try:
                # Official env.run callbacks receive Kaggle ``Struct`` objects,
                # not raw dicts.  Recreate that boundary after the plain-value
                # equality check so complex archive agents see the same API.
                action = replay_policies[seat](structify(observed), configuration)
                if isinstance(action, BaseException):
                    raise action
            except BaseException as exc:
                result["first_difference"] = (
                    f"turn {turn} seat {seat} callback error: "
                    f"{type(exc).__name__}: {exc}"
                )
                return result
            normalised = canonical_action(action)
            found = first_diff(official_recorders[seat].actions[turn], normalised)
            if found:
                result["first_difference"] = (
                    f"turn {turn} seat {seat} action: {found}"
                )
                return result
            result["actions_compared"] += 1
            actions.append(normalised)
        game.step(actions[0], actions[1])

    result["kagsim_done"] = bool(game.done)
    result["kagsim_rewards"] = [float(game.reward(0)), float(game.reward(1))]
    if not result["kagsim_done"]:
        result["first_difference"] = "kagsim did not finish"
        return result
    found = first_diff(result["official_rewards"], result["kagsim_rewards"])
    if found:
        result["first_difference"] = f"final reward/bank: {found}"
        return result
    result["pass"] = True
    return result


def built_in_l1_case(kagsim: Any, seed: int) -> dict[str, Any]:
    from kaggle_environments import make
    from kaggle_environments.envs.kaggriculture.kaggriculture import starter_agent

    def starter(observation: Any, _configuration: Any = None) -> Any:
        return starter_agent(observation)

    official_env = make(
        "kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False
    )
    recorders = [
        CallbackRecorder(starter, "starter-seat0"),
        CallbackRecorder(starter, "starter-seat1"),
    ]
    official_env.run(recorders)
    result = run_l1_replay(
        kagsim=kagsim,
        seed=seed,
        official_env=official_env,
        official_recorders=recorders,
        replay_policies=[starter, starter],
        configuration=official_env.configuration,
    )
    result["case"] = "official-callback-starter-vs-starter"
    return result


def complex_l1_case(
    *,
    kagsim: Any,
    seed: int,
    a2_archive: Path,
    a2_seat: int,
    scratch: Path,
) -> dict[str, Any]:
    from kaggle_environments import make
    from kaggle_environments.agent import Agent

    case_name = f"a2-seat{a2_seat}-vs-starter"
    official_extract = scratch / f"{case_name}-official"
    kagsim_extract = scratch / f"{case_name}-kagsim"
    official_main = safe_extract(a2_archive, official_extract)
    kagsim_main = safe_extract(a2_archive, kagsim_extract)

    official_env = make(
        "kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False
    )
    official_a2 = Agent(str(official_main), official_env)
    official_starter = Agent("starter", official_env)
    inner = [official_starter, official_starter]
    inner[a2_seat] = official_a2
    recorders = [
        CallbackRecorder(agent_act_policy(inner[0]), f"{case_name}-seat0"),
        CallbackRecorder(agent_act_policy(inner[1]), f"{case_name}-seat1"),
    ]
    official_env.run(recorders)
    loaded_official = modules_loaded_from(official_extract)
    purge_modules(loaded_official)

    adapter_env = make(
        "kaggriculture", configuration={"episodeSteps": 720, "seed": seed}, debug=False
    )
    kagsim_a2 = Agent(str(kagsim_main), adapter_env)
    kagsim_starter = Agent("starter", adapter_env)
    replay_agents = [kagsim_starter, kagsim_starter]
    replay_agents[a2_seat] = kagsim_a2
    replay_policies = [agent_act_policy(replay_agents[0]), agent_act_policy(replay_agents[1])]
    result = run_l1_replay(
        kagsim=kagsim,
        seed=seed,
        official_env=official_env,
        official_recorders=recorders,
        replay_policies=replay_policies,
        configuration=official_env.configuration,
    )
    result.update(
        {
            "case": case_name,
            "a2_seat": a2_seat,
            "a2_archive": str(a2_archive),
            "a2_archive_sha256": sha256_file(a2_archive),
            "official_agent_modules_purged": sorted(loaded_official),
        }
    )
    purge_modules(modules_loaded_from(kagsim_extract))
    return result


def parse_args() -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parents[3]
    default_repo = (
        project_root
        / "kaggle_Kaggriculture/model/community_research/2026-08-26/live_cli"
        / "external_repos/kaggriculture-cppsim"
    )
    default_a2 = (
        project_root
        / "kaggle_Kaggriculture/model/v12a2_no_shop_gate/submission.tar.gz"
    )
    parser = argparse.ArgumentParser()
    parser.add_argument("--cppsim-repo", type=Path, default=default_repo)
    parser.add_argument("--a2-archive", type=Path, default=default_a2)
    parser.add_argument("--fresh-seed", type=int, default=2026082601)
    parser.add_argument("--artifact-dir", type=Path, default=script_dir)
    parser.add_argument("--output", type=Path, default=script_dir / "fidelity_result.json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.cppsim_repo.resolve()
    a2_archive = args.a2_archive.resolve()
    artifact_dir = args.artifact_dir.resolve()
    output = args.output.resolve()
    strict_wrapper = Path(__file__).resolve().with_name("strict_trace_wrapper.py")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)

    result: dict[str, Any] = {
        "schema": "kaggriculture-cppsim-v15-fidelity-pilot-v1",
        "started_at_epoch": time.time(),
        "scope": {
            "strategy_generator_002_read": False,
            "fresh_v15_source_consumed": False,
            "evaluator_modified": False,
            "candidate_modified": False,
        },
        "runtime": {
            "python": sys.version,
            "python_executable": sys.executable,
            "platform": platform.platform(),
        },
        "source_pin": {},
        "checks": {},
        "integration": {
            "direct_evaluator_integration_attempted": False,
            "qualified_for_direct_integration": False,
            "blocking_differences": [],
        },
        "overall_pass": False,
        "fail_closed_decision": "BLOCK",
        "error": None,
    }

    try:
        if not repo.is_dir():
            raise FileNotFoundError(repo)
        if not a2_archive.is_file():
            raise FileNotFoundError(a2_archive)
        if not strict_wrapper.is_file():
            raise FileNotFoundError(strict_wrapper)
        git_commit = run_command(
            ["git", "rev-parse", "HEAD"], cwd=repo, timeout=30
        )
        git_dirty = run_command(
            ["git", "status", "--porcelain"], cwd=repo, timeout=30
        )
        commit = git_commit["stdout"].strip()
        dirty = git_dirty["stdout"].strip()
        engine_version = importlib.metadata.version("kaggle-environments")
        import kaggle_environments

        engine_root = Path(kaggle_environments.__file__).resolve().parent
        core_path = engine_root / "core.py"
        kg_path = engine_root / "envs/kaggriculture/kaggriculture.py"
        result["source_pin"] = {
            "cppsim_repo": str(repo),
            "cppsim_commit": commit,
            "cppsim_expected_commit": EXPECTED_CPPSIM_COMMIT,
            "cppsim_dirty": bool(dirty),
            "cppsim_license_sha256": sha256_file(repo / "LICENSE"),
            "engine_version": engine_version,
            "engine_expected_version": EXPECTED_ENGINE_VERSION,
            "core_sha256": sha256_file(core_path),
            "core_expected_sha256": EXPECTED_CORE_SHA256,
            "kaggriculture_sha256": sha256_file(kg_path),
            "kaggriculture_expected_sha256": EXPECTED_KAGGRICULTURE_SHA256,
            "a2_archive": str(a2_archive),
            "a2_archive_sha256": sha256_file(a2_archive),
            "strict_trace_wrapper": str(strict_wrapper),
            "strict_trace_wrapper_sha256": sha256_file(strict_wrapper),
        }
        pin_ok = (
            git_commit["pass"]
            and git_dirty["pass"]
            and commit == EXPECTED_CPPSIM_COMMIT
            and not dirty
            and engine_version == EXPECTED_ENGINE_VERSION
            and sha256_file(core_path) == EXPECTED_CORE_SHA256
            and sha256_file(kg_path) == EXPECTED_KAGGRICULTURE_SHA256
        )
        result["checks"]["source_pin"] = {"pass": pin_ok}
        if not pin_ok:
            raise RuntimeError("source pin gate failed")

        with tempfile.TemporaryDirectory(prefix="v15-cppsim-fidelity-") as raw_scratch:
            scratch = Path(raw_scratch)
            site = scratch / "site"
            site.mkdir()
            uv = shutil.which("uv")
            if not uv:
                raise RuntimeError("uv not found; refusing an unpinned build workaround")
            build = run_command(
                [
                    uv,
                    "pip",
                    "install",
                    "--python",
                    sys.executable,
                    "--target",
                    str(site),
                    "--no-deps",
                    str(repo),
                ],
                cwd=repo,
                timeout=300,
            )
            result["checks"]["isolated_binding_build"] = build
            if not build["pass"]:
                raise RuntimeError("isolated kagsim build failed")

            child_env = dict(os.environ)
            old_pythonpath = child_env.get("PYTHONPATH", "")
            child_env["PYTHONPATH"] = (
                str(site) if not old_pythonpath else str(site) + os.pathsep + old_pythonpath
            )
            binary = scratch / "validate"
            compiler = shutil.which("clang++") or shutil.which("g++") or shutil.which("c++")
            if not compiler:
                raise RuntimeError("no C++17 compiler found")
            compile_check = run_command(
                [
                    compiler,
                    "-O3",
                    "-std=c++17",
                    "-o",
                    str(binary),
                    str(repo / "tools/validate.cpp"),
                ],
                cwd=repo,
                timeout=180,
            )
            result["checks"]["compile_cpp_validator"] = compile_check
            if not compile_check["pass"]:
                raise RuntimeError("C++ validator compile failed")

            bundled_traces = sorted((repo / "traces").glob("*.txt"))
            bundled_structure = run_command(
                [sys.executable, str(strict_wrapper), *[str(path) for path in bundled_traces]],
                cwd=artifact_dir,
                timeout=60,
            )
            bundled_structure_payload = command_json(
                bundled_structure, "bundled strict trace wrapper"
            )
            bundled_structure["validator_payload"] = bundled_structure_payload
            bundled_structure["pass"] = (
                bundled_structure["returncode"] == 0
                and bundled_structure_payload.get("pass") is True
                and bundled_structure_payload.get("trace_count") == len(bundled_traces)
                and all(
                    item.get("truth_state_count")
                    == item.get("declared_turns", -1) + 1
                    for item in bundled_structure_payload.get("results", [])
                )
            )
            result["checks"]["bundled_trace_structure"] = bundled_structure
            if not bundled_structure["pass"]:
                raise RuntimeError("bundled strict trace structure gate failed")

            cpp_golden = run_command(
                [str(binary), *[str(path) for path in bundled_traces]],
                cwd=repo,
                timeout=180,
            )
            cpp_golden["trace_count"] = len(bundled_traces)
            cpp_golden["pass_line_count"] = sum(
                line.startswith("PASS ") for line in cpp_golden["stdout"].splitlines()
            )
            cpp_golden["pass"] = (
                cpp_golden["pass"]
                and cpp_golden["trace_count"] > 0
                and cpp_golden["pass_line_count"] == cpp_golden["trace_count"]
            )
            result["checks"]["bundled_cpp_stepwise_golden"] = cpp_golden

            python_golden = run_command(
                [sys.executable, str(repo / "tests/test_golden.py")],
                cwd=repo,
                env=child_env,
                timeout=180,
            )
            python_golden["pass"] = python_golden["pass"] and "GOLDEN: PASS" in python_golden["stdout"]
            result["checks"]["bundled_python_l0_golden"] = python_golden

            bundled_l1 = run_command(
                [sys.executable, str(repo / "tests/test_l1.py")],
                cwd=repo,
                env=child_env,
                timeout=240,
            )
            bundled_l1["pass"] = bundled_l1["pass"] and "6/6 traces observation-exact" in bundled_l1["stdout"]
            result["checks"]["bundled_python_l1_observation_golden"] = bundled_l1

            if not all(
                check["pass"]
                for check in (cpp_golden, python_golden, bundled_l1)
            ):
                raise RuntimeError("one or more bundled fidelity tests failed")

            sys.path.insert(0, str(site))
            try:
                import kagsim
            finally:
                # Keep the extension imported, but do not leak the build target
                # into subsequent module resolution.
                sys.path.pop(0)
            binding_check = {
                "version": getattr(kagsim, "__version__", None),
                "engine_version": getattr(kagsim, "ENGINE_VERSION", None),
            }
            binding_check["pass"] = binding_check["engine_version"] == EXPECTED_ENGINE_VERSION
            result["checks"]["binding_identity"] = binding_check
            if not binding_check["pass"]:
                raise RuntimeError("binding engine identity failed")

            # Fresh trace: public built-in callbacks only, with a seed absent
            # from every bundled trace. It consumes no competition/V15 source.
            export_module = import_path(
                "cppsim_export_trace_for_v15_pilot", repo / "tools/export_trace.py"
            )
            bundled_seeds: set[int] = set()
            for trace in bundled_traces:
                bundled_seeds.add(int(trace.read_text().splitlines()[0].split()[0]))
            if args.fresh_seed in bundled_seeds:
                raise RuntimeError("fresh seed collides with a bundled trace")
            trace_path = export_module.export(
                args.fresh_seed,
                agents=("starter", "starter"),
                out_dir=str(artifact_dir),
            )
            trace_path = Path(trace_path).resolve()

            fresh_structure = run_command(
                [sys.executable, str(strict_wrapper), str(trace_path)],
                cwd=artifact_dir,
                timeout=60,
            )
            fresh_structure_payload = command_json(
                fresh_structure, "fresh strict trace wrapper"
            )
            fresh_structure_result = (
                fresh_structure_payload.get("results", [{}])[0]
                if fresh_structure_payload.get("results")
                else {}
            )
            fresh_structure["validator_payload"] = fresh_structure_payload
            fresh_structure["pass"] = (
                fresh_structure["returncode"] == 0
                and fresh_structure_payload.get("pass") is True
                and fresh_structure_payload.get("trace_count") == 1
                and fresh_structure_result.get("declared_turns") == 719
                and fresh_structure_result.get("truth_state_count") == 720
                and fresh_structure_result.get("expected_truth_state_count") == 720
            )
            result["checks"]["fresh_trace_structure"] = fresh_structure
            if not fresh_structure["pass"]:
                raise RuntimeError("fresh strict trace structure gate failed")

            # Prove that the wrapper fails closed rather than merely reporting
            # the well-formed trace. Never pass malformed input to the upstream
            # C++ validator, whose unchecked truth indexing could be undefined.
            truncated_path = scratch / "fresh-trace-missing-final-truth-state.txt"
            trace_lines = trace_path.read_text(encoding="utf-8").splitlines()
            truncated_path.write_text(
                "\n".join(trace_lines[:-1]) + "\n", encoding="utf-8"
            )
            truncated_structure = run_command(
                [sys.executable, str(strict_wrapper), str(truncated_path)],
                cwd=artifact_dir,
                timeout=60,
            )
            truncated_payload = command_json(
                truncated_structure, "truncated strict trace wrapper"
            )
            truncated_result = (
                truncated_payload.get("results", [{}])[0]
                if truncated_payload.get("results")
                else {}
            )
            truncated_structure["validator_payload"] = truncated_payload
            truncated_structure["pass"] = (
                truncated_structure["returncode"] != 0
                and truncated_payload.get("pass") is False
                and truncated_result.get("declared_turns") == 719
                and truncated_result.get("truth_state_count") == 719
                and truncated_result.get("expected_truth_state_count") == 720
                and "truth_state_count=719" in str(truncated_result.get("error"))
            )
            result["checks"]["truncated_trace_rejected"] = truncated_structure
            if not truncated_structure["pass"]:
                raise RuntimeError("strict trace wrapper did not reject truncation")

            fresh_cpp = run_command(
                [str(binary), str(trace_path)], cwd=repo, timeout=180
            )
            fresh_cpp["trace_path"] = str(trace_path)
            fresh_cpp["trace_sha256"] = sha256_file(trace_path)
            fresh_cpp["seed"] = args.fresh_seed
            fresh_cpp["agents"] = ["starter", "starter"]
            fresh_cpp["declared_turns"] = fresh_structure_result["declared_turns"]
            fresh_cpp["truth_marker_count"] = fresh_structure_result["truth_marker_count"]
            fresh_cpp["truth_state_count"] = fresh_structure_result["truth_state_count"]
            fresh_cpp["expected_truth_state_count"] = fresh_structure_result[
                "expected_truth_state_count"
            ]
            fresh_cpp["pass"] = (
                fresh_cpp["pass"]
                and fresh_cpp["stdout"].startswith("PASS ")
                and "719 steps exact" in fresh_cpp["stdout"]
                and fresh_cpp["declared_turns"] == 719
                and fresh_cpp["truth_marker_count"] == 1
                and fresh_cpp["truth_state_count"]
                == fresh_cpp["expected_truth_state_count"]
                == 720
            )
            result["checks"]["fresh_l0_stepwise_money_market"] = fresh_cpp
            if not fresh_cpp["pass"]:
                raise RuntimeError("fresh L0 trace failed stepwise validation")

            golden_module = import_path(
                "cppsim_test_golden_for_v15_pilot", repo / "tests/test_golden.py"
            )
            fresh_seed, fresh_actions, fresh_truth = golden_module.parse_trace(trace_path)
            l0_banks = kagsim.run_episode(
                kagsim.Stream(fresh_actions[0]),
                kagsim.Stream(fresh_actions[1]),
                fresh_seed,
            )
            l0_python = {
                "seed": fresh_seed,
                "official_final_banks": list(fresh_truth),
                "kagsim_final_banks": [float(l0_banks[0]), float(l0_banks[1])],
            }
            l0_python["pass"] = l0_python["official_final_banks"] == l0_python["kagsim_final_banks"]
            result["checks"]["fresh_l0_python_binding_final_bank"] = l0_python
            if not l0_python["pass"]:
                raise RuntimeError("fresh L0 Python binding final bank mismatch")

            builtin_case = built_in_l1_case(kagsim, args.fresh_seed + 1)
            result["checks"]["fresh_l1_official_callback_both_seats"] = builtin_case
            if not builtin_case["pass"]:
                raise RuntimeError("fresh built-in callback L1 case failed")

            complex_cases = [
                complex_l1_case(
                    kagsim=kagsim,
                    seed=args.fresh_seed + 2,
                    a2_archive=a2_archive,
                    a2_seat=0,
                    scratch=scratch,
                ),
                complex_l1_case(
                    kagsim=kagsim,
                    seed=args.fresh_seed + 3,
                    a2_archive=a2_archive,
                    a2_seat=1,
                    scratch=scratch,
                ),
            ]
            result["checks"]["fresh_l1_complex_a2"] = {
                "cases": complex_cases,
                "pass": all(case["pass"] for case in complex_cases),
            }
            if not result["checks"]["fresh_l1_complex_a2"]["pass"]:
                raise RuntimeError("one or more complex A2 L1 cases failed")

            # Passing the engine/callback fidelity gate does not make the
            # binding a direct V15 backend. These lifecycle semantics remain
            # deliberately unimplemented and therefore block integration.
            result["integration"]["blocking_differences"] = [
                "upstream tools/validate.cpp has no explicit truth_count == turns + 1 guard; every semantic run must be preceded by the local strict trace wrapper",
                "kagsim.Game does not load or isolate submission archives; the pilot used kaggle_environments.agent.Agent as an adapter",
                "kagsim.Game.observe returns dict while official callbacks receive attribute-accessible Struct; complex agents require an explicit structify boundary",
                "kagsim.Game does not implement Agent.act timeout, remaining-overage accounting, stdout/stderr capture, ERROR/TIMEOUT status or crash-as-loss semantics",
                "kagsim.Game constructor exposes only seed/steps; V15 must reject non-default engine configuration or add a config fingerprint adapter",
                "a production adapter must create fresh agent/module state per episode and preserve Kaggle last-callable/__raw_path__ behaviour",
                "the V15 sealed task/result/source-integrity protocol is not implemented by this pilot",
            ]

        required_checks = [
            "source_pin",
            "isolated_binding_build",
            "compile_cpp_validator",
            "bundled_trace_structure",
            "bundled_cpp_stepwise_golden",
            "bundled_python_l0_golden",
            "bundled_python_l1_observation_golden",
            "binding_identity",
            "fresh_trace_structure",
            "truncated_trace_rejected",
            "fresh_l0_stepwise_money_market",
            "fresh_l0_python_binding_final_bank",
            "fresh_l1_official_callback_both_seats",
            "fresh_l1_complex_a2",
        ]
        result["overall_pass"] = all(
            result["checks"].get(name, {}).get("pass") is True
            for name in required_checks
        )
        result["integration"]["qualified_for_direct_integration"] = False
        result["fail_closed_decision"] = (
            "FIDELITY_PASS_INTEGRATION_BLOCKED"
            if result["overall_pass"]
            else "BLOCK"
        )
    except BaseException as exc:
        result["error"] = {
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }
        result["overall_pass"] = False
        result["fail_closed_decision"] = "BLOCK"
    finally:
        result["finished_at_epoch"] = time.time()
        result["duration_seconds"] = round(
            result["finished_at_epoch"] - result["started_at_epoch"], 6
        )
        output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "output": str(output),
            "overall_pass": result["overall_pass"],
            "decision": result["fail_closed_decision"],
            "error": result["error"],
        }, ensure_ascii=False, indent=2))
    return 0 if result["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
