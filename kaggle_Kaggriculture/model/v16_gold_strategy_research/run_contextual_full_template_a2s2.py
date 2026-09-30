#!/usr/bin/env python3
"""Paired cppsim evaluation for the frozen contextual full-template router.

Two panels are reported separately:

* recent top/meta replay tapes (wide two-seat stress, not live-policy evidence);
* heterogeneous local complete agents (closed-loop unknown-policy proxies).

A2 is a regression anchor only.  The script never promotes a candidate from
the A2 comparison alone.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import statistics
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MODEL = ROOT / "kaggle_Kaggriculture" / "model"
DATA = ROOT / "kaggle_Kaggriculture" / "model_data" / "kaggriculture_episodes_index" / "date=2026-08-25" / "data"
CPPSIM = MODEL / "community_research" / "2026-08-26" / "live_cli" / "external_repos" / "kaggriculture-cppsim"
DEFAULT_TEAMS = ("Crop Dusta", "Ryo Hasegawa", "Subramanya N", "tetsuya", "Kronki", "tyz123456")
LOCAL_PROXY_POOL = ("baseline_v1", "baseline_v2", "baseline_v5", "baseline_v8")
PASS_ACTION = {"farmer": ["PASS"], "hands": [], "market": []}


def _load_cppsim() -> Any:
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    if not builds:
        raise RuntimeError(f"cppsim is not built under {CPPSIM / 'build'}")
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore

    return kagsim


KAGSIM = _load_cppsim()
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from contextual_full_template_a2s2 import make_agent  # noqa: E402
from mine_portfolio_templates import header  # noqa: E402
from kaggle_Kaggriculture.model.v10_replay_lolo_router.expert_registry import create_agent  # noqa: E402


_SERIAL = 0


def load_a2(tag: str) -> Any:
    global _SERIAL
    _SERIAL += 1
    path = MODEL / "v1_adaptive_market" / "main.py"
    spec = importlib.util.spec_from_file_location(f"_v16_a2s2_anchor_{tag}_{_SERIAL}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def action_digest(actions: list[dict[str, Any]]) -> str:
    payload = json.dumps(actions, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def score(own: float, opponent: float) -> float:
    return 1.0 if own > opponent else 0.5 if own == opponent else 0.0


def selected_replays(teams: tuple[str, ...], ranks: range) -> dict[str, list[dict[str, Any]]]:
    selected: dict[str, list[dict[str, Any]]] = {team: [] for team in teams}
    for path in DATA.glob("*.json"):
        row = header(path)
        if row is None:
            continue
        for team in set(row["teams"]) & set(teams):
            selected[team].append(row)
    stop = ranks.stop
    for team in teams:
        rows = sorted(selected[team], key=lambda row: row["episode_id"], reverse=True)
        selected[team] = rows[ranks.start:stop]
    return selected


def replay_tape(replay: dict[str, Any], source_seat: int) -> list[dict[str, Any]]:
    tape = [pair[source_seat].get("action") or {} for pair in replay["steps"][1:720]]
    if len(tape) != 719:
        raise ValueError("replay does not contain exactly 719 acting turns")
    return tape


def play_tape(seed: int, own_seat: int, live: Callable[[dict[str, Any]], dict[str, Any]], tape: list[dict[str, Any]]) -> tuple[tuple[float, float], list[dict[str, Any]]]:
    game = KAGSIM.Game(int(seed))
    own_actions = []
    while not game.done:
        step = int(game.step_count)
        actions: list[dict[str, Any] | None] = [None, None]
        own_action = live(game.observe(own_seat))
        own_actions.append(own_action)
        actions[own_seat] = own_action
        actions[1 - own_seat] = tape[step]
        game.step(actions[0], actions[1])
    if int(game.step_count) != 719:
        raise AssertionError(f"unexpected acting turns: {game.step_count}")
    return (float(game.reward(0)), float(game.reward(1))), own_actions


def play_live(seed: int, agent0: Callable, agent1: Callable) -> tuple[float, float]:
    game = KAGSIM.Game(int(seed))
    while not game.done:
        game.step(agent0(game.observe(0)), agent1(game.observe(1)))
    return float(game.reward(0)), float(game.reward(1))


def pair_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    baseline_scores = [row["baseline_score"] for row in rows]
    candidate_scores = [row["candidate_score"] for row in rows]
    margin_delta = [row["candidate_margin"] - row["baseline_margin"] for row in rows]
    own_delta = [row["candidate_own"] - row["baseline_own"] for row in rows]
    return {
        "comparisons": len(rows),
        "baseline_score_rate": statistics.mean(baseline_scores),
        "candidate_score_rate": statistics.mean(candidate_scores),
        "paired_score_uplift": statistics.mean(c - b for b, c in zip(baseline_scores, candidate_scores, strict=True)),
        "baseline_mean_margin": statistics.mean(row["baseline_margin"] for row in rows),
        "candidate_mean_margin": statistics.mean(row["candidate_margin"] for row in rows),
        "margin_delta_mean": statistics.mean(margin_delta),
        "margin_delta_median": statistics.median(margin_delta),
        "margin_positive_zero_negative": [sum(x > 0 for x in margin_delta), sum(x == 0 for x in margin_delta), sum(x < 0 for x in margin_delta)],
        "own_delta_mean": statistics.mean(own_delta),
        "own_positive_zero_negative": [sum(x > 0 for x in own_delta), sum(x == 0 for x in own_delta), sum(x < 0 for x in own_delta)],
    }


def cluster_ci(rows: list[dict[str, Any]], cluster_key: str, rounds: int = 5000) -> dict[str, list[float]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[cluster_key])].append(row)
    keys = sorted(grouped)
    rng = random.Random(20260826)
    score_values, margin_values = [], []
    for _ in range(rounds):
        sample = [item for _key in (rng.choice(keys) for _ in keys) for item in grouped[_key]]
        score_values.append(statistics.mean(item["candidate_score"] - item["baseline_score"] for item in sample))
        margin_values.append(statistics.mean(item["candidate_margin"] - item["baseline_margin"] for item in sample))
    score_values.sort()
    margin_values.sort()
    lo = max(0, int(0.025 * rounds) - 1)
    hi = min(rounds - 1, int(0.975 * rounds))
    return {
        "paired_score_uplift_ci95": [score_values[lo], score_values[hi]],
        "margin_delta_mean_ci95": [margin_values[lo], margin_values[hi]],
    }


def identity_replay_check(replay: dict[str, Any]) -> dict[str, Any]:
    tapes = [replay_tape(replay, seat) for seat in (0, 1)]
    game = KAGSIM.Game(int(replay["info"]["seed"]))
    while not game.done:
        step = int(game.step_count)
        game.step(tapes[0][step], tapes[1][step])
    actual = [float(game.reward(0)), float(game.reward(1))]
    expected = [float(value) for value in replay["rewards"]]
    return {"episode_id": int(replay["info"]["EpisodeId"]), "expected": expected, "actual": actual, "exact": actual == expected}


def top_tape_panel(teams: tuple[str, ...], start_rank: int, latest_per_team: int) -> dict[str, Any]:
    selected = selected_replays(teams, range(start_rank, latest_per_team))
    anchor = load_a2("top")
    candidate = make_agent()
    rows: list[dict[str, Any]] = []
    identities: dict[int, dict[str, Any]] = {}
    for team in teams:
        for indexed in selected[team]:
            replay = json.loads(indexed["path"].read_text())
            episode_id = int(replay["info"]["EpisodeId"])
            identities.setdefault(episode_id, identity_replay_check(replay))
            source_seat = replay["info"]["TeamNames"].index(team)
            tape = replay_tape(replay, source_seat)
            for own_seat in (0, 1):
                baseline, baseline_actions = play_tape(int(replay["info"]["seed"]), own_seat, anchor.agent, tape)
                routed, routed_actions = play_tape(int(replay["info"]["seed"]), own_seat, candidate, tape)
                other = 1 - own_seat
                diag = candidate.diagnostics(own_seat)
                rows.append({
                    "team": team,
                    "episode_id": episode_id,
                    "seed": int(replay["info"]["seed"]),
                    "own_seat": own_seat,
                    "baseline_own": baseline[own_seat],
                    "baseline_opponent": baseline[other],
                    "candidate_own": routed[own_seat],
                    "candidate_opponent": routed[other],
                    "baseline_margin": baseline[own_seat] - baseline[other],
                    "candidate_margin": routed[own_seat] - routed[other],
                    "baseline_score": score(baseline[own_seat], baseline[other]),
                    "candidate_score": score(routed[own_seat], routed[other]),
                    "baseline_action_sha256": action_digest(baseline_actions),
                    "candidate_action_sha256": action_digest(routed_actions),
                    "selected": diag["selected"],
                    "reason": diag["reason"],
                    "opponent_tiles": diag["opponent_tiles"],
                    "prefix_complete": diag["prefix_complete"],
                    "prefix_match": diag["prefix_match"],
                    "first_mismatch": diag["first_mismatch"],
                })
    by_team = {team: pair_summary([row for row in rows if row["team"] == team]) for team in teams}
    overall = pair_summary(rows)
    overall.update(cluster_ci(rows, "episode_id"))
    overall["family_equal_baseline_score_rate"] = statistics.mean(value["baseline_score_rate"] for value in by_team.values())
    overall["family_equal_candidate_score_rate"] = statistics.mean(value["candidate_score_rate"] for value in by_team.values())
    overall["prefix_failures"] = sum(not row["prefix_complete"] or not row["prefix_match"] for row in rows)
    overall["selection_counts"] = {name: sum(row["selected"] == name for row in rows) for name in sorted({row["selected"] for row in rows})}
    return {
        "status": "FIXED_TOP_TAPE_STRESS_NOT_LIVE_POLICY_EVIDENCE",
        "source_date": "2026-08-25",
        "ranks_zero_based": [start_rank, latest_per_team - 1],
        "episodes_per_team": latest_per_team - start_rank,
        "identity_replay": {"checks": len(identities), "exact": sum(row["exact"] for row in identities.values()), "rows": list(identities.values())},
        "overall": overall,
        "by_team": by_team,
        "rows": rows,
    }


def local_proxy_panel(seed_count: int) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for opponent_id in LOCAL_PROXY_POOL:
        anchor = load_a2(f"proxy_{opponent_id}")
        candidate = make_agent()
        baseline_opponent = create_agent(opponent_id)
        candidate_opponent = create_agent(opponent_id)
        for seed in range(seed_count):
            for own_seat in (0, 1):
                if own_seat == 0:
                    baseline = play_live(seed, anchor.agent, baseline_opponent)
                    routed = play_live(seed, candidate, candidate_opponent)
                else:
                    baseline = play_live(seed, baseline_opponent, anchor.agent)
                    routed = play_live(seed, candidate_opponent, candidate)
                other = 1 - own_seat
                diag = candidate.diagnostics(own_seat)
                rows.append({
                    "opponent": opponent_id,
                    "seed": seed,
                    "cluster": f"{opponent_id}:{seed}",
                    "own_seat": own_seat,
                    "baseline_own": baseline[own_seat],
                    "baseline_opponent": baseline[other],
                    "candidate_own": routed[own_seat],
                    "candidate_opponent": routed[other],
                    "baseline_margin": baseline[own_seat] - baseline[other],
                    "candidate_margin": routed[own_seat] - routed[other],
                    "baseline_score": score(baseline[own_seat], baseline[other]),
                    "candidate_score": score(routed[own_seat], routed[other]),
                    "selected": diag["selected"],
                    "reason": diag["reason"],
                    "opponent_tiles": diag["opponent_tiles"],
                    "prefix_complete": diag["prefix_complete"],
                    "prefix_match": diag["prefix_match"],
                })
    by_opponent = {opponent: pair_summary([row for row in rows if row["opponent"] == opponent]) for opponent in LOCAL_PROXY_POOL}
    overall = pair_summary(rows)
    overall.update(cluster_ci(rows, "cluster"))
    overall["family_equal_baseline_score_rate"] = statistics.mean(value["baseline_score_rate"] for value in by_opponent.values())
    overall["family_equal_candidate_score_rate"] = statistics.mean(value["candidate_score_rate"] for value in by_opponent.values())
    overall["worst_family_candidate_score_rate"] = min(value["candidate_score_rate"] for value in by_opponent.values())
    overall["prefix_failures"] = sum(not row["prefix_complete"] or not row["prefix_match"] for row in rows)
    overall["selection_counts"] = {name: sum(row["selected"] == name for row in rows) for name in sorted({row["selected"] for row in rows})}
    return {"status": "CLOSED_LOOP_HETEROGENEOUS_LOCAL_PROXY_DEVELOPMENT", "seeds": seed_count, "overall": overall, "by_opponent": by_opponent, "rows": rows}


def a2_identity_panel(seed_count: int = 8) -> dict[str, Any]:
    rows = []
    for seat in (0, 1):
        anchor = load_a2(f"identity_{seat}")
        candidate = make_agent()
        for seed in range(seed_count):
            baseline, baseline_actions = play_tape(seed, seat, anchor.agent, [dict(PASS_ACTION) for _ in range(719)])
            routed, routed_actions = play_tape(seed, seat, candidate, [dict(PASS_ACTION) for _ in range(719)])
            diag = candidate.diagnostics(seat)
            rows.append({"seed": seed, "seat": seat, "reward_exact": baseline == routed, "actions_exact": baseline_actions == routed_actions, "selected": diag["selected"], "prefix_match": diag["prefix_match"]})
    return {"comparisons": len(rows), "reward_exact": sum(row["reward_exact"] for row in rows), "actions_exact": sum(row["actions_exact"] for row in rows), "prefix_match": sum(row["prefix_match"] for row in rows), "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--teams", default=",".join(DEFAULT_TEAMS))
    parser.add_argument("--discovery-per-team", type=int, default=3)
    parser.add_argument("--latest-per-team", type=int, default=12)
    parser.add_argument("--proxy-seeds", type=int, default=24)
    parser.add_argument("--output", default=str(HERE / "contextual_full_template_a2s2_results.json"))
    args = parser.parse_args()
    teams = tuple(value.strip() for value in args.teams.split(",") if value.strip())
    if not 0 <= args.discovery_per_team < args.latest_per_team:
        raise ValueError("discovery-per-team must be in [0, latest-per-team)")
    result = {
        "status": "DEVELOPMENT_ONLY_NOT_GOLD_QUALIFIED",
        "engine": KAGSIM.ENGINE_VERSION,
        "candidate": "public opponent MELON >= 10 at step72 -> complete V8; else complete A2",
        "search_templates": [
            "A2 complete", "V8 Kawa adaptive complete", "V9 forced 10C4S",
            "V9 forced 8C6S", "V9 forced 6C8S", "V9 forced 6C12S second-YARN",
        ],
        "commands": {
            "full": ".venv/bin/python kaggle_Kaggriculture/model/v16_gold_strategy_research/run_contextual_full_template_a2s2.py --discovery-per-team 3 --latest-per-team 12 --proxy-seeds 24",
            "smoke": ".venv/bin/python kaggle_Kaggriculture/model/v16_gold_strategy_research/run_contextual_full_template_a2s2.py --discovery-per-team 3 --latest-per-team 4 --proxy-seeds 1 --output /tmp/contextual_full_template_a2s2_smoke.json",
        },
        "a2_role": "regression anchor only; never a standalone promotion target",
        "a2_identity": a2_identity_panel(),
        "top_tape_holdout": top_tape_panel(teams, args.discovery_per_team, args.latest_per_team),
        "local_closed_loop_proxy": local_proxy_panel(args.proxy_seeds),
        "failure_boundaries": [
            "fixed replay tapes are open-loop stress proxies, not live top-agent win-rate evidence",
            "local complete opponents are historical internal lineages, not unknown leaderboard policies",
            "the MELON threshold was discovered on the newest 3 replays per family and requires future-date confirmation",
            "any incomplete/mismatched 72-step prefix fails closed to A2",
            "no candidate is gold-qualified from A2 uplift alone",
        ],
    }
    output = Path(args.output)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    compact = {
        "status": result["status"],
        "engine": result["engine"],
        "a2_identity": result["a2_identity"],
        "top_tape_holdout": {"overall": result["top_tape_holdout"]["overall"], "by_team": result["top_tape_holdout"]["by_team"]},
        "local_closed_loop_proxy": {"overall": result["local_closed_loop_proxy"]["overall"], "by_opponent": result["local_closed_loop_proxy"]["by_opponent"]},
        "output": str(output),
    }
    print(json.dumps(compact, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

