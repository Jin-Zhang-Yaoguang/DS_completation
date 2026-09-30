"""Audit effective neural interventions against the frozen V1 executor."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import numpy as np
import main
import base_agent


def normalized(action):
    action = action or {}
    return {"farmer": list(action.get("farmer") or ["PASS"]), "hands": [list(x or ["PASS"]) for x in action.get("hands", [])], "market": [list(x or []) for x in action.get("market", [])]}


def run(seeds, output):
    from kaggle_environments import make
    rows = []
    changed = 0
    calls = 0
    errors = 0
    macro_decisions = 0
    nondefault_macros = 0
    neural_days = 0
    for seed in seeds:
        for seat in (0, 1):
            env = make("kaggriculture", configuration={"seed": int(seed)}, debug=False)
            env.reset(2)
            for step in range(719):
                env.state[0].observation.step = step
                env.state[1].observation.step = step
                candidate = main.agent(env.state[seat].observation)
                baseline = base_agent.agent(env.state[seat].observation)
                calls += 1
                if int(env.state[seat].observation.get("hour", step % 24) or 0) == 0:
                    macro_decisions += 1
                    state_macro = main._GAME[seat].get("macro", main.DEFAULT_MACRO)
                    if not np.array_equal(state_macro[1:], main.DEFAULT_MACRO[1:]):
                        nondefault_macros += 1
                    if main._GAME[seat].get("neural_enabled"):
                        neural_days += 1
                if normalized(candidate) != normalized(baseline):
                    changed += 1
                    if len(rows) < 20:
                        rows.append({"seed": int(seed), "seat": seat, "step": step, "candidate": copy.deepcopy(normalized(candidate)), "baseline": copy.deepcopy(normalized(baseline))})
                actions = [candidate, base_agent.agent(env.state[1 - seat].observation)] if seat == 0 else [base_agent.agent(env.state[1 - seat].observation), candidate]
                try:
                    env.step(actions)
                except Exception:
                    errors += 1
                    break
            if [str(state.status) for state in env.state] != ["DONE", "DONE"]:
                errors += 1
    result = {"schema": "kaggriculture-ppo-v2-action-audit-1", "seeds": len(seeds), "games": len(seeds) * 2, "candidate_calls": calls, "actual_action_changes": changed, "actual_action_change_rate": changed / max(1, calls), "macro_decisions": macro_decisions, "nondefault_macro_decisions": nondefault_macros, "nondefault_macro_rate": nondefault_macros / max(1, macro_decisions), "neural_days": neural_days, "errors": errors, "examples": rows, "gates": {"zero_errors": errors == 0, "change_rate_ge_5pct": changed / max(1, calls) >= 0.05}}
    Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-start", type=int, default=93000000)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "action_audit_report.json")
    args = parser.parse_args()
    print(json.dumps(run([args.seed_start + i * 101 for i in range(args.seeds)], args.output), ensure_ascii=False, indent=2))
