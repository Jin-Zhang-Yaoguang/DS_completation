"""Build and clean-room validate the multi-file V12A submission archive."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _copy_runtime(stage: Path) -> None:
    runtime = stage / "runtime"
    runtime.mkdir(parents=True)
    (runtime / "__init__.py").write_text("\n", encoding="utf-8")
    for name in RUNTIME_FILES:
        source = V10 / name if name != "fast_router.py" else V11 / name
        target = runtime / name
        if name == "fast_router.py":
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
                raise RuntimeError("fast_router import block changed; refusing stale rewrite")
            target.write_text(text.replace(old, new, 1), encoding="utf-8")
        else:
            shutil.copy2(source, target)


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
        "schema": "kaggriculture-v12a-embedded-parent-1",
        "source_registry_sha256": _sha256(SOURCE_REGISTRY),
        "router_spec": kwargs["router_spec"],
        "expert_specs": kwargs["expert_specs"],
    }
    (stage / "runtime" / "policy.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_clean_main(path: Path) -> Any:
    module_name = f"_v12a_clean_{hashlib.sha256(str(path).encode()).hexdigest()[:12]}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import extracted main.py")
    module = importlib.util.module_from_spec(spec)
    old_path = list(sys.path)
    sys.modules[module_name] = module
    try:
        sys.path.insert(0, str(path.parent))
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path[:] = old_path
        sys.modules.pop(module_name, None)


def _clean_match(module: Any, seed: int = 434439023) -> dict[str, Any]:
    from kaggle_environments import make
    from kaggle_environments.envs.kaggriculture import kaggriculture as kg

    candidate = module.make_agent()
    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=True)
    steps = env.run([candidate, kg.starter_agent])
    statuses = [str(state.status) for state in steps[-1]]
    if len(steps) != 720 or statuses != ["DONE", "DONE"]:
        raise RuntimeError({"steps": len(steps), "statuses": statuses})
    diagnostics = candidate.diagnostics()
    if diagnostics.get("residual_fallbacks") != 0:
        raise RuntimeError(diagnostics)
    return {
        "seed": int(seed),
        "steps": len(steps),
        "statuses": statuses,
        "rewards": [float(state.reward or 0.0) for state in steps[-1]],
        "selected": (diagnostics.get("parent_diagnostics") or {}).get("selected"),
        "changed_steps": diagnostics.get("changed_steps"),
        "residual_fallbacks": diagnostics.get("residual_fallbacks"),
    }


def build() -> dict[str, Any]:
    with TemporaryDirectory(prefix="kaggriculture_v12a_build_") as directory:
        stage = Path(directory) / "stage"
        stage.mkdir()
        shutil.copy2(HERE / "main.py", stage / "main.py")
        _copy_runtime(stage)
        _copy_experts(stage)
        _write_policy(stage)
        members = sorted(path for path in stage.rglob("*") if path.is_file())
        with tarfile.open(ARCHIVE, "w:gz") as archive:
            for path in members:
                archive.add(path, arcname=path.relative_to(stage))
        extract = Path(directory) / "extract"
        extract.mkdir()
        with tarfile.open(ARCHIVE, "r:gz") as archive:
            archive.extractall(extract, filter="data")
        module = _load_clean_main(extract / "main.py")
        clean_match = _clean_match(module)
        file_records = [
            {
                "path": str(path.relative_to(extract)),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in sorted(extract.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
        ]
    result = {
        "schema": "kaggriculture-v12a-submission-1",
        "model_id": "v12a_terminal_branch_guard",
        "parent_id": "r002_learned_router_topday_animal_throttle",
        "archive": ARCHIVE.name,
        "archive_size_bytes": ARCHIVE.stat().st_size,
        "archive_sha256": _sha256(ARCHIVE),
        "files": file_records,
        "clean_match": clean_match,
    }
    MANIFEST.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    build()

