#!/usr/bin/env python3
"""Execute this report notebook top-to-bottom using only Python stdlib.

The project environment intentionally does not require ``nbclient``.  This
runner supports the plain Python cells used by ``v14_analysis.ipynb``, captures
stdout/stderr in standard notebook output objects, and fails on the first cell
error.  It does not provide IPython magics or shell execution.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path


def repo_root_for(notebook_path: Path) -> Path:
    for candidate in (notebook_path.parent, *notebook_path.parents):
        if (candidate / ".venv").is_dir() and (candidate / "kaggle_Kaggriculture").is_dir():
            return candidate
    raise RuntimeError(f"cannot locate repository root from {notebook_path}")


def execute(notebook_path: Path) -> dict:
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    root = repo_root_for(notebook_path.resolve())
    executable = Path(sys.executable)
    if Path(sys.prefix).resolve() != (root / ".venv").resolve():
        raise RuntimeError(f"must use project .venv, got {executable}")
    namespace = {"__name__": "__main__", "__builtins__": __builtins__}
    execution_count = 0
    previous_cwd = Path.cwd()
    try:
        os.chdir(root)
        for cell_index, cell in enumerate(notebook.get("cells", []), start=1):
            if cell.get("cell_type") != "code":
                continue
            execution_count += 1
            source = "".join(cell.get("source", []))
            stdout = io.StringIO()
            stderr = io.StringIO()
            cell["outputs"] = []
            cell["execution_count"] = execution_count
            try:
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    exec(compile(source, f"{notebook_path.name}:cell-{cell_index}", "exec"), namespace)
            except Exception as exc:
                if stdout.getvalue():
                    cell["outputs"].append(
                        {"name": "stdout", "output_type": "stream", "text": stdout.getvalue().splitlines(keepends=True)}
                    )
                if stderr.getvalue():
                    cell["outputs"].append(
                        {"name": "stderr", "output_type": "stream", "text": stderr.getvalue().splitlines(keepends=True)}
                    )
                trace = traceback.format_exc().splitlines()
                cell["outputs"].append(
                    {
                        "ename": type(exc).__name__,
                        "evalue": str(exc),
                        "output_type": "error",
                        "traceback": trace,
                    }
                )
                notebook_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
                raise RuntimeError(f"notebook failed at code cell {execution_count}") from exc
            if stdout.getvalue():
                cell["outputs"].append(
                    {"name": "stdout", "output_type": "stream", "text": stdout.getvalue().splitlines(keepends=True)}
                )
            if stderr.getvalue():
                cell["outputs"].append(
                    {"name": "stderr", "output_type": "stream", "text": stderr.getvalue().splitlines(keepends=True)}
                )
    finally:
        os.chdir(previous_cwd)

    notebook.setdefault("metadata", {})["codex_execution"] = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "executable": str(executable),
        "runner": str(Path(__file__).resolve()),
        "status": "passed",
        "code_cells": execution_count,
    }
    notebook_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return notebook["metadata"]["codex_execution"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("notebook", type=Path)
    args = parser.parse_args()
    receipt = execute(args.notebook.resolve())
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
