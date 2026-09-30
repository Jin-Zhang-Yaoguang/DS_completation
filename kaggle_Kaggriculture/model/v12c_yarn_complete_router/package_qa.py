"""Independent clean-archive QA for the sealed V12C submission."""

from __future__ import annotations

from contextlib import redirect_stderr
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import random
import sys
import tarfile
from tempfile import TemporaryDirectory
from typing import Any


HERE = Path(__file__).resolve().parent
ARCHIVE = HERE / "submission.tar.gz"
MANIFEST = HERE / "submission_manifest.json"
SEAL = HERE / "pre_screen_design_seal.json"
REPORT = HERE / "package_qa_report.json"
QA_SEEDS = (1991475240, 298154402, 850110075)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    sys.modules[name] = module
    try:
        sys.path.insert(0, str(path.parent))
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = old_path
        sys.modules.pop(name, None)


class _Recorder:
    def __init__(self, agent: Any) -> None:
        self.agent = agent
        self.digest = hashlib.sha256()
        self.calls = 0

    def __call__(self, obs: Any, configuration: Any = None):
        action = self.agent(obs, configuration)
        encoded = json.dumps(
            action,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        self.digest.update(len(encoded).to_bytes(8, "big"))
        self.digest.update(encoded)
        self.calls += 1
        return action


def _run(module: Any, seed: int, seat: int) -> dict[str, Any]:
    from kaggle_environments import make
    import numpy as np
    from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
        create_agent,
        load_registry,
    )

    raw = module.make_agent()
    candidate = _Recorder(raw)
    registry = load_registry(HERE.parent / "v10_replay_lolo_router" / "final_registry.json")
    opponent = create_agent(registry, "baseline_v8")
    agents = [candidate, opponent] if seat == 0 else [opponent, candidate]
    # Match the frozen evaluator's deterministic global RNG initialisation.
    # Kaggriculture's shop draw is otherwise sensitive to process-global RNG
    # history even when the environment configuration seed is fixed.
    random.seed(int(seed) * 104729 + int(seat) * 1009)
    np.random.seed((int(seed) + int(seat) * 65537) % (2**32 - 1))
    stderr = io.StringIO()
    with redirect_stderr(stderr):
        env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
        steps = env.run(agents)
    diagnostics = raw.diagnostics()
    return {
        "seed": int(seed),
        "seat": int(seat),
        "states": len(steps),
        "calls": candidate.calls,
        "statuses": [str(item.status) for item in steps[-1]],
        "rewards": [float(item.reward or 0.0) for item in steps[-1]],
        "action_trace_sha256": candidate.digest.hexdigest(),
        "selected": diagnostics["selected"],
        "selection_reason": diagnostics["selection_reason"],
        "prefix_complete": diagnostics["prefix_complete"],
        "prefix_match": diagnostics["prefix_match"],
        "runtime_errors": list(diagnostics["runtime_errors"]),
        "selected_fallbacks": int(diagnostics["selected_fallbacks"]),
        "stderr": stderr.getvalue(),
    }


def qa() -> dict[str, Any]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    seal = json.loads(SEAL.read_text(encoding="utf-8"))
    checks: dict[str, bool] = {
        "archive_matches_manifest": _sha256(ARCHIVE) == manifest["archive_sha256"],
        "archive_matches_pre_screen_seal": _sha256(ARCHIVE)
        == seal["implementation_seal"]["submission_archive_sha256"],
        "main_matches_pre_screen_seal": _sha256(HERE / "main.py")
        == seal["implementation_seal"]["main_sha256"],
        "registry_matches_pre_screen_seal": _sha256(HERE / "registry_entry.json")
        == seal["implementation_seal"]["registry_entry_sha256"],
        "manifest_matches_pre_screen_seal": _sha256(MANIFEST)
        == seal["implementation_seal"]["submission_manifest_sha256"],
    }

    with tarfile.open(ARCHIVE, "r:gz") as archive:
        members = archive.getmembers()
        checks["safe_member_names"] = all(
            not member.name.startswith("/")
            and ".." not in Path(member.name).parts
            and not member.issym()
            and not member.islnk()
            for member in members
        )
        with TemporaryDirectory(prefix="kaggriculture_v12c_qa_") as directory:
            root = Path(directory)
            archive.extractall(root, filter="data")
            actual = {
                str(path.relative_to(root)): {
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
                for path in sorted(root.rglob("*"))
                if path.is_file() and "__pycache__" not in path.parts
            }
            expected = {
                str(item["path"]): {
                    "size_bytes": int(item["size_bytes"]),
                    "sha256": str(item["sha256"]),
                }
                for item in manifest["files"]
            }
            checks["exact_manifest_members"] = actual == expected
            archive_module = _load_module(
                root / "main.py", "_v12c_package_qa_archive"
            )
            source_module = _load_module(
                HERE / "main.py", "_v12c_package_qa_source"
            )
            comparisons = []
            for seed in QA_SEEDS:
                for seat in (0, 1):
                    source = _run(source_module, seed, seat)
                    archive_run = _run(archive_module, seed, seat)
                    exact_fields = (
                        "states",
                        "calls",
                        "statuses",
                        "rewards",
                        "action_trace_sha256",
                        "selected",
                        "selection_reason",
                        "prefix_complete",
                        "prefix_match",
                        "runtime_errors",
                        "selected_fallbacks",
                    )
                    exact = all(source[key] == archive_run[key] for key in exact_fields)
                    comparisons.append(
                        {
                            "seed": seed,
                            "seat": seat,
                            "exact_source_archive": exact,
                            "source": source,
                            "archive": archive_run,
                        }
                    )

    checks["six_source_archive_matches"] = len(comparisons) == 6 and all(
        row["exact_source_archive"] for row in comparisons
    )
    checks["all_720_states_719_calls"] = all(
        row[side]["states"] == 720 and row[side]["calls"] == 719
        for row in comparisons
        for side in ("source", "archive")
    )
    checks["all_done_done"] = all(
        row[side]["statuses"] == ["DONE", "DONE"]
        for row in comparisons
        for side in ("source", "archive")
    )
    checks["zero_runtime_errors_or_fallbacks"] = all(
        not row[side]["runtime_errors"] and row[side]["selected_fallbacks"] == 0
        for row in comparisons
        for side in ("source", "archive")
    )
    checks["zero_stderr"] = all(
        row[side]["stderr"] == ""
        for row in comparisons
        for side in ("source", "archive")
    )
    checks["both_router_branches_covered"] = {
        row["archive"]["selected"] for row in comparisons
    } == {"baseline_v5", "baseline_v8"}
    payload = {
        "schema": "kaggriculture-v12c-package-qa-1",
        "archive": str(ARCHIVE.resolve()),
        "archive_size_bytes": ARCHIVE.stat().st_size,
        "archive_sha256": _sha256(ARCHIVE),
        "pre_screen_design_seal_sha256": _sha256(SEAL),
        "qa_seeds": list(QA_SEEDS),
        "qa_seed_provenance": "all three are already-exposed frozen_v3 screen18 sources",
        "comparisons": comparisons,
        "checks": checks,
        "passed": all(checks.values()),
        "formal_panel_accessed": False,
    }
    REPORT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return payload


if __name__ == "__main__":
    qa()
