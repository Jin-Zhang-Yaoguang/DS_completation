#!/usr/bin/env python3
"""OOF probe: can public market shocks identify the opponent's prior trade direction?"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
PROJECT = MODEL.parent
CPPSIM = MODEL / "community_research/2026-08-26/live_cli/external_repos/kaggriculture-cppsim"
CACHE = HERE / "predictive_probe_arrays.npz"

REPLAY = PROJECT / "model_data/v17_rc1_online_2026-08-27/top5_leaderboard_replays/episode-100458412-replay.json"
OPPONENTS = {
    "v20": MODEL / "v20_demand_timing_moe/main.py",
    "v21": MODEL / "v21_top_meta_moe/main.py",
    "v32": MODEL / "v32_clone_horizon_preempt/main.py",
    "v54": MODEL / "v54_terminal_water_bypass/main.py",
    "v66": MODEL / "v66_margin_gated_sell_bubble/main.py",
    "v76": MODEL / "v76_adjacent_safe_buy_lead/main.py",
}
ITEMS = ("WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER")
SHOPS = ("BAKERY", "BRUNCH_SPOT", "FARMERS_MARKET", "ICE_CREAM_SHOP", "PET_CAFE", "PIZZA_SHOP", "SMOOTHIE_SHOP", "YARN_STORE")
SEEDS = tuple(range(97101, 97113))


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def source_actions():
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    seat = replay["info"]["TeamNames"].index("lucaskna")
    return [pair[seat].get("action") or {} for pair in replay["steps"][1:720]]


def signed_market(action, item):
    value = 0
    first_slot = 10
    for slot, order in enumerate((action or {}).get("market", []) or []):
        if len(order) < 3 or str(order[1]) != item:
            continue
        if order[0] == "SELL":
            value += max(0, int(order[2] or 0))
            first_slot = min(first_slot, slot)
        elif order[0] == "BUY_PRODUCT":
            value -= max(0, int(order[2] or 0))
            first_slot = min(first_slot, slot)
    return value, first_slot


def collect():
    sys.path.insert(0, str(sorted((CPPSIM / "build").glob("lib.*"))[-1]))
    import kagsim  # type: ignore
    route = source_actions()
    rows = []
    for family, path in OPPONENTS.items():
        for seed in SEEDS:
            for seat in (0, 1):
                rival = load(path, f"v97_{family}_{seed}_{seat}")
                game = kagsim.Game(seed)
                while not game.done:
                    step = game.step_count
                    before = game.observe(seat)
                    own = route[step]
                    opponent = rival.agent(game.observe(1 - seat))
                    actions = [None, None]
                    actions[seat], actions[1 - seat] = own, opponent
                    game.step(actions[0], actions[1])
                    after = game.observe(seat)
                    before_inv = before["market"]["inventory"]
                    after_inv = after["market"]["inventory"]
                    before_prices = before["market"]["prices"]
                    after_prices = after["market"]["prices"]
                    unlocked = set(before["town"]["unlocked_shops"])
                    for item_index, item in enumerate(ITEMS):
                        own_signed, own_slot = signed_market(own, item)
                        rival_signed, _ = signed_market(opponent, item)
                        label = 1 if rival_signed > 0 else -1 if rival_signed < 0 else 0
                        features = [
                            int(after_inv[item]) - int(before_inv[item]),
                            int(after_prices[item]) - int(before_prices[item]),
                            own_signed,
                            own_slot,
                            item_index,
                            seat,
                            step % 4,
                            step % 24,
                            int(step % 4 == 0),
                            int(step % 24 == 0),
                            *[int(shop in unlocked) for shop in SHOPS],
                        ]
                        rows.append((features, label, seed, family, seat, step, item))
    return rows


def evaluate(x, y, groups):
    from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score
    from sklearn.model_selection import GroupKFold
    from sklearn.tree import DecisionTreeClassifier
    predictions = np.zeros_like(y)
    ablation_predictions = np.zeros_like(y)
    folds = []
    for fold, (train, valid) in enumerate(GroupKFold(n_splits=4).split(x, y, groups), 1):
        model = DecisionTreeClassifier(max_depth=6, min_samples_leaf=100, class_weight="balanced", random_state=9700 + fold)
        ablation = DecisionTreeClassifier(max_depth=6, min_samples_leaf=100, class_weight="balanced", random_state=9800 + fold)
        model.fit(x[train], y[train])
        ablation.fit(x[train, 2:], y[train])
        predictions[valid] = model.predict(x[valid])
        ablation_predictions[valid] = ablation.predict(x[valid, 2:])
        folds.append({"fold": fold, "train_seeds": sorted(set(groups[train].tolist())), "valid_seeds": sorted(set(groups[valid].tolist()))})
    majority = int(np.bincount(y + 1).argmax() - 1)
    majority_predictions = np.full_like(y, majority)
    return {
        "rows": len(y),
        "class_counts": {str(label): int(np.sum(y == label)) for label in (-1, 0, 1)},
        "oof_balanced_accuracy": balanced_accuracy_score(y, predictions),
        "ablation_balanced_accuracy": balanced_accuracy_score(y, ablation_predictions),
        "majority_balanced_accuracy": balanced_accuracy_score(y, majority_predictions),
        "oof_macro_f1": f1_score(y, predictions, average="macro"),
        "confusion_matrix_labels_minus1_0_1": confusion_matrix(y, predictions, labels=[-1, 0, 1]).tolist(),
        "folds": folds,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--collect-only", action="store_true")
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    if args.collect_only:
        rows = collect()
        np.savez_compressed(
            CACHE,
            x=np.asarray([row[0] for row in rows], dtype=np.float32),
            y=np.asarray([row[1] for row in rows], dtype=np.int8),
            groups=np.asarray([row[2] for row in rows], dtype=np.int64),
        )
        print(json.dumps({"cache": str(CACHE), "rows": len(rows)}, ensure_ascii=False))
        return
    if args.analyze_only:
        arrays = np.load(CACHE)
        x, y, groups = arrays["x"], arrays["y"], arrays["groups"]
    else:
        rows = collect()
        x = np.asarray([row[0] for row in rows], dtype=np.float32)
        y = np.asarray([row[1] for row in rows], dtype=np.int8)
        groups = np.asarray([row[2] for row in rows], dtype=np.int64)
    metrics = evaluate(x, y, groups)
    gate = bool(
        metrics["oof_balanced_accuracy"] >= metrics["majority_balanced_accuracy"] + 0.05
        and metrics["oof_balanced_accuracy"] >= metrics["ablation_balanced_accuracy"] + 0.05
    )
    payload = {
        "schema": "kaggriculture-v97-market-impact-predictive-probe-v1",
        "status": "SYNTHETIC_PRECONSTRUCTION_NOT_MODEL_EVIDENCE",
        "engine": "1.32.7",
        "synthetic_seed_range": [min(SEEDS), max(SEEDS)],
        "games": len(OPPONENTS) * len(SEEDS) * 2,
        "features_are_public_at_next_call": True,
        "opponent_actions_used_as_offline_labels_only": True,
        "official_replay_sources_consumed": 0,
        "metrics": metrics,
        "gate": "PASS_PREDICTIVE_PROBE" if gate else "REJECT_PREDICTIVE_PROBE",
    }
    (HERE / "predictive_probe_results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
