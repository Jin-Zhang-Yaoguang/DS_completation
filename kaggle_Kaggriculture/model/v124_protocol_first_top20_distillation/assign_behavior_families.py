#!/usr/bin/env python3
"""按可观测闭环行为指纹分族，并为 purged nested CV 写入组标签。"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans, SpectralClustering
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


HERE = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=HERE / "dataset")
    return parser.parse_args()


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def aggregate_team_fingerprints(rows: list[dict], teams: set[str]) -> tuple[list[str], list[str], np.ndarray, dict[str, int]]:
    chosen = [row for row in rows if str(row["team"]) in teams]
    feature_names = sorted(
        name for name in chosen[0]["fingerprint"]
        if "money_delta" not in name
    )
    vectors: dict[str, list[np.ndarray]] = defaultdict(list)
    episode_counts: Counter = Counter()
    for row in chosen:
        team = str(row["team"])
        vectors[team].append(np.asarray([float(row["fingerprint"].get(name, 0.0)) for name in feature_names]))
        episode_counts[team] += 1
    names = sorted(vectors)
    matrix = np.vstack([np.mean(vectors[name], axis=0) for name in names])
    return names, feature_names, matrix, dict(episode_counts)


def choose_clustering(
    names: list[str], matrix: np.ndarray, episode_counts: dict[str, int],
    k_values: range, min_teams: int, min_episodes: int,
) -> tuple[dict[str, int], dict]:
    scaled = StandardScaler().fit_transform(matrix)
    candidates: list[dict] = []
    for method in ("kmeans", "spectral_nearest_neighbors"):
        for k in k_values:
            if k >= len(names):
                continue
            if method == "kmeans":
                labels = KMeans(n_clusters=k, random_state=124, n_init=64).fit_predict(scaled)
            else:
                labels = SpectralClustering(
                    n_clusters=k,
                    random_state=124,
                    assign_labels="cluster_qr",
                    affinity="nearest_neighbors",
                    n_neighbors=min(8, len(names) - 1),
                ).fit_predict(scaled)
            team_support = Counter(int(v) for v in labels)
            episode_support: Counter = Counter()
            for name, label in zip(names, labels, strict=True):
                episode_support[int(label)] += int(episode_counts[name])
            admissible = min(team_support.values()) >= min_teams and min(episode_support.values()) >= min_episodes
            candidates.append({
                "method": method,
                "k": k,
                "silhouette": float(silhouette_score(scaled, labels)),
                "minimum_team_support": min(team_support.values()),
                "minimum_episode_support": min(episode_support.values()),
                "team_support": {str(key): value for key, value in sorted(team_support.items())},
                "episode_support": {str(key): value for key, value in sorted(episode_support.items())},
                "admissible": bool(admissible),
                "labels": [int(v) for v in labels],
            })
    admissible = [item for item in candidates if item["admissible"]]
    if not admissible:
        raise RuntimeError(f"没有满足支持度要求的行为分族: {candidates}")
    winner = max(admissible, key=lambda item: (item["silhouette"], -item["k"]))
    mapping = {name: label for name, label in zip(names, winner["labels"], strict=True)}
    public_candidates = [{k: v for k, v in item.items() if k != "labels"} for item in candidates]
    return mapping, {
        "selected_method": winner["method"],
        "selected_k": winner["k"],
        "selected_silhouette": winner["silhouette"],
        "candidates": public_candidates,
    }


def canonicalize(mapping: dict[str, int], prefix: str) -> dict[str, str]:
    members: dict[int, list[str]] = defaultdict(list)
    for team, label in mapping.items():
        members[label].append(team)
    ordered = sorted(members, key=lambda label: tuple(sorted(members[label])))
    rename = {old: f"{prefix}_{index:02d}" for index, old in enumerate(ordered)}
    return {team: rename[label] for team, label in mapping.items()}


def main() -> int:
    args = parse_args()
    dataset = args.dataset.resolve()
    daily = read_jsonl(dataset / "daily_contract.jsonl")
    fingerprints = read_jsonl(dataset / "trajectory_fingerprints.jsonl")
    trajectory_rows = daily[::30]
    teachers = {str(row["teacher"]) for row in trajectory_rows}
    opponents = {str(row["opponent"]) for row in trajectory_rows}
    all_profiled = {str(row["team"]) for row in fingerprints}
    if not teachers.issubset(all_profiled) or not opponents.issubset(all_profiled):
        raise ValueError("教师或对手缺少行为指纹")

    teacher_names, teacher_features, teacher_matrix, teacher_episodes = aggregate_team_fingerprints(
        [row for row in fingerprints if row["role"] == "teacher"], teachers,
    )
    teacher_raw, teacher_report = choose_clustering(
        teacher_names, teacher_matrix, teacher_episodes, range(3, 6), min_teams=3, min_episodes=8,
    )
    teacher_mapping = canonicalize(teacher_raw, "teacher_family")

    opponent_names, opponent_features, opponent_matrix, opponent_episodes = aggregate_team_fingerprints(
        fingerprints, opponents,
    )
    opponent_raw, opponent_report = choose_clustering(
        opponent_names, opponent_matrix, opponent_episodes, range(4, 9), min_teams=2, min_episodes=4,
    )
    opponent_mapping = canonicalize(opponent_raw, "opponent_family")

    enriched: list[dict] = []
    for row in daily:
        enriched.append({
            **row,
            "teacher_family": teacher_mapping[str(row["teacher"])],
            "opponent_family": opponent_mapping[str(row["opponent"])],
        })
    write_jsonl(dataset / "daily_contract_families.jsonl", enriched)

    episode_teacher_families: dict[tuple[int, str], set[str]] = defaultdict(set)
    for row in enriched[::30]:
        episode_teacher_families[(int(row["episode_id"]), str(row["replay_sha256"]))].add(str(row["teacher_family"]))
    multi_family_episodes = {
        str(episode): sorted(families)
        for (episode, _), families in episode_teacher_families.items() if len(families) > 1
    }
    teacher_support = Counter(row["teacher_family"] for row in enriched[::30])
    opponent_support = Counter(row["opponent_family"] for row in enriched[::30])
    report = {
        "schema": "kaggriculture-v124-behavior-family-audit-v1",
        "status": "BEHAVIOR_FAMILIES_READY_FOR_PURGED_NESTED_CV",
        "fingerprint_policy": {
            "closed_loop_actions_only": True,
            "outcome_money_fields_excluded_from_clustering": True,
            "fingerprints_enter_runtime": False,
            "random_state": 124,
        },
        "teacher": {
            **teacher_report,
            "feature_count": len(teacher_features),
            "team_count": len(teacher_names),
            "mapping": dict(sorted(teacher_mapping.items())),
            "trajectory_support": dict(sorted(teacher_support.items())),
        },
        "opponent": {
            **opponent_report,
            "feature_count": len(opponent_features),
            "team_count": len(opponent_names),
            "mapping": dict(sorted(opponent_mapping.items())),
            "trajectory_support": dict(sorted(opponent_support.items())),
        },
        "purge_contract": {
            "unit": "episode_id+replay_sha256",
            "multi_teacher_family_episode_count": len(multi_family_episodes),
            "multi_teacher_family_episodes": multi_family_episodes,
            "rule": "when a family is held out, every row from its episode is removed from training",
        },
    }
    (dataset / "behavior_family_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps({
        "teacher_families": teacher_report["selected_k"],
        "opponent_families": opponent_report["selected_k"],
        "teacher_support": dict(sorted(teacher_support.items())),
        "opponent_support": dict(sorted(opponent_support.items())),
        "multi_family_episodes_to_purge": len(multi_family_episodes),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
