"""Fresh-seed dual-seat evaluation of fixed V114 event-program decisions."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import tempfile
import time
from typing import Any, Callable, Iterable, Mapping, Sequence

from event_program import MacroDecision
from policy_event_program import FixedEventProgramPolicy, decision_as_dict
from seed_ledger import SeedLedger


HERE = Path(__file__).resolve().parent
EVENT_PROGRAM_PATH = HERE / "event_program.py"
CATASTROPHE_REWARD = 3000.0
EXPECTED_ACTION_STEPS = 719


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def percentile_10(values: Iterable[float]) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = max(0, min(len(ordered) - 1, int(0.1 * (len(ordered) - 1))))
    return ordered[index]


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def _load_agent(path: Path, name: str) -> Callable[..., Any]:
    path = path.resolve()
    if not path.is_file():
        raise ValueError(f"opponent agent does not exist: {path}")
    agent_dir = path.parent
    sibling_names = {candidate.stem for candidate in agent_dir.glob("*.py")}
    for module_name, loaded_module in list(sys.modules.items()):
        if module_name.split(".", 1)[0] in sibling_names:
            del sys.modules[module_name]
            continue
        module_file = getattr(loaded_module, "__file__", None)
        if module_file is None:
            continue
        try:
            if Path(module_file).resolve().is_relative_to(agent_dir):
                del sys.modules[module_name]
        except (OSError, RuntimeError, ValueError):
            continue
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot load opponent agent: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(agent_dir))
    try:
        spec.loader.exec_module(module)
    finally:
        try:
            sys.path.remove(str(agent_dir))
        except ValueError:
            pass
    agent = getattr(module, "agent", None)
    if not callable(agent):
        raise ValueError(f"opponent module has no callable agent: {path}")
    return agent


def resolve_opponent(value: str, name: str) -> Callable[..., Any]:
    if value.startswith("registry:"):
        from evaluate_league import build_registered_opponent
        from opponent_registry import load_registry

        member_id = value.split(":", 1)[1]
        registry = load_registry(HERE / "opponent_registry.json", verify_artifacts=True)
        return build_registered_opponent(registry, member_id, name)
    if value.startswith("builtin:"):
        from kaggle_environments.envs.kaggriculture import kaggriculture

        builtins = {
            "pass": kaggriculture.pass_agent,
            "random": kaggriculture.random_agent,
            "starter": kaggriculture.starter_agent,
        }
        key = value.split(":", 1)[1]
        if key not in builtins:
            raise ValueError(f"unknown builtin opponent: {key}")
        return builtins[key]
    return _load_agent(Path(value), name)


def builtin_decisions() -> list[dict[str, Any]]:
    return [
        {
            "name": f"{crop.lower()}_w4_r500_immediate",
            "decision": {
                "production_line": crop,
                "worker_cap": 4,
                "cash_reserve": 500,
                "sell_style": "IMMEDIATE",
                "terminal_mode": "NORMAL",
            },
        }
        for crop in ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
    ]


def _read_json_spec(value: str) -> Any:
    stripped = value.lstrip()
    if stripped.startswith(("[", "{")):
        return json.loads(value)
    candidate = Path(value).expanduser()
    if candidate.is_file():
        return json.loads(candidate.read_text(encoding="utf-8"))
    return json.loads(value)


def parse_decision_specs(value: str | None) -> list[dict[str, Any]]:
    raw = builtin_decisions() if value is None else _read_json_spec(value)
    if isinstance(raw, Mapping):
        if "decisions" in raw:
            raw = raw["decisions"]
        else:
            raw = [dict(spec, name=name) for name, spec in raw.items()]
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or not raw:
        raise ValueError("decision spec JSON must contain a non-empty list or object")

    result: list[dict[str, Any]] = []
    names: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ValueError(f"decision spec {index} must be an object")
        name = str(item.get("name", "")).strip()
        if not name or name in names:
            raise ValueError("every decision requires a unique non-empty name")
        payload = item.get("decision", item)
        if not isinstance(payload, Mapping):
            raise ValueError(f"decision {name!r} payload must be an object")
        fields = {
            key: payload[key]
            for key in (
                "production_line",
                "worker_cap",
                "cash_reserve",
                "sell_style",
                "terminal_mode",
            )
            if key in payload
        }
        missing = {
            "production_line", "worker_cap", "cash_reserve", "sell_style"
        } - fields.keys()
        if missing:
            raise ValueError(f"decision {name!r} missing fields: {sorted(missing)}")
        fields.setdefault("terminal_mode", "NORMAL")
        parsed = MacroDecision(**fields)
        result.append({"name": name, "decision": decision_as_dict(parsed)})
        names.add(name)
    return result


def opponent_artifact(opponent_id: str) -> dict[str, Any]:
    if opponent_id.startswith("registry:"):
        from opponent_registry import load_registry

        member_id = opponent_id.split(":", 1)[1]
        registry = load_registry(HERE / "opponent_registry.json", verify_artifacts=True)
        try:
            member = next(row for row in registry["members"] if row["id"] == member_id)
        except StopIteration as exc:
            raise ValueError(f"unknown registry opponent: {member_id}") from exc
        return {
            "id": member_id,
            "kind": f"registry_{member['kind']}",
            "path": member.get("resolved_path"),
            "sha256": member["sha256"],
            "architecture": member.get("architecture"),
            "training_layer": member.get("training_layer"),
            "lineage": member["lineage"],
            "behavior_family": member["behavior_family"],
            "registry_sha256": registry["registry_sha256"],
        }
    if opponent_id.startswith("builtin:"):
        try:
            import kaggle_environments

            version = getattr(kaggle_environments, "__version__", "unknown")
        except Exception:
            version = "unavailable"
        return {"id": opponent_id, "kind": "builtin", "version": version}
    path = Path(opponent_id).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"opponent agent does not exist: {path}")
    return {
        "id": opponent_id,
        "kind": "python_agent",
        "path": str(path),
        "sha256": file_sha256(path),
    }


def default_registry_sha256(
    opponent: Mapping[str, Any], event_program_sha256: str
) -> str:
    payload = {
        "opponent": dict(opponent),
        "event_program_sha256": event_program_sha256,
        "seat_contract": [0, 1],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def evaluate_decision_seed(
    decision_spec: Mapping[str, Any], seed: int, opponent_id: str
) -> list[dict[str, Any]]:
    """Run one named decision in both seats of one seed block."""

    from kaggle_environments import make

    name = str(decision_spec["name"])
    decision = dict(decision_spec["decision"])
    rows: list[dict[str, Any]] = []
    for seat in (0, 1):
        candidate = FixedEventProgramPolicy(decision, name=name)
        opponent = resolve_opponent(
            opponent_id, f"v114_event_program_{name}_{seed}_{seat}"
        )
        agents: list[Any] = [None, None]
        agents[seat], agents[1 - seat] = candidate, opponent
        env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
        error = None
        try:
            env.run(agents)
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        rewards = [float(state.reward or 0.0) for state in env.state]
        statuses = [str(state.status) for state in env.state]
        margin = rewards[seat] - rewards[1 - seat]
        rows.append({
            "decision_name": name,
            "decision": dict(decision),
            "seed": int(seed),
            "seat": int(seat),
            "opponent_id": opponent_id,
            "candidate_reward": rewards[seat],
            "opponent_reward": rewards[1 - seat],
            "margin": margin,
            "score": score(margin),
            "catastrophe": rewards[seat] < CATASTROPHE_REWARD,
            "error": error,
            "statuses": statuses,
            "action_steps": int(candidate.action_steps),
            "expected_action_steps": EXPECTED_ACTION_STEPS,
            "environment_states": len(env.steps),
            "contract_violations": int(candidate.contract_violation_count),
            "manager_decision_count": int(candidate.manager_decision_count),
            "terminal_procurement_count": int(candidate.terminal_procurement_count),
        })
    return rows


def failure_rows(
    decision_spec: Mapping[str, Any], seed: int, opponent_id: str, error: str
) -> list[dict[str, Any]]:
    return [
        {
            "decision_name": str(decision_spec["name"]),
            "decision": dict(decision_spec["decision"]),
            "seed": int(seed),
            "seat": seat,
            "opponent_id": opponent_id,
            "candidate_reward": 0.0,
            "opponent_reward": 0.0,
            "margin": 0.0,
            "score": 0.0,
            "catastrophe": True,
            "error": error,
            "statuses": ["ERROR", "ERROR"],
            "action_steps": 0,
            "expected_action_steps": EXPECTED_ACTION_STEPS,
            "environment_states": 0,
            "contract_violations": 0,
            "manager_decision_count": 0,
            "terminal_procurement_count": 0,
        }
        for seat in (0, 1)
    ]


def valid_row(row: Mapping[str, Any]) -> bool:
    return bool(
        row.get("error") is None
        and row.get("statuses") == ["DONE", "DONE"]
        and int(row.get("action_steps", -1)) == EXPECTED_ACTION_STEPS
        and int(row.get("contract_violations", -1)) == 0
        and int(row.get("terminal_procurement_count", -1)) == 0
    )


def summarize_decision(rows: list[dict[str, Any]], decision_name: str) -> dict[str, Any]:
    selected = [row for row in rows if row["decision_name"] == decision_name]
    valid = [row for row in selected if valid_row(row)]
    wins = sum(row["score"] == 1.0 for row in valid)
    draws = sum(row["score"] == 0.5 for row in valid)
    losses = sum(row["score"] == 0.0 for row in valid)
    catastrophes = sum(bool(row["catastrophe"]) for row in valid)
    return {
        "decision_name": decision_name,
        "decision": dict(selected[0]["decision"]) if selected else {},
        "games": len(selected),
        "valid_games": len(valid),
        "wdl": {"wins": wins, "draws": draws, "losses": losses},
        "score_rate": statistics.mean(row["score"] for row in valid) if valid else 0.0,
        "mean_candidate_reward": (
            statistics.mean(row["candidate_reward"] for row in valid) if valid else 0.0
        ),
        "p10_candidate_reward": percentile_10(
            row["candidate_reward"] for row in valid
        ),
        "mean_opponent_reward": (
            statistics.mean(row["opponent_reward"] for row in valid) if valid else 0.0
        ),
        "mean_margin": statistics.mean(row["margin"] for row in valid) if valid else 0.0,
        "catastrophe_games": catastrophes,
        "catastrophe_rate": catastrophes / len(valid) if valid else 0.0,
        "errors": sum(row.get("error") is not None for row in selected),
        "incomplete_games": sum(not valid_row(row) for row in selected),
        "contract_violations": sum(
            int(row.get("contract_violations", 0)) for row in selected
        ),
        "terminal_procurement_count": sum(
            int(row.get("terminal_procurement_count", 0)) for row in selected
        ),
        "mean_manager_decision_count": (
            statistics.mean(row["manager_decision_count"] for row in valid)
            if valid else 0.0
        ),
    }


def atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as sink:
        json.dump(payload, sink, ensure_ascii=False, indent=2, sort_keys=True)
        sink.write("\n")
        temporary = Path(sink.name)
    os.replace(temporary, path)


def _validate_args(args: argparse.Namespace) -> None:
    if int(args.seeds) <= 0:
        raise ValueError("seeds must be positive")
    if int(args.workers) <= 0:
        raise ValueError("workers must be positive")
    if int(args.seed_start) < 0:
        raise ValueError("seed_start must be non-negative")
    if not str(args.campaign).strip():
        raise ValueError("campaign is required")


def run_campaign(
    args: argparse.Namespace,
    *,
    worker_fn: Callable[..., list[dict[str, Any]]] = evaluate_decision_seed,
    executor_cls: type = ProcessPoolExecutor,
    ledger_cls: type = SeedLedger,
) -> dict[str, Any]:
    """Reserve once, execute all decisions, expose once and atomically report."""

    _validate_args(args)
    specs = getattr(args, "decision_specs", None)
    if specs is None:
        specs = parse_decision_specs(getattr(args, "decision_spec_json", None))
    else:
        specs = parse_decision_specs(json.dumps(specs))
    seeds = list(range(int(args.seed_start), int(args.seed_start) + int(args.seeds)))
    opponent = opponent_artifact(str(args.opponent))
    event_sha_before = file_sha256(EVENT_PROGRAM_PATH)
    registry_sha256 = getattr(args, "registry_sha256", None) or default_registry_sha256(
        opponent, event_sha_before
    )
    ledger = ledger_cls(Path(args.ledger))
    schedule = [{"seed": seed, "opponent_id": str(args.opponent)} for seed in seeds]
    ledger.reserve_schedule(
        schedule,
        split=str(args.split),
        campaign_id=str(args.campaign),
        registry_sha256=registry_sha256,
    )
    ledger_sha_reserved = ledger.sha256()

    started = time.time()
    rows: list[dict[str, Any]] = []
    worker_failures: list[dict[str, Any]] = []
    exposure_error: str | None = None
    try:
        jobs = [(spec, seed) for spec in specs for seed in seeds]
        with executor_cls(max_workers=min(int(args.workers), len(jobs))) as pool:
            futures = {
                pool.submit(worker_fn, spec, seed, str(args.opponent)): (spec, seed)
                for spec, seed in jobs
            }
            for future in as_completed(futures):
                spec, seed = futures[future]
                try:
                    result = future.result()
                    if len(result) != 2 or sorted(row.get("seat") for row in result) != [0, 1]:
                        raise ValueError("worker must return exactly seat 0 and seat 1")
                    rows.extend(result)
                except Exception as exc:
                    error = f"{type(exc).__name__}: {exc}"
                    worker_failures.append({
                        "decision_name": spec["name"], "seed": seed, "error": error
                    })
                    rows.extend(failure_rows(spec, seed, str(args.opponent), error))
    finally:
        try:
            ledger.mark_schedule_exposed(schedule)
        except Exception as exc:
            exposure_error = f"{type(exc).__name__}: {exc}"

    ledger_sha_exposed = ledger.sha256()
    event_sha_after = file_sha256(EVENT_PROGRAM_PATH)
    summaries = [summarize_decision(rows, spec["name"]) for spec in specs]
    summaries.sort(key=lambda row: (
        row["incomplete_games"],
        row["contract_violations"],
        row["catastrophe_games"],
        -row["score_rate"],
        -row["p10_candidate_reward"],
        -row["mean_candidate_reward"],
    ))
    expected_rows = len(specs) * len(seeds) * 2
    validation_errors: list[str] = []
    if len(rows) != expected_rows:
        validation_errors.append(f"row count mismatch: {len(rows)} != {expected_rows}")
    if event_sha_after != event_sha_before:
        validation_errors.append("event_program.py SHA256 changed during evaluation")
    if exposure_error is not None:
        validation_errors.append("seed ledger exposure failed")
    if any(not valid_row(row) for row in rows):
        validation_errors.append("one or more games failed execution contract")

    report = {
        "schema": "kaggriculture-v114-fixed-event-program-evaluation-v1",
        "status": "VALID" if not validation_errors else "INVALID",
        "checkpoint": {"applicable": False, "reason": "checkpoint-free fixed event program"},
        "event_program": {
            "path": str(EVENT_PROGRAM_PATH),
            "sha256_before": event_sha_before,
            "sha256_after": event_sha_after,
            "unchanged": event_sha_before == event_sha_after,
        },
        "campaign": str(args.campaign),
        "split": str(args.split),
        "decision_specs": specs,
        "seed_start": int(args.seed_start),
        "seed_blocks": len(seeds),
        "seats_per_seed": [0, 1],
        "fresh_seed_dual_seat": True,
        "opponent": opponent,
        "registry_sha256": registry_sha256,
        "seed_ledger": {
            "path": str(args.ledger),
            "reserve_schedule_calls_expected": 1,
            "sha256_after_reservation": ledger_sha_reserved,
            "sha256_after_exposure": ledger_sha_exposed,
            "reserved_seed_blocks": seeds,
            "exposure_error": exposure_error,
        },
        "metric_contract": {
            "win": "candidate_reward > opponent_reward",
            "draw": "candidate_reward == opponent_reward",
            "loss": "candidate_reward < opponent_reward",
            "catastrophe": f"candidate_reward < {CATASTROPHE_REWARD:g}",
            "p10": "empirical lower P10 of valid candidate rewards",
            "complete_episode": f"exactly {EXPECTED_ACTION_STEPS} candidate action steps",
            "terminal_procurement": "must be zero from step 671 onward",
        },
        "elapsed_seconds": time.time() - started,
        "expected_rows": expected_rows,
        "validation_errors": validation_errors,
        "worker_failures": worker_failures,
        "summaries": summaries,
        "best": summaries[0] if summaries else None,
        "rows": sorted(
            rows, key=lambda row: (row["decision_name"], row["seed"], row["seat"])
        ),
    }
    atomic_json(Path(args.output), report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--decision-spec-json",
        help=(
            "inline JSON or JSON file; omit to evaluate five crop decisions with "
            "worker_cap=4, cash_reserve=500 and IMMEDIATE selling"
        ),
    )
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--seeds", type=int, required=True)
    parser.add_argument("--opponent", default="builtin:starter")
    parser.add_argument("--campaign", required=True)
    parser.add_argument("--split", choices=("train", "dev", "blind"), default="train")
    parser.add_argument("--registry-sha256")
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=max(1, os.cpu_count() or 1))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        report = run_campaign(args)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps({
        "status": report["status"],
        "best": report["best"],
        "summaries": report["summaries"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
