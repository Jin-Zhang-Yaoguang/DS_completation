"""Build a deterministic, self-contained V14-QS1 Kaggle archive."""

from __future__ import annotations

import gzip
import hashlib
from io import BytesIO
import json
from pathlib import Path
import shutil
import sys
import tarfile
from tempfile import TemporaryDirectory
from typing import Any

from kaggle_Kaggriculture.model.v12a_terminal_branch_guard import (
    build_submission as parent_build,
)


HERE = Path(__file__).resolve().parent
MODEL_ROOT = HERE.parent
SEARCH_ROOT = MODEL_ROOT / "v14_first_principles_search"
QUEUE_SOURCE = SEARCH_ROOT / "prototype_queue_solver.py"
S1_SOURCE = SEARCH_ROOT / "alternatives" / "s1_wheat_squeeze" / "main.py"
A2_SOURCE = MODEL_ROOT / "v12a2_no_shop_gate" / "main.py"
BASE_SOURCE = MODEL_ROOT / "v12a_terminal_branch_guard" / "main.py"
ARCHIVE = HERE / "submission.tar.gz"
MANIFEST = HERE / "submission_manifest.json"
MODEL_ID = "v14_queue_s1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"{label} changed; refusing stale source rewrite")
    return text.replace(old, new, 1)


def _queue_bundle_text() -> str:
    text = QUEUE_SOURCE.read_text(encoding="utf-8")
    text = _replace_once(text, "from pathlib import Path\nimport sys\n", "", "queue imports")
    text = _replace_once(
        text,
        "_WORKSPACE = Path(__file__).resolve().parents[3]\n"
        "if str(_WORKSPACE) not in sys.path:\n"
        "    sys.path.insert(0, str(_WORKSPACE))\n\n"
        "from kaggle_Kaggriculture.model.v12a2_no_shop_gate import main as a2\n\n"
        "try:\n"
        "    from kaggle_environments.envs.kaggriculture import kaggriculture as kg\n"
        "except Exception:  # Serving must fail closed if engine helpers are unavailable.\n"
        "    kg = None\n",
        "import a2_agent as a2  # type: ignore\n\n"
        "try:\n"
        "    import official_kaggriculture as kg  # type: ignore\n"
        "except Exception:  # Serving must fail closed if bundled helpers are unavailable.\n"
        "    kg = None\n",
        "queue runtime bootstrap",
    )
    if "kaggle_Kaggriculture.model" in text or "/Users/" in text:
        raise RuntimeError("queue bundle retained a repository dependency")
    return text


def _s1_bundle_text() -> str:
    text = S1_SOURCE.read_text(encoding="utf-8")
    text = _replace_once(
        text,
        "from kaggle_Kaggriculture.model.v12a2_no_shop_gate import main as a2\n"
        "from kaggle_Kaggriculture.model.v8_kawa_lead2_slot import main as v8\n",
        "import a2_agent as a2  # type: ignore\n"
        "from v8_kawa_lead2_slot import main as v8  # type: ignore\n",
        "S1 bundled imports",
    )
    if "kaggle_Kaggriculture.model" in text or "/Users/" in text:
        raise RuntimeError("S1 bundle retained a repository dependency")
    return text


def _official_sources() -> tuple[Path, Path, str]:
    from kaggle_environments.envs.kaggriculture import kaggriculture as installed

    module = Path(installed.__file__).resolve()
    specification = module.with_name("kaggriculture.json")
    if not module.is_file() or not specification.is_file():
        raise FileNotFoundError("official Kaggriculture runtime closure is incomplete")
    return module, specification, str(getattr(installed, "__version__", "1.32.7"))


def _stage(root: Path) -> dict[str, Any]:
    shutil.copy2(HERE / "main.py", root / "main.py")
    (root / "queue_core.py").write_text(_queue_bundle_text(), encoding="utf-8")
    (root / "s1_agent.py").write_text(_s1_bundle_text(), encoding="utf-8")
    shutil.copy2(A2_SOURCE, root / "a2_agent.py")
    shutil.copy2(BASE_SOURCE, root / "base_agent.py")
    parent_build._copy_runtime(root)
    parent_build._copy_experts(root)
    parent_build._write_policy(root)
    official_module, official_json, version = _official_sources()
    shutil.copy2(official_module, root / "official_kaggriculture.py")
    shutil.copy2(official_json, root / "kaggriculture.json")
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in {".py", ".json"}:
            continue
        payload = path.read_text(encoding="utf-8", errors="strict")
        if "/Users/" in payload or str(MODEL_ROOT.parent.parent) in payload:
            raise RuntimeError(f"absolute project path leaked into {path.relative_to(root)}")
    main_text = (root / "main.py").read_text(encoding="utf-8")
    if "__file__" in main_text or main_text.rfind("def agent(") <= main_text.rfind("def model_status("):
        raise RuntimeError("serving main violates raw-loader entry contract")
    return {
        "official_runtime_module": "kaggle_environments.envs.kaggriculture.kaggriculture",
        "official_runtime_filename": official_module.name,
        "official_runtime_sha256": sha256(official_module),
        "official_spec_sha256": sha256(official_json),
        "declared_runtime_version": version,
    }


def _records(root: Path) -> list[dict[str, Any]]:
    return [
        {"path": str(path.relative_to(root)), "size_bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in sorted(root.rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
    ]


def _write_deterministic_archive(root: Path, records: list[dict[str, Any]]) -> None:
    with ARCHIVE.open("wb") as sink:
        with gzip.GzipFile(filename="", mode="wb", fileobj=sink, mtime=0) as zipped:
            with tarfile.open(fileobj=zipped, mode="w", format=tarfile.PAX_FORMAT) as archive:
                for record in records:
                    path = root / str(record["path"])
                    data = path.read_bytes()
                    info = tarfile.TarInfo(str(record["path"]))
                    info.size = len(data)
                    info.mode = 0o644
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    archive.addfile(info, BytesIO(data))


def _raw_contract(extract: Path) -> dict[str, Any]:
    from kaggle_environments.agent import get_last_callable

    for name in (
        "queue_core", "s1_agent", "a2_agent", "base_agent", "official_kaggriculture",
        "fast_router", "agent_factory", "expert_registry", "router", "variants",
    ):
        sys.modules.pop(name, None)
    main_path = extract / "main.py"
    loaded = get_last_callable(main_path.read_text(encoding="utf-8"), path=str(main_path))
    queue = loaded.__globals__.get("queue")
    s1 = loaded.__globals__.get("s1")
    return {
        "callable_name": getattr(loaded, "__name__", None),
        "is_agent_global": loaded.__globals__.get("agent") is loaded,
        "code_filename_is_extracted_main": Path(loaded.__code__.co_filename).resolve() == main_path.resolve(),
        "queue_core_is_extracted": Path(queue.__file__).resolve() == (extract / "queue_core.py").resolve(),
        "s1_is_extracted": Path(s1.__file__).resolve() == (extract / "s1_agent.py").resolve(),
        "a2_is_extracted": Path(queue.a2.__file__).resolve() == (extract / "a2_agent.py").resolve(),
        "base_is_extracted": Path(queue.a2.base.__file__).resolve() == (extract / "base_agent.py").resolve(),
        "official_runtime_is_extracted": Path(queue.kg.__file__).resolve() == (extract / "official_kaggriculture.py").resolve(),
    }


def _source_closure() -> dict[str, str]:
    entry = json.loads((HERE / "registry_entry.json").read_text(encoding="utf-8"))
    closure: dict[str, str] = {}
    for raw in entry.get("code_paths", []):
        path = (HERE / str(raw)).resolve()
        if not path.is_file() or not path.is_relative_to(MODEL_ROOT):
            raise RuntimeError(f"invalid registry code path: {raw}")
        closure[str(path.relative_to(MODEL_ROOT))] = sha256(path)
    if not closure:
        raise RuntimeError("registry code path closure is empty")
    return dict(sorted(closure.items()))


def build() -> dict[str, Any]:
    with TemporaryDirectory(prefix="v14_qs1_build_") as directory:
        stage = Path(directory) / "stage"
        extract = Path(directory) / "extract"
        stage.mkdir()
        extract.mkdir()
        official = _stage(stage)
        records = _records(stage)
        _write_deterministic_archive(stage, records)
        with tarfile.open(ARCHIVE, "r:gz") as archive:
            archive.extractall(extract, filter="data")
        raw_contract = _raw_contract(extract)
        if not all(raw_contract.values()):
            raise RuntimeError({"invalid_raw_contract": raw_contract})
        if records != _records(extract):
            raise RuntimeError("archive extraction differs from staged member manifest")
    sources = _source_closure()
    result = {
        "schema": "kaggriculture-v14-self-contained-submission-1",
        "model_id": MODEL_ID,
        "parent_id": "v12a2_no_shop_gate",
        "candidate_source_frozen": False,
        "archive": ARCHIVE.name,
        "archive_size_bytes": ARCHIVE.stat().st_size,
        "archive_sha256": sha256(ARCHIVE),
        "deterministic_archive": True,
        "serving_main_avoids_file_assumption": True,
        "source_closure": sources,
        "official_runtime": official,
        "kaggle_raw_loader": raw_contract,
        "files": records,
    }
    MANIFEST.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2, sort_keys=True))
