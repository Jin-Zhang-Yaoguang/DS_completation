#!/usr/bin/env python3
"""Mine top-five routes that are prefix-compatible with the V21 opening."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import sys
from pathlib import Path

try:
    import orjson
except ImportError:  # pragma: no cover - stdlib fallback remains portable.
    orjson = None


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
MODEL = PROJECT / "model"
V19 = MODEL / "v19_hierarchical_moe"
V21 = MODEL / "v21_top_meta_moe"
DATA = PROJECT / "model_data" / "v17_rc1_online_2026-08-27"
sys.path[:0] = [str(V21), str(V19)]

from top_route_panel import HIER, route_actions


_TOP_TEAMS: set[str] = set()
_DEFAULT_ACTIONS: list[dict] = []
_LUCAS_ACTIONS: list[dict] = []


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def first_shop(replay: dict, seat: int) -> str:
    for pair in replay.get("steps", []):
        obs = pair[seat].get("observation") or {}
        shops = list(((obs.get("town") or {}).get("unlocked_shops") or []))
        if shops:
            return str(shops[0])
    return "NO_SHOP"


def init_worker(top_teams, default, lucas) -> None:
    global _TOP_TEAMS, _DEFAULT_ACTIONS, _LUCAS_ACTIONS
    _TOP_TEAMS = set(top_teams)
    _DEFAULT_ACTIONS = default
    _LUCAS_ACTIONS = lucas


def analyze_path(path_string: str) -> dict:
    path = Path(path_string)
    try:
        replay = orjson.loads(path.read_bytes()) if orjson is not None else json.loads(path.read_text(encoding="utf-8"))
        names = [str(value) for value in replay["info"]["TeamNames"]]
        episode = int(path.name.split("-")[1])
        rows = []
        for seat, team in enumerate(names):
            if team not in _TOP_TEAMS:
                continue
            actions = [pair[seat].get("action") or {} for pair in replay["steps"][1:720]]
            if len(actions) != 719:
                continue
            rewards = [float(pair.get("reward") or 0) for pair in replay["steps"][-1]]
            prefix_exact = {str(step): sum(actions[i] == _DEFAULT_ACTIONS[i] for i in range(step)) for step in (72, 144, 216)}
            suffix_exact_lucas = sum(actions[i] == _LUCAS_ACTIONS[i] for i in range(216, 719))
            suffix_exact_default = sum(actions[i] == _DEFAULT_ACTIONS[i] for i in range(216, 719))
            rows.append({
                "team": team, "episode": episode, "seat": seat, "first_shop": first_shop(replay, seat),
                "reward": rewards[seat], "opponent_reward": rewards[1 - seat], "margin": rewards[seat] - rewards[1 - seat],
                "won": rewards[seat] > rewards[1 - seat],
                "action_sha256": hashlib.sha256(canonical(actions)).hexdigest(),
                "prefix_exact": prefix_exact,
                "prefix_exact_rate_216": prefix_exact["216"] / 216,
                "suffix_exact_lucas_216": suffix_exact_lucas,
                "suffix_diff_lucas_216": 503 - suffix_exact_lucas,
                "suffix_exact_default_216": suffix_exact_default,
            })
        return {"rows": rows}
    except Exception as exc:
        return {"error": {"path": str(path), "error": repr(exc)}}


def main() -> int:
    blueprint = json.loads((DATA / "report" / "top5_replication_blueprint.json").read_text(encoding="utf-8"))
    top_teams = {str(row["team"]) for row in blueprint["submissions"]}
    default = HIER._ROUTES["default"]
    lucas = route_actions("lucaskna_high")
    paths = sorted((DATA / "top5_leaderboard_replays").glob("episode-*-replay.json"))
    rows = []
    errors = []
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=min(8, max(1, os.cpu_count() or 1)),
        initializer=init_worker,
        initargs=(tuple(top_teams), default, lucas),
    ) as pool:
        for result in pool.map(analyze_path, map(str, paths), chunksize=2):
            rows.extend(result.get("rows") or [])
            if result.get("error"):
                errors.append(result["error"])
    eligible = [
        row for row in rows
        if row["first_shop"] != "YARN_STORE"
        and row["prefix_exact"]["216"] >= 175
        and row["suffix_diff_lucas_216"] >= 120
    ]
    eligible.sort(key=lambda row: (row["prefix_exact"]["216"], row["won"], row["margin"], row["reward"], row["suffix_diff_lucas_216"]), reverse=True)
    # Keep one evidence-rich representative per team/shop/action tape.
    selected = []
    seen = set()
    for row in eligible:
        key = (row["team"], row["first_shop"], row["action_sha256"])
        if key in seen:
            continue
        seen.add(key)
        selected.append(row)
        if len(selected) >= 80:
            break
    result = {
        "schema": "kaggriculture-v25-prefix-compatible-route-catalog-v1",
        "status": "MINING_ONLY_NOT_EVALUATION",
        "source_replays": len(paths),
        "perspectives": len(rows), "eligible": len(eligible), "selected": len(selected),
        "thresholds": {"prefix_exact_216_min": 175, "suffix_diff_lucas_216_min": 120, "exclude_first_shop": "YARN_STORE"},
        "top_teams": sorted(top_teams), "candidates": selected, "errors": errors,
    }
    (HERE / "compatible_route_catalog.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**{k: result[k] for k in ("source_replays", "perspectives", "eligible", "selected")}, "top20": selected[:20]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
