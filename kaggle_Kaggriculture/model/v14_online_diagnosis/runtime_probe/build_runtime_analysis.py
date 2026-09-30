"""把 V14 runtime probe、官方 episode 元数据和 leaderboard 快照汇成诊断结论。"""

from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import statistics
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROBE = HERE / "runtime_probe.json"
V14_EPISODES = ROOT / "raw" / "v14" / "episodes_full.json"
A2_EPISODES = ROOT / "raw" / "a2" / "episodes_full.json"
SNAPSHOT = ROOT / "raw" / "snapshot" / "current_snapshot.json"
LEADERBOARD = ROOT / "raw" / "snapshot" / "kaggriculture_public_leaderboard.csv"
OUTPUT_JSON = HERE / "runtime_analysis.json"
OUTPUT_MD = HERE / "runtime_analysis.md"
V14_SUBMISSION = 55722630
A2_SUBMISSION = 55713355


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def outcome(margin: float) -> str:
    return "W" if margin > 0 else "L" if margin < 0 else "T"


def public_rows(path: Path, submission_id: int) -> list[dict[str, Any]]:
    result = []
    for episode in load(path):
        if episode.get("type") != "EPISODE_TYPE_PUBLIC":
            continue
        ours = [
            row for row in episode.get("agents", [])
            if int(row.get("submissionId", -1)) == submission_id
        ]
        if len(ours) != 1:
            continue
        us = ours[0]
        opponents = [
            row for row in episode.get("agents", [])
            if int(row.get("index", -1)) != int(us["index"])
        ]
        if len(opponents) != 1:
            continue
        opponent = opponents[0]
        margin = float(us["reward"]) - float(opponent["reward"])
        result.append(
            {
                "episode_id": str(episode["id"]),
                "candidate_seat": int(us["index"]),
                "candidate_reward": float(us["reward"]),
                "opponent_reward": float(opponent["reward"]),
                "margin": margin,
                "outcome": outcome(margin),
                "opponent_submission_id": int(opponent["submissionId"]),
                "opponent_team_id": int(opponent["teamId"]),
                "opponent_team_name": str(opponent["teamName"]),
            }
        )
    return result


def leaderboard_scores() -> dict[int, float]:
    with LEADERBOARD.open("r", encoding="utf-8-sig", newline="") as handle:
        return {
            int(row["TeamId"]): float(row["Score"])
            for row in csv.DictReader(handle)
        }


def schedule_summary(rows: list[dict[str, Any]], scores: Mapping[int, float]) -> dict[str, Any]:
    mapped = []
    for row in rows:
        value = scores.get(row["opponent_team_id"])
        if value is not None:
            row["opponent_current_score"] = value
            mapped.append(value)
    counts = Counter(row["outcome"] for row in rows)
    bins = {}
    for lower, upper in ((0, 1000), (1000, 1500), (1500, 2000), (2000, 2500), (2500, 4000)):
        selected = [
            row for row in rows
            if lower <= float(row.get("opponent_current_score", -1)) < upper
        ]
        wins = sum(row["outcome"] == "W" for row in selected)
        bins[f"{lower}-{upper}"] = {
            "games": len(selected),
            "wins": wins,
            "win_rate": wins / len(selected) if selected else None,
        }
    by_seat = {}
    for seat in (0, 1):
        selected = [row for row in rows if row["candidate_seat"] == seat]
        seat_counts = Counter(row["outcome"] for row in selected)
        by_seat[str(seat)] = {
            "games": len(selected),
            "wins_ties_losses": [seat_counts["W"], seat_counts["T"], seat_counts["L"]],
            "pure_win_rate": seat_counts["W"] / len(selected) if selected else None,
            "mean_margin": (
                statistics.mean(row["margin"] for row in selected) if selected else None
            ),
        }
    return {
        "games": len(rows),
        "wins_ties_losses": [counts["W"], counts["T"], counts["L"]],
        "pure_win_rate": counts["W"] / len(rows) if rows else None,
        "mean_margin": statistics.mean(row["margin"] for row in rows) if rows else None,
        "unique_opponent_submissions": len({row["opponent_submission_id"] for row in rows}),
        "unique_opponent_teams": len({row["opponent_team_id"] for row in rows}),
        "by_candidate_seat": by_seat,
        "opponent_current_score": {
            "mapped_games": len(mapped),
            "mean": statistics.mean(mapped) if mapped else None,
            "median": statistics.median(mapped) if mapped else None,
            "minimum": min(mapped) if mapped else None,
            "maximum": max(mapped) if mapped else None,
            "bins": bins,
            "caveat": "Leaderboard score is the current snapshot, not necessarily the rating at match time.",
        },
    }


def step_bins(values: list[int]) -> dict[str, int]:
    return {
        "0": sum(value == 0 for value in values),
        "1-71": sum(1 <= value <= 71 for value in values),
        "72-95": sum(72 <= value <= 95 for value in values),
        "96-143": sum(96 <= value <= 143 for value in values),
        "144+": sum(value >= 144 for value in values),
    }


def main() -> None:
    probe = load(PROBE)
    snapshot = load(SNAPSHOT)
    scores = leaderboard_scores()
    v14_rows = public_rows(V14_EPISODES, V14_SUBMISSION)
    a2_rows = public_rows(A2_EPISODES, A2_SUBMISSION)
    probe_by_id = {row["episode_id"]: row for row in probe["episodes"]}
    if set(probe_by_id) != {row["episode_id"] for row in v14_rows}:
        raise ValueError("runtime probe does not cover the exact 87 V14 public episodes")

    calls = sum(row["selected_probe"]["calls"] for row in probe["episodes"])
    parent_differences = sum(
        row["selected_probe"]["recorded_candidate_exact_parent_a2"]["different_steps"]
        for row in probe["episodes"]
    )
    reorder_steps = sum(
        int(row["selected_probe"]["final_diagnostics"].get("reordered_steps", 0) or 0)
        for row in probe["episodes"]
    )
    reorder_games = [
        row for row in probe["episodes"]
        if int(row["selected_probe"]["final_diagnostics"].get("reordered_steps", 0) or 0) > 0
    ]
    exact_parent_games = [
        row for row in probe["episodes"]
        if row["selected_probe"]["recorded_candidate_exact_parent_a2"]["different_steps"] == 0
    ]
    first_identity = [
        int(row["selected_probe"]["recorded_opponent_exact_a2"]["first_mismatch_step"])
        for row in probe["episodes"]
    ]
    first_fault = [
        int(row["selected_probe"]["first_shadow_fault_step"])
        for row in probe["episodes"]
    ]
    wrong_current_shadow = sum(
        len(row["selected_probe"]["reorder_with_wrong_current_shadow_steps"])
        for row in probe["episodes"]
    )
    update_errors = sum(
        int(row["selected_probe"]["final_diagnostics"].get("shadow_update_errors", 0) or 0)
        for row in probe["episodes"]
    )
    intervention_checks = [
        check
        for row in probe["episodes"]
        for check in row["selected_probe"]["queue_search_verification"][
            "observed_parent_difference_steps_searched"
        ]
    ]
    validation_a2 = probe["validation_benchmark"]["by_anchor"]["v12a2_no_shop_gate"]
    online_reorders_per_game = reorder_steps / len(probe["episodes"])
    local_reorders_per_game = float(validation_a2["mean_reordered_steps"])

    v14_schedule = schedule_summary(v14_rows, scores)
    a2_schedule = schedule_summary(a2_rows, scores)
    common_submissions = sorted(
        {row["opponent_submission_id"] for row in v14_rows}
        & {row["opponent_submission_id"] for row in a2_rows}
    )
    common_teams = sorted(
        {row["opponent_team_id"] for row in v14_rows}
        & {row["opponent_team_id"] for row in a2_rows}
    )

    loss_rows = []
    v14_meta = {row["episode_id"]: row for row in v14_rows}
    for episode in probe["episodes"]:
        if episode["outcome"] != "L":
            continue
        selected = episode["selected_probe"]
        meta = v14_meta[episode["episode_id"]]
        loss_rows.append(
            {
                "episode_id": episode["episode_id"],
                "opponent_team": meta["opponent_team_name"],
                "opponent_submission_id": meta["opponent_submission_id"],
                "opponent_current_score": scores.get(meta["opponent_team_id"]),
                "candidate_seat": episode["candidate_seat"],
                "rewards": episode["rewards"],
                "margin": episode["margin"],
                "first_opponent_a2_action_mismatch_step": selected[
                    "recorded_opponent_exact_a2"
                ]["first_mismatch_step"],
                "first_public_shadow_fault_step": selected["first_shadow_fault_step"],
                "opponent_a2_action_matches": selected["recorded_opponent_exact_a2"]["matches"],
                "parent_a2_action_differences": selected[
                    "recorded_candidate_exact_parent_a2"
                ]["different_steps"],
                "reorder_steps": selected["reorder_steps"],
                "reorder_with_wrong_current_shadow_steps": selected[
                    "reorder_with_wrong_current_shadow_steps"
                ],
                "shadow_trusted_at_end": selected["final_diagnostics"]["shadow_trusted"],
            }
        )
    loss_rows.sort(key=lambda row: int(row["episode_id"]))

    target_scores = snapshot["targets"]
    payload = {
        "schema": "kaggriculture-v14-online-runtime-analysis-1",
        "scope": {
            "v14_public_replays": 87,
            "all_v14_public_replays_downloaded": True,
            "test_access": False,
            "new_games_run": False,
            "strategy_modified": False,
            "submission_performed": False,
        },
        "sources": {
            "runtime_probe": {"path": str(PROBE.resolve()), "sha256": sha256(PROBE)},
            "v14_episodes": {"path": str(V14_EPISODES.resolve()), "sha256": sha256(V14_EPISODES)},
            "a2_episodes": {"path": str(A2_EPISODES.resolve()), "sha256": sha256(A2_EPISODES)},
            "snapshot": {"path": str(SNAPSHOT.resolve()), "sha256": sha256(SNAPSHOT)},
            "leaderboard": {"path": str(LEADERBOARD.resolve()), "sha256": sha256(LEADERBOARD)},
        },
        "score_snapshot": {
            "queried_at_taipei": snapshot["queried_at_taipei"],
            "v14": target_scores["v14"],
            "a2": target_scores["a2"],
            "score_gap_v14_minus_a2": float(target_scores["v14"]["publicScore"])
            - float(target_scores["a2"]["publicScore"]),
        },
        "online_schedule": {
            "v14": v14_schedule,
            "a2": a2_schedule,
            "common_opponent_submissions": common_submissions,
            "common_opponent_teams": common_teams,
            "opponent_current_score_mean_gap_v14_minus_a2": (
                v14_schedule["opponent_current_score"]["mean"]
                - a2_schedule["opponent_current_score"]["mean"]
            ),
            "paired_online_comparison_available": False,
        },
        "runtime": {
            "episodes": len(probe["episodes"]),
            "calls": calls,
            "archive_action_path_exact_games": sum(
                row["selected_probe"]["candidate_action_exact"]["matches"]
                == row["selected_probe"]["calls"]
                for row in probe["episodes"]
            ),
            "exact_a2_opponent_games": probe["aggregate"]["exact_a2_opponent_games"],
            "opponent_exact_a2_action_matches": sum(
                row["selected_probe"]["recorded_opponent_exact_a2"]["matches"]
                for row in probe["episodes"]
            ),
            "opponent_exact_a2_action_rate": probe["aggregate"]["opponent_action_exact_a2_rate"],
            "first_opponent_a2_action_mismatch": {
                "median_step": statistics.median(first_identity),
                "maximum_step": max(first_identity),
                "bins": step_bins(first_identity),
            },
            "first_public_shadow_fault": {
                "median_step": statistics.median(first_fault),
                "maximum_step": max(first_fault),
                "bins": step_bins(first_fault),
                "trusted_at_end_games": probe["aggregate"]["games_shadow_trusted_at_end"],
                "untrusted_at_end_games": probe["aggregate"]["games_shadow_untrusted_at_end"],
            },
            "parent_a2_equivalence": {
                "exact_action_games": len(exact_parent_games),
                "games_with_any_difference": len(probe["episodes"]) - len(exact_parent_games),
                "equal_action_calls": calls - parent_differences,
                "different_action_calls": parent_differences,
                "equal_action_rate": (calls - parent_differences) / calls,
            },
            "queue_best_response": {
                "games_with_reorder": len(reorder_games),
                "reorder_steps": reorder_steps,
                "reorder_call_rate": reorder_steps / calls,
                "reorders_with_wrong_current_shadow": wrong_current_shadow,
                "intervention_search_checks": len(intervention_checks),
                "all_intervention_search_checks_exact": all(
                    row["expected_exact"] for row in intervention_checks
                ),
                "shadow_update_errors": update_errors,
                "outcomes_in_reorder_games": dict(Counter(row["outcome"] for row in reorder_games)),
                "reorder_episode_ids": [row["episode_id"] for row in reorder_games],
            },
            "loss_attribution": {
                "losses": len(loss_rows),
                "losses_exact_parent_a2_all_719_calls": sum(
                    row["parent_a2_action_differences"] == 0 for row in loss_rows
                ),
                "losses_with_v14_action_difference": sum(
                    row["parent_a2_action_differences"] > 0 for row in loss_rows
                ),
                "rows": loss_rows,
            },
        },
        "local_vs_online_mechanism": {
            "local_exact_a2_confirmatory": validation_a2,
            "online_reorders_per_game": online_reorders_per_game,
            "local_reorders_per_game": local_reorders_per_game,
            "activation_ratio_online_div_local": online_reorders_per_game / local_reorders_per_game,
            "local_activation_multiple_over_online": local_reorders_per_game / online_reorders_per_game,
        },
        "conclusions": [
            "The 74.5% local figure is conditional on an exact A2 opponent; the online pool contains zero exact-A2 games.",
            "The 2026-08-18..20 holdout supplied unseen environment seeds, but closed-loop opponents were still fixed A2/r002; it held out stochastic scenarios, not opponent-policy lineages.",
            "V14 and A2 did not face any identical opponent submission, so their public ratings are not a paired comparison.",
            "V14 matched parent A2 on 62543/62553 calls; 20/21 losses are action-for-action parent A2 losses, not Q2b regressions.",
            "The anti-A2 mechanism activated only 10 times online versus 2600 times in 200 local A2 games, a roughly 113x per-game activation gap.",
            "Current opponent-score mapping shows V14 received a much weaker schedule and therefore its losses, especially versus low-rated teams, are much more costly under rating updates.",
            "One loss contains one verified reorder, but the current shadow action was correct and immediate predicted advantage was positive; the replay alone cannot identify its counterfactual terminal effect.",
            "A hidden/no-public-effect opponent divergence can be detected late: episode 98371925 first differs from exact A2 at step 175 but public conformance faults only at step 255.",
        ],
    }
    OUTPUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    runtime = payload["runtime"]
    schedule = payload["online_schedule"]
    lines = [
        "# V14 线上得分低于 A2：runtime 归因",
        "",
        "## 结论",
        "",
        "本地 74.5% 是 **对 exact A2 的条件胜率**，不是线上混合对手池胜率。87 场线上局中 exact-A2 对手为 0；V14 只有 10/62,553 个动作不同于父 A2。因此线上分差主要来自不配对的 Elo 对手日程和父 A2 自身对这些策略的表现，不能解释成 Q2b 在同一批对手上输给了 A2。",
        "0818–0820 留出集只提供了未见过的环境 seed，闭环对手仍固定为 A2/r002；它验证了场景外推，没有验证对手谱系外推。",
        "",
        "## 证据",
        "",
        f"- 当前快照：V14 {payload['score_snapshot']['v14']['publicScore']}，A2 {payload['score_snapshot']['a2']['publicScore']}，差 {payload['score_snapshot']['score_gap_v14_minus_a2']:.1f}。",
        f"- V14 线上 66/0/21，A2 线上 41/0/22；共同 opponent submission 为 {len(schedule['common_opponent_submissions'])}，不是同周期同对手检验。",
        f"- V14 seat0 为 39/0/12（{schedule['v14']['by_candidate_seat']['0']['pure_win_rate']:.1%}），seat1 为 27/0/9（{schedule['v14']['by_candidate_seat']['1']['pure_win_rate']:.1%}）；seat 方向不是主要解释。",
        f"- 当前 leaderboard 映射的对手均分：V14 {schedule['v14']['opponent_current_score']['mean']:.1f}，A2 {schedule['a2']['opponent_current_score']['mean']:.1f}；该值是当前快照，只用于刻画日程差异。",
        f"- exact-A2 对手：{runtime['exact_a2_opponent_games']}/87；终局 shadow trusted：{runtime['first_public_shadow_fault']['trusted_at_end_games']}/87。",
        f"- 完全等于父 A2 的局：{runtime['parent_a2_equivalence']['exact_action_games']}/87；逐步等同率：{runtime['parent_a2_equivalence']['equal_action_calls']}/{runtime['calls']} = {runtime['parent_a2_equivalence']['equal_action_rate']:.6%}。",
        f"- 重排：{runtime['queue_best_response']['games_with_reorder']} 局、{runtime['queue_best_response']['reorder_steps']} 步；使用错误当前 shadow 的重排为 {runtime['queue_best_response']['reorders_with_wrong_current_shadow']}。",
        f"- 21 个负局中 {runtime['loss_attribution']['losses_exact_parent_a2_all_719_calls']} 局与父 A2 719/719 相同，只有 {runtime['loss_attribution']['losses_with_v14_action_difference']} 局包含一次 V14 重排。",
        f"- 本地 exact-A2 confirmatory 每局平均重排 {payload['local_vs_online_mechanism']['local_reorders_per_game']:.2f} 次，线上仅 {payload['local_vs_online_mechanism']['online_reorders_per_game']:.4f} 次，激活密度相差 {payload['local_vs_online_mechanism']['local_activation_multiple_over_online']:.1f} 倍。",
        "",
        "## 21 个负局",
        "",
        "| episode | opponent | 当前分 | seat | margin | 首次非A2 | 首次fault | parent差异 | reorder |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in loss_rows:
        lines.append(
            f"| {row['episode_id']} | {row['opponent_team']} | {row['opponent_current_score']} | {row['candidate_seat']} | {row['margin']:.0f} | {row['first_opponent_a2_action_mismatch_step']} | {row['first_public_shadow_fault_step']} | {row['parent_a2_action_differences']} | {row['reorder_steps']} |"
        )
    lines.extend(
        [
            "",
            "## 方法边界",
            "",
            "对手身份用提交包内 exact A2 在对手真实 private observation 上逐步重放判定；V14 shadow 则用自身预测 private state 判定。报告不读取 test、不运行新对局、不修改或提交策略。当前 leaderboard 分数并非每场发生时的历史分数，因此只能证明日程明显不同，不能精确复原每次 Elo 增减。",
        ]
    )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "json": str(OUTPUT_JSON.resolve()),
                "markdown": str(OUTPUT_MD.resolve()),
                "json_sha256": sha256(OUTPUT_JSON),
                "runtime": payload["runtime"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
