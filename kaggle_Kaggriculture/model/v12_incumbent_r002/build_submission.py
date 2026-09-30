"""Build a deterministic, self-contained Kaggle archive for frozen r002."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
from tempfile import TemporaryDirectory
from typing import Any


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent
V10 = MODEL_ROOT / "v10_replay_lolo_router"
V11 = MODEL_ROOT / "v11_iterative_league"
SOURCE_REGISTRY = V11 / "runs" / "round_002" / "strategy" / "registry_next.json"
ARCHIVE = HERE / "submission.tar.gz"
MANIFEST = HERE / "submission_manifest.json"

MODEL_ID = "v12_incumbent_r002"
SOURCE_MODEL_ID = "r002_learned_router_topday_animal_throttle"
FAILED_SUBMISSION_ID = 55713101
FAILED_VALIDATION_EPISODE_ID = 97566763
FAILED_ARCHIVE_SHA256 = (
    "453df6eed29e5daa4160371ad31b3286c01ed7a7dbe2e7db735867ba236fe67d"
)
EXPECTED_SOURCE_REGISTRY_FILE_SHA256 = (
    "e98156a0ac3741f5c9cfa698ea00f37d54e9277b53bfa864eb848928eb8dbaf0"
)
EXPECTED_SOURCE_REGISTRY_AND_CODE_SHA256 = (
    "a4d63598c95a165add426aaac7b1dbe2cd9ff2e6f91dde71e6e3ec0e54da26a5"
)
EXPECTED_SOURCE_SERVING_SHA256 = (
    "38afb12bd5fbc987adf752acb437abe9330bd385233c22782b35353f77be2d74"
)
EXPECTED_ROUTER_PARENT_SERVING_SHA256 = (
    "9813b175856c8e702613bb27b4e0a4b95403cae65093615d9611f12cdb184ed6"
)

RUNTIME_FILES = (
    "agent_factory.py",
    "expert_registry.py",
    "variants.py",
    "router.py",
    "fast_router.py",
    "learned_router_weights.npz",
)
EXPERT_FILES = {
    "v1_adaptive_market": ("main.py",),
    "v2_survival_guard": ("main.py",),
    "v5_rule_hybrid": ("main.py", "base_agent.py", "v1_fallback.py", "routes.py"),
    "v8_kawa_lead2_slot": ("main.py",),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_sha256(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _source_preflight() -> dict[str, Any]:
    from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
        load_registry,
        registry_fingerprint,
    )
    from kaggle_Kaggriculture.model.v11_iterative_league.league import (
        model_fingerprint,
    )

    registry = load_registry(SOURCE_REGISTRY)
    candidate = registry.require(SOURCE_MODEL_ID)
    kwargs = candidate.get("factory_kwargs") or {}
    exact_mutation = {
        "parent_id": kwargs.get("parent_id"),
        "mutation_name": kwargs.get("mutation_name"),
        "mutation_params": kwargs.get("mutation_params"),
    }
    expected_mutation = {
        "parent_id": "learned_router",
        "mutation_name": "topday_animal_throttle",
        "mutation_params": {"days": [10, 17, 24], "fraction": 0.5},
    }
    checks = {
        "registry_file_sha256": sha256(SOURCE_REGISTRY),
        "registry_and_code_sha256": registry_fingerprint(registry),
        "source_serving_sha256": model_fingerprint(registry, SOURCE_MODEL_ID),
        "router_parent_serving_sha256": model_fingerprint(registry, "learned_router"),
        "exact_mutation_definition": exact_mutation == expected_mutation,
    }
    expected = {
        "registry_file_sha256": EXPECTED_SOURCE_REGISTRY_FILE_SHA256,
        "registry_and_code_sha256": EXPECTED_SOURCE_REGISTRY_AND_CODE_SHA256,
        "source_serving_sha256": EXPECTED_SOURCE_SERVING_SHA256,
        "router_parent_serving_sha256": EXPECTED_ROUTER_PARENT_SERVING_SHA256,
        "exact_mutation_definition": True,
    }
    if checks != expected:
        raise RuntimeError(
            "frozen r002 source drifted; refusing to build: "
            + json.dumps({"expected": expected, "actual": checks}, sort_keys=True)
        )
    source_files = {
        "registry_next.json": SOURCE_REGISTRY,
        "candidate_agent.py": V11 / "candidate_agent.py",
        "mutation_catalog.py": V11 / "mutation_catalog.py",
        "fast_router.py": V11 / "fast_router.py",
        "agent_factory.py": V10 / "agent_factory.py",
        "expert_registry.py": V10 / "expert_registry.py",
        "router.py": V10 / "router.py",
        "variants.py": V10 / "variants.py",
        "learned_router_weights.npz": V10 / "learned_router_weights.npz",
    }
    return {
        **checks,
        "candidate_spec_sha256": _canonical_sha256(candidate),
        "mutation_definition": exact_mutation,
        "source_files": {
            name: {"size_bytes": path.stat().st_size, "sha256": sha256(path)}
            for name, path in sorted(source_files.items())
        },
    }


def _copy_runtime(stage: Path) -> None:
    runtime = stage / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "__init__.py").write_text("\n", encoding="utf-8")
    for name in RUNTIME_FILES:
        source = V11 / name if name == "fast_router.py" else V10 / name
        target = runtime / name
        if name != "fast_router.py":
            shutil.copy2(source, target)
            continue
        text = source.read_text(encoding="utf-8")
        old = (
            "from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (\n"
            "    Registry,\n"
            "    create_agent as create_registered_agent,\n"
            "    resolve_path,\n"
            ")\n"
            "from kaggle_Kaggriculture.model.v10_replay_lolo_router.router import (\n"
        )
        new = (
            "from agent_factory import (\n"
            "    Registry,\n"
            "    create_agent as create_registered_agent,\n"
            "    resolve_path,\n"
            ")\n"
            "from router import (\n"
        )
        if old not in text:
            raise RuntimeError("fast_router import block drifted; refusing stale rewrite")
        target.write_text(text.replace(old, new, 1), encoding="utf-8")


def _copy_experts(stage: Path) -> None:
    for directory, names in EXPERT_FILES.items():
        target_dir = stage / directory
        target_dir.mkdir(parents=True)
        for name in names:
            shutil.copy2(MODEL_ROOT / directory / name, target_dir / name)


def _write_policy(stage: Path) -> None:
    registry = json.loads(SOURCE_REGISTRY.read_text(encoding="utf-8"))
    learned = next(item for item in registry["models"] if item["id"] == "learned_router")
    kwargs = learned["factory_kwargs"]
    payload = {
        "schema": "kaggriculture-v12-r002-embedded-router-1",
        "source_model_id": SOURCE_MODEL_ID,
        "source_serving_sha256": EXPECTED_SOURCE_SERVING_SHA256,
        "source_registry_file_sha256": EXPECTED_SOURCE_REGISTRY_FILE_SHA256,
        "router_spec": kwargs["router_spec"],
        "expert_specs": kwargs["expert_specs"],
        "residual": {
            "name": "topday_animal_throttle",
            "days": [10, 17, 24],
            "fraction": 0.5,
            "products": ["EGG", "MILK", "WOOL"],
        },
    }
    (stage / "runtime" / "policy.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_deterministic_archive(stage: Path) -> None:
    members = sorted(path for path in stage.rglob("*") if path.is_file())
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.PAX_FORMAT) as archive:
        for path in members:
            info = archive.gettarinfo(str(path), arcname=str(path.relative_to(stage)))
            info.uid = 0
            info.gid = 0
            info.uname = ""
            info.gname = ""
            info.mtime = 0
            info.mode = 0o644
            with path.open("rb") as source:
                archive.addfile(info, source)
    with ARCHIVE.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed:
            compressed.write(buffer.getvalue())


def _load_clean_agent(path: Path) -> Any:
    from kaggle_environments.agent import get_last_callable

    return get_last_callable(path.read_text(encoding="utf-8"), path=str(path))


def _clean_match(
    candidate: Any, expected_bundle: Path, seed: int = 93451031
) -> dict[str, Any]:
    from kaggle_environments import make
    from kaggle_environments.envs.kaggriculture import kaggriculture as kg

    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=True)
    steps = env.run([candidate, kg.starter_agent])
    statuses = [str(state.status) for state in steps[-1]]
    diagnostics = candidate.__globals__["model_status"]()
    runtime_errors = (diagnostics.get("parent_diagnostics") or {}).get(
        "runtime_errors", []
    )
    if len(steps) != 720 or statuses != ["DONE", "DONE"] or runtime_errors:
        raise RuntimeError(
            {"steps": len(steps), "statuses": statuses, "diagnostics": diagnostics}
        )
    return {
        "seed": int(seed),
        "steps": len(steps),
        "calls": diagnostics["calls"],
        "statuses": statuses,
        "rewards": [float(state.reward or 0.0) for state in steps[-1]],
        "selected": (diagnostics.get("parent_diagnostics") or {}).get("selected"),
        "changed_actions": diagnostics["changed_actions"],
        "runtime_errors": runtime_errors,
        "loader": "kaggle_environments.agent.get_last_callable",
        "loader_globals_has_file": "__file__" in candidate.__globals__,
        "bundle_directory_match": candidate.__globals__["HERE"]
        == expected_bundle.resolve(),
    }


def build() -> dict[str, Any]:
    provenance = _source_preflight()
    with TemporaryDirectory(prefix="kaggriculture_v12_r002_build_") as directory:
        stage = Path(directory) / "stage"
        stage.mkdir()
        shutil.copy2(HERE / "main.py", stage / "main.py")
        _copy_runtime(stage)
        _copy_experts(stage)
        _write_policy(stage)
        _write_deterministic_archive(stage)

        extract = Path(directory) / "extract"
        extract.mkdir()
        with tarfile.open(ARCHIVE, "r:gz") as archive:
            archive.extractall(extract, filter="data")
        clean_match = _clean_match(
            _load_clean_agent(extract / "main.py"), extract
        )
        file_records = [
            {
                "path": str(path.relative_to(extract)),
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            for path in sorted(extract.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
        ]
    result = {
        "schema": "kaggriculture-v12-r002-submission-manifest-1",
        "model_id": MODEL_ID,
        "source_model_id": SOURCE_MODEL_ID,
        "policy_changed": False,
        "archive": ARCHIVE.name,
        "archive_size_bytes": ARCHIVE.stat().st_size,
        "archive_sha256": sha256(ARCHIVE),
        "serving_repair": {
            "failed_submission_id": FAILED_SUBMISSION_ID,
            "failed_validation_episode_id": FAILED_VALIDATION_EPISODE_ID,
            "failed_archive_sha256": FAILED_ARCHIVE_SHA256,
            "failure": "NameError: name '__file__' is not defined",
            "root_cause": (
                "kaggle_environments.agent.get_last_callable executes raw "
                "main.py with env={} and therefore does not define __file__"
            ),
            "repair": (
                "use globals()['__file__'] for normal imports; otherwise use "
                "the get_last_callable exec_dir temporarily appended at "
                "sys.path[-1]"
            ),
            "repaired_archive_sha256": sha256(ARCHIVE),
            "policy_changed": False,
        },
        "files": file_records,
        "source_provenance": provenance,
        "clean_match": clean_match,
    }
    MANIFEST.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    build()
