#!/usr/bin/env python3
"""V124：purged nested CV 训练多教师合同 HMoE，并与 BestFixed 比较。"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import ExtraTreesRegressor


HERE = Path(__file__).resolve().parent
SIGNED_TARGETS = {"money_delta", "rival_money_delta", "money_gap_delta"}
EXPERT_DOMAINS = (
    "crop_flow", "livestock_cycle", "market_liquidity",
    "land_labor_capacity", "recovery", "terminal_liquidation",
)
FULL_CONFIGS = (
    {
        "name": "regularized_6expert",
        "router_estimators": 64, "router_depth": 10, "router_leaf": 18,
        "expert_estimators": 48, "expert_depth": 14, "expert_leaf": 8,
        "pooled_blend": 0.20,
    },
    {
        "name": "adaptive_6expert",
        "router_estimators": 72, "router_depth": 14, "router_leaf": 10,
        "expert_estimators": 56, "expert_depth": 18, "expert_leaf": 4,
        "pooled_blend": 0.15,
    },
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=HERE / "dataset")
    parser.add_argument("--output", type=Path, default=HERE / "training")
    parser.add_argument("--quick", action="store_true", help="仅减少树数，用于管线烟测")
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def episode_key(row: dict) -> str:
    return f"{int(row['episode_id'])}:{row['replay_sha256']}"


def target_domain(name: str) -> str:
    if name.startswith("early_sell_"):
        return "terminal_liquidation"
    if name.startswith("plant_") or "BUY_SEED" in name or name in {
        "unit_PLANT", "unit_WATER", "unit_FERTILIZE", "unit_DIG", "unit_HARVEST",
    }:
        return "crop_flow"
    if "BUY_ANIMAL" in name or name in {
        "unit_BUILD_PASTURE", "unit_BUILD_COOP", "unit_PLACE", "unit_FEED",
        "unit_CARE", "unit_COLLECT_FERTILIZER",
    }:
        return "livestock_cycle"
    if name.startswith("sell_") or name.startswith("market_BUY_PRODUCT") or name in {
        "market_SELL", "money_delta", "rival_money_delta", "money_gap_delta",
    }:
        return "market_liquidity"
    if name in {
        "market_HIRE", "market_BUY_LAND", "moves", "idle", "productive",
        "productive_share", "unit_decisions", "mean_task_distance", "center_task_share",
    }:
        return "land_labor_capacity"
    if name in {"unit_PICKUP", "unit_DROP"}:
        return "recovery"
    return "recovery"


def arrays(rows: list[dict]) -> dict[str, Any]:
    feature_names = sorted({name for row in rows for name in row["features"]})
    all_target_names = sorted({name for row in rows for name in row["target"]})
    x = np.asarray([[float(row["features"].get(name, 0.0)) for name in feature_names] for row in rows])
    y_all = np.asarray([[float(row["target"].get(name, 0.0)) for name in all_target_names] for row in rows])
    active = np.std(y_all, axis=0) > 1e-9
    target_names = [name for name, keep in zip(all_target_names, active, strict=True) if keep]
    y = y_all[:, active]
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("训练数组包含非有限值")
    return {
        "feature_names": feature_names,
        "target_names": target_names,
        "x": x,
        "y": y,
        "days": np.asarray([int(row["decision_day"]) for row in rows]),
        "episodes": np.asarray([episode_key(row) for row in rows]),
        "teachers": np.asarray([str(row["teacher"]) for row in rows]),
        "teacher_families": np.asarray([str(row["teacher_family"]) for row in rows]),
        "opponent_families": np.asarray([str(row["opponent_family"]) for row in rows]),
    }


def fit_hmoe(
    x: np.ndarray, y: np.ndarray, target_names: list[str], teachers: np.ndarray,
    episodes: np.ndarray, config: dict, seed: int,
) -> dict:
    domain_columns = {
        domain: [column for column, name in enumerate(target_names) if target_domain(name) == domain]
        for domain in EXPERT_DOMAINS
    }
    if any(not columns for columns in domain_columns.values()):
        raise RuntimeError(f"语义专家缺少目标: {domain_columns}")
    transformed = np.log1p(np.abs(y))
    domain_activity = np.column_stack([
        np.mean(transformed[:, domain_columns[domain]], axis=1)
        for domain in EXPERT_DOMAINS
    ])
    # 各领域原始量纲差异很大；先在训练折内标准化，再映射成软路由，
    # 防止资金/劳动总量天然压过作物、恢复与终局专家。
    center = np.mean(domain_activity, axis=0)
    spread = np.maximum(np.std(domain_activity, axis=0), 1e-6)
    logits = np.clip((domain_activity - center) / spread, -8.0, 8.0)
    logits -= np.max(logits, axis=1, keepdims=True)
    route_target = np.exp(logits)
    route_target /= np.sum(route_target, axis=1, keepdims=True)
    router = ExtraTreesRegressor(
        n_estimators=int(config["router_estimators"]),
        max_depth=int(config["router_depth"]),
        min_samples_leaf=int(config["router_leaf"]),
        max_features="sqrt",
        random_state=seed + 1,
        n_jobs=-1,
    ).fit(x, route_target)
    experts: dict[str, ExtraTreesRegressor] = {}
    support: dict[str, dict] = {}
    shared_support = {
        "rows": int(len(x)),
        "teachers": len(set(teachers.tolist())),
        "episodes": len(set(episodes.tolist())),
    }
    for offset, domain in enumerate(EXPERT_DOMAINS):
        support[domain] = {**shared_support, "target_count": len(domain_columns[domain])}
        if shared_support["teachers"] < 3 or shared_support["episodes"] < 8:
            raise RuntimeError(f"专家 {domain} 支持度不足: {support[domain]}")
        experts[domain] = ExtraTreesRegressor(
            n_estimators=int(config["expert_estimators"]),
            max_depth=int(config["expert_depth"]),
            min_samples_leaf=int(config["expert_leaf"]),
            max_features=0.75,
            random_state=seed + 10 + offset,
            n_jobs=-1,
        ).fit(x, y[:, domain_columns[domain]])
    pooled = ExtraTreesRegressor(
        n_estimators=int(config["expert_estimators"]),
        max_depth=int(config["expert_depth"]),
        min_samples_leaf=int(config["expert_leaf"]),
        max_features=0.75,
        random_state=seed + 100,
        n_jobs=-1,
    ).fit(x, y)
    return {
        "router": router,
        "experts": experts,
        "pooled": pooled,
        "support": support,
        "domain_columns": domain_columns,
        "mean_route": np.mean(route_target, axis=0),
        "route_activity_center": center,
        "route_activity_spread": spread,
        "config": dict(config),
    }


def predict_hmoe(model: dict, x: np.ndarray, target_names: list[str]) -> np.ndarray:
    route = np.maximum(1e-9, np.asarray(model["router"].predict(x)))
    route /= np.sum(route, axis=1, keepdims=True)
    prediction = np.zeros((len(x), len(target_names)), dtype=float)
    mean_route = np.maximum(1e-9, np.asarray(model["mean_route"]))
    for domain_index, domain in enumerate(EXPERT_DOMAINS):
        columns = model["domain_columns"][domain]
        expert_prediction = np.asarray(model["experts"][domain].predict(x))
        if expert_prediction.ndim == 1:
            expert_prediction = expert_prediction[:, None]
        gate = np.clip(route[:, domain_index] / mean_route[domain_index], 0.5, 1.5)
        prediction[:, columns] = expert_prediction * (0.9 + 0.1 * gate[:, None])
    blend = float(model["config"]["pooled_blend"])
    prediction = (1.0 - blend) * prediction + blend * np.asarray(model["pooled"].predict(x))
    for column, name in enumerate(target_names):
        if name not in SIGNED_TARGETS:
            prediction[:, column] = np.maximum(0.0, prediction[:, column])
    return prediction


def best_fixed(train_y: np.ndarray, train_days: np.ndarray, test_days: np.ndarray) -> np.ndarray:
    global_mean = np.mean(train_y, axis=0)
    by_day = {day: np.mean(train_y[train_days == day], axis=0) for day in sorted(set(train_days.tolist()))}
    return np.vstack([by_day.get(int(day), global_mean) for day in test_days])


def metric_report(y_true: np.ndarray, y_model: np.ndarray, y_fixed: np.ndarray, train_y: np.ndarray, target_names: list[str]) -> dict:
    scale = np.maximum(np.std(train_y, axis=0), 1.0)
    model_by_target = np.mean(np.abs(y_model - y_true), axis=0) / scale
    fixed_by_target = np.mean(np.abs(y_fixed - y_true), axis=0) / scale
    model_loss = float(np.mean(model_by_target))
    fixed_loss = float(np.mean(fixed_by_target))
    domains: dict[str, dict] = {}
    for domain in EXPERT_DOMAINS:
        columns = [i for i, name in enumerate(target_names) if target_domain(name) == domain]
        if not columns:
            continue
        domain_model = float(np.mean(model_by_target[columns]))
        domain_fixed = float(np.mean(fixed_by_target[columns]))
        domains[domain] = {
            "target_count": len(columns),
            "hmoe_normalized_mae": domain_model,
            "best_fixed_normalized_mae": domain_fixed,
            "skill_vs_best_fixed": 1.0 - domain_model / max(domain_fixed, 1e-12),
        }
    return {
        "hmoe_normalized_mae": model_loss,
        "best_fixed_normalized_mae": fixed_loss,
        "skill_vs_best_fixed": 1.0 - model_loss / max(fixed_loss, 1e-12),
        "domains": domains,
    }


def evaluate_split(data: dict, train_mask: np.ndarray, test_mask: np.ndarray, config: dict, seed: int) -> tuple[dict, dict]:
    train_episodes = set(data["episodes"][train_mask].tolist())
    test_episodes = set(data["episodes"][test_mask].tolist())
    overlap = train_episodes.intersection(test_episodes)
    if overlap:
        raise RuntimeError(f"episode purge 失败: {len(overlap)}")
    model = fit_hmoe(
        data["x"][train_mask], data["y"][train_mask], data["target_names"],
        data["teachers"][train_mask], data["episodes"][train_mask], config, seed,
    )
    pred = predict_hmoe(model, data["x"][test_mask], data["target_names"])
    fixed = best_fixed(data["y"][train_mask], data["days"][train_mask], data["days"][test_mask])
    report = metric_report(
        data["y"][test_mask], pred, fixed, data["y"][train_mask], data["target_names"],
    )
    report.update({
        "train_rows": int(train_mask.sum()),
        "test_rows": int(test_mask.sum()),
        "train_episodes": len(train_episodes),
        "test_episodes": len(test_episodes),
        "episode_overlap": 0,
        "expert_support": model["support"],
    })
    route = np.asarray(model["router"].predict(data["x"][test_mask]))
    primary = np.argmax(route, axis=1)
    report["router_primary_use"] = {
        domain: int(np.sum(primary == index))
        for index, domain in enumerate(EXPERT_DOMAINS)
    }
    report["router_experts_used"] = sum(value > 0 for value in report["router_primary_use"].values())
    return report, model


def purged_masks(data: dict, holdout_axis: str, holdout_value: str, allowed_mask: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    base = np.ones(len(data["x"]), dtype=bool) if allowed_mask is None else allowed_mask.copy()
    axis_values = data[holdout_axis]
    holdout_rows = base & (axis_values == holdout_value)
    holdout_episodes = set(data["episodes"][holdout_rows].tolist())
    test_mask = holdout_rows
    train_mask = base & np.asarray([episode not in holdout_episodes for episode in data["episodes"]])
    return train_mask, test_mask


def inner_select(data: dict, base_mask: np.ndarray, configs: tuple[dict, ...], seed_offset: int) -> tuple[dict, list[dict]]:
    reports: list[dict] = []
    opponent_families = sorted(set(data["opponent_families"][base_mask].tolist()))
    for config_index, config in enumerate(configs):
        fold_reports: list[dict] = []
        for fold_index, family in enumerate(opponent_families):
            train_mask, dev_mask = purged_masks(data, "opponent_families", family, base_mask)
            report, _ = evaluate_split(
                data, train_mask, dev_mask, config,
                seed=124000 + seed_offset + config_index * 100 + fold_index,
            )
            report["opponent_family"] = family
            fold_reports.append(report)
        mean_skill = float(np.mean([item["skill_vs_best_fixed"] for item in fold_reports]))
        worst_skill = float(min(item["skill_vs_best_fixed"] for item in fold_reports))
        reports.append({
            "config": config["name"],
            "mean_skill_vs_best_fixed": mean_skill,
            "worst_skill_vs_best_fixed": worst_skill,
            "folds": fold_reports,
        })
    winner = max(reports, key=lambda item: (item["mean_skill_vs_best_fixed"], item["worst_skill_vs_best_fixed"]))
    chosen = next(config for config in configs if config["name"] == winner["config"])
    return chosen, reports


def main() -> int:
    args = parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    rows = read_jsonl(args.dataset.resolve() / "daily_contract_families.jsonl")
    data = arrays(rows)
    configs = tuple(dict(item) for item in FULL_CONFIGS)
    if args.quick:
        for config in configs:
            config["router_estimators"] = 8
            config["expert_estimators"] = 8

    outer_reports: list[dict] = []
    teacher_families = sorted(set(data["teacher_families"].tolist()))
    for outer_index, teacher_family in enumerate(teacher_families):
        outer_train, outer_test = purged_masks(data, "teacher_families", teacher_family)
        chosen, inner_reports = inner_select(data, outer_train, configs, seed_offset=outer_index * 1000)
        outer_report, _ = evaluate_split(
            data, outer_train, outer_test, chosen, seed=124500 + outer_index,
        )
        outer_report.update({
            "teacher_family": teacher_family,
            "chosen_by_inner_cv": chosen["name"],
            "inner_cv": inner_reports,
        })
        outer_reports.append(outer_report)
        print(
            f"outer {teacher_family}: config={chosen['name']} skill={outer_report['skill_vs_best_fixed']:.4f}",
            flush=True,
        )

    full_mask = np.ones(len(data["x"]), dtype=bool)
    final_config, full_inner_reports = inner_select(data, full_mask, configs, seed_offset=9000)
    final_model = fit_hmoe(
        data["x"], data["y"], data["target_names"], data["teachers"],
        data["episodes"], final_config, seed=124999,
    )
    artifact = {
        "schema": "kaggriculture-v124-contract-hmoe-model-v1",
        "feature_names": data["feature_names"],
        "target_names": data["target_names"],
        "expert_domains": EXPERT_DOMAINS,
        "model": final_model,
    }
    joblib.dump(artifact, output / "contract_hmoe.joblib", compress=3)

    outer_skills = [item["skill_vs_best_fixed"] for item in outer_reports]
    support_pass = all(
        value["teachers"] >= 3 and value["episodes"] >= 8
        for value in final_model["support"].values()
    )
    router_use_pass = all(item["router_experts_used"] >= 3 for item in outer_reports)
    gate_pass = bool(
        support_pass
        and router_use_pass
        and outer_skills
        and min(outer_skills) > 0.0
        and float(np.median(outer_skills)) >= 0.03
    )
    report = {
        "schema": "kaggriculture-v124-purged-nested-cv-v1",
        "status": "GATE1_PASS_TIME_BLIND_DEFERRED" if gate_pass else "GATE1_FAIL",
        "quick_mode": bool(args.quick),
        "training_rows": len(rows),
        "unique_episodes": len(set(data["episodes"].tolist())),
        "teacher_count": len(set(data["teachers"].tolist())),
        "teacher_family_count": len(teacher_families),
        "opponent_family_count": len(set(data["opponent_families"].tolist())),
        "feature_count": len(data["feature_names"]),
        "active_target_count": len(data["target_names"]),
        "method": {
            "outer": "leave-one-teacher-behavior-family-out",
            "inner": "leave-one-opponent-behavior-family-out",
            "purge": "all rows sharing episode_id+replay_sha256",
            "selection": "inner CV only; outer scores never select final hyperparameters",
            "best_fixed": "training-set mean contract conditioned on exact decision_day",
            "time_blind": "deferred to later-date own-online and separate official-daily panels",
        },
        "configs": list(configs),
        "outer_folds": outer_reports,
        "outer_summary": {
            "skills_vs_best_fixed": outer_skills,
            "minimum": float(min(outer_skills)),
            "median": float(np.median(outer_skills)),
            "all_positive": all(value > 0.0 for value in outer_skills),
        },
        "full_inner_selection": {
            "selected_config": final_config["name"],
            "reports": full_inner_reports,
        },
        "final_expert_support": final_model["support"],
        "gates": {
            "episode_overlap_zero": all(item["episode_overlap"] == 0 for item in outer_reports),
            "all_outer_families_beat_best_fixed": all(value > 0.0 for value in outer_skills),
            "median_outer_skill_at_least_0_03": float(np.median(outer_skills)) >= 0.03,
            "every_expert_has_3_teachers_and_8_episodes": support_pass,
            "at_least_3_router_experts_used_in_every_outer_fold": router_use_pass,
            "time_blind_available_inside_training_data": False,
        },
        "promotion_effect": "NONE; this is training/development evidence only",
    }
    (output / "nested_cv_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "status": report["status"],
        "outer_skills": outer_skills,
        "selected_config": final_config["name"],
        "model_path": str(output / "contract_hmoe.joblib"),
    }, ensure_ascii=False, indent=2))
    return 0 if gate_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
