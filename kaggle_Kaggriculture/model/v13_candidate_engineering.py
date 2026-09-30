"""Shared build and exposed-seed QA utilities for V13 residual candidates.

This file is development tooling only.  It is never copied into a Kaggle
submission archive.
"""

from __future__ import annotations

from contextlib import redirect_stderr
import hashlib
from io import StringIO
import json
from pathlib import Path
import random
import shutil
import tarfile
from tempfile import TemporaryDirectory
from typing import Any, Callable, Mapping

import numpy as np

from kaggle_Kaggriculture.model.v12a_terminal_branch_guard import (
    build_submission as parent_build,
)


MODEL_ROOT = Path(__file__).resolve().parent
A2_ROOT = MODEL_ROOT / "v12a2_no_shop_gate"
CORE_ROOT = MODEL_ROOT / "v12a_terminal_branch_guard"
EXPOSED_QA_SEEDS = (93451031, 93451032, 93451033)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _files(root: Path) -> dict[str, dict[str, Any]]:
    return {
        str(path.relative_to(root)): {
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def build_candidate(
    candidate_root: Path,
    *,
    model_id: str,
    change_scope: str,
) -> dict[str, Any]:
    """Build a self-contained A2-descendant archive and bind its raw entry."""

    archive_path = candidate_root / "submission.tar.gz"
    manifest_path = candidate_root / "submission_manifest.json"
    source_text = (candidate_root / "main.py").read_text(encoding="utf-8")
    if "__file__" in source_text:
        raise RuntimeError("serving main.py must not assume __file__ exists")

    with TemporaryDirectory(prefix=f"{model_id}_build_") as directory:
        stage = Path(directory) / "stage"
        stage.mkdir()
        shutil.copy2(candidate_root / "main.py", stage / "main.py")
        shutil.copy2(A2_ROOT / "main.py", stage / "a2_agent.py")
        shutil.copy2(CORE_ROOT / "main.py", stage / "base_agent.py")
        parent_build._copy_runtime(stage)
        parent_build._copy_experts(stage)
        parent_build._write_policy(stage)
        members = sorted(path for path in stage.rglob("*") if path.is_file())
        with tarfile.open(archive_path, "w:gz") as archive:
            for path in members:
                archive.add(path, arcname=path.relative_to(stage))

        extract = Path(directory) / "extract"
        extract.mkdir()
        with tarfile.open(archive_path, "r:gz") as archive:
            archive.extractall(extract, filter="data")

        from kaggle_environments.agent import get_last_callable

        main_path = extract / "main.py"
        raw_callable = get_last_callable(
            main_path.read_text(encoding="utf-8"), path=str(main_path)
        )
        raw_entry = {
            "callable_name": getattr(raw_callable, "__name__", None),
            "is_agent_global": raw_callable.__globals__.get("agent") is raw_callable,
            "is_not_model_status": (
                raw_callable.__globals__.get("model_status") is not raw_callable
            ),
            "code_filename_is_extracted_main": (
                Path(raw_callable.__code__.co_filename).resolve()
                == main_path.resolve()
            ),
            "a2_module_is_extracted": (
                Path(raw_callable.__globals__["a2"].__file__).resolve()
                == (extract / "a2_agent.py").resolve()
            ),
            "core_module_is_extracted": (
                Path(raw_callable.__globals__["a2"].base.__file__).resolve()
                == (extract / "base_agent.py").resolve()
            ),
        }
        if not all(raw_entry.values()):
            raise RuntimeError({"invalid_kaggle_raw_entry": raw_entry})

        clean_module = parent_build._load_clean_main(main_path)
        clean_match = parent_build._clean_match(clean_module)
        files = [
            {
                "path": name,
                "size_bytes": record["size_bytes"],
                "sha256": record["sha256"],
            }
            for name, record in sorted(_files(extract).items())
        ]

    result = {
        "schema": "kaggriculture-v13-a2-residual-submission-1",
        "model_id": model_id,
        "parent_id": "v12a2_no_shop_gate",
        "change_scope": change_scope,
        "serving_main_avoids_file_assumption": True,
        "archive": archive_path.name,
        "archive_size_bytes": archive_path.stat().st_size,
        "archive_sha256": _sha256(archive_path),
        "kaggle_raw_loader": raw_entry,
        "files": files,
        "clean_match": clean_match,
    }
    manifest_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def _is_no_op(action: Mapping[str, Any]) -> bool:
    farmer = list(action.get("farmer") or ["PASS"])
    hands = [list(item or ["PASS"]) for item in (action.get("hands") or [])]
    market = list(action.get("market") or [])
    return farmer == ["PASS"] and all(item == ["PASS"] for item in hands) and not market


class _TraceAgent:
    def __init__(self, handle: Callable[..., Any]) -> None:
        self.handle = handle
        self.actions: list[dict[str, Any]] = []

    def __call__(self, obs: Any, configuration: Any = None) -> Any:
        action = self.handle(obs, configuration)
        self.actions.append(json.loads(json.dumps(action)))
        return action


def _run(
    handle: Callable[..., Any],
    diagnostics: Callable[[], dict[str, Any]],
    seed: int,
    seat: int,
) -> dict[str, Any]:
    from kaggle_environments import make
    from kaggle_environments.envs.kaggriculture import kaggriculture as kg

    random.seed(seed * 104729 + seat * 1009)
    np.random.seed((seed + seat * 65537) % (2**32 - 1))
    traced = _TraceAgent(handle)
    agents = [traced, kg.starter_agent] if seat == 0 else [kg.starter_agent, traced]
    stderr = StringIO()
    with redirect_stderr(stderr):
        steps = make(
            "kaggriculture", configuration={"seed": seed}, debug=False
        ).run(agents)
    final = steps[-1]
    diag = diagnostics()
    return {
        "steps": len(steps),
        "calls": len(traced.actions),
        "statuses": [str(state.status) for state in final],
        "rewards": [float(state.reward or 0.0) for state in final],
        "actions": traced.actions,
        "non_noop_action_count": sum(not _is_no_op(action) for action in traced.actions),
        "stderr": stderr.getvalue(),
        "diagnostics": diag,
    }


def _raw_diagnostics(raw_agent: Callable[..., Any]) -> dict[str, Any]:
    instance = raw_agent.__globals__.get("_AGENT")
    method = getattr(instance, "diagnostics", None)
    return dict(method()) if callable(method) else {}


def package_qa(
    candidate_root: Path,
    source_module: Any,
    *,
    model_id: str,
    effect_counter_key: str,
) -> dict[str, Any]:
    """Exercise real Kaggle raw loading on only the exposed QA seeds."""

    archive_path = candidate_root / "submission.tar.gz"
    manifest_path = candidate_root / "submission_manifest.json"
    output_path = candidate_root / "package_qa_report.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    from kaggle_environments.agent import get_last_callable

    with TemporaryDirectory(prefix=f"{model_id}_qa_") as directory:
        extract = Path(directory) / "extract"
        extract.mkdir()
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
            archive.extractall(extract, filter="data")
        main_path = extract / "main.py"
        raw_agent = get_last_callable(
            main_path.read_text(encoding="utf-8"), path=str(main_path)
        )
        raw_entry = {
            "callable_name": getattr(raw_agent, "__name__", None),
            "is_agent_global": raw_agent.__globals__.get("agent") is raw_agent,
            "is_not_model_status": raw_agent.__globals__.get("model_status") is not raw_agent,
            "code_filename_is_extracted_main": (
                Path(raw_agent.__code__.co_filename).resolve() == main_path.resolve()
            ),
            "a2_module_is_extracted": (
                Path(raw_agent.__globals__["a2"].__file__).resolve()
                == (extract / "a2_agent.py").resolve()
            ),
            "core_module_is_extracted": (
                Path(raw_agent.__globals__["a2"].base.__file__).resolve()
                == (extract / "base_agent.py").resolve()
            ),
        }

        games = []
        for seed in EXPOSED_QA_SEEDS:
            for seat in (0, 1):
                source_agent = source_module.make_agent()
                source = _run(
                    source_agent, source_agent.diagnostics, seed, seat
                )
                raw = _run(
                    raw_agent, lambda: _raw_diagnostics(raw_agent), seed, seat
                )
                mismatch = next(
                    (
                        index
                        for index, (expected, actual) in enumerate(
                            zip(source["actions"], raw["actions"], strict=False)
                        )
                        if expected != actual
                    ),
                    None,
                )
                if mismatch is None and len(source["actions"]) != len(raw["actions"]):
                    mismatch = min(len(source["actions"]), len(raw["actions"]))
                games.append(
                    {
                        "seed": seed,
                        "seat": seat,
                        "steps": raw["steps"],
                        "calls": raw["calls"],
                        "statuses": raw["statuses"],
                        "rewards": raw["rewards"],
                        "non_noop_action_count": raw["non_noop_action_count"],
                        "source_action_equal": source["actions"] == raw["actions"],
                        "source_reward_equal": source["rewards"] == raw["rewards"],
                        "first_action_mismatch_step": mismatch,
                        "stderr": raw["stderr"],
                        "source_stderr": source["stderr"],
                        "residual_fallbacks": raw["diagnostics"].get("residual_fallbacks"),
                        effect_counter_key: raw["diagnostics"].get(effect_counter_key, 0),
                        "model_id": raw["diagnostics"].get("model_id"),
                    }
                )
        extracted = _files(extract)

    expected = {
        str(item["path"]): {
            "size_bytes": int(item["size_bytes"]),
            "sha256": str(item["sha256"]),
        }
        for item in manifest["files"]
    }
    member_names = [member.name for member in members]
    checks = {
        "archive_manifest_size_hash": (
            archive_path.stat().st_size == int(manifest["archive_size_bytes"])
            and _sha256(archive_path) == manifest["archive_sha256"]
        ),
        "manifest_file_records_match": extracted == expected,
        "safe_unique_regular_members": (
            len(member_names) == len(set(member_names))
            and all(member.isfile() for member in members)
            and all(
                not Path(name).is_absolute() and ".." not in Path(name).parts
                for name in member_names
            )
        ),
        "source_main_matches_packaged": (
            extracted["main.py"]["sha256"] == _sha256(candidate_root / "main.py")
        ),
        "serving_main_avoids_file_assumption": (
            "__file__" not in (candidate_root / "main.py").read_text(encoding="utf-8")
        ),
        "kaggle_raw_loader_returns_agent_from_extracted_bundle": all(raw_entry.values()),
        "three_exposed_qa_seeds_both_seats": len(games) == 6,
        "all_720_steps_719_calls_done_done": all(
            game["steps"] == 720
            and game["calls"] == 719
            and game["statuses"] == ["DONE", "DONE"]
            for game in games
        ),
        "non_noop_policy": all(game["non_noop_action_count"] > 0 for game in games),
        "zero_stderr_and_fallbacks": all(
            not game["stderr"]
            and not game["source_stderr"]
            and game["residual_fallbacks"] == 0
            for game in games
        ),
        "source_archive_exact_actions_rewards": all(
            game["source_action_equal"]
            and game["source_reward_equal"]
            and game["first_action_mismatch_step"] is None
            for game in games
        ),
        "diagnostics_identify_candidate": all(
            game["model_id"] == model_id for game in games
        ),
    }
    report = {
        "schema": "kaggriculture-v13-a2-residual-package-qa-1",
        "candidate": model_id,
        "validation_or_new_panel_accessed": False,
        "qa_seeds_are_previously_exposed": True,
        "effect_counter_key": effect_counter_key,
        "effect_counter_total": sum(int(game[effect_counter_key] or 0) for game in games),
        "raw_loader": raw_entry,
        "archive": {
            "path": str(archive_path.resolve()),
            "size_bytes": archive_path.stat().st_size,
            "sha256": _sha256(archive_path),
        },
        "games": games,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
    }
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report
