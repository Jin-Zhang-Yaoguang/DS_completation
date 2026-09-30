"""Independent raw-loader smoke test for one firewall-sealed V15 archive."""

from __future__ import annotations

import argparse
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import inspect
import io
import json
import os
from pathlib import Path
import tempfile

from kaggle_environments import make
from kaggle_environments.agent import get_last_callable

from .inventory import archive_closure
from .protocol import atomic_create_json_strict, file_sha256


SCHEMA = "kaggriculture-v15-private-package-qa-1"
EXPOSED_QA_SEEDS = (93_451_031, 93_451_032, 93_451_033)


class Counted:
    def __init__(self, policy):
        self.policy = policy
        self.calls = 0
        signature = inspect.signature(policy)
        try:
            signature.bind(None, None)
            self.accepts_configuration = True
        except TypeError:
            self.accepts_configuration = False

    def __call__(self, observation, configuration=None):
        self.calls += 1
        if self.accepts_configuration:
            return self.policy(observation, configuration)
        return self.policy(observation)


def _load(main_path: Path):
    policy = get_last_callable(main_path.read_text(encoding="utf-8"), path=str(main_path))
    if not callable(policy) or getattr(policy, "__name__", "") != "agent":
        raise ValueError("raw loader did not select the final agent callable")
    return policy


def run_qa(archive: Path) -> dict:
    archive = archive.resolve(strict=True)
    closure = archive_closure(archive)
    if [row["path"] for row in closure["members"]] != ["main.py"]:
        raise ValueError("candidate QA accepts only the sealed single-file archive")
    source = archive.parent / "main.py"
    if not source.is_file() or file_sha256(source) != closure["members"][0]["sha256"]:
        raise ValueError("archive main.py differs from the sealed source")

    rows = []
    all_stderr = []
    with tempfile.TemporaryDirectory(prefix="v15-candidate-qa-") as raw:
        main_path = Path(raw) / "main.py"
        main_path.write_bytes(source.read_bytes())
        os.chmod(main_path, 0o444)
        for seed in EXPOSED_QA_SEEDS:
            for orientation in (0, 1):
                stdout = io.StringIO()
                stderr = io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    first = Counted(_load(main_path))
                    second = Counted(_load(main_path))
                    env = make("kaggriculture", configuration={"seed": seed}, debug=False)
                    env.run([first, second] if orientation == 0 else [second, first])
                statuses = [str(state.status) for state in env.state]
                err = stderr.getvalue()
                all_stderr.append(err)
                rows.append(
                    {
                        "seed": seed,
                        "orientation": orientation,
                        "statuses": statuses,
                        "calls": [first.calls, second.calls],
                        "state_count": len(env.steps),
                        "stdout_bytes": len(stdout.getvalue().encode("utf-8")),
                        "stderr_bytes": len(err.encode("utf-8")),
                    }
                )
    passed = bool(
        len(rows) == 6
        and all(row["statuses"] == ["DONE", "DONE"] for row in rows)
        and all(row["calls"] == [719, 719] for row in rows)
        and all(row["state_count"] == 720 for row in rows)
        and all(row["stderr_bytes"] == 0 for row in rows)
    )
    payload = {
        "schema": SCHEMA,
        "passed": passed,
        "archive_sha256": closure["archive_sha256"],
        "serving_sha256": closure["members"][0]["sha256"],
        "serving_fingerprint": closure["serving_fingerprint"],
        "seeds_sha256": hashlib.sha256(
            json.dumps(EXPOSED_QA_SEEDS, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "games": len(rows),
        "all_done": all(row["statuses"] == ["DONE", "DONE"] for row in rows),
        "all_calls_719": all(row["calls"] == [719, 719] for row in rows),
        "all_states_720": all(row["state_count"] == 720 for row in rows),
        "stderr_bytes": sum(row["stderr_bytes"] for row in rows),
        "stdout_bytes": sum(row["stdout_bytes"] for row in rows),
        "test_sources_accessed": False,
    }
    if not passed:
        raise RuntimeError("candidate raw-loader QA failed")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = run_qa(args.archive)
    atomic_create_json_strict(args.output.resolve(), payload)
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
