#!/usr/bin/env python3
"""One-shot 256-source Confirmation and V85 hard-gate report."""

from __future__ import annotations

import concurrent.futures
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import sys


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
PROJECT = MODEL.parent
DATA = PROJECT / "model_data/loop_evaluations/v85_fertilizer_substitution_moe"
SOURCE_MANIFEST = DATA / "confirmation_source_manifest.json"
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
FACTORY = MODEL / "v10_replay_lolo_router"
V80 = MODEL / "v80_spatial_work_stealing_moe"
sys.path[:0] = [str(V80), str(FACTORY), str(sorted((CPPSIM / "build").glob("lib.*"))[-1])]
import kagsim  # type: ignore
from agent_factory import Registry, create_agent  # type: ignore
import evaluate_development as metrics  # type: ignore


POLICIES = {"candidate": HERE / "main.py", "parent": MODEL / "v76_adjacent_safe_buy_lead/main.py"}
PARENT = MODEL / "v76_adjacent_safe_buy_lead/main.py"
OPPONENTS = {
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
    "v32": MODEL / "v32_clone_horizon_preempt/main.py",
    "v54": MODEL / "v54_terminal_water_bypass/main.py",
    "v66": MODEL / "v66_margin_gated_sell_bubble/main.py",
    "v76": PARENT,
}
EXPECTED_ARCHIVE_SHA = "c2e822ec1d56f76f2edb857b2877041a38257f876cbe14de7d2c4cbd153fe51f"


def sha256(path: Path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def score(margin):
    return 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0


def validate_action(action, obs):
    if not isinstance(action, dict):
        return 1
    seat = int(obs.get("player", 0) or 0)
    expected = len(obs["farms"][seat].get("hands", []) or [])
    return int(len(action.get("market", []) or []) > 10 or len(action.get("hands", []) or []) != expected)


def unit_orders(action):
    return [action.get("farmer") or ["PASS"], *(action.get("hands") or [])]


def play(task):
    mode, family, source, seat = task
    base = {"mode": mode, "family": family, "source_id": source["episode_id"],
            "seed": source["seed"], "date": source["date"], "first_shop": source["first_shop"],
            "shops": source["shops"], "seat": seat}
    try:
        registry = Registry(path=HERE / "confirmation_registry.json", models={}, raw={})
        own = create_agent(registry, {"id": f"{mode}_{family}_{source['episode_id']}_{seat}_{os.getpid()}",
                                      "kind": "python", "path": str(POLICIES[mode]), "entrypoint": "agent"})
        rival = create_agent(registry, {"id": f"opp_{mode}_{family}_{source['episode_id']}_{seat}_{os.getpid()}",
                                        "kind": "python", "path": str(OPPONENTS[family]), "entrypoint": "agent"})
        shadow = None
        if mode == "candidate":
            shadow = create_agent(registry, {"id": f"shadow_{family}_{source['episode_id']}_{seat}_{os.getpid()}",
                                             "kind": "python", "path": str(PARENT), "entrypoint": "agent"})
        agents = [None, None]
        agents[seat], agents[1 - seat] = own, rival
        game = kagsim.Game(int(source["seed"]))
        violations = calls = action_change_calls = mechanism_triggers = 0
        while not game.done:
            observations = [game.observe(0), game.observe(1)]
            shadow_action = shadow(observations[seat]) if shadow is not None else None
            own_action = agents[seat](observations[seat])
            rival_action = agents[1 - seat](observations[1 - seat])
            if shadow_action is not None and own_action != shadow_action:
                action_change_calls += 1
                mechanism_triggers += sum(
                    int(candidate and candidate[0] == "COLLECT_FERTILIZER"
                        and (not parent or parent[0] == "PASS"))
                    for candidate, parent in zip(unit_orders(own_action), unit_orders(shadow_action)))
            actions = [None, None]
            actions[seat], actions[1 - seat] = own_action, rival_action
            violations += validate_action(own_action, observations[seat])
            game.step(actions[0], actions[1])
            calls += 1
        rewards = [float(game.reward(0)), float(game.reward(1))]
        return {**base, "status": "DONE", "error": None, "calls": calls,
                "own": rewards[seat], "opponent": rewards[1 - seat],
                "margin": rewards[seat] - rewards[1 - seat], "safety_violations": violations,
                "action_change_calls": action_change_calls, "mechanism_triggers": mechanism_triggers}
    except Exception as exc:
        return {**base, "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"}


def stratified_ci(source_rows, field, salt):
    strata = defaultdict(list)
    for row in source_rows:
        strata[row["date"], row["first_shop"]].append(row)
    rng, values = random.Random(salt), []
    for _ in range(20000):
        sample = []
        for rows in strata.values():
            sample.extend(rng.choices(rows, k=len(rows)))
        values.append(statistics.mean(float(row[field]) for row in sample))
    return [metrics.percentile(values, 0.025), metrics.percentile(values, 0.975)]


def confirmation_metrics(rows, sources, summary):
    good = [row for row in rows if row.get("status") == "DONE"]
    candidate = [row for row in good if row["mode"] == "candidate"]
    parent = [row for row in good if row["mode"] == "parent"]
    family_score = {family: statistics.mean(score(row["margin"]) for row in candidate if row["family"] == family)
                    for family in OPPONENTS}
    family_parent = {family: statistics.mean(score(row["margin"]) for row in parent if row["family"] == family)
                     for family in OPPONENTS}
    direct_sources = []
    for source in sources:
        values = [score(row["margin"]) for row in candidate
                  if row["family"] == "v76" and row["source_id"] == source["episode_id"]]
        direct_sources.append({"date": source["date"], "first_shop": source["first_shop"],
                               "direct_score": statistics.mean(values)})
    direct_ci = stratified_ci(direct_sources, "direct_score", 850256)
    changed_rows = [row for row in candidate if int(row.get("action_change_calls", 0)) > 0]
    trigger_sources = {row["source_id"] for row in changed_rows}
    trigger_regimes = {row["first_shop"] for row in changed_rows}
    checks = {
        "pou_at_least_1pp": summary["pou_pp"] >= 1.0,
        "pou_ci_lower_positive": summary["pou_95ci_pp"][0] > 0,
        "panel_score_at_least_52pct": summary["candidate_panel_score"] >= 0.52,
        "panel_ci_lower_above_50pct": summary["panel_score_95ci"][0] > 0.50,
        "direct_parent_score_at_least_50pct": family_score["v76"] >= 0.50,
        "direct_parent_ci_lower_at_least_48pct": direct_ci[0] >= 0.48,
        "every_original_score_at_least_48pct": min(family_score.values()) >= 0.48,
        "every_original_delta_at_least_minus_2pp": min(100 * (family_score[f] - family_parent[f]) for f in OPPONENTS) >= -2.0,
        "positive_flips_exceed_negative": summary["positive_zero_negative"][0] > summary["positive_zero_negative"][2],
        "mcu_positive_and_ci_lower_positive": summary["pou_pp"] > 0 and summary["pou_95ci_pp"][0] > 0,
        "trigger_sources_at_least_8": len(trigger_sources) >= 8,
        "trigger_regimes_at_least_2": len(trigger_regimes) >= 2,
        "zero_errors_integrity_safety": summary["error_count"] == 0 and summary["task_keys_unique"] and summary["safety_violations"] == 0,
    }
    return {"candidate_score_by_opponent": family_score,
            "parent_score_by_opponent": family_parent,
            "direct_parent_score": family_score["v76"], "direct_parent_score_95ci": direct_ci,
            "mcu_pp": summary["pou_pp"], "mcu_95ci_pp": summary["pou_95ci_pp"],
            "mechanism_trigger_sources": len(trigger_sources),
            "mechanism_trigger_shop_regimes": sorted(trigger_regimes),
            "mechanism_trigger_calls": sum(int(row.get("mechanism_triggers", 0)) for row in candidate),
            "w_t_l": [sum(row["margin"] > 0 for row in candidate),
                       sum(row["margin"] == 0 for row in candidate),
                       sum(row["margin"] < 0 for row in candidate)],
            "hard_gate_checks": checks, "strategy_gate": "PASS" if all(checks.values()) else "FAIL"}


def main():
    if sha256(HERE / "submission.tar.gz") != EXPECTED_ARCHIVE_SHA:
        raise RuntimeError("candidate archive drifted before Confirmation")
    payload = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    sources = payload["sources"]
    if payload.get("phase") != "confirmation" or len(sources) != 256:
        raise RuntimeError("Confirmation manifest violates one-shot protocol")
    tasks = [(mode, family, source, seat) for mode in POLICIES for family in OPPONENTS
             for source in sources for seat in (0, 1)]
    with concurrent.futures.ProcessPoolExecutor(max_workers=min(16, os.cpu_count() or 1)) as pool:
        rows = list(pool.map(play, tasks, chunksize=1))
    games_path = DATA / "confirmation_games.jsonl"
    with games_path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")
    metrics.OPPONENTS = OPPONENTS
    summary = metrics.summarize(rows, sources)
    gates = confirmation_metrics(rows, sources, summary)
    result = {"schema": "kaggriculture-loop-confirmation-v1",
              "model_id": "v85_fertilizer_substitution_moe", "engine": str(kagsim.ENGINE_VERSION),
              "candidate_archive_sha256": EXPECTED_ARCHIVE_SHA,
              "source_manifest_sha256": sha256(SOURCE_MANIFEST), "games_sha256": sha256(games_path),
              "source_count": len(sources), "originality_panel": list(OPPONENTS),
              "summary": summary, "confirmation": gates}
    (DATA / "confirmation_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "confirmation_summary.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
