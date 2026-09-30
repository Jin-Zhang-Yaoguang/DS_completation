"""PPO v3 MoVE Kaggle agent: flat experts, shared safe compilation.

Before a trained Router weight is present the agent is intentionally exactly
V1-equivalent at the decision layer.  A missing/invalid model is a normal
fail-closed condition, not a reason to emit a malformed action.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from action_compiler import ActionCompiler
from catalog import Catalog
from features import encode_observation, get, update_history
from router_numpy import NumpyRouter


HERE = Path(__file__).resolve().parent
MODEL_FILE = HERE / "router_weights.npz"
_POLICY = None
_POLICY_ERROR = None
_GAMES = {0: None, 1: None}
UNCERTAINTY_PENALTY = 1.0


def _seat(obs) -> int:
    return 1 if int(get(obs, "player", 0) or 0) == 1 else 0


def _new_game(player: int):
    game = {
        "catalog": Catalog("ppo_v3_submission_%s" % int(player)),
        "compiler": ActionCompiler(),
        "history": {},
        "previous": (0, 0),
        "production_id": "E_V1",
        "market_id": "M_NONE",
        "last_step": -1,
        "fallback": False,
        "audit": [],
    }
    _GAMES[int(player)] = game
    return game


def _load_router():
    global _POLICY, _POLICY_ERROR
    if _POLICY is None and _POLICY_ERROR is None:
        try:
            _POLICY = NumpyRouter(MODEL_FILE)
        except Exception as exc:  # missing weights remains a safe V1 fallback
            _POLICY_ERROR = repr(exc)
    return _POLICY


def model_status():
    return {"loaded": _POLICY is not None, "error": _POLICY_ERROR, "model_file": str(MODEL_FILE)}


def _choose_index(scores, names, legal, default_name, uncertainty=None):
    """Only choose a non-V1/non-none option with positive conservative score."""
    values = np.asarray(scores, dtype=np.float64)
    eligible = np.asarray(legal, dtype=bool)
    default_index = list(names).index(default_name)
    if values.shape != eligible.shape:
        return default_index
    deviation = np.zeros_like(values) if uncertainty is None else np.asarray(uncertainty, dtype=np.float64)
    if deviation.shape != values.shape:
        return default_index
    masked = np.where(eligible & np.isfinite(values) & np.isfinite(deviation), values - UNCERTAINTY_PENALTY * deviation, -np.inf)
    best = int(np.argmax(masked)) if masked.size else default_index
    if best == default_index or not np.isfinite(masked[best]) or float(masked[best]) <= 0.0:
        return default_index
    return best


def _production_proposals(game, obs):
    catalog = game["catalog"]
    # Every full-plan expert is advanced in shadow.  This preserves its own
    # stateful V1-derived guards if it is selected at the day-3 commitment.
    return {name: catalog.production_proposal(name, obs) for name in catalog.production_names}


def agent(obs):
    player = _seat(obs)
    step = int(get(obs, "step", 0) or 0)
    day = int(get(obs, "day", step // 24) or 0)
    hour = int(get(obs, "hour", step % 24) or 0)
    game = _GAMES.get(player)
    if game is None or step == 0 or step < int(game.get("last_step", -1)):
        game = _new_game(player)
    game["last_step"] = step
    try:
        proposals = _production_proposals(game, obs)
        baseline = proposals["E_V1"]
        if not baseline.eligible or baseline.plan is None:
            raise RuntimeError("V1 baseline unavailable")
        policy = _load_router()
        production_names = game["catalog"].production_names
        market_names = game["catalog"].market_names
        p_scores = np.zeros(len(production_names), dtype=np.float32)
        m_scores = np.zeros(len(market_names), dtype=np.float32)
        p_uncertainty = np.zeros(len(production_names), dtype=np.float32)
        m_uncertainty = np.zeros(len(market_names), dtype=np.float32)
        if hour == 0 and policy is not None:
            features = encode_observation(obs, game["history"], game["previous"])
            model_p_names = tuple(policy.production_names)
            model_m_names = tuple(policy.market_names)
            raw_p, raw_m, _, raw_p_std, raw_m_std = policy.predict_with_uncertainty(features)
            if model_p_names == production_names and model_m_names == market_names:
                p_scores, m_scores, p_uncertainty, m_uncertainty = raw_p, raw_m, raw_p_std, raw_m_std
            else:
                # A catalog/weight mismatch is an OOD condition, never a
                # positional reinterpretation of learned expert IDs.
                game["fallback"] = True

        # Production is a full-plan commitment after the frozen opening.  It
        # is selected once at step 72, not arbitrarily switched every hour.
        if step == 72 and not game["fallback"]:
            legal = [bool(proposals[name].eligible and proposals[name].plan is not None) for name in production_names]
            selected = _choose_index(p_scores, production_names, legal, "E_V1", p_uncertainty)
            game["production_id"] = production_names[selected]
        selected_production = proposals.get(game["production_id"], baseline)
        if not selected_production.eligible or selected_production.plan is None:
            selected_production = baseline
            game["production_id"] = "E_V1"
            game["fallback"] = True

        if hour == 0 and day >= 3 and not game["fallback"]:
            legal = [True]
            candidates = [(None, None)]
            for name in market_names[1:]:
                expert, proposal = game["catalog"].market_proposal(name, obs, selected_production)
                candidates.append((expert, proposal))
                legal.append(bool(proposal is not None and proposal.eligible))
            chosen = _choose_index(m_scores, market_names, legal, "M_NONE", m_uncertainty)
            game["market_id"] = market_names[chosen]
            game["previous"] = (production_names.index(game["production_id"]), chosen)
            game["history"] = update_history(obs)
        elif hour == 0:
            game["previous"] = (production_names.index(game["production_id"]), 0)
            game["history"] = update_history(obs)

        # The selected daily residual is applied to every hourly action in
        # that day, rather than disappearing after the hour-0 action.
        market_expert, market_proposal = game["catalog"].market_proposal(
            game["market_id"], obs, selected_production
        )

        result = game["compiler"].compile(
            obs,
            baseline_action=baseline.plan.action,
            production=selected_production,
            market_expert=market_expert,
            market=market_proposal,
        )
        game["audit"].append(result.audit_row())
        return result.action
    except Exception:
        # The final failure closure is a pass-shaped valid action.  Normal
        # model failures generally take the V1 path above and do not reach it.
        farm = get(obs, "farms", []) or []
        own = farm[player] if player < len(farm) else {}
        return {"farmer": ["PASS"], "hands": [["PASS"] for _ in (get(own, "hands", []) or [])], "market": []}


# File-agent loader convention: keep the public callable as the last callable.
submission_agent = agent
agent = submission_agent
