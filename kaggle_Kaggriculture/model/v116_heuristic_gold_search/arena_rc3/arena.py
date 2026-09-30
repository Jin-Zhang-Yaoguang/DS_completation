#!/usr/bin/env python3
"""Read-only, evidence-preserving arena for V116 candidates.

The arena never registers or edits a candidate.  Runtime outputs are written
only to a new run directory selected by the caller.  ERROR and missing worker
results remain in the planned-game denominator.
"""

from __future__ import annotations

import argparse
import ast
import concurrent.futures
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import sys
from typing import Any, Iterable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
MODEL = HERE.parents[1]
PROJECT = MODEL.parent
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
ENGINE_VERSION = "1.32.7"

FULL_GOLD = {
    "v19": MODEL / "v19_hierarchical_moe/main.py",
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
    "v32": MODEL / "v32_clone_horizon_preempt/main.py",
    "v33": MODEL / "v33_demand_gap_horizon4/main.py",
    "v34": MODEL / "v34_demand_boundary_preempt/main.py",
    "v37": MODEL / "v37_preterminal_boundary_preempt/main.py",
    "v46": MODEL / "v46_full_terminal_front_run/main.py",
    "v51": MODEL / "v51_post_action_terminal_sell/main.py",
    "v52": MODEL / "v52_terminal_route_acceleration/main.py",
    "v53": MODEL / "v53_terminal_access_flush/main.py",
    "v54": MODEL / "v54_terminal_water_bypass/main.py",
    "v66": MODEL / "v66_margin_gated_sell_bubble/main.py",
    "v70": MODEL / "v70_duplicate_wheat_buy_lead/main.py",
    "v71": MODEL / "v71_duplicate_wheat_buy_lead_50/main.py",
    "v72": MODEL / "v72_duplicate_wheat_buy_lead_75/main.py",
    "v73": MODEL / "v73_duplicate_wheat_buy_full_merge/main.py",
    "v76": MODEL / "v76_adjacent_safe_buy_lead/main.py",
}
ANCHORS = {name: FULL_GOLD[name] for name in ("v20", "v21", "v32", "v54", "v66", "v76")}

PROFILE_DEFAULTS = {
    "smoke": {"seed_count": 2, "pool": "anchors"},
    "development": {"seed_count": 64, "pool": "full"},
    "confirmation": {"seed_count": 128, "pool": "full"},
}
SEED_SALTS = {
    "smoke": "v116-arena-rc3-anchor-smoke-20260830",
    "development": "v116-arena-rc3-development-20260830",
    "confirmation": "v116-arena-rc3-confirmation-20260830",
}

PRODUCTS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"}
CROPS = {"WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON"}
ANIMALS = {"GOOSE", "COW", "SHEEP"}
ITEMS = PRODUCTS | ANIMALS
UNIT_NO_ARG = {
    "NORTH", "SOUTH", "EAST", "WEST", "PASS", "DROP", "WATER", "HARVEST",
    "FERTILIZE", "BUILD_COOP", "BUILD_PASTURE", "DIG", "FEED",
    "COLLECT_FERTILIZER", "CARE",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def load_runtime() -> tuple[Any, Any, Any, Path]:
    builds = sorted((CPPSIM / "build").glob("lib.*/kagsim*.so"))
    if not builds:
        raise RuntimeError(f"missing compiled kagsim under {CPPSIM / 'build'}")
    sys.path[:0] = [str(FACTORY), str(builds[-1].parent)]
    try:
        import kagsim  # type: ignore
    except ModuleNotFoundError as exc:
        abi = builds[-1].name.split("cpython-")[-1].split("-")[0]
        raise RuntimeError(
            f"kagsim binary exists but is not importable by {sys.executable}; "
            f"use the matching CPython ABI ({abi})"
        ) from exc
    from agent_factory import Registry, create_agent  # type: ignore

    if str(getattr(kagsim, "ENGINE_VERSION", "")) != ENGINE_VERSION:
        raise RuntimeError(f"engine drift: expected {ENGINE_VERSION}, got {getattr(kagsim, 'ENGINE_VERSION', None)}")
    return kagsim, Registry, create_agent, builds[-1]


def deterministic_seeds(profile: str, count: int) -> list[int]:
    if count <= 0:
        raise ValueError("seed count must be positive")
    salt = SEED_SALTS[profile]
    values: list[int] = []
    seen: set[int] = set()
    index = 0
    while len(values) < count:
        digest = hashlib.sha256(f"{salt}:{index}".encode("ascii")).digest()
        value = int.from_bytes(digest[:8], "big") % 2_147_483_646 + 1
        if value not in seen:
            seen.add(value)
            values.append(value)
        index += 1
    return values


def read_seeds(path: Path) -> list[int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("seeds") if isinstance(payload, Mapping) else payload
    if not isinstance(raw, list) or not raw:
        raise ValueError("seeds file must be a non-empty JSON list or {'seeds': [...]} object")
    seeds = [int(value) for value in raw]
    if len(seeds) != len(set(seeds)):
        raise ValueError("seed manifest contains duplicates")
    if any(value <= 0 for value in seeds):
        raise ValueError("seeds must be positive integers")
    return seeds


def _literal_fixed_experts(candidate: Path) -> dict[str, Path]:
    """Discover an optional literal ARENA_FIXED_EXPERTS mapping without import."""
    tree = ast.parse(candidate.read_text(encoding="utf-8"), filename=str(candidate))
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            names: list[str] = []
            value = node.value
            if isinstance(node, ast.Assign):
                names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            elif isinstance(node.target, ast.Name):
                names = [node.target.id]
            if "ARENA_FIXED_EXPERTS" not in names or value is None:
                continue
            raw = ast.literal_eval(value)
            if not isinstance(raw, Mapping):
                raise ValueError("ARENA_FIXED_EXPERTS must be a literal {name: relative_main_path} mapping")
            return {str(name): (candidate.parent / str(path)).resolve() for name, path in raw.items()}
    return {}


def parse_named_path(value: str) -> tuple[str, Path]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("fixed expert must use NAME=/path/to/main.py")
    name, raw_path = value.split("=", 1)
    if not name.strip() or not raw_path.strip():
        raise argparse.ArgumentTypeError("fixed expert name and path must be non-empty")
    return name.strip(), Path(raw_path).expanduser().resolve()


def resolve_variants(candidate: Path, explicit: Sequence[tuple[str, Path]]) -> dict[str, Path]:
    variants = {"router": candidate.resolve()}
    for name, path in [*_literal_fixed_experts(candidate).items(), *explicit]:
        if name == "router" or name in variants:
            raise ValueError(f"duplicate/reserved candidate mode: {name}")
        variants[name] = path.resolve()
    for name, path in variants.items():
        if not path.is_file():
            raise FileNotFoundError(f"candidate mode {name} does not exist: {path}")
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    return variants


def _is_sequence(value: Any) -> bool:
    return isinstance(value, (list, tuple))


def _positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def validate_unit(order: Any, label: str) -> list[str]:
    if not _is_sequence(order) or not order:
        return [f"{label}:not_nonempty_sequence"]
    op = str(order[0])
    if op in UNIT_NO_ARG:
        return [] if len(order) == 1 else [f"{label}:{op}_arity"]
    if op == "PLANT":
        return [] if len(order) == 2 and str(order[1]) in CROPS else [f"{label}:PLANT_schema"]
    if op in {"PICKUP", "PLACE"}:
        valid = len(order) in {2, 3} and str(order[1]) in ITEMS
        valid = valid and (len(order) == 2 or _positive_int(order[2]))
        return [] if valid else [f"{label}:{op}_schema"]
    return [f"{label}:unknown_unit_op:{op}"]


def validate_market(order: Any, label: str) -> list[str]:
    if not _is_sequence(order) or not order:
        return [f"{label}:not_nonempty_sequence"]
    op = str(order[0])
    if op in {"HIRE", "BUY_LAND"}:
        return [] if len(order) == 1 else [f"{label}:{op}_arity"]
    if len(order) != 3 or not _positive_int(order[2]):
        return [f"{label}:{op}_schema"]
    item = str(order[1])
    allowed = {
        "SELL": PRODUCTS,
        "BUY_SEED": CROPS,
        "BUY_PRODUCT": {"WHEAT", "FERTILIZER"},
        "BUY_ANIMAL": ANIMALS,
    }
    return [] if op in allowed and item in allowed[op] else [f"{label}:unknown_market_order:{op}:{item}"]


def validate_action(action: Any, observation: Mapping[str, Any]) -> list[str]:
    if not isinstance(action, Mapping):
        return ["action:not_mapping"]
    seat = 1 if int(observation.get("player", 0) or 0) == 1 else 0
    farms = list(observation.get("farms", []) or [])
    expected_hands = len((farms[seat] if seat < len(farms) else {}).get("hands", []) or [])
    issues = validate_unit(action.get("farmer"), "farmer")
    hands = action.get("hands")
    if not _is_sequence(hands):
        issues.append("hands:not_sequence")
    else:
        if len(hands) != expected_hands:
            issues.append(f"hands:length:{len(hands)}!={expected_hands}")
        for index, order in enumerate(hands):
            issues.extend(validate_unit(order, f"hands[{index}]"))
    market = action.get("market")
    if not _is_sequence(market):
        issues.append("market:not_sequence")
    else:
        if len(market) > 10:
            issues.append(f"market:length:{len(market)}>10")
        for index, order in enumerate(market):
            issues.extend(validate_market(order, f"market[{index}]"))
    return issues


def outcome(margin: float) -> tuple[int, int, int, float]:
    if margin > 0:
        return 1, 0, 0, 1.0
    if margin == 0:
        return 0, 1, 0, 0.5
    return 0, 0, 1, 0.0


def task_id(mode: str, opponent: str, seed: int, seat: int) -> str:
    return f"{mode}__{opponent}__{seed}__s{seat}"


def error_row(task: Mapping[str, Any], error: str) -> dict[str, Any]:
    return {
        "task_id": task["task_id"],
        "candidate_mode": task["candidate_mode"],
        "opponent": task["opponent"],
        "seed": int(task["seed"]),
        "candidate_seat": int(task["candidate_seat"]),
        "status": "ERROR",
        "error": error,
        "calls": 0,
        "candidate_schema_violations": 0,
        "opponent_schema_violations": 0,
        "win": 0,
        "tie": 0,
        "loss": 0,
        "score": 0.0,
    }


def play(task: Mapping[str, Any]) -> dict[str, Any]:
    base = {
        "task_id": task["task_id"],
        "candidate_mode": task["candidate_mode"],
        "opponent": task["opponent"],
        "seed": int(task["seed"]),
        "candidate_seat": int(task["candidate_seat"]),
    }
    try:
        kagsim, Registry, create_agent, _ = load_runtime()
        registry = Registry(path=HERE / "runtime_registry.json", models={}, raw={})
        suffix = f"{os.getpid()}_{task['task_id']}"
        candidate = create_agent(registry, {
            "id": f"candidate_{suffix}", "kind": "python",
            "path": str(task["candidate_path"]), "entrypoint": "agent",
        })
        opponent = create_agent(registry, {
            "id": f"opponent_{suffix}", "kind": "python",
            "path": str(task["opponent_path"]), "entrypoint": "agent",
        })
        seat = int(task["candidate_seat"])
        agents = [None, None]
        agents[seat], agents[1 - seat] = candidate, opponent
        game = kagsim.Game(int(task["seed"]))
        calls = 0
        candidate_issues: list[str] = []
        opponent_issues: list[str] = []
        candidate_violation_count = 0
        opponent_violation_count = 0
        candidate_trace = hashlib.sha256()
        opponent_trace = hashlib.sha256()
        while not game.done:
            observations = [game.observe(0), game.observe(1)]
            actions = [agents[index](observations[index]) for index in (0, 1)]
            own_issues = validate_action(actions[seat], observations[seat])
            rival_issues = validate_action(actions[1 - seat], observations[1 - seat])
            candidate_violation_count += len(own_issues)
            opponent_violation_count += len(rival_issues)
            if len(candidate_issues) < 20:
                candidate_issues.extend(f"step={calls}:{issue}" for issue in own_issues[:20 - len(candidate_issues)])
            if len(opponent_issues) < 20:
                opponent_issues.extend(f"step={calls}:{issue}" for issue in rival_issues[:20 - len(opponent_issues)])
            candidate_trace.update(canonical(actions[seat]) + b"\n")
            opponent_trace.update(canonical(actions[1 - seat]) + b"\n")
            game.step(actions[0], actions[1])
            calls += 1
        rewards = [float(game.reward(0)), float(game.reward(1))]
        margin = rewards[seat] - rewards[1 - seat]
        win, tie, loss, score = outcome(margin)
        return {
            **base,
            "status": "DONE",
            "error": None,
            "calls": calls,
            "candidate_reward": rewards[seat],
            "opponent_reward": rewards[1 - seat],
            "margin": margin,
            "win": win,
            "tie": tie,
            "loss": loss,
            "score": score,
            "candidate_schema_violations": candidate_violation_count,
            "candidate_schema_examples": candidate_issues,
            "opponent_schema_violations": opponent_violation_count,
            "opponent_schema_examples": opponent_issues,
            "candidate_action_sha256": candidate_trace.hexdigest(),
            "opponent_action_sha256": opponent_trace.hexdigest(),
        }
    except Exception as exc:
        return error_row(task, f"{type(exc).__name__}: {exc}")


def aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    planned = len(rows)
    done = [row for row in rows if row.get("status") == "DONE"]
    wins = sum(int(row.get("win", 0)) for row in rows)
    ties = sum(int(row.get("tie", 0)) for row in rows)
    losses = sum(int(row.get("loss", 0)) for row in rows)
    errors = planned - len(done)
    return {
        "planned_games": planned,
        "completed_games": len(done),
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "errors_as_nonwins": errors,
        "pure_win_rate": wins / planned if planned else 0.0,
        "score_rate": (wins + 0.5 * ties) / planned if planned else 0.0,
        "mean_margin_completed": statistics.mean(float(row["margin"]) for row in done) if done else None,
        "candidate_schema_violations": sum(int(row.get("candidate_schema_violations", 0)) for row in rows),
        "opponent_schema_violations": sum(int(row.get("opponent_schema_violations", 0)) for row in rows),
        "all_719_calls": planned > 0 and all(row.get("status") == "DONE" and int(row.get("calls", 0)) == 719 for row in rows),
    }


def opponent_behavior_clusters(
    router_rows: Sequence[Mapping[str, Any]],
    opponents: Sequence[str],
) -> tuple[dict[str, str], dict[str, list[str]]]:
    signatures: dict[str, str] = {}
    for opponent in opponents:
        rows = sorted(
            (row for row in router_rows if row["opponent"] == opponent),
            key=lambda row: (int(row["seed"]), int(row["candidate_seat"])),
        )
        evidence = [
            {
                "seed": row["seed"],
                "candidate_seat": row["candidate_seat"],
                "status": row["status"],
                "calls": row.get("calls", 0),
                "opponent_action_sha256": row.get("opponent_action_sha256"),
            }
            for row in rows
        ]
        if any(row.get("status") != "DONE" or int(row.get("calls", 0)) != 719 for row in rows):
            # An incomplete trace cannot prove equivalence; fail closed and
            # keep that opponent in a singleton cluster.
            signatures[opponent] = hashlib.sha256(canonical(["incomplete", opponent, evidence])).hexdigest()
        else:
            signatures[opponent] = hashlib.sha256(canonical(evidence)).hexdigest()
    grouped: dict[str, list[str]] = {}
    for opponent in opponents:
        grouped.setdefault(signatures[opponent], []).append(opponent)
    cluster_map: dict[str, str] = {}
    clusters: dict[str, list[str]] = {}
    for signature, members in sorted(grouped.items(), key=lambda item: item[1]):
        cluster_id = f"behavior_{signature[:12]}"
        clusters[cluster_id] = members
        for member in members:
            cluster_map[member] = cluster_id
    return cluster_map, clusters


def paired_router_effect(
    router_rows: Sequence[Mapping[str, Any]],
    fixed_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    key = lambda row: (str(row["opponent"]), int(row["seed"]), int(row["candidate_seat"]))
    router = {key(row): row for row in router_rows}
    fixed = {key(row): row for row in fixed_rows}
    keys = sorted(set(router) | set(fixed))
    positive = negative = 0
    router_wins = fixed_wins = 0
    missing_pairs = 0
    for pair_key in keys:
        left, right = router.get(pair_key), fixed.get(pair_key)
        if left is None or right is None:
            missing_pairs += 1
            continue
        left_win = int(left.get("win", 0))
        right_win = int(right.get("win", 0))
        router_wins += left_win
        fixed_wins += right_win
        positive += int(left_win > right_win)
        negative += int(left_win < right_win)
    planned = len(keys)
    return {
        "planned_pairs": planned,
        "missing_pairs": missing_pairs,
        "router_wins": router_wins,
        "fixed_wins": fixed_wins,
        "beu_pure_win_uplift": (router_wins - fixed_wins) / planned if planned else 0.0,
        "positive_flips": positive,
        "negative_flips": negative,
        "net_flips": positive - negative,
    }


def summarize(
    rows: Sequence[Mapping[str, Any]],
    variants: Mapping[str, Path],
    opponents: Mapping[str, Path],
    profile: str,
    seeds: Sequence[int],
    pool_name: str,
) -> dict[str, Any]:
    router_rows = [row for row in rows if row["candidate_mode"] == "router"]
    cluster_map, clusters = opponent_behavior_clusters(router_rows, list(opponents))
    modes: dict[str, Any] = {}
    for mode in variants:
        mode_rows = [row for row in rows if row["candidate_mode"] == mode]
        by_version = {
            opponent: aggregate([row for row in mode_rows if row["opponent"] == opponent])
            for opponent in opponents
        }
        by_seat = {
            str(seat): aggregate([row for row in mode_rows if int(row["candidate_seat"]) == seat])
            for seat in (0, 1)
        }
        by_cluster = {
            cluster: aggregate([row for row in mode_rows if row["opponent"] in members])
            for cluster, members in clusters.items()
        }
        overall = aggregate(mode_rows)
        overall.update({
            "version_weighted_pure_win_rate": statistics.mean(value["pure_win_rate"] for value in by_version.values()),
            "behavior_cluster_weighted_pure_win_rate": statistics.mean(value["pure_win_rate"] for value in by_cluster.values()),
            "minimum_opponent_pure_win_rate": min(value["pure_win_rate"] for value in by_version.values()),
            "by_version": by_version,
            "by_behavior_cluster": by_cluster,
            "by_seat": by_seat,
        })
        modes[mode] = overall

    fixed_effects = {
        mode: paired_router_effect(
            router_rows,
            [row for row in rows if row["candidate_mode"] == mode],
        )
        for mode in variants if mode != "router"
    }
    valid_fixed = [
        mode for mode in fixed_effects
        if not modes[mode]["errors_as_nonwins"]
        and not modes[mode]["candidate_schema_violations"]
        and modes[mode]["all_719_calls"]
        and not fixed_effects[mode]["missing_pairs"]
    ]
    best_fixed = None
    if valid_fixed:
        best_fixed = max(
            valid_fixed,
            key=lambda mode: modes[mode]["pure_win_rate"],
        )
    router = modes["router"]
    expected_count = PROFILE_DEFAULTS[profile]["seed_count"]
    protocol_panel = bool(
        len(seeds) == expected_count
        and pool_name == PROFILE_DEFAULTS[profile]["pool"]
        and (profile == "smoke" or len(opponents) == 18)
    )
    mechanics_ok = bool(
        not router["errors_as_nonwins"]
        and not router["candidate_schema_violations"]
        and router["all_719_calls"]
    )
    strength_ok = bool(
        router["version_weighted_pure_win_rate"] >= 0.75
        and router["behavior_cluster_weighted_pure_win_rate"] >= 0.75
        and router["minimum_opponent_pure_win_rate"] >= 0.50
        and (
            profile != "confirmation"
            or all(router["by_seat"][str(seat)]["pure_win_rate"] >= 0.75 for seat in (0, 1))
        )
    )
    router_ok = None if not fixed_effects else False
    if best_fixed is not None:
        effect = fixed_effects[best_fixed]
        router_ok = bool(effect["beu_pure_win_uplift"] > 0 and effect["positive_flips"] > 0)
    return {
        "primary_metric": "wins/planned_games; ties and ERROR are nonwins",
        "behavior_cluster_basis": "exact opponent action traces on identical router opponent/seed/seat panel",
        "behavior_cluster_map": cluster_map,
        "behavior_clusters": clusters,
        "modes": modes,
        "router_vs_fixed_experts": fixed_effects,
        "best_fixed_expert": best_fixed,
        "gates": {
            "protocol_panel": protocol_panel,
            "mechanics_ok": mechanics_ok,
            "strength_75_ok": strength_ok,
            "router_contribution_ok": router_ok,
            "gold_eligible_from_this_panel": bool(
                profile == "confirmation" and protocol_panel and mechanics_ok and strength_ok and router_ok is True
            ),
        },
        "caveat": "Arena results alone do not prove originality, official Python parity, package parity, or gold status.",
    }


def build_tasks(
    variants: Mapping[str, Path],
    opponents: Mapping[str, Path],
    seeds: Sequence[int],
) -> list[dict[str, Any]]:
    return [
        {
            "task_id": task_id(mode, opponent, seed, seat),
            "candidate_mode": mode,
            "candidate_path": str(candidate_path),
            "opponent": opponent,
            "opponent_path": str(opponent_path),
            "seed": int(seed),
            "candidate_seat": seat,
        }
        for mode, candidate_path in variants.items()
        for opponent, opponent_path in opponents.items()
        for seed in seeds
        for seat in (0, 1)
    ]


def preflight(
    candidate: Path,
    variants: Mapping[str, Path],
    opponents: Mapping[str, Path],
    seeds: Sequence[int],
    workers: int,
) -> tuple[dict[str, Any], Path]:
    if not 1 <= workers <= 4:
        raise ValueError("workers must be between 1 and 4")
    if len(FULL_GOLD) != 18 or len(set(FULL_GOLD)) != 18:
        raise RuntimeError("frozen full gold pool must contain exactly 18 version ids")
    if "v29" in FULL_GOLD or "v30" in FULL_GOLD:
        raise RuntimeError("known V21 behavior aliases V29/V30 must not be weighted")
    for name, path in opponents.items():
        if not path.is_file():
            raise FileNotFoundError(f"missing gold opponent {name}: {path}")
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    kagsim, _, _, engine_binary = load_runtime()
    artifacts = {"candidate:router": sha256_file(candidate)}
    artifacts.update({f"candidate:{name}": sha256_file(path) for name, path in variants.items() if name != "router"})
    artifacts.update({f"opponent:{name}": sha256_file(path) for name, path in opponents.items()})
    artifacts.update({
        "evaluator": sha256_file(Path(__file__).resolve()),
        "simulator_binary": sha256_file(engine_binary),
        "agent_factory": sha256_file(FACTORY / "agent_factory.py"),
    })
    return {
        "engine": str(kagsim.ENGINE_VERSION),
        "engine_binary": str(engine_binary),
        "candidate": str(candidate),
        "candidate_modes": {name: str(path) for name, path in variants.items()},
        "opponents": {name: str(path) for name, path in opponents.items()},
        "artifact_sha256": artifacts,
        "seed_count": len(seeds),
        "seed_sha256": hashlib.sha256(canonical(list(seeds))).hexdigest(),
        "workers": workers,
    }, engine_binary


def run(args: argparse.Namespace) -> int:
    candidate = args.candidate.expanduser().resolve()
    if not candidate.is_file():
        raise FileNotFoundError(f"candidate main.py not found: {candidate}")
    variants = resolve_variants(candidate, args.fixed_expert or [])
    defaults = PROFILE_DEFAULTS[args.profile]
    pool_name = args.pool or defaults["pool"]
    opponents = ANCHORS if pool_name == "anchors" else FULL_GOLD
    seeds = read_seeds(args.seeds_file) if args.seeds_file else deterministic_seeds(
        args.profile,
        args.seed_count if args.seed_count is not None else defaults["seed_count"],
    )
    tasks = build_tasks(variants, opponents, seeds)
    frozen, _ = preflight(candidate, variants, opponents, seeds, args.workers)
    frozen.update({
        "schema": "kaggriculture-v116-arena-rc3-manifest-v1",
        "profile": args.profile,
        "pool": pool_name,
        "planned_router_games": len(opponents) * len(seeds) * 2,
        "planned_all_modes_games": len(tasks),
        "known_behavior_aliases_excluded": {"v29": "v21", "v30": "v21"},
    })
    frozen["run_fingerprint"] = hashlib.sha256(canonical(frozen)).hexdigest()
    frozen["generated_at_utc"] = datetime.now(timezone.utc).isoformat()

    if args.dry_run:
        print(json.dumps({"dry_run": True, "writes": False, **frozen}, ensure_ascii=False, indent=2))
        return 0

    output_dir = args.output_dir.expanduser().resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite existing run directory: {output_dir}")
    output_dir.mkdir(parents=True)
    (output_dir / "seeds.json").write_text(
        json.dumps({"profile": args.profile, "seeds": seeds}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "run_manifest.json").write_text(
        json.dumps(frozen, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    rows: list[dict[str, Any]] = []
    expected = {task["task_id"]: task for task in tasks}
    completed_ids: set[str] = set()
    jsonl_path = output_dir / "games.jsonl"
    with jsonl_path.open("x", encoding="utf-8", buffering=1) as stream:
        # Restart the worker pool at each opponent boundary.  Historical agents
        # retain module state, so this bounds contamination and resident memory.
        for opponent in opponents:
            family_tasks = [task for task in tasks if task["opponent"] == opponent]
            with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
                futures = {executor.submit(play, task): task for task in family_tasks}
                for future in concurrent.futures.as_completed(futures):
                    task = futures[future]
                    try:
                        row = future.result()
                    except BaseException as exc:
                        row = error_row(task, f"worker:{type(exc).__name__}: {exc}")
                    if row["task_id"] in completed_ids:
                        continue
                    completed_ids.add(row["task_id"])
                    rows.append(row)
                    stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        for missing_id in sorted(set(expected) - completed_ids):
            row = error_row(expected[missing_id], "missing_result_after_executor")
            rows.append(row)
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    summary = summarize(rows, variants, opponents, args.profile, seeds, pool_name)
    payload = {
        "schema": "kaggriculture-v116-arena-rc3-summary-v1",
        "run_fingerprint": frozen["run_fingerprint"],
        "manifest": frozen,
        "rows_file": str(jsonl_path),
        "rows_sha256": sha256_file(jsonl_path),
        "summary": summary,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output_dir": str(output_dir), "summary": summary}, ensure_ascii=False, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Evaluate one candidate against the frozen 18-version gold panel without modifying models.",
    )
    result.add_argument("--candidate", type=Path, required=True, help="path to candidate main.py")
    result.add_argument(
        "--profile", choices=tuple(PROFILE_DEFAULTS), default="smoke",
        help="smoke=2 seeds/6 anchors, development=64/18, confirmation=128/18",
    )
    result.add_argument("--pool", choices=("anchors", "full"), help="optional research override")
    result.add_argument("--seed-count", type=int, help="research override; formal profile gate then fails if non-default")
    result.add_argument("--seeds-file", type=Path, help="frozen JSON seed list; overrides deterministic seeds")
    result.add_argument("--workers", type=int, default=4, help="1..4 worker processes (default: 4)")
    result.add_argument(
        "--fixed-expert", action="append", type=parse_named_path, default=[], metavar="NAME=PATH",
        help="paired fixed-expert main.py; may repeat. Candidate can alternatively expose literal ARENA_FIXED_EXPERTS.",
    )
    result.add_argument(
        "--output-dir", type=Path, default=HERE / "runs" / "latest",
        help="new directory for manifest, games.jsonl and summary; existing paths are never overwritten",
    )
    result.add_argument("--dry-run", action="store_true", help="validate paths/hashes/task plan without games or writes")
    return result


def main() -> int:
    return run(parser().parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
