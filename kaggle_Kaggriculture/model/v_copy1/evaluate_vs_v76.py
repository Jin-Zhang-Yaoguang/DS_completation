#!/usr/bin/env python3
"""在 kagsim 1.32.7 中运行 v_copy1 对 V76 的 256-seed 双席位评测。"""

from __future__ import annotations

import concurrent.futures
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import random
import statistics
import sys
import tarfile
import tempfile
import time
from typing import Any


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
PROJECT = MODEL.parent
FACTORY = MODEL / "v10_replay_lolo_router"
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
CPPSIM_LIBS = sorted((CPPSIM / "build").glob("lib.*"))
if not CPPSIM_LIBS:
    raise RuntimeError(f"missing built kagsim under {CPPSIM / 'build'}")
sys.path[:0] = [str(FACTORY), str(CPPSIM_LIBS[-1])]

import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore


CANDIDATE = HERE / "main.py"
CANDIDATE_ARCHIVE = HERE / "submission.tar.gz"
GOLD = MODEL / "v76_adjacent_safe_buy_lead/main.py"
GOLD_ARCHIVE = MODEL / "v76_adjacent_safe_buy_lead/submission.tar.gz"
EXPECTED = {
    "candidate_main": "01f0cd470f669f86d4b53eb5b014614d3b383970d0755f119de14153fd77c1eb",
    "candidate_archive": "3039b7b80d0cf5f58b220ec48028a0f5feec262a2ae38ac069f5ec3e7dd74e3a",
    "gold_main": "efa9442da3c7d2bca333cccdcf46757fb1286c3bc09e81a91e971764353f776e",
    "gold_archive": "ba79b84a140287eb41608f33cf6bd57dad93d1b9c535cc6b6945e1c431c9fdf1",
}
PANEL_SALT = "kaggriculture-v-copy1-vs-v76-20260830"
SOURCE_COUNT = 256
BOOTSTRAP_DRAWS = 20_000
SEED_MANIFEST = HERE / "seed_manifest.json"
GAMES_PATH = HERE / "evaluation_games.jsonl"
REPORT_PATH = HERE / "evaluation_report.json"
V76_DATA = PROJECT / "model_data/loop_evaluations/v76_adjacent_safe_buy_lead"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        temporary = Path(stream.name)
    temporary.replace(path)


def preflight() -> dict[str, Any]:
    actual = {
        "candidate_main": sha256(CANDIDATE),
        "candidate_archive": sha256(CANDIDATE_ARCHIVE),
        "gold_main": sha256(GOLD),
        "gold_archive": sha256(GOLD_ARCHIVE),
    }
    if actual != EXPECTED:
        raise RuntimeError(f"frozen artifact drift: {actual}")
    compile(CANDIDATE.read_bytes(), str(CANDIDATE), "exec")
    compile(GOLD.read_bytes(), str(GOLD), "exec")
    with tarfile.open(CANDIDATE_ARCHIVE, "r:gz") as archive:
        if archive.getnames() != ["main.py"]:
            raise RuntimeError(f"unexpected archive members: {archive.getnames()}")
        archived_main = archive.extractfile("main.py")
        if archived_main is None or archived_main.read() != CANDIDATE.read_bytes():
            raise RuntimeError("archive main.py differs from copied main.py")
    if str(kagsim.ENGINE_VERSION) != "1.32.7":
        raise RuntimeError(f"unexpected engine: {kagsim.ENGINE_VERSION}")
    return actual


def forbidden_seeds() -> set[int]:
    seeds: set[int] = set()
    for name in ("development_source_manifest.json", "confirmation_source_manifest.json"):
        path = V76_DATA / name
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        seeds.update(int(row["seed"]) for row in payload.get("sources", []))
    return seeds


def build_panel() -> list[dict[str, Any]]:
    forbidden = forbidden_seeds()
    records: list[dict[str, Any]] = []
    used: set[int] = set()
    counter = 0
    while len(records) < SOURCE_COUNT:
        digest = hashlib.sha256(f"{PANEL_SALT}:{counter}".encode("utf-8")).digest()
        seed = int.from_bytes(digest[:4], "big") & 0x7FFFFFFF
        counter += 1
        if seed == 0 or seed in used or seed in forbidden:
            continue
        used.add(seed)
        records.append({
            "source_index": len(records),
            "source_id": f"v_copy1_duel_{len(records):03d}",
            "seed": seed,
        })
    manifest = {
        "schema": "kaggriculture-v-copy1-duel-panel-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "panel_salt": PANEL_SALT,
        "source_count": SOURCE_COUNT,
        "seat_assignments": [0, 1],
        "game_count": SOURCE_COUNT * 2,
        "excluded_v76_seed_count": len(forbidden),
        "records": records,
    }
    atomic_json(SEED_MANIFEST, manifest)
    return records


def validate_action(action: Any, obs: Any) -> int:
    if not isinstance(action, dict):
        return 1
    market = action.get("market", []) or []
    hands = action.get("hands", []) or []
    player = int(obs.get("player", 0) or 0)
    farms = obs.get("farms", []) or []
    own_farm = farms[player] if 0 <= player < len(farms) else {}
    expected_hands = len(own_farm.get("hands", []) or [])
    return int(len(market) > 10 or len(hands) != expected_hands)


def play(task: tuple[dict[str, Any], int]) -> dict[str, Any]:
    source, seat = task
    base = {
        "source_index": source["source_index"],
        "source_id": source["source_id"],
        "seed": source["seed"],
        "candidate_seat": seat,
    }
    try:
        registry = Registry(path=HERE / "duel_registry.json", models={}, raw={})
        unique = f"{source['source_id']}_{seat}_{os.getpid()}"
        candidate = create_agent(registry, {
            "id": f"candidate_{unique}", "kind": "python",
            "path": str(CANDIDATE), "entrypoint": "agent",
        })
        gold = create_agent(registry, {
            "id": f"gold_{unique}", "kind": "python",
            "path": str(GOLD), "entrypoint": "agent",
        })
        agents = [None, None]
        agents[seat], agents[1 - seat] = candidate, gold
        game = kagsim.Game(int(source["seed"]))
        candidate_safety = 0
        gold_safety = 0
        calls = 0
        while not game.done:
            observations = [game.observe(0), game.observe(1)]
            actions = [agents[0](observations[0]), agents[1](observations[1])]
            candidate_safety += validate_action(actions[seat], observations[seat])
            gold_safety += validate_action(actions[1 - seat], observations[1 - seat])
            game.step(actions[0], actions[1])
            calls += 1
        rewards = [float(game.reward(0)), float(game.reward(1))]
        margin = rewards[seat] - rewards[1 - seat]
        return {
            **base, "status": "DONE", "error": None, "calls": calls,
            "candidate_reward": rewards[seat], "gold_reward": rewards[1 - seat],
            "margin": margin,
            "score": 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0,
            "candidate_safety_violations": candidate_safety,
            "gold_safety_violations": gold_safety,
        }
    except Exception as exc:
        return {**base, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}


def percentile(values: list[float], probability: float) -> float:
    values = sorted(values)
    index = (len(values) - 1) * probability
    low, high = math.floor(index), math.ceil(index)
    if low == high:
        return values[low]
    return values[low] * (high - index) + values[high] * (index - low)


def cluster_bootstrap(pairs: list[dict[str, float]]) -> dict[str, list[float]]:
    rng = random.Random(290076)
    score_draws: list[float] = []
    margin_draws: list[float] = []
    for _ in range(BOOTSTRAP_DRAWS):
        sample = rng.choices(pairs, k=len(pairs))
        score_draws.append(statistics.mean(row["score"] for row in sample))
        margin_draws.append(statistics.mean(row["combined_margin"] for row in sample))
    return {
        "score_rate_95ci": [percentile(score_draws, 0.025), percentile(score_draws, 0.975)],
        "combined_margin_95ci": [percentile(margin_draws, 0.025), percentile(margin_draws, 0.975)],
    }


def exact_two_sided_binomial(wins: int, losses: int) -> float:
    total = wins + losses
    if total == 0:
        return 1.0
    tail = sum(math.comb(total, k) for k in range(min(wins, losses) + 1)) / (2 ** total)
    return min(1.0, 2.0 * tail)


def outcome(margin: float) -> str:
    return "win" if margin > 0 else "draw" if margin == 0 else "loss"


def summarize(rows: list[dict[str, Any]], elapsed: float, artifacts: dict[str, str]) -> dict[str, Any]:
    valid = [row for row in rows if row.get("status") == "DONE"]
    by_seed: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in valid:
        by_seed[int(row["seed"])].append(row)
    paired: list[dict[str, float]] = []
    for seed, seed_rows in sorted(by_seed.items()):
        if len(seed_rows) != 2 or {int(row["candidate_seat"]) for row in seed_rows} != {0, 1}:
            continue
        paired.append({
            "seed": float(seed),
            "score": statistics.mean(float(row["score"]) for row in seed_rows),
            "combined_margin": sum(float(row["margin"]) for row in seed_rows),
        })
    game_counts = Counter(outcome(float(row["margin"])) for row in valid)
    pair_counts = Counter(outcome(float(row["combined_margin"])) for row in paired)
    seat_stats = {}
    for seat in (0, 1):
        seat_rows = [row for row in valid if int(row["candidate_seat"]) == seat]
        seat_stats[str(seat)] = {
            "games": len(seat_rows),
            "score_rate": statistics.mean(float(row["score"]) for row in seat_rows),
            "mean_margin": statistics.mean(float(row["margin"]) for row in seat_rows),
            "win_draw_loss": dict(Counter(outcome(float(row["margin"])) for row in seat_rows)),
        }
    bootstrap = cluster_bootstrap(paired) if paired else {
        "score_rate_95ci": [0.0, 0.0], "combined_margin_95ci": [0.0, 0.0]
    }
    score_rate = statistics.mean(float(row["score"]) for row in valid) if valid else 0.0
    ci_low, ci_high = bootstrap["score_rate_95ci"]
    verdict = (
        "V_COPY1_STRONGER" if ci_low > 0.5 else
        "V76_STRONGER" if ci_high < 0.5 else
        "INCONCLUSIVE"
    )
    return {
        "schema": "kaggriculture-v-copy1-vs-v76-dual-seat-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "engine": str(kagsim.ENGINE_VERSION),
        "candidate": "v_copy1",
        "gold_baseline": "v76_adjacent_safe_buy_lead",
        "artifact_sha256": artifacts,
        "panel_salt": PANEL_SALT,
        "seed_manifest_sha256": sha256(SEED_MANIFEST),
        "requested_seed_count": SOURCE_COUNT,
        "requested_game_count": SOURCE_COUNT * 2,
        "completed_games": len(valid),
        "completed_seed_pairs": len(paired),
        "error_count": len(rows) - len(valid),
        "errors": [row for row in rows if row.get("status") != "DONE"][:20],
        "game_win_draw_loss": {
            "win": game_counts["win"], "draw": game_counts["draw"], "loss": game_counts["loss"]
        },
        "paired_win_draw_loss": {
            "win": pair_counts["win"], "draw": pair_counts["draw"], "loss": pair_counts["loss"]
        },
        "score_rate": score_rate,
        "score_rate_95ci": bootstrap["score_rate_95ci"],
        "mean_candidate_reward": statistics.mean(float(row["candidate_reward"]) for row in valid) if valid else 0.0,
        "mean_gold_reward": statistics.mean(float(row["gold_reward"]) for row in valid) if valid else 0.0,
        "mean_margin_per_game": statistics.mean(float(row["margin"]) for row in valid) if valid else 0.0,
        "mean_combined_margin_per_seed": statistics.mean(float(row["combined_margin"]) for row in paired) if paired else 0.0,
        "combined_margin_95ci": bootstrap["combined_margin_95ci"],
        "paired_exact_binomial_p": exact_two_sided_binomial(pair_counts["win"], pair_counts["loss"]),
        "seat_stats": seat_stats,
        "candidate_safety_violations": sum(int(row.get("candidate_safety_violations", 0)) for row in valid),
        "gold_safety_violations": sum(int(row.get("gold_safety_violations", 0)) for row in valid),
        "elapsed_seconds": elapsed,
        "verdict": verdict,
    }


def main() -> None:
    started = time.time()
    artifacts = preflight()
    panel = build_panel()
    tasks = [(source, seat) for source in panel for seat in (0, 1)]
    workers = min(16, os.cpu_count() or 1)
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    with GAMES_PATH.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    report = summarize(rows, time.time() - started, artifacts)
    report["games_sha256"] = sha256(GAMES_PATH)
    atomic_json(REPORT_PATH, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
