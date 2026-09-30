#!/usr/bin/env python3
"""Run the accounting test suite and persist a fail-closed verification report."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
from datetime import datetime, timezone
import unittest


HERE = Path(__file__).resolve().parent
REPORT = HERE / "verification_report.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    module_files = sorted((HERE / "_module").glob("kagsim_accounting*.so"))
    if len(module_files) != 1:
        raise RuntimeError(
            "fail closed: build_accounting_engine.py must produce exactly one module; "
            f"got {module_files}"
        )
    loader = unittest.defaultTestLoader
    suite = loader.discover(str(HERE), pattern="test_accounting_engine.py")
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    payload = {
        "schema": "kagsim-accounting-verification-v1",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine_version": "1.32.7",
        "module_name": "kagsim_accounting",
        "module_sha256": sha256(module_files[0]),
        "tests_run": int(result.testsRun),
        "failures": [str(test) for test, _trace in result.failures],
        "errors": [str(test) for test, _trace in result.errors],
        "skipped": [str(test) for test, _reason in result.skipped],
        "successful": bool(result.wasSuccessful()),
        "status": "PASS_ACCOUNTING_ENGINE" if result.wasSuccessful()
        else "FAIL_CLOSED_ACCOUNTING_ENGINE",
        "test_output": stream.getvalue(),
        "scope": "No P2, no Replay, no candidate actions informed by accounting truth.",
    }
    REPORT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
