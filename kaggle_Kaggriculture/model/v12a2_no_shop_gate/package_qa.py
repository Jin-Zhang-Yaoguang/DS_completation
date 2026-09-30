"""Clean-archive Kaggle raw-loader QA for the serving-only A2 repair.

The reference policy is the immutable clean submission used by frozen_v5's
factory-based formal evaluation. No formal/test episodes or results are read
or rerun here; only that already-frozen policy artifact is executed on the
three previously exposed package-QA seeds.
"""

from __future__ import annotations

import ast
from contextlib import redirect_stderr
import hashlib
from io import StringIO
import json
from pathlib import Path
import random
import tarfile
from tempfile import TemporaryDirectory
from typing import Any, Callable

import numpy as np

from kaggle_Kaggriculture.model.v12a_terminal_branch_guard import (
    build_submission as parent_build,
)


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent
ARCHIVE = HERE / "submission.tar.gz"
MANIFEST = HERE / "submission_manifest.json"
OUTPUT = HERE / "package_qa_report.json"
EQUIVALENCE_OUTPUT = HERE / "serving_entry_repair_report.json"
FORMAL_CLOSURE = (
    MODEL_ROOT / "v12_validation" / "frozen_v5" / "submission_closure.json"
)
FORMAL_ROOT = (
    MODEL_ROOT
    / "v12_validation"
    / "frozen_v5"
    / "clean_submissions"
    / "v12a2_no_shop_gate"
)
FORMAL_MAIN = FORMAL_ROOT / "main.py"
SEEDS = (93451031, 93451032, 93451033)
OLD_ARCHIVE_SHA256 = (
    "53fda5ec6773a339fb181e2102c5e6e266620ecd0616a7034ea117587e20bd0b"
)
OLD_MAIN_SHA256 = (
    "9cff1572e5bfe651b6318f601021450600ee7d0f9733e245194b20c950f21da7"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_policy_ast(text: str) -> str:
    """Ignore only the top-level order of agent/model_status definitions."""

    tree = ast.parse(text)
    indexes = [
        index
        for index, node in enumerate(tree.body)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name in {"agent", "model_status"}
    ]
    if len(indexes) != 2:
        raise RuntimeError({"unexpected_entrypoint_definition_indexes": indexes})
    definitions = [tree.body[index] for index in indexes]
    if {node.name for node in definitions} != {"agent", "model_status"}:
        raise RuntimeError("missing agent/model_status definition")
    insert_at = min(indexes)
    remaining = [node for index, node in enumerate(tree.body) if index not in indexes]
    remaining[insert_at:insert_at] = sorted(definitions, key=lambda node: node.name)
    tree.body = remaining
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


def _is_no_op(action: dict[str, Any]) -> bool:
    farmer = list(action.get("farmer") or ["PASS"])
    hands = [list(item or ["PASS"]) for item in (action.get("hands") or [])]
    market = list(action.get("market") or [])
    return (
        farmer == ["PASS"]
        and all(item == ["PASS"] for item in hands)
        and not market
    )


class TraceAgent:
    def __init__(self, handle: Callable[..., Any]) -> None:
        self.handle = handle
        self.actions: list[dict[str, Any]] = []

    def __call__(self, obs: Any, configuration: Any = None) -> Any:
        action = self.handle(obs, configuration)
        self.actions.append(json.loads(json.dumps(action)))
        return action


def _run_handle(
    handle: Callable[..., Any],
    diagnostics: Callable[[], dict[str, Any]],
    seed: int,
    seat: int,
) -> dict[str, Any]:
    from kaggle_environments import make
    from kaggle_environments.envs.kaggriculture import kaggriculture as kg

    random.seed(seed * 104729 + seat * 1009)
    np.random.seed((seed + seat * 65537) % (2**32 - 1))
    traced = TraceAgent(handle)
    agents = [traced, kg.starter_agent] if seat == 0 else [kg.starter_agent, traced]
    stderr = StringIO()
    with redirect_stderr(stderr):
        steps = make(
            "kaggriculture", configuration={"seed": seed}, debug=False
        ).run(agents)
    final = steps[-1]
    action_bytes = json.dumps(
        traced.actions, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    diag = diagnostics()
    return {
        "steps": len(steps),
        "calls": len(traced.actions),
        "statuses": [str(state.status) for state in final],
        "rewards": [float(state.reward or 0.0) for state in final],
        "actions": traced.actions,
        "action_sha256": hashlib.sha256(action_bytes).hexdigest(),
        "non_noop_action_count": sum(
            not _is_no_op(action) for action in traced.actions
        ),
        "stderr": stderr.getvalue(),
        "residual_fallbacks": diag.get("residual_fallbacks"),
        "model_id": diag.get("model_id"),
    }


def _raw_diagnostics(raw_agent: Callable[..., Any]) -> dict[str, Any]:
    instance = raw_agent.__globals__.get("_AGENT")
    if instance is None:
        return {}
    method = getattr(instance, "diagnostics", None)
    return dict(method()) if callable(method) else {}


def _files(root: Path) -> dict[str, dict[str, Any]]:
    return {
        str(path.relative_to(root)): {
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


def main() -> None:
    from kaggle_environments.agent import get_last_callable

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    closure = json.loads(FORMAL_CLOSURE.read_text(encoding="utf-8"))
    old_closure = closure["candidates"]["v12a2_no_shop_gate"]
    formal_text = FORMAL_MAIN.read_text(encoding="utf-8")

    with TemporaryDirectory(prefix="v12a2_shop_raw_loader_qa_") as directory:
        extract = Path(directory) / "extract"
        extract.mkdir()
        with tarfile.open(ARCHIVE, "r:gz") as archive:
            members = archive.getmembers()
            archive.extractall(extract, filter="data")

        packaged_main = extract / "main.py"
        packaged_text = packaged_main.read_text(encoding="utf-8")
        raw_agent = get_last_callable(packaged_text, path=str(packaged_main))
        old_raw_callable = get_last_callable(formal_text, path=str(FORMAL_MAIN))
        formal_module = parent_build._load_clean_main(FORMAL_MAIN)

        raw_entry = {
            "callable_name": getattr(raw_agent, "__name__", None),
            "is_agent_global": raw_agent.__globals__.get("agent") is raw_agent,
            "is_not_model_status": (
                raw_agent.__globals__.get("model_status") is not raw_agent
            ),
            "code_filename_is_extracted_main": (
                Path(raw_agent.__code__.co_filename).resolve()
                == packaged_main.resolve()
            ),
            "base_module_is_extracted_bundle": (
                Path(raw_agent.__globals__["base"].__file__).resolve()
                == (extract / "base_agent.py").resolve()
            ),
        }
        old_entry = {
            "archive_sha256": old_closure["archive_sha256"],
            "main_sha256": _sha256(FORMAL_MAIN),
            "raw_loader_callable_name": getattr(old_raw_callable, "__name__", None),
            "raw_loader_was_agent": (
                getattr(old_raw_callable, "__name__", None) == "agent"
            ),
            "formal_registry_factory": "make_agent",
        }

        games = []
        for seed in SEEDS:
            for seat in (0, 1):
                formal_agent = formal_module.make_agent()
                formal = _run_handle(
                    formal_agent,
                    formal_agent.diagnostics,
                    seed,
                    seat,
                )
                raw = _run_handle(
                    raw_agent,
                    lambda: _raw_diagnostics(raw_agent),
                    seed,
                    seat,
                )
                mismatch = next(
                    (
                        index
                        for index, (expected, actual) in enumerate(
                            zip(formal["actions"], raw["actions"], strict=False)
                        )
                        if expected != actual
                    ),
                    None,
                )
                if mismatch is None and len(formal["actions"]) != len(raw["actions"]):
                    mismatch = min(len(formal["actions"]), len(raw["actions"]))
                games.append(
                    {
                        "seed": seed,
                        "seat": seat,
                        "steps": raw["steps"],
                        "calls": raw["calls"],
                        "statuses": raw["statuses"],
                        "rewards": raw["rewards"],
                        "action_sha256": raw["action_sha256"],
                        "non_noop_action_count": raw["non_noop_action_count"],
                        "formal_steps": formal["steps"],
                        "formal_calls": formal["calls"],
                        "formal_statuses": formal["statuses"],
                        "formal_action_sha256": formal["action_sha256"],
                        "first_action_mismatch_step": mismatch,
                        "formal_factory_stepwise_action_equal": (
                            raw["actions"] == formal["actions"]
                        ),
                        "formal_factory_reward_equal": (
                            raw["rewards"] == formal["rewards"]
                        ),
                        "stderr": raw["stderr"],
                        "formal_stderr": formal["stderr"],
                        "residual_fallbacks": raw["residual_fallbacks"],
                        "model_id": raw["model_id"],
                    }
                )

        extracted = _files(extract)
        formal_files = _files(FORMAL_ROOT)

    expected = {
        str(item["path"]): {
            "size_bytes": int(item["size_bytes"]),
            "sha256": str(item["sha256"]),
        }
        for item in manifest["files"]
    }
    member_names = [member.name for member in members]
    non_main = set(extracted) - {"main.py"}
    formal_non_main = set(formal_files) - {"main.py"}
    unchanged_members = {
        name: extracted[name]["sha256"] == formal_files[name]["sha256"]
        for name in sorted(non_main & formal_non_main)
    }
    checks = {
        "old_archive_hash_bound_by_frozen_v5_closure": (
            old_closure["archive_sha256"] == OLD_ARCHIVE_SHA256
        ),
        "old_formal_main_hash_bound": _sha256(FORMAL_MAIN) == OLD_MAIN_SHA256,
        "old_raw_loader_fault_reproduced": (
            old_entry["raw_loader_callable_name"] == "model_status"
            and not old_entry["raw_loader_was_agent"]
        ),
        "archive_manifest_size_hash": (
            ARCHIVE.stat().st_size == int(manifest["archive_size_bytes"])
            and _sha256(ARCHIVE) == manifest["archive_sha256"]
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
        "source_main_matches_packaged_main": (
            extracted["main.py"]["sha256"] == _sha256(HERE / "main.py")
        ),
        "all_non_entry_files_match_formal_package": (
            non_main == formal_non_main and all(unchanged_members.values())
        ),
        "entry_source_diff_is_only_definition_order": (
            _canonical_policy_ast(packaged_text) == _canonical_policy_ast(formal_text)
        ),
        "kaggle_raw_loader_returns_agent": (
            raw_entry["callable_name"] == "agent"
            and raw_entry["is_agent_global"]
            and raw_entry["is_not_model_status"]
        ),
        "kaggle_raw_loader_uses_extracted_archive": (
            raw_entry["code_filename_is_extracted_main"]
            and raw_entry["base_module_is_extracted_bundle"]
        ),
        "three_exposed_qa_seeds_both_seats": len(games) == 6,
        "raw_and_formal_factory_all_720_719_done": all(
            game["steps"] == 720
            and game["calls"] == 719
            and game["statuses"] == ["DONE", "DONE"]
            and game["formal_steps"] == 720
            and game["formal_calls"] == 719
            and game["formal_statuses"] == ["DONE", "DONE"]
            for game in games
        ),
        "raw_policy_is_non_noop": all(
            game["non_noop_action_count"] > 0 for game in games
        ),
        "zero_stderr_and_fallbacks": all(
            not game["stderr"]
            and not game["formal_stderr"]
            and game["residual_fallbacks"] == 0
            for game in games
        ),
        "raw_loader_exactly_matches_original_formal_factory": all(
            game["formal_factory_stepwise_action_equal"]
            and game["formal_factory_reward_equal"]
            and game["first_action_mismatch_step"] is None
            for game in games
        ),
        "diagnostics_identify_a2": all(
            game["model_id"] == "v12a2_no_shop_gate" for game in games
        ),
    }
    policy_equivalent = all(
        checks[name]
        for name in (
            "all_non_entry_files_match_formal_package",
            "entry_source_diff_is_only_definition_order",
            "raw_policy_is_non_noop",
            "zero_stderr_and_fallbacks",
            "raw_loader_exactly_matches_original_formal_factory",
        )
    )
    report = {
        "schema": "v12a2-serving-entry-repair-1",
        "candidate": "v12a2_no_shop_gate",
        "repair_scope": (
            "move model_status before agent so agent is Kaggle's last callable"
        ),
        "validation_data_accessed": False,
        "formal_or_test_panel_rerun": False,
        "formal_policy_artifact_used_as_reference": True,
        "qa_seeds_are_previously_exposed": True,
        "old_package": old_entry,
        "new_package": {
            "archive_path": str(ARCHIVE.resolve()),
            "archive_size_bytes": ARCHIVE.stat().st_size,
            "archive_sha256": _sha256(ARCHIVE),
            "main_sha256": _sha256(HERE / "main.py"),
            "raw_loader": raw_entry,
        },
        "policy_equivalence": {
            "verdict": "EXACT" if policy_equivalent else "FAILED",
            "reference": str(FORMAL_MAIN.resolve()),
            "reference_factory": "make_agent",
            "canonical_ast_equal_after_entry_definition_reorder": checks[
                "entry_source_diff_is_only_definition_order"
            ],
            "all_non_main_members_byte_identical": checks[
                "all_non_entry_files_match_formal_package"
            ],
            "games_stepwise_exact": checks[
                "raw_loader_exactly_matches_original_formal_factory"
            ],
        },
        "unchanged_non_main_members": unchanged_members,
        "games": games,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    OUTPUT.write_text(rendered, encoding="utf-8")
    EQUIVALENCE_OUTPUT.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    if report["verdict"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
