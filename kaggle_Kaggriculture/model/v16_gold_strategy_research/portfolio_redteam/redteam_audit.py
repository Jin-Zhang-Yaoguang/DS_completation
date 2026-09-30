#!/usr/bin/env python3
"""Independent, frozen red-team audit for the complete-portfolio candidate.

This file deliberately imports the candidate as-is and never changes its
route, threshold, or executor.  Evaluation data predates the 2026-08-25 route
source and was not used to choose either continuation.
"""

from __future__ import annotations

import argparse
import base64
import copy
import gzip
import hashlib
from io import BytesIO, StringIO
import importlib.util
import json
import math
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
import statistics
import sys
import tarfile
from tempfile import TemporaryDirectory
import uuid
import zlib
from collections import Counter


HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[4]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
INDEX = ROOT / "kaggle_Kaggriculture" / "model_data" / "kaggriculture_episodes_index"
CANDIDATE = HERE.parent / "top_complete_portfolio" / "portfolio_policy.py"
BASE = MODEL / "v1_adaptive_market" / "main.py"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"

# Frozen before red-team evaluation.  Selection is solely by high historical
# replay reward, with two independent teams per date and no 2026-08-25 file.
HISTORICAL_PROXIES = (
    ("2026-08-20", "Ryo Hasegawa", 94854181),
    ("2026-08-20", "SaiKushal185", 95531759),
    ("2026-08-21", "Subramanya N", 96275739),
    ("2026-08-21", "James Holland", 95908394),
    ("2026-08-22", "Arman Tuganbaev", 96925631),
    ("2026-08-22", "Excluding", 96651843),
    ("2026-08-23", "Crop Dusta", 97710447),
    ("2026-08-23", "MiMi", 97687527),
    ("2026-08-24", "Kronki", 98486063),
    ("2026-08-24", "taiseiu", 98463302),
)
SEED_START = 45000


def load_module(path: Path, prefix: str):
    name = f"{prefix}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def runtime():
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    if not builds:
        raise RuntimeError("cppsim build missing")
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore
    return kagsim


def replay_path(day: str, episode: int) -> Path:
    path = INDEX / f"date={day}" / "data" / f"{episode}.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def route_from_replay(day: str, team: str, episode: int) -> tuple[list[dict], dict]:
    path = replay_path(day, episode)
    replay = json.loads(path.read_text(encoding="utf-8"))
    if replay["info"]["EpisodeId"] != episode or team not in replay["info"]["TeamNames"]:
        raise RuntimeError(f"identity mismatch: {path}")
    seat = replay["info"]["TeamNames"].index(team)
    actions = [copy.deepcopy(pair[seat].get("action") or {}) for pair in replay["steps"][1:720]]
    metadata = {
        "date": day,
        "team": team,
        "episode": episode,
        "seat": seat,
        "source_seed": int(replay["info"]["seed"]),
        "source_reward": float(replay["rewards"][seat]),
        "source_opponent": replay["info"]["TeamNames"][1 - seat],
        "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    del replay
    return actions, metadata


def semantic_signature(actions: list[dict]) -> tuple[str, dict]:
    crops = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON")
    animals = ("GOOSE", "COW", "SHEEP")
    buys = {key: 0 for key in (*crops, *animals)}
    plants = {key: 0 for key in crops}
    ops: dict[str, int] = {}
    for action in actions:
        for order in [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]:
            op = str(order[0]) if order else "PASS"
            ops[op] = ops.get(op, 0) + 1
            if op == "PLANT" and len(order) >= 2 and order[1] in plants:
                plants[order[1]] += 1
        for order in action.get("market") or []:
            if not order:
                continue
            op = str(order[0])
            ops[op] = ops.get(op, 0) + 1
            if op in {"BUY_SEED", "BUY_ANIMAL"} and len(order) >= 3 and order[1] in buys:
                buys[order[1]] += max(0, int(order[2] or 0))
    descriptor = {
        "buy_totals": buys,
        "plant_counts": plants,
        "land_requests": ops.get("BUY_LAND", 0),
        "hire_requests": ops.get("HIRE", 0),
        "animal_care": [ops.get("FEED", 0), ops.get("CARE", 0)],
        "prefix_exact_sha256": hashlib.sha256(
            json.dumps(actions[:72], sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
    }
    signature = hashlib.sha256(json.dumps(descriptor, sort_keys=True).encode()).hexdigest()
    return signature, descriptor


def fresh_base():
    return load_module(BASE, "redteam_base")


def replay_proxy(actions: list[dict]):
    """Use the frozen historical complete route with the common live executor."""
    base = fresh_base()

    def policy(obs, configuration=None):
        del configuration
        base._ACTIONS = actions
        return base._CORE_AGENT(obs)

    return policy


def score(margin: float) -> float:
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def quantile(values: list[float], p: float) -> float:
    values = sorted(values)
    position = (len(values) - 1) * p
    lo, hi = math.floor(position), math.ceil(position)
    return values[lo] if lo == hi else values[lo] * (hi - position) + values[hi] * (position - lo)


def summarize(rows: list[dict]) -> dict:
    margins = sorted(float(row["margin"]) for row in rows)
    n = max(1, math.ceil(len(margins) * 0.10))
    return {
        "games": len(rows),
        "wins_ties_losses": [sum(x > 0 for x in margins), sum(x == 0 for x in margins), sum(x < 0 for x in margins)],
        "score_rate": statistics.mean(score(x) for x in margins),
        "mean_bank": statistics.mean(float(row["own"]) for row in rows),
        "mean_margin": statistics.mean(margins),
        "margin_p10": quantile(margins, 0.10),
        "margin_cvar10": statistics.mean(margins[:n]),
    }


def play(policy, opponent, seed: int, seat: int, kagsim) -> tuple[float, float]:
    game = kagsim.Game(seed)
    agents = [None, None]
    agents[seat], agents[1 - seat] = policy, opponent
    while not game.done:
        game.step(agents[0](game.observe(0)), agents[1](game.observe(1)))
    rewards = [float(game.reward(0)), float(game.reward(1))]
    return rewards[seat], rewards[1 - seat]


def evaluate(seeds: int, output: Path) -> dict:
    kagsim = runtime()
    candidate_module = load_module(CANDIDATE, "redteam_candidate")
    proxies = []
    signatures = {}
    for day, team, episode in HISTORICAL_PROXIES:
        actions, metadata = route_from_replay(day, team, episode)
        signature, descriptor = semantic_signature(actions)
        metadata.update({"behavior_signature": signature, "behavior_descriptor": descriptor})
        if signature in signatures:
            raise RuntimeError(f"behavior duplicate: {team} and {signatures[signature]}")
        signatures[signature] = team
        proxies.append((metadata, actions))

    rows = []
    for metadata, actions in proxies:
        family = f"{metadata['date']}::{metadata['team']}::{metadata['behavior_signature'][:12]}"
        for seed in range(SEED_START, SEED_START + seeds):
            for seat in (0, 1):
                for mode in ("single_default", "router"):
                    own, opp = play(
                        candidate_module.make_agent(mode), replay_proxy(actions), seed, seat, kagsim
                    )
                    rows.append({
                        "mode": mode, "family": family, "date": metadata["date"],
                        "team": metadata["team"], "episode": metadata["episode"],
                        "behavior_signature": metadata["behavior_signature"],
                        "seed": seed, "seat": seat, "own": own, "opp": opp,
                        "margin": own - opp,
                    })

    modes = {}
    for mode in ("single_default", "router"):
        selected = [row for row in rows if row["mode"] == mode]
        by_family = {
            family: summarize([row for row in selected if row["family"] == family])
            for family in sorted({row["family"] for row in selected})
        }
        modes[mode] = {
            **summarize(selected),
            "family_equal_score_rate": statistics.mean(x["score_rate"] for x in by_family.values()),
            "worst_family_score_rate": min(x["score_rate"] for x in by_family.values()),
            "by_family": by_family,
        }

    default = {
        (row["family"], row["seed"], row["seat"]): row
        for row in rows if row["mode"] == "single_default"
    }
    paired = []
    for row in rows:
        if row["mode"] != "router":
            continue
        base = default[(row["family"], row["seed"], row["seat"])]
        paired.append({
            "family": row["family"], "seed": row["seed"], "seat": row["seat"],
            "score_delta": score(row["margin"]) - score(base["margin"]),
            "margin_delta": row["margin"] - base["margin"],
            "own_delta": row["own"] - base["own"],
        })
    result = {
        "status": "INDEPENDENT_FROZEN_REDTEAM_HELDOUT_HISTORICAL_PROXY_TEST",
        "candidate_source_date": "2026-08-25",
        "evaluation_source_dates": sorted({x[0] for x in HISTORICAL_PROXIES}),
        "seed_range": [SEED_START, SEED_START + seeds - 1],
        "seat_policy": "both seats for every family and seed; fresh agents every game",
        "selection_policy": "high historical replay reward, two independent teams per date, selected without candidate outcomes",
        "engine": str(kagsim.ENGINE_VERSION),
        "behavior_dedup": {"unique": len(signatures), "selected": len(proxies), "exact_duplicate_count": len(proxies) - len(signatures)},
        "proxies": [metadata for metadata, _ in proxies],
        "modes": modes,
        "paired_router_vs_single_default": {
            "games": len(paired),
            "score_uplift_pp": 100 * statistics.mean(x["score_delta"] for x in paired),
            "positive_zero_negative": [sum(x["score_delta"] > 0 for x in paired), sum(x["score_delta"] == 0 for x in paired), sum(x["score_delta"] < 0 for x in paired)],
            "mean_margin_delta": statistics.mean(x["margin_delta"] for x in paired),
            "mean_own_delta": statistics.mean(x["own_delta"] for x in paired),
        },
        "rows": rows,
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def fingerprint(obs: dict) -> str:
    payload = {
        "step": obs.get("step"), "farms": obs.get("farms"), "private": obs.get("private"),
        "market": obs.get("market"), "town": obs.get("town"),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def causal_audit(output: Path) -> dict:
    kagsim = runtime()
    candidate_module = load_module(CANDIDATE, "redteam_causal")
    exact_prefix = all(
        candidate_module._DEFAULT_ACTIONS[s] == candidate_module._YARN_ACTIONS[s]
        for s in range(candidate_module.ROUTER_STEP)
    )
    # Verify the *native replay states* at the splice, not only the constructed
    # hybrid's common prefix.  Shops are intentionally different and are the
    # causal routing signal; own resources/positions and global market must be
    # identical for a genuine state-homomorphic continuation.
    native = []
    for team, episode in (candidate_module.DEFAULT, candidate_module.YARN):
        replay = json.loads((candidate_module.DATA / f"{episode}.json").read_text())
        seat = replay["info"]["TeamNames"].index(team)
        obs = replay["steps"][candidate_module.ROUTER_STEP][seat]["observation"]
        native.append({
            "team": team, "episode": episode,
            "farm": obs["farms"][seat], "private": obs["private"],
            "market": obs["market"], "shops": obs["town"]["unlocked_shops"],
        })
    native_state_identity = all(native[0][key] == native[1][key] for key in ("farm", "private", "market"))
    probe_actions, _ = route_from_replay(*HISTORICAL_PROXIES[4])
    rows = []
    for seed in range(SEED_START + 1000, SEED_START + 1016):
        games = {}
        for mode in ("single_default", "single_yarn", "router"):
            game = kagsim.Game(seed)
            policy = candidate_module.make_agent(mode)
            opponent = replay_proxy(probe_actions)
            observations = {}
            actions = {}
            while not game.done and game.step_count <= candidate_module.ROUTER_STEP:
                observations[game.step_count] = fingerprint(game.observe(0))
                pair = [policy(game.observe(0)), opponent(game.observe(1))]
                actions[game.step_count] = pair[0]
                game.step(pair[0], pair[1])
            games[mode] = {"observations": observations, "actions": actions}
        step = candidate_module.ROUTER_STEP
        # Up to and including the pre-action observation at step 72 must be
        # identical.  The step-72 returned action may differ by visible shop.
        state_identity = all(
            games["single_default"]["observations"][s] == games["single_yarn"]["observations"][s]
            for s in range(step + 1)
        )
        shops = list(kagsim.Game(seed).observe(0)["town"]["unlocked_shops"])
        # Record actual first visibility using the replayed trajectory.
        first_visible = None
        game = kagsim.Game(seed)
        policy = candidate_module.make_agent("single_default")
        opponent = replay_proxy(probe_actions)
        while not game.done and game.step_count <= step:
            visible = list(game.observe(0)["town"]["unlocked_shops"])
            if visible and first_visible is None:
                first_visible = game.step_count
                shops = visible
            if game.step_count == step:
                break
            game.step(policy(game.observe(0)), opponent(game.observe(1)))
        expected_mode = "single_yarn" if shops and shops[0] == "YARN_STORE" else "single_default"
        rows.append({
            "seed": seed, "shops_at_decision": shops, "first_shop_visible_step": first_visible,
            "state_identity_through_decision_observation": state_identity,
            "router_action_matches_visible_branch_at_step72": games["router"]["actions"][step] == games[expected_mode]["actions"][step],
            "expected_branch": expected_mode,
        })
    result = {
        "status": "INDEPENDENT_CAUSAL_AND_STATE_HOMOMORPHISM_AUDIT",
        "router_step": candidate_module.ROUTER_STEP,
        "prefix_actions_exact_steps_0_71": exact_prefix,
        "native_source_splice_state": {
            "own_farm_private_market_exact": native_state_identity,
            "default_shops": native[0]["shops"],
            "yarn_shops": native[1]["shops"],
        },
        "decision_feature": "obs.town.unlocked_shops[0] at pre-action observation step 72",
        "future_or_private_opponent_fields_used": False,
        "rows": rows,
        "checks": {
            "all_shop_first_visible_at_step72": all(x["first_shop_visible_step"] == 72 for x in rows),
            "native_source_state_homomorphic_except_shop": native_state_identity,
            "all_prefix_states_identical": all(x["state_identity_through_decision_observation"] for x in rows),
            "all_router_actions_match_visible_branch": all(x["router_action_matches_visible_branch_at_step72"] for x in rows),
        },
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "EAST": (1, 0), "WEST": (-1, 0)}


def _shed_access(position, size: int) -> bool:
    x, y = map(int, position)
    half = size // 2
    return (x, y) in {(half - 1, half - 1), (half, half - 1), (half - 1, half), (half, half)}


def _tile(farm: dict, position):
    x, y = map(int, position)
    return farm["tiles"][y][x]


def _audit_action(obs: dict, action: dict, counts: Counter, invalid: list[dict]) -> Counter:
    seat = int(obs["player"])
    farm = obs["farms"][seat]
    positions = [farm["farmer"], *farm["hands"]]
    inventories = list(obs["private"]["inventories"])
    orders = [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]
    counts["turns"] += 1
    counts["market_orders"] += len(action.get("market") or [])
    counts["market_overflow_turns"] += int(len(action.get("market") or []) > 10)
    counts["hand_mismatch_turns"] += int(len(action.get("hands") or []) != len(farm["hands"]))
    remaining_seeds = Counter({k: int(v or 0) for k, v in obs["private"]["seeds"].items()})
    planted = Counter()
    for actor, (position, order) in enumerate(zip(positions, orders)):
        if not order or order[0] == "PASS":
            continue
        op = order[0]
        tile = _tile(farm, position)
        inv = inventories[actor] if actor < len(inventories) else {}
        valid = True
        if op in MOVES:
            dx, dy = MOVES[op]
            x, y = map(int, position)
            valid = 0 <= x + dx < len(farm["tiles"][0]) and 0 <= y + dy < len(farm["tiles"])
        elif op == "PLANT":
            crop = order[1] if len(order) >= 2 else ""
            valid = tile is None and remaining_seeds[crop] > 0
            if valid:
                remaining_seeds[crop] -= 1
                planted[crop] += 1
        elif op == "WATER":
            valid = isinstance(tile, dict) and tile.get("kind") == "PLANT" and not tile.get("watered_today")
        elif op == "HARVEST":
            valid = isinstance(tile, dict) and int(tile.get("yield_units", 0) or 0) > 0
        elif op == "FERTILIZE":
            valid = isinstance(tile, dict) and tile.get("kind") == "PLANT" and int(inv.get("FERTILIZER", 0) or 0) > 0
        elif op in {"BUILD_COOP", "BUILD_PASTURE"}:
            valid = tile is None
        elif op == "DIG":
            valid = tile is not None and tile != "LOCKED" and not (isinstance(tile, dict) and tile.get("animal"))
        elif op == "FEED":
            valid = isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("fed_today") and int(inv.get("WHEAT", 0) or 0) > 0
        elif op == "CARE":
            valid = isinstance(tile, dict) and bool(tile.get("animal")) and not tile.get("cared_today")
        elif op == "COLLECT_FERTILIZER":
            valid = isinstance(tile, dict) and bool(tile.get("fertilizer_available"))
        elif op == "PICKUP":
            item = order[1] if len(order) >= 2 else ""
            valid = _shed_access(position, len(farm["tiles"])) and int(obs["private"]["shed"].get(item, 0) or 0) > 0
        elif op == "DROP":
            valid = _shed_access(position, len(farm["tiles"])) and sum(int(v or 0) for v in inv.values()) > 0
        elif op == "PLACE":
            item = order[1] if len(order) >= 2 else ""
            valid = int(inv.get(item, 0) or 0) > 0
        counts["unit_orders"] += 1
        counts["unit_valid"] += int(valid)
        counts["unit_invalid"] += int(not valid)
        if not valid:
            counts[f"unit_invalid_{op}"] += 1
            if len(invalid) < 25:
                invalid.append({"step": int(obs["step"]), "seat": seat, "actor": actor, "order": order, "position": position})
    return planted


def action_audit(output: Path) -> dict:
    kagsim = runtime()
    candidate_module = load_module(CANDIDATE, "redteam_action")
    proxy_actions, proxy_meta = route_from_replay(*HISTORICAL_PROXIES[4])
    counts: Counter = Counter()
    invalid: list[dict] = []
    resource_failures: list[dict] = []
    rewards = []
    for seed in range(SEED_START + 2000, SEED_START + 2016):
        for seat in (0, 1):
            game = kagsim.Game(seed)
            policy = candidate_module.make_agent("router")
            opponent = replay_proxy(proxy_actions)
            while not game.done:
                obs = game.observe(seat)
                action = policy(obs)
                planted = _audit_action(obs, action, counts, invalid)
                pair = [None, None]
                pair[seat] = action
                pair[1 - seat] = opponent(game.observe(1 - seat))
                before_land = len(obs["farms"][seat]["unlocked_quadrants"])
                before_hands = len(obs["farms"][seat]["hands"])
                before_seeds = {k: int(v or 0) for k, v in obs["private"]["seeds"].items()}
                land_req = sum(bool(x and x[0] == "BUY_LAND") for x in action.get("market") or [])
                hire_req = sum(bool(x and x[0] == "HIRE") for x in action.get("market") or [])
                seed_req = Counter()
                for order in action.get("market") or []:
                    if len(order) >= 3 and order[0] == "BUY_SEED":
                        seed_req[order[1]] += max(0, int(order[2] or 0))
                game.step(pair[0], pair[1])
                if game.done:
                    continue
                after = game.observe(seat)
                land_filled = min(land_req, max(0, len(after["farms"][seat]["unlocked_quadrants"]) - before_land))
                counts["land_requests"] += land_req
                counts["land_success"] += land_filled
                if land_filled < land_req and len(resource_failures) < 25:
                    resource_failures.append({"kind": "BUY_LAND", "seed": seed, "step": int(obs["step"]), "seat": seat, "requested": land_req, "filled": land_filled, "money": int(obs["farms"][seat]["money"])})
                if int(obs["hour"]) != 23:
                    hire_filled = min(hire_req, max(0, len(after["farms"][seat]["hands"]) - before_hands))
                    counts["hire_requests_auditable"] += hire_req
                    counts["hire_success"] += hire_filled
                    if hire_filled < hire_req and len(resource_failures) < 25:
                        resource_failures.append({"kind": "HIRE", "seed": seed, "step": int(obs["step"]), "seat": seat, "requested": hire_req, "filled": hire_filled, "money": int(obs["farms"][seat]["money"]), "market": action.get("market") or []})
                for item, requested in seed_req.items():
                    bought = max(0, int(after["private"]["seeds"].get(item, 0) or 0) - before_seeds.get(item, 0) + planted[item])
                    counts["seed_buy_requested_units"] += requested
                    counts["seed_buy_success_units"] += min(requested, bought)
            rewards.append(float(game.reward(seat)))
    result = {
        "status": "INDEPENDENT_ACTION_AND_RESOURCE_EXECUTABILITY_AUDIT",
        "engine": str(kagsim.ENGINE_VERSION),
        "seed_range": [SEED_START + 2000, SEED_START + 2015],
        "games": len(rewards),
        "opponent_proxy": proxy_meta,
        "counts": dict(counts),
        "rates": {
            "hand_shape_match": 1 - counts["hand_mismatch_turns"] / max(1, counts["turns"]),
            "market_order_limit_compliance": 1 - counts["market_overflow_turns"] / max(1, counts["turns"]),
            "unit_precondition_valid": counts["unit_valid"] / max(1, counts["unit_orders"]),
            "land_success": counts["land_success"] / max(1, counts["land_requests"]),
            "hire_success_non_dayend": counts["hire_success"] / max(1, counts["hire_requests_auditable"]),
            "seed_buy_success": counts["seed_buy_success_units"] / max(1, counts["seed_buy_requested_units"]),
        },
        "invalid_examples": invalid,
        "resource_failure_examples": resource_failures,
        "mean_bank": statistics.mean(rewards),
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def encoded_actions(actions: list[dict]) -> str:
    raw = json.dumps(actions, separators=(",", ":")).encode()
    return base64.b85encode(zlib.compress(raw, 9)).decode()


def build_and_qa(output: Path) -> dict:
    production = HERE.parent / "top_complete_portfolio"
    production_main = production / "main.py"
    production_archive = production / "submission.tar.gz"
    manifest = json.loads((production / "submission_manifest.json").read_text())
    source = production_main.read_bytes()
    main_path = HERE / "packaged_candidate_main.py"
    main_path.write_bytes(source)
    archive_path = HERE / "packaged_candidate_submission.tar.gz"
    archive_path.write_bytes(production_archive.read_bytes())

    from kaggle_environments import make
    from kaggle_environments.agent import get_last_callable
    selected = get_last_callable(source.decode(), path=str(main_path))
    games = []
    with TemporaryDirectory(prefix="portfolio_redteam_") as directory:
        root = Path(directory)
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(root, filter="data")
        extracted = (root / "main.py").read_text(encoding="utf-8")
        for seed in (SEED_START + 3000, SEED_START + 3001):
            for seat in (0, 1):
                handle = get_last_callable(extracted, path=str(root / "main.py"))
                calls = 0
                def traced(obs, configuration=None):
                    nonlocal calls
                    calls += 1
                    return handle(obs, configuration)
                agents = [traced, "random"] if seat == 0 else ["random", traced]
                stdout, stderr = StringIO(), StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    steps = make("kaggriculture", configuration={"seed": seed}, debug=False).run(agents)
                final = steps[-1]
                games.append({
                    "seed": seed, "seat": seat, "steps": len(steps), "calls": calls,
                    "statuses": [str(x.status) for x in final],
                    "stdout": stdout.getvalue(), "stderr": stderr.getvalue(),
                })
    with tarfile.open(archive_path, "r:gz") as tar:
        members = [x.name for x in tar.getmembers()]
        extracted_main = tar.extractfile("main.py").read()

    # Independent exact behavior parity between the research policy and the
    # actual raw-loaded production main.py on cppsim, against a frozen unseen
    # historical route proxy.  This catches build-time omissions in addition
    # to ordinary import/termination errors.
    kagsim = runtime()
    candidate_module = load_module(CANDIDATE, "redteam_package_policy")
    proxy_actions, _ = route_from_replay(*HISTORICAL_PROXIES[6])
    parity = []
    for seed in (SEED_START + 3100, SEED_START + 3101):
        for seat in (0, 1):
            research_reward = play(
                candidate_module.make_agent("router"), replay_proxy(proxy_actions), seed, seat, kagsim
            )
            raw_handle = get_last_callable(source.decode(), path=str(main_path))
            package_reward = play(raw_handle, replay_proxy(proxy_actions), seed, seat, kagsim)
            parity.append({
                "seed": seed, "seat": seat,
                "research_rewards": list(research_reward),
                "package_rewards": list(package_reward),
                "exact": research_reward == package_reward,
            })
    result = {
        "status": "INDEPENDENT_PRODUCTION_ARCHIVE_RAW_LOADER_PARITY_AND_OFFICIAL_QA",
        "main_sha256": hashlib.sha256(source).hexdigest(),
        "archive_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        "archive_size_bytes": archive_path.stat().st_size,
        "manifest": manifest,
        "members": members,
        "raw_loader_callable": getattr(selected, "__name__", None),
        "games": games,
        "research_package_parity": parity,
        "checks": {
            "single_main_member": members == ["main.py"],
            "archive_main_exact": extracted_main == source,
            "manifest_hashes_exact": (
                manifest.get("main_sha256") == hashlib.sha256(source).hexdigest()
                and manifest.get("archive_sha256") == hashlib.sha256(archive_path.read_bytes()).hexdigest()
            ),
            "raw_loader_selects_agent": getattr(selected, "__name__", None) == "agent",
            "all_official_games_done": all(x["steps"] == 720 and x["calls"] == 719 and x["statuses"] == ["DONE", "DONE"] for x in games),
            "zero_output": all(not x["stdout"] and not x["stderr"] for x in games),
            "research_package_exact_cppsim": all(x["exact"] for x in parity),
        },
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def compact(result: dict) -> dict:
    return {key: value for key, value in result.items() if key not in {"rows", "proxies", "games"}}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("evaluate", "causal", "actions", "package", "all"))
    parser.add_argument("--seeds", type=int, default=24)
    args = parser.parse_args()
    if args.command in {"causal", "all"}:
        print(json.dumps(compact(causal_audit(HERE / "causal_audit.json")), ensure_ascii=False, indent=2))
    if args.command in {"package", "all"}:
        print(json.dumps(compact(build_and_qa(HERE / "package_qa.json")), ensure_ascii=False, indent=2))
    if args.command in {"actions", "all"}:
        print(json.dumps(compact(action_audit(HERE / "action_audit.json")), ensure_ascii=False, indent=2))
    if args.command in {"evaluate", "all"}:
        print(json.dumps(compact(evaluate(args.seeds, HERE / "heldout_historical_results.json")), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
