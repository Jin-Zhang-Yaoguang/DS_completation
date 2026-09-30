"""构建并在干净目录验证 V5 Kaggle 提交归档。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tarfile
from tempfile import TemporaryDirectory

from kaggle_environments import make


HERE = Path(__file__).resolve().parent
FILES = ("main.py", "base_agent.py", "routes.py", "v1_fallback.py")
ARCHIVE = HERE / "submission.tar.gz"


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load(path):
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location("clean_v5_main", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def _clean_match(module):
    from kaggle_environments.envs.kaggriculture import kaggriculture as kg
    env = make("kaggriculture", configuration={"seed": 990001}, debug=True)
    steps = env.run([module.agent, kg.starter_agent])
    statuses = [str(state.status) for state in steps[-1]]
    if len(steps) != 720 or statuses != ["DONE", "DONE"]:
        raise RuntimeError((len(steps), statuses))
    return [float(state.reward or 0) for state in steps[-1]]


def build():
    for name in FILES:
        if not (HERE / name).is_file():
            raise FileNotFoundError(name)
    with tarfile.open(ARCHIVE, "w:gz") as archive:
        for name in FILES:
            archive.add(HERE / name, arcname=name)
    with TemporaryDirectory(prefix="kaggriculture_v4_submission_") as directory:
        target = Path(directory)
        with tarfile.open(ARCHIVE, "r:gz") as archive:
            archive.extractall(target, filter="data")
        members = sorted(path.name for path in target.iterdir())
        if members != sorted(FILES):
            raise RuntimeError(members)
        module = _load(target / "main.py")
        rewards = _clean_match(module)
    result = {
        "schema": "kaggriculture-v5-submission-1",
        "archive": ARCHIVE.name,
        "files": list(FILES),
        "size_bytes": ARCHIVE.stat().st_size,
        "sha256": _sha256(ARCHIVE),
        "clean_match_rewards": rewards,
    }
    (HERE / "submission_manifest.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    build()
