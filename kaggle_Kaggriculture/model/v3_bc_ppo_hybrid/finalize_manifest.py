"""Attach exact generator semantics and runtime provenance to a BC manifest."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
from pathlib import Path
import platform

import kaggle_environments
import numpy as np

import collect_bc
import main


HERE = Path(__file__).resolve().parent


def _hash_bytes(value):
    return hashlib.sha256(value).hexdigest()


def finalize(directory):
    directory = Path(directory)
    path = directory / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    semantic_functions = (
        collect_bc._episode,
        main.teacher_route,
        main.encode_observation,
        main.update_history,
        main.potential,
    )
    semantics = "\n\n".join(inspect.getsource(function) for function in semantic_functions).encode("utf-8")
    manifest["generation_semantics_sha256"] = _hash_bytes(semantics)
    manifest["runtime"] = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "kaggle_environments": kaggle_environments.__version__,
    }
    manifest["source_sha256"] = {
        name: _hash_bytes((HERE / name).read_bytes())
        for name in ("collect_bc.py", "main.py", "base_agent.py")
    }
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=HERE / "data" / "bc")
    result = finalize(parser.parse_args().data)
    print(json.dumps({key: result[key] for key in ("episodes", "generation_semantics_sha256", "runtime", "source_sha256")}, ensure_ascii=False, indent=2))
