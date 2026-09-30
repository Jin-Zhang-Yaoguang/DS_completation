"""Build and verify the self-contained V12B Kaggle submission archive."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tarfile
from pathlib import Path
from tempfile import TemporaryDirectory

from kaggle_environments import make


HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "v8_kawa_lead2_slot" / "main.py"
EXPECTED_PARENT_SHA256 = "ed2e443f6ae3683da9f34c55920bc8aa06a81e22e3b905df92389597e8adc327"
ARCHIVE = HERE / "submission.tar.gz"
MANIFEST = HERE / "submission_manifest.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_clean(path: Path):
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location("clean_v12b_main", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def build() -> dict[str, object]:
    parent_hash = sha256(PARENT)
    if parent_hash != EXPECTED_PARENT_SHA256:
        raise RuntimeError(
            f"sealed V8 parent changed: expected {EXPECTED_PARENT_SHA256}, got {parent_hash}"
        )
    with tarfile.open(ARCHIVE, "w:gz") as archive:
        archive.add(HERE / "main.py", arcname="main.py")
        archive.add(PARENT, arcname="parent_agent.py")

    with TemporaryDirectory(prefix="kaggriculture_v12b_submission_") as directory:
        target = Path(directory)
        with tarfile.open(ARCHIVE, "r:gz") as archive:
            archive.extractall(target, filter="data")
        members = sorted(path.name for path in target.iterdir())
        if members != ["main.py", "parent_agent.py"]:
            raise RuntimeError(f"unexpected archive members: {members}")
        module = _load_clean(target / "main.py")
        from kaggle_environments.envs.kaggriculture import kaggriculture as kg

        env = make("kaggriculture", configuration={"seed": 120012}, debug=True)
        steps = env.run([module.agent, kg.starter_agent])
        statuses = [str(state.status) for state in steps[-1]]
        if len(steps) != 720 or statuses != ["DONE", "DONE"]:
            raise RuntimeError((len(steps), statuses))
        rewards = [float(state.reward or 0) for state in steps[-1]]
        diagnostics = module.model_status()
        if diagnostics["errors"]:
            raise RuntimeError(diagnostics["errors"])

    payload: dict[str, object] = {
        "schema": "kaggriculture-v12b-v2-submission-manifest-1",
        "archive": ARCHIVE.name,
        "files": ["main.py", "parent_agent.py"],
        "size_bytes": ARCHIVE.stat().st_size,
        "sha256": sha256(ARCHIVE),
        "parent_model": "baseline_v8",
        "model_id": "v12b_v2_winrisk_feedback_gate",
        "parent_source": str(PARENT),
        "parent_sha256": parent_hash,
        "clean_match": {
            "seed": 120012,
            "steps": len(steps),
            "statuses": statuses,
            "rewards": rewards,
            "diagnostics": diagnostics,
        },
    }
    MANIFEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return payload


if __name__ == "__main__":
    build()
