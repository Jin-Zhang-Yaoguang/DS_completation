"""D1: reproducible qualification for PPO v3's flat expert catalog.

This is deliberately a *gate*, not a training collector.  Each candidate is
measured against the frozen V1 control under the same ``(seed, seat,
opponent)`` cell.  A candidate only becomes eligible for D2 when it changes
deployable actions, finishes every game safely, and is not materially worse
than the V1 control according to the configured paired confidence interval.

The runner keeps the candidate's production action and its V1 baseline action
in separate isolated modules through :class:`catalog.Catalog`.  It therefore
tests the same compiler path used by a router deployment, without importing
``main.py`` or relying on a model weight file.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from action_compiler import ActionCompiler
from catalog import Catalog
from runtime import set_step_for_both_seats


SCHEMA_VERSION = "kaggriculture-ppo-v3-d1-qualification-1"
DEFAULT_EXPERTS = ("M_ANIMAL_HALF_TOPDAYS",)
DEFAULT_OPPONENTS = ("starter", "v1", "forced_low", "forced_high")
_PRODUCTION = frozenset(("E_V1", "E_HIGH"))
_MARKET = frozenset(("M_NONE", "M_ANIMAL_HALF_TOPDAYS"))


def _opponent_agent(opponent_id: str, namespace: str):
    """Return only deterministic opponents with fresh mutable state."""
    catalog = Catalog(namespace + "_catalog")
    if opponent_id in ("v1", "adaptive"):
        return catalog.v1
    if opponent_id == "forced_low":
        return catalog.low
    if opponent_id == "forced_high":
        return catalog.high
    if opponent_id == "starter":
        from kaggle_environments.envs.kaggriculture import kaggriculture as kg

        return kg.starter_agent
    raise ValueError("unsupported deterministic opponent: %s" % opponent_id)


def _animal_count(obs: Mapping[str, Any]) -> int:
    """Count public animals; decreases are a diagnostic, not death proof."""
    player = 1 if int((obs or {}).get("player", 0) or 0) == 1 else 0
    farms = list((obs or {}).get("farms", []) or [])
    farm = farms[player] if player < len(farms) else {}
    count = 0
    for row in list((farm or {}).get("tiles", []) or []):
        for tile in (row if isinstance(row, (list, tuple)) else []):
            # Empty cells and locked cells are respectively None and strings.
            # Only structured tile payloads can own an animal field.
            getter = getattr(tile, "get", None)
            animal = getter("animal", "") if callable(getter) else ""
            count += int(str(animal).upper() in {"COW", "SHEEP", "GOOSE"})
    return count


def _shed_used(obs: Mapping[str, Any]) -> int:
    private = (obs or {}).get("private", {}) or {}
    shed = private.get("shed", {}) if isinstance(private, Mapping) else {}
    if not isinstance(shed, Mapping):
        return 0
    return sum(max(0, int(value or 0)) for value in shed.values())


@dataclass
class SafetyAudit:
    calls: int = 0
    effective_changes: int = 0
    fallback_calls: int = 0
    terminal_guard_calls: int = 0
    malformed_reasons: dict[str, int] = field(default_factory=dict)
    max_shed_used: int = 0
    shed_full_steps: int = 0
    observed_animal_count_decreases: int = 0
    _previous_animals: int | None = None

    def observe(self, obs: Mapping[str, Any], result) -> None:
        self.calls += 1
        self.effective_changes += int(bool(result.effective_intervention))
        self.fallback_calls += int(bool(result.fallback_used))
        self.terminal_guard_calls += int(bool(result.terminal_guard_applied))
        used = _shed_used(obs)
        self.max_shed_used = max(self.max_shed_used, used)
        self.shed_full_steps += int(used >= 100)
        animals = _animal_count(obs)
        if self._previous_animals is not None and animals < self._previous_animals:
            self.observed_animal_count_decreases += self._previous_animals - animals
        self._previous_animals = animals
        for reason in result.reasons:
            # The frozen opening is planned policy, not an error.
            if reason != "opening_frozen":
                self.malformed_reasons[str(reason)] = self.malformed_reasons.get(str(reason), 0) + 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "calls": self.calls,
            "effective_action_changes": self.effective_changes,
            "effective_action_change_rate": self.effective_changes / max(1, self.calls),
            "compiler_fallback_calls": self.fallback_calls,
            "compiler_fallback_rate": self.fallback_calls / max(1, self.calls),
            "terminal_guard_calls": self.terminal_guard_calls,
            "max_shed_used": self.max_shed_used,
            "shed_full_steps": self.shed_full_steps,
            # The environment API does not label removals as deaths.  This is
            # intentionally named as an observation so it cannot be mistaken
            # for a causal mortality counter.
            "observed_animal_count_decreases": self.observed_animal_count_decreases,
            "compiler_nonopening_reasons": dict(sorted(self.malformed_reasons.items())),
        }


class CandidateAgent:
    """Execute a fixed flat expert through the deployment compiler path."""

    def __init__(self, expert_id: str, namespace: str) -> None:
        if expert_id not in _PRODUCTION | _MARKET:
            raise ValueError("unknown catalog expert: %s" % expert_id)
        self.expert_id = expert_id
        self.catalog = Catalog(namespace)
        self.compiler = ActionCompiler()
        self.audit = SafetyAudit()

    def __call__(self, obs: Mapping[str, Any]):
        # Propose every production plan exactly once per observation, matching
        # `main.py`'s shadow-state contract.  It also avoids calling stateful
        # V1 twice when V1 itself is the selected production proposal.
        proposals = {name: self.catalog.production_proposal(name, obs) for name in self.catalog.production_names}
        baseline = proposals["E_V1"]
        production = proposals.get(self.expert_id, baseline) if self.expert_id in _PRODUCTION else baseline
        market_expert, market_proposal = self.catalog.market_proposal(
            self.expert_id if self.expert_id in _MARKET else "M_NONE", obs, production
        )
        result = self.compiler.compile(
            obs,
            baseline_action=baseline.plan.action if baseline.plan is not None else {},
            production=production,
            market_expert=market_expert,
            market=market_proposal,
        )
        self.audit.observe(obs, result)
        return result.action


def _play_one(seed: int, seat: int, expert_id: str, opponent_id: str, mode: str) -> dict[str, Any]:
    """Play one full game.  ``mode`` is candidate or same-cell V1 control."""
    from kaggle_environments import make

    selected = expert_id if mode == "candidate" else "E_V1"
    namespace = "d1_%s_%s_%s_%s_%s_%s" % (os.getpid(), mode, selected, opponent_id, seed, seat)
    candidate = CandidateAgent(selected, namespace + "_candidate")
    opponent = _opponent_agent(opponent_id, namespace + "_opponent")
    env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
    env.reset(2)
    for step in range(719):
        set_step_for_both_seats(env, step)
        own_action = candidate(env.state[seat].observation)
        other_action = opponent(env.state[1 - seat].observation)
        env.step([own_action, other_action] if seat == 0 else [other_action, own_action])
    statuses = [str(state.status) for state in env.state]
    if statuses != ["DONE", "DONE"]:
        raise RuntimeError({"seed": seed, "seat": seat, "expert": expert_id, "mode": mode, "statuses": statuses})
    rewards = [float(state.reward or 0.0) for state in env.state]
    margin = rewards[seat] - rewards[1 - seat]
    return {
        "seed": int(seed), "seat": int(seat), "expert_id": expert_id, "opponent_id": opponent_id,
        "mode": mode, "candidate_coins": rewards[seat], "opponent_coins": rewards[1 - seat],
        "coin_margin": margin, "score": 1.0 if margin > 0 else 0.5 if margin == 0 else 0.0,
        "safety": candidate.audit.as_dict(), "statuses": statuses,
    }


def _task(task):
    return _play_one(**task)


def bootstrap_ci(values: Iterable[float], *, seed: int = 911, rounds: int = 4000) -> list[float]:
    values = np.asarray(list(values), dtype=np.float64)
    if not len(values):
        return [float("nan"), float("nan")]
    rng = np.random.default_rng(int(seed))
    samples = np.empty(int(rounds), dtype=np.float64)
    for start in range(0, int(rounds), 500):
        size = min(500, int(rounds) - start)
        samples[start:start + size] = values[rng.integers(0, len(values), size=(size, len(values)))].mean(axis=1)
    return [float(np.quantile(samples, 0.025)), float(np.quantile(samples, 0.975))]


def _mean_safety(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    safety = [row["safety"] for row in rows]
    calls = sum(int(item["calls"]) for item in safety)
    return {
        "calls": calls,
        "effective_action_changes": sum(int(item["effective_action_changes"]) for item in safety),
        "effective_action_change_rate": sum(int(item["effective_action_changes"]) for item in safety) / max(1, calls),
        "compiler_fallback_calls": sum(int(item["compiler_fallback_calls"]) for item in safety),
        "compiler_fallback_rate": sum(int(item["compiler_fallback_calls"]) for item in safety) / max(1, calls),
        "terminal_guard_calls": sum(int(item["terminal_guard_calls"]) for item in safety),
        "max_shed_used": max([int(item["max_shed_used"]) for item in safety] or [0]),
        "shed_full_steps": sum(int(item["shed_full_steps"]) for item in safety),
        "observed_animal_count_decreases": sum(int(item["observed_animal_count_decreases"]) for item in safety),
        "compiler_nonopening_reasons": {
            reason: sum(int(item["compiler_nonopening_reasons"].get(reason, 0)) for item in safety)
            for reason in sorted({reason for item in safety for reason in item["compiler_nonopening_reasons"]})
        },
    }


def _summary(expert_id: str, candidate: list[Mapping[str, Any]], control: list[Mapping[str, Any]], *, min_change_rate: float, min_ci: float) -> dict[str, Any]:
    control_by_cell = {(row["seed"], row["seat"], row["opponent_id"]): row for row in control}
    paired = []
    for row in candidate:
        reference = control_by_cell[(row["seed"], row["seat"], row["opponent_id"])]
        paired.append({
            "seed": row["seed"], "seat": row["seat"], "opponent_id": row["opponent_id"],
            "score_delta": float(row["score"] - reference["score"]),
            "coin_margin_delta": float(row["coin_margin"] - reference["coin_margin"]),
            "candidate_coin_delta": float(row["candidate_coins"] - reference["candidate_coins"]),
        })

    # Bootstrap clusters use both seats of a seed/opponent cell as one unit;
    # that preserves the seat-paired design rather than pretending they are
    # independent games.
    clusters = {}
    for row in paired:
        clusters.setdefault((row["seed"], row["opponent_id"]), []).append(row)
    clustered = [{key: float(np.mean([item[key] for item in values])) for key in ("score_delta", "coin_margin_delta", "candidate_coin_delta")} for values in clusters.values()]
    safety = _mean_safety(candidate)
    score_delta = [row["score_delta"] for row in clustered]
    margin_delta = [row["coin_margin_delta"] for row in clustered]
    coin_delta = [row["candidate_coin_delta"] for row in clustered]
    by_opponent = {}
    for opponent_id in sorted({row["opponent_id"] for row in candidate}):
        subset = [row for row in paired if row["opponent_id"] == opponent_id]
        by_opponent[opponent_id] = {
            "games": len(subset),
            "candidate_score_rate": float(np.mean([row["score"] for row in candidate if row["opponent_id"] == opponent_id])),
            "v1_control_score_rate": float(np.mean([row["score"] for row in control if row["opponent_id"] == opponent_id])),
            "score_delta": float(np.mean([row["score_delta"] for row in subset])),
            "mean_coin_margin_delta": float(np.mean([row["coin_margin_delta"] for row in subset])),
        }
    score_ci = bootstrap_ci(score_delta, seed=311 + sum(map(ord, expert_id)))
    gate = {
        "all_games_done": len(candidate) == len(control) and all(row["statuses"] == ["DONE", "DONE"] for row in candidate + control),
        "action_change_rate_ge_min": safety["effective_action_change_rate"] >= float(min_change_rate),
        "no_compiler_fallback": safety["compiler_fallback_calls"] == 0,
        "paired_score_ci_lower_ge_min": score_ci[0] >= float(min_ci),
    }
    gate["qualified_for_d2"] = bool(all(gate.values()))
    return {
        "expert_id": expert_id,
        "candidate_games": len(candidate),
        "control_games": len(control),
        "paired_clusters": len(clustered),
        "candidate_score_rate": float(np.mean([row["score"] for row in candidate])),
        "v1_control_score_rate": float(np.mean([row["score"] for row in control])),
        "candidate_mean_coin_margin": float(np.mean([row["coin_margin"] for row in candidate])),
        "v1_control_mean_coin_margin": float(np.mean([row["coin_margin"] for row in control])),
        "paired_score_delta": float(np.mean(score_delta)),
        "paired_score_delta_ci95": score_ci,
        "paired_coin_margin_delta": float(np.mean(margin_delta)),
        "paired_coin_margin_delta_ci95": bootstrap_ci(margin_delta, seed=521 + sum(map(ord, expert_id))),
        "paired_candidate_coins_delta": float(np.mean(coin_delta)),
        "paired_candidate_coins_delta_ci95": bootstrap_ci(coin_delta, seed=719 + sum(map(ord, expert_id))),
        "by_opponent": by_opponent,
        "candidate_safety": safety,
        "d2_gate": gate,
        # Full per-game evidence intentionally remains in the JSON report.
        "paired_rows": paired,
    }


def qualify(
    *, experts: Iterable[str] = DEFAULT_EXPERTS, opponents: Iterable[str] = DEFAULT_OPPONENTS,
    seeds: Iterable[int], workers: int = 1, min_change_rate: float = 0.005,
    min_score_ci_lower: float = -0.03,
) -> dict[str, Any]:
    experts, opponents, seeds = tuple(experts), tuple(opponents), tuple(int(seed) for seed in seeds)
    if not experts or not opponents or not seeds:
        raise ValueError("experts, opponents and seeds must be non-empty")
    if any(expert not in _PRODUCTION | _MARKET or expert in {"E_V1", "M_NONE"} for expert in experts):
        raise ValueError("D1 accepts non-default catalog candidates only")
    tasks = [
        {"seed": seed, "seat": seat, "expert_id": expert, "opponent_id": opponent, "mode": mode}
        for expert in experts for opponent in opponents for seed in seeds for seat in (0, 1) for mode in ("candidate", "control")
    ]
    rows: list[dict[str, Any]] = []
    started = time.time()
    if int(workers) <= 1:
        for index, task in enumerate(tasks, 1):
            rows.append(_task(task))
            if index % max(1, len(tasks) // 20) == 0 or index == len(tasks):
                print(json.dumps({"phase": "d1", "completed": index, "games": len(tasks), "games_per_second": index / max(time.time() - started, 1e-9)}), flush=True)
    else:
        with ProcessPoolExecutor(max_workers=int(workers)) as pool:
            futures = [pool.submit(_task, task) for task in tasks]
            for index, future in enumerate(as_completed(futures), 1):
                rows.append(future.result())
                if index % max(1, len(tasks) // 20) == 0 or index == len(tasks):
                    print(json.dumps({"phase": "d1", "completed": index, "games": len(tasks), "games_per_second": index / max(time.time() - started, 1e-9)}), flush=True)
    rows.sort(key=lambda row: (row["expert_id"], row["opponent_id"], row["seed"], row["seat"], row["mode"]))
    summaries = {}
    for expert in experts:
        candidate = [row for row in rows if row["expert_id"] == expert and row["mode"] == "candidate"]
        control = [row for row in rows if row["expert_id"] == expert and row["mode"] == "control"]
        summaries[expert] = _summary(expert, candidate, control, min_change_rate=min_change_rate, min_ci=min_score_ci_lower)
    return {
        "schema": SCHEMA_VERSION,
        "design": "candidate and V1 control share each seed, seat and deterministic opponent cell; bootstrap clusters both seats within seed/opponent",
        "experts": list(experts), "opponents": list(opponents), "seeds": list(seeds), "both_seats": True,
        "games": len(rows), "thresholds": {"min_effective_action_change_rate": min_change_rate, "min_paired_score_ci95_lower": min_score_ci_lower},
        "results": summaries, "rows": rows,
    }


def _seed_values(start: int, count: int) -> list[int]:
    return [int(start) + 7919 * index for index in range(int(count))]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experts", nargs="+", default=list(DEFAULT_EXPERTS))
    parser.add_argument("--opponents", nargs="+", default=list(DEFAULT_OPPONENTS))
    parser.add_argument("--seed-start", type=int, default=98500000)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--min-action-change-rate", type=float, default=0.005)
    parser.add_argument("--min-score-ci-lower", type=float, default=-0.03)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "qualification_d1.json")
    args = parser.parse_args()
    report = qualify(
        experts=args.experts, opponents=args.opponents, seeds=_seed_values(args.seed_start, args.seeds), workers=args.workers,
        min_change_rate=args.min_action_change_rate, min_score_ci_lower=args.min_score_ci_lower,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "qualified": {name: row["d2_gate"]["qualified_for_d2"] for name, row in report["results"].items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
