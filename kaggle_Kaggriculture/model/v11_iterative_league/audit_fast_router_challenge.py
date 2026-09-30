#!/usr/bin/env python3
"""对正式 FastRouter 等价证据做独立、只读的 fresh challenge。

正式报告的原始 JSONL 与语义哈希用于防止混跑和封存后篡改，但它们不
构成受信执行环境的密码学证明。本审计器从报告文件 SHA-256 确定性抽取
4 个 validation source，重新执行 2 Router x 4 opponent x 双席位，共
64 组 original-vs-fast 比较（128 局环境），并逐字段对照已封存行。

它不读取 test split，不修改正式报告/JSONL/registry，也不替代 1,600 组
正式门禁；只提供额外的真实性 challenge。
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from . import verify_fast_router as formal
except ImportError:  # direct-file CLI compatibility
    import verify_fast_router as formal


SCHEMA = "kaggriculture-v11-fast-router-fresh-challenge-1"
DEFAULT_SOURCE_COUNT = 4


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def implementation_fingerprint() -> str:
    digest = hashlib.sha256()
    digest.update(Path(__file__).resolve().read_bytes())
    digest.update(formal.implementation_fingerprint().encode("ascii"))
    return digest.hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def challenge_source_indices(
    report_file_sha256: str,
    source_total: int,
    count: int = DEFAULT_SOURCE_COUNT,
) -> list[int]:
    """Derive a stable, unique source sample from the sealed report bytes."""

    if len(str(report_file_sha256)) != 64 or any(
        character not in "0123456789abcdef" for character in report_file_sha256
    ):
        raise ValueError("challenge requires a lowercase 64-hex report SHA-256")
    if int(source_total) <= 0 or not 2 <= int(count) <= 4 or int(count) > int(
        source_total
    ):
        raise ValueError("challenge source count must be 2-4 and fit the source pool")
    result: list[int] = []
    nonce = 0
    while len(result) < int(count):
        digest = hashlib.sha256(
            f"{report_file_sha256}:fresh-challenge:{nonce}".encode("ascii")
        ).digest()
        index = int.from_bytes(digest[:8], "big") % int(source_total)
        if index not in result:
            result.append(index)
        nonce += 1
    return sorted(result)


def _semantic_sha256(row: Mapping[str, Any]) -> str:
    semantic = {
        key: value
        for key, value in row.items()
        if key not in {"elapsed_seconds", "semantic_sha256"}
    }
    return formal._canonical_sha256(semantic)


def run_challenge(
    report_path: Path,
    *,
    workers: int = 1,
    source_count: int = DEFAULT_SOURCE_COUNT,
) -> dict[str, Any]:
    """Freshly rerun the SHA-derived validation sample and compare raw rows."""

    report_path = report_path.expanduser().resolve()
    # First require the complete formal report/JSONL gate. This is read-only.
    formal_seal = formal.validate_formal_report(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("environment_split") != formal.FORMAL_SPLIT:
        raise ValueError("fresh challenge may use validation only")
    sources = [dict(item) for item in (report.get("sources") or [])]
    report_sha = _sha256(report_path)
    source_indices = challenge_source_indices(
        report_sha, len(sources), int(source_count)
    )
    selected_sources = [sources[index] for index in source_indices]
    if any(str(item.get("split")) != formal.FORMAL_SPLIT for item in selected_sources):
        raise ValueError("fresh challenge selected a non-validation source")

    registry_path = Path(str(report["source_final_registry"])).expanduser().resolve()
    games_path = Path(str(report["games_jsonl"])).expanduser().resolve()
    run_fingerprint = str(report["run_fingerprint"])
    all_tasks = formal.build_tasks(registry_path, run_fingerprint, sources)
    all_expected = {str(task["task_id"]): task for task in all_tasks}
    stored_successes, _ = formal._read_existing(
        games_path, run_fingerprint, all_expected
    )
    challenge_tasks = formal.build_tasks(
        registry_path, run_fingerprint, selected_sources
    )
    expected_comparisons = (
        len(formal.ROUTERS)
        * len(formal.OPPONENTS)
        * len(selected_sources)
        * 2
    )
    if len(challenge_tasks) != expected_comparisons:
        raise AssertionError("fresh challenge schedule is not exact")

    fresh_rows: dict[str, dict[str, Any]] = {}
    workers = max(1, int(workers))
    if workers == 1:
        for task in challenge_tasks:
            row = formal._one_comparison(task)
            fresh_rows[str(task["task_id"])] = row
    else:
        with ProcessPoolExecutor(
            max_workers=min(workers, len(challenge_tasks))
        ) as executor:
            future_map = {
                executor.submit(formal._one_comparison, task): str(task["task_id"])
                for task in challenge_tasks
            }
            for future in as_completed(future_map):
                fresh_rows[future_map[future]] = future.result()

    comparisons = []
    matched = 0
    for task in challenge_tasks:
        task_id = str(task["task_id"])
        stored = stored_successes.get(task_id)
        fresh = fresh_rows.get(task_id)
        error = None
        if stored is None:
            error = "stored_success_missing"
        elif fresh is None:
            error = "fresh_result_missing"
        else:
            try:
                formal._validate_success(fresh)
            except ValueError as exc:
                error = f"fresh_validation_failed:{exc}"
        stored_sha = _semantic_sha256(stored) if stored is not None else None
        fresh_sha = _semantic_sha256(fresh) if fresh is not None else None
        exact = error is None and stored_sha == fresh_sha
        matched += int(exact)
        comparisons.append(
            {
                "task_id": task_id,
                "router_id": task["router_id"],
                "opponent_id": task["opponent_id"],
                "source": dict(task["source"]),
                "router_seat": int(task["router_seat"]),
                "stored_semantic_sha256": stored_sha,
                "fresh_semantic_sha256": fresh_sha,
                "exact": exact,
                "error": error,
                # Keep the complete fresh evidence so materializer and league
                # init can independently recompute health and semantic hashes.
                "fresh": fresh,
            }
        )

    passed = matched == expected_comparisons
    return {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read_only_input_audit": True,
        "formal_gate_revalidated": True,
        "test_sources_accessed": False,
        "environment_split": formal.FORMAL_SPLIT,
        "report": str(report_path),
        "report_file_sha256": report_sha,
        "games_jsonl": str(games_path),
        "games_jsonl_file_sha256": _sha256(games_path),
        "formal_run_fingerprint": run_fingerprint,
        "challenge_implementation_sha256": implementation_fingerprint(),
        "formal_seal": formal_seal,
        "selection_derivation": "sha256(report bytes + fixed domain + nonce)",
        "source_indices": source_indices,
        "sources": selected_sources,
        "source_count": len(selected_sources),
        "routers": list(formal.ROUTERS),
        "opponents": list(formal.OPPONENTS),
        "seats": [0, 1],
        "expected_comparisons": expected_comparisons,
        "fresh_comparisons": len(fresh_rows),
        "environment_games": expected_comparisons * 2,
        "exact_matches": matched,
        "mismatches": expected_comparisons - matched,
        "passed": passed,
        "comparisons": comparisons,
    }


def validate_challenge_report(
    challenge_path: Path,
    formal_report_path: Path | None = None,
    source_registry_path: Path | None = None,
) -> dict[str, Any]:
    """Strictly re-open a 4-source/64-comparison fresh challenge artifact."""

    challenge_path = challenge_path.expanduser().resolve()
    if not challenge_path.is_file():
        raise FileNotFoundError(f"fresh challenge report missing: {challenge_path}")
    payload = json.loads(challenge_path.read_text(encoding="utf-8"))
    if payload.get("schema") != SCHEMA:
        raise ValueError("unexpected FastRouter fresh challenge schema")
    if (
        payload.get("read_only_input_audit") is not True
        or payload.get("formal_gate_revalidated") is not True
        or payload.get("test_sources_accessed") is not False
        or payload.get("environment_split") != formal.FORMAL_SPLIT
        or payload.get("passed") is not True
        or int(payload.get("source_count", -1)) != DEFAULT_SOURCE_COUNT
        or int(payload.get("expected_comparisons", -1)) != 64
        or int(payload.get("fresh_comparisons", -1)) != 64
        or int(payload.get("environment_games", -1)) != 128
        or int(payload.get("exact_matches", -1)) != 64
        or int(payload.get("mismatches", -1)) != 0
        or payload.get("routers") != list(formal.ROUTERS)
        or payload.get("opponents") != list(formal.OPPONENTS)
        or payload.get("seats") != [0, 1]
    ):
        raise ValueError("fresh challenge is not an exact passing 4x2x4x2 audit")
    if payload.get("challenge_implementation_sha256") != implementation_fingerprint():
        raise ValueError("fresh challenge implementation changed after execution")

    report_value = Path(str(payload.get("report") or "")).expanduser()
    games_value = Path(str(payload.get("games_jsonl") or "")).expanduser()
    if not report_value.is_absolute() or not games_value.is_absolute():
        raise ValueError("fresh challenge provenance paths must be absolute")
    report_path = report_value.resolve()
    games_path = games_value.resolve()
    if formal_report_path is not None and report_path != formal_report_path.expanduser().resolve():
        raise ValueError("fresh challenge belongs to a different formal report")
    if not report_path.is_file() or payload.get("report_file_sha256") != _sha256(report_path):
        raise ValueError("fresh challenge formal report file/hash mismatch")
    if not games_path.is_file() or payload.get("games_jsonl_file_sha256") != _sha256(games_path):
        raise ValueError("fresh challenge formal JSONL file/hash mismatch")
    formal_seal = formal.validate_formal_report(report_path, source_registry_path)
    if payload.get("formal_seal") != formal_seal:
        raise ValueError("fresh challenge embedded formal seal differs from current evidence")

    report = json.loads(report_path.read_text(encoding="utf-8"))
    sources = [dict(item) for item in (report.get("sources") or [])]
    source_indices = challenge_source_indices(_sha256(report_path), len(sources), 4)
    selected_sources = [sources[index] for index in source_indices]
    if payload.get("source_indices") != source_indices or payload.get("sources") != selected_sources:
        raise ValueError("fresh challenge source sample is not report-SHA-derived")
    if any(str(item.get("split")) != formal.FORMAL_SPLIT for item in selected_sources):
        raise ValueError("fresh challenge contains a non-validation source")
    fit_sources, _ = formal._source_rows(
        Path(str(report["fit_exclusions"])), formal.FORMAL_SPLIT
    )
    fit_keys = {
        (str(item["date"]), str(item["episode_id"]), int(item["seed"]))
        for item in fit_sources
    }
    if any(
        (str(item["date"]), str(item["episode_id"]), int(item["seed"]))
        not in fit_keys
        for item in selected_sources
    ):
        raise ValueError("fresh challenge source is outside Router-fit exclusions")

    registry_path = Path(str(report["source_final_registry"])).expanduser().resolve()
    run_fingerprint = str(report["run_fingerprint"])
    all_tasks = formal.build_tasks(registry_path, run_fingerprint, sources)
    all_expected = {str(task["task_id"]): task for task in all_tasks}
    stored_successes, _ = formal._read_existing(
        games_path, run_fingerprint, all_expected
    )
    challenge_tasks = formal.build_tasks(
        registry_path, run_fingerprint, selected_sources
    )
    expected = {str(task["task_id"]): task for task in challenge_tasks}
    comparisons = payload.get("comparisons") or []
    if len(comparisons) != 64 or len(
        {str(item.get("task_id") or "") for item in comparisons}
    ) != 64:
        raise ValueError("fresh challenge comparison rows are incomplete/duplicated")
    by_task = {str(item["task_id"]): item for item in comparisons}
    if set(by_task) != set(expected):
        raise ValueError("fresh challenge task IDs differ from the derived schedule")
    for task_id, task in expected.items():
        comparison = by_task[task_id]
        for key in ("router_id", "opponent_id", "source", "router_seat"):
            if comparison.get(key) != task.get(key):
                raise ValueError(f"fresh challenge task semantic mismatch: {task_id}/{key}")
        if comparison.get("exact") is not True or comparison.get("error") is not None:
            raise ValueError(f"fresh challenge contains failed comparison: {task_id}")
        stored = stored_successes.get(task_id)
        fresh = comparison.get("fresh")
        if stored is None or not isinstance(fresh, Mapping):
            raise ValueError(f"fresh challenge lacks raw evidence: {task_id}")
        for key in (
            "schema",
            "task_id",
            "run_fingerprint",
            "router_id",
            "opponent_id",
            "source",
            "router_seat",
        ):
            if fresh.get(key) != stored.get(key):
                raise ValueError(f"fresh/stored task semantic mismatch: {task_id}/{key}")
        formal._validate_success(fresh)
        claimed_semantic = str(fresh.get("semantic_sha256") or "")
        fresh_semantic = _semantic_sha256(fresh)
        stored_semantic = _semantic_sha256(stored)
        if (
            claimed_semantic != fresh_semantic
            or comparison.get("fresh_semantic_sha256") != fresh_semantic
            or comparison.get("stored_semantic_sha256") != stored_semantic
            or fresh_semantic != stored_semantic
        ):
            raise ValueError(f"fresh challenge semantic mismatch: {task_id}")

    return {
        "schema": SCHEMA,
        "report": str(challenge_path),
        "report_file_sha256": _sha256(challenge_path),
        "challenge_implementation_sha256": implementation_fingerprint(),
        "formal_report": str(report_path),
        "formal_report_file_sha256": _sha256(report_path),
        "formal_games_jsonl": str(games_path),
        "formal_games_jsonl_file_sha256": _sha256(games_path),
        "formal_run_fingerprint": run_fingerprint,
        "selection_derivation": payload.get("selection_derivation"),
        "source_indices": source_indices,
        "sources_sha256": formal._canonical_sha256(selected_sources),
        "source_count": 4,
        "routers": list(formal.ROUTERS),
        "opponents": list(formal.OPPONENTS),
        "seats": [0, 1],
        "comparisons": 64,
        "environment_games": 128,
        "exact_matches": 64,
        "runtime_errors": 0,
        "test_sources_accessed": False,
        "all_validation_sources_in_router_fit_exclusions": True,
        "passed": True,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=max(1, min(8, os.cpu_count() or 1)))
    parser.add_argument("--sources", type=int, choices=(2, 3, 4), default=DEFAULT_SOURCE_COUNT)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_challenge(
        args.report,
        workers=args.workers,
        source_count=args.sources,
    )
    if args.output is not None:
        _atomic_json(args.output.expanduser().resolve(), result)
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "sources": result["source_count"],
                "comparisons": result["expected_comparisons"],
                "environment_games": result["environment_games"],
                "mismatches": result["mismatches"],
                "output": str(args.output.expanduser().resolve())
                if args.output is not None
                else None,
            },
            ensure_ascii=False,
        )
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
