#!/usr/bin/env python3
"""Seal the goal-achieved V11 16-model pool before any final-test game.

The output must live beside the source pool registry so model specifications
remain byte-for-byte identical; this avoids turning path rebasing into an
unreviewed serving change.  Only metadata and serving files are read.  No
environment or test outcome is opened.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

try:
    from .league import (
        TARGET_BASELINES,
        _atomic_json,
        load_state,
        model_fingerprints,
    )
except ImportError:  # direct-file CLI compatibility
    from league import TARGET_BASELINES, _atomic_json, load_state, model_fingerprints

from kaggle_Kaggriculture.model.v10_replay_lolo_router.agent_factory import (
    load_registry,
    registry_fingerprint,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router.pairwise_evaluate import (
    implementation_fingerprint,
)
from kaggle_Kaggriculture.model.v10_replay_lolo_router.report_frozen_test import (
    _validate_registry_seals,
)


SCHEMA = "kaggriculture-v11-terminal-pool-registry-1"
MODEL_COUNT = 16
PAIR_COUNT = 120
GAMES_PER_PAIR = 200
EXPECTED_GAMES = 24_000


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_terminal_state(
    state: Mapping[str, Any], source_registry: Any
) -> tuple[list[str], dict[str, str]]:
    """Validate terminal semantics and every serving fingerprint."""

    models = [str(item) for item in (state.get("active_models") or [])]
    goal = state.get("goal") or {}
    if (
        state.get("status") != "goal_achieved"
        or goal.get("achieved") is not True
        or goal.get("achieved_after_round") is None
    ):
        raise ValueError("league has not reached a frozen terminal state")
    if len(models) != MODEL_COUNT or len(set(models)) != MODEL_COUNT:
        raise ValueError("terminal league pool must contain exactly 16 unique models")
    required_absent = set(str(item) for item in TARGET_BASELINES)
    if set(goal.get("required_absent_models") or []) != required_absent:
        raise ValueError("terminal absent-baseline goal changed")
    if set(models) & required_absent:
        raise ValueError("terminal pool still contains an original baseline")
    if int(goal.get("required_pool_size") or -1) != MODEL_COUNT:
        raise ValueError("terminal pool-size goal changed")
    if state.get("pending_candidate") or state.get("candidate_required"):
        raise ValueError("terminal pool still has a pending candidate")
    if registry_fingerprint(source_registry) != state.get(
        "registry_and_code_sha256"
    ):
        raise ValueError("source pool registry/code changed after terminal state")
    for model_id in models:
        source_registry.require(model_id)
    actual = model_fingerprints(source_registry, models)
    expected = {
        model_id: str(
            (state.get("model_entries") or {})
            .get(model_id, {})
            .get("serving_sha256")
            or ""
        )
        for model_id in models
    }
    if actual != expected:
        changed = sorted(
            model_id for model_id in models if actual.get(model_id) != expected.get(model_id)
        )
        raise ValueError(f"terminal serving fingerprints changed: {changed}")
    return models, actual


def seal_registry(
    state_path: Path,
    output_path: Path | None = None,
) -> dict[str, Any]:
    state_path = state_path.expanduser().resolve()
    state = load_state(state_path)
    source_path = Path(str(state.get("registry") or "")).expanduser()
    if not source_path.is_absolute():
        source_path = (state_path.parent / source_path).resolve()
    source = load_registry(source_path)
    models, fingerprints = validate_terminal_state(state, source)
    # All V10 metadata/test seals must survive candidate admission unchanged.
    source_seals = _validate_registry_seals(source)

    output_path = (
        output_path.expanduser().resolve()
        if output_path is not None
        else source.path.with_name("terminal_pool_registry.json")
    )
    if output_path.parent != source.path.parent:
        raise ValueError(
            "terminal registry must be written beside source pool registry; "
            "cross-directory path rebasing is not an approved serving change"
        )
    test_protocol = deepcopy(source.raw.get("test_protocol") or {})
    test_protocol.update(
        {
            "sealed_before_test": True,
            "model_ids": models,
            "panel_sources": 100,
            "games_per_pair": GAMES_PER_PAIR,
            "unordered_pairs": PAIR_COUNT,
            "expected_games": EXPECTED_GAMES,
        }
    )
    preserved = {
        key: deepcopy(value)
        for key, value in source.raw.items()
        if key not in {
            "schema",
            "created_at",
            "models",
            "agents",
            "test_protocol",
            "sealed_before_test",
            "sealed_before_final_test",
            "league_terminal_state",
            "evaluation_implementation_sha256",
        }
    }
    payload = {
        **preserved,
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sealed_before_test": True,
        "sealed_before_final_test": True,
        "test_used_for_fit": False,
        "pre_selection_test_access": False,
        "evaluation_implementation_sha256": implementation_fingerprint(),
        "league_terminal_state": {
            "schema": str(state.get("schema") or ""),
            "path": str(state_path),
            "file_sha256": _sha256(state_path),
            "state_sha256": state.get("state_sha256"),
            "achieved_after_round": (state.get("goal") or {}).get(
                "achieved_after_round"
            ),
            "active_models": models,
            "required_absent_models": list(TARGET_BASELINES),
            "source_pool_registry": str(source.path),
            "source_pool_registry_file_sha256": _sha256(source.path),
            "source_pool_registry_and_code_sha256": registry_fingerprint(source),
            "serving_fingerprints": fingerprints,
        },
        "pretest_metadata_seal_audit": source_seals,
        "test_protocol": test_protocol,
        "models": [deepcopy(source.require(model_id)) for model_id in models],
    }
    _atomic_json(output_path, payload)
    emitted = load_registry(output_path)
    if list(emitted.models) != models:
        raise AssertionError("terminal registry changed the active model order")
    if model_fingerprints(emitted, models) != fingerprints:
        raise AssertionError("terminal registry changed active serving fingerprints")
    return payload


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--league-state", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    payload = seal_registry(args.league_state, args.output)
    output = (
        args.output.expanduser().resolve()
        if args.output is not None
        else Path(payload["league_terminal_state"]["source_pool_registry"]).with_name(
            "terminal_pool_registry.json"
        )
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "schema": payload["schema"],
                "models": len(payload["models"]),
                "pairs": payload["test_protocol"]["unordered_pairs"],
                "expected_games": payload["test_protocol"]["expected_games"],
                "sealed_before_final_test": True,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
