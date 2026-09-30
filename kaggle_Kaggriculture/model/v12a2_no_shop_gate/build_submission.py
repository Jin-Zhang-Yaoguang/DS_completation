"""Build and clean-room validate the self-contained V12A2 archive."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import tarfile
from tempfile import TemporaryDirectory

from kaggle_Kaggriculture.model.v12a_terminal_branch_guard import build_submission as parent_build


HERE = Path(__file__).resolve().parent
PARENT = HERE.parent / "v12a_terminal_branch_guard"
ARCHIVE = HERE / "submission.tar.gz"
MANIFEST = HERE / "submission_manifest.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> dict[str, object]:
    with TemporaryDirectory(prefix="kaggriculture_v12a2_shop_build_") as directory:
        stage = Path(directory) / "stage"
        stage.mkdir()
        shutil.copy2(HERE / "main.py", stage / "main.py")
        shutil.copy2(PARENT / "main.py", stage / "base_agent.py")
        parent_build._copy_runtime(stage)
        parent_build._copy_experts(stage)
        parent_build._write_policy(stage)
        members = sorted(path for path in stage.rglob("*") if path.is_file())
        with tarfile.open(ARCHIVE, "w:gz") as archive:
            for path in members:
                archive.add(path, arcname=path.relative_to(stage))
        extract = Path(directory) / "extract"
        extract.mkdir()
        with tarfile.open(ARCHIVE, "r:gz") as archive:
            archive.extractall(extract, filter="data")
        from kaggle_environments.agent import get_last_callable

        raw_loader_callable = get_last_callable(
            (extract / "main.py").read_text(encoding="utf-8"),
            path=str(extract / "main.py"),
        )
        raw_loader_check = {
            "callable_name": getattr(raw_loader_callable, "__name__", None),
            "is_agent_global": (
                getattr(raw_loader_callable, "__globals__", {}).get("agent")
                is raw_loader_callable
            ),
            "is_not_model_status": (
                getattr(raw_loader_callable, "__globals__", {}).get("model_status")
                is not raw_loader_callable
            ),
        }
        if not all(
            (
                raw_loader_check["callable_name"] == "agent",
                raw_loader_check["is_agent_global"],
                raw_loader_check["is_not_model_status"],
            )
        ):
            raise RuntimeError(
                {"kaggle_raw_loader_entrypoint_invalid": raw_loader_check}
            )
        module = parent_build._load_clean_main(extract / "main.py")
        clean_match = parent_build._clean_match(module)
        files = [
            {
                "path": str(path.relative_to(extract)),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
            for path in sorted(extract.rglob("*"))
            if path.is_file() and "__pycache__" not in path.parts
        ]
    result: dict[str, object] = {
        "schema": "kaggriculture-v12a2-submission-1",
        "model_id": "v12a2_no_shop_gate",
        "parent_id": "v12a_terminal_branch_guard",
        "removed_component": "unlocked-shop product gate",
        "archive": ARCHIVE.name,
        "archive_size_bytes": ARCHIVE.stat().st_size,
        "archive_sha256": _sha256(ARCHIVE),
        "kaggle_raw_loader": raw_loader_check,
        "files": files,
        "clean_match": clean_match,
    }
    MANIFEST.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    build()
