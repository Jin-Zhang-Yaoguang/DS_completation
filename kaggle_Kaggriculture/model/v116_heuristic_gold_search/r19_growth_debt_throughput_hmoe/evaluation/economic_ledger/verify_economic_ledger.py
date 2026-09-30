#!/usr/bin/env python3
"""Run economic-ledger tests and persist their exact status."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern="test_economic_ledger.py")
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    payload = {
        "schema": "v116-r19-economic-ledger-tests-v1",
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "tests_run": int(result.testsRun),
        "failures": [str(test) for test, _trace in result.failures],
        "errors": [str(test) for test, _trace in result.errors],
        "skipped": [str(test) for test, _reason in result.skipped],
        "successful": bool(result.wasSuccessful()),
        "status": "PASS_ECONOMIC_LEDGER" if result.wasSuccessful()
        else "FAIL_CLOSED_ECONOMIC_LEDGER",
        "test_output": stream.getvalue(),
        "evaluator_sha256": sha256(HERE / "evaluate_economy.py"),
        "test_source_sha256": sha256(HERE / "test_economic_ledger.py"),
        "scope": "Single-seed dual-seat diagnostic; no P2, Replay, or gold claim.",
    }
    (HERE / "test_results.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
