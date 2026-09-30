"""Clean-extraction equivalence QA on three already-exposed seeds."""

from __future__ import annotations

from contextlib import redirect_stderr
import hashlib
from io import StringIO
import json
from pathlib import Path
import random
import sys
import tarfile
from tempfile import TemporaryDirectory
from typing import Any, Callable, Mapping

import numpy as np

from kaggle_Kaggriculture.model.v12a2_no_shop_gate import main as a2
from kaggle_Kaggriculture.model.v14_queue_s1 import build_submission
from kaggle_Kaggriculture.model.v14_queue_s1 import main as source_main


HERE = Path(__file__).resolve().parent
MODEL_ID = "v14_queue_s1"
EXPOSED_QA_SEEDS = (93451031, 93451032, 93451033)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _files(root: Path) -> dict[str, dict[str, Any]]:
    return {
        str(path.relative_to(root)): {"size_bytes": path.stat().st_size, "sha256": _sha256(path)}
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


class TraceAgent:
    def __init__(self, handle: Callable[..., Any]) -> None:
        self.handle = handle
        self.actions: list[dict[str, Any]] = []

    def __call__(self, obs: Any, configuration: Any = None) -> Any:
        action = self.handle(obs, configuration)
        self.actions.append(json.loads(json.dumps(action)))
        return action


def _run(handle: Callable[..., Any], diagnostics: Callable[[], Mapping[str, Any]], seed: int, seat: int) -> dict[str, Any]:
    from kaggle_environments import make

    random.seed(seed * 104729 + seat * 1009)
    np.random.seed((seed + seat * 65537) % (2**32 - 1))
    candidate = TraceAgent(handle)
    opponent = a2.make_agent()
    agents = [candidate, opponent] if seat == 0 else [opponent, candidate]
    stderr = StringIO()
    with redirect_stderr(stderr):
        steps = make("kaggriculture", configuration={"seed": seed}, debug=False).run(agents)
    final = steps[-1]
    diag = dict(diagnostics())
    parent = dict(diag.get("parent_diagnostics") or {})
    return {
        "steps": len(steps),
        "calls": len(candidate.actions),
        "statuses": [str(state.status) for state in final],
        "rewards": [float(state.reward or 0.0) for state in final],
        "actions": candidate.actions,
        "stderr": stderr.getvalue(),
        "diagnostics": {
            "model_id": diag.get("model_id"),
            "reordered_steps": int(diag.get("reordered_steps", 0) or 0),
            "shadow_faults": int(diag.get("shadow_faults", 0) or 0),
            "shadow_update_errors": int(diag.get("shadow_update_errors", 0) or 0),
            "conformance_steps": int(diag.get("conformance_steps", 0) or 0),
            "s1_prepared": int(parent.get("s1_prepared", 0) or 0),
            "s1_executed": int(parent.get("s1_executed", 0) or 0),
            "s1_pending_faults": int(parent.get("s1_pending_faults", 0) or 0),
        },
    }


def _raw_diagnostics(raw_agent: Callable[..., Any]) -> Mapping[str, Any]:
    instance = raw_agent.__globals__.get("_AGENT")
    method = getattr(instance, "diagnostics", None)
    return method() if callable(method) else {}


def qa() -> dict[str, Any]:
    archive_path = HERE / "submission.tar.gz"
    manifest_path = HERE / "submission_manifest.json"
    output_path = HERE / "package_qa_report.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("candidate_source_frozen") is not True:
        raise RuntimeError("candidate source is provisional; refusing long package QA")
    from kaggle_environments.agent import get_last_callable

    with TemporaryDirectory(prefix="v14_qs1_qa_") as directory:
        extract = Path(directory) / "extract"
        extract.mkdir()
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
            archive.extractall(extract, filter="data")
        for name in (
            "queue_core", "s1_agent", "a2_agent", "base_agent", "official_kaggriculture",
            "fast_router", "agent_factory", "expert_registry", "router", "variants",
        ):
            sys.modules.pop(name, None)
        main_path = extract / "main.py"
        raw_agent = get_last_callable(main_path.read_text(encoding="utf-8"), path=str(main_path))
        queue = raw_agent.__globals__.get("queue")
        s1 = raw_agent.__globals__.get("s1")
        raw_entry = {
            "callable_name_is_agent": getattr(raw_agent, "__name__", None) == "agent",
            "is_agent_global": raw_agent.__globals__.get("agent") is raw_agent,
            "code_filename_is_extracted_main": Path(raw_agent.__code__.co_filename).resolve() == main_path.resolve(),
            "queue_core_is_extracted": Path(queue.__file__).resolve() == (extract / "queue_core.py").resolve(),
            "s1_is_extracted": Path(s1.__file__).resolve() == (extract / "s1_agent.py").resolve(),
            "a2_is_extracted": Path(queue.a2.__file__).resolve() == (extract / "a2_agent.py").resolve(),
            "base_is_extracted": Path(queue.a2.base.__file__).resolve() == (extract / "base_agent.py").resolve(),
            "official_runtime_is_extracted": Path(queue.kg.__file__).resolve() == (extract / "official_kaggriculture.py").resolve(),
        }
        games: list[dict[str, Any]] = []
        for seed in EXPOSED_QA_SEEDS:
            for seat in (0, 1):
                source_agent = source_main.make_agent()
                source = _run(source_agent, source_agent.diagnostics, seed, seat)
                raw = _run(raw_agent, lambda: _raw_diagnostics(raw_agent), seed, seat)
                mismatch = next(
                    (
                        index
                        for index, (expected, actual) in enumerate(zip(source["actions"], raw["actions"], strict=False))
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
                        "source_action_equal": source["actions"] == raw["actions"],
                        "source_reward_equal": source["rewards"] == raw["rewards"],
                        "first_action_mismatch_step": mismatch,
                        "stderr": raw["stderr"],
                        "source_stderr": source["stderr"],
                        "diagnostics": raw["diagnostics"],
                    }
                )
        extracted = _files(extract)

    expected = {
        str(row["path"]): {"size_bytes": int(row["size_bytes"]), "sha256": str(row["sha256"])}
        for row in manifest["files"]
    }
    member_names = [member.name for member in members]
    checks = {
        "archive_manifest_size_hash": archive_path.stat().st_size == int(manifest["archive_size_bytes"]) and _sha256(archive_path) == manifest["archive_sha256"],
        "archive_member_manifest_exact": extracted == expected,
        "safe_unique_regular_members": len(member_names) == len(set(member_names)) and all(member.isfile() for member in members) and all(not Path(name).is_absolute() and ".." not in Path(name).parts for name in member_names),
        "source_main_matches_packaged": extracted["main.py"]["sha256"] == _sha256(HERE / "main.py"),
        "manifest_source_closure_matches_current": manifest.get("source_closure") == build_submission._source_closure(),
        "serving_main_avoids_file_assumption": "__file__" not in (HERE / "main.py").read_text(encoding="utf-8"),
        "real_kaggle_raw_loader_clean_extraction": all(raw_entry.values()),
        "three_exposed_qa_seeds_both_seats": len(games) == 6,
        "all_720_states_719_calls_done": all(game["steps"] == 720 and game["calls"] == 719 and game["statuses"] == ["DONE", "DONE"] for game in games),
        "zero_stderr": all(not game["stderr"] and not game["source_stderr"] for game in games),
        "source_archive_exact_actions_rewards": all(game["source_action_equal"] and game["source_reward_equal"] and game["first_action_mismatch_step"] is None for game in games),
        "diagnostics_identify_candidate": all(game["diagnostics"]["model_id"] == MODEL_ID for game in games),
    }
    report = {
        "schema": "kaggriculture-v14-clean-extraction-package-qa-1",
        "candidate": MODEL_ID,
        "opponent": "v12a2_no_shop_gate",
        "validation_or_new_panel_accessed": False,
        "qa_seeds_are_previously_exposed": True,
        "raw_loader": raw_entry,
        "archive": {"path": str(archive_path.resolve()), "size_bytes": archive_path.stat().st_size, "sha256": _sha256(archive_path)},
        "games": games,
        "checks": checks,
        "verdict": "PASS" if all(checks.values()) else "FAIL",
    }
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    result = qa()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if result["verdict"] != "PASS":
        raise SystemExit(1)
