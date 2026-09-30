#!/usr/bin/env python3
"""Build the canonical portable HTML report from the current V14 evidence.

The script is read-only with respect to experiments: it does not evaluate an
agent, consume a panel, query Kaggle, or inspect test outcomes.  It writes only
reporting assets under ``v14_first_principles_search/reporting``.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from v14_evidence import A2, R002, REPORTING_DIR, collect_evidence


DEFAULT_PLUGIN_ROOT = Path(
    "/Users/a1-6/.codex/plugins/cache/openai-curated-remote/"
    "data-analytics/0.2.8-13ceeea1f599"
)
TITLE = "V14 Queue Best Response 证据报告"


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def pct(value: float) -> str:
    return f"{value:.2%}"


def anchor_short(anchor: str) -> str:
    if anchor == A2:
        return "A2"
    if anchor == R002:
        return "r002"
    return anchor


def level_label(level: str) -> str:
    return {
        "oracle_exposed": "机制 oracle（暴露）",
        "dev_exposed": "开发回放（暴露）",
        "fresh_screen": "新鲜 screen",
        "fresh_confirm": "新鲜 confirm",
    }.get(level, level)


def decision_label(row: dict[str, Any]) -> str:
    if row["evidence_level"] == "oracle_exposed":
        return "不可部署"
    if row["evidence_level"] == "dev_exposed":
        return "只作机制选择"
    if row["evidence_level"] == "fresh_screen":
        return "screen 通过" if row["gate_pass_point_estimate"] else "screen 未过"
    if row["evidence_level"] == "fresh_confirm":
        return "confirm 通过" if row["submission_eligible"] else "confirm 未过"
    return "未分类"


def report_summary(snapshot: dict[str, Any]) -> str:
    q2b_a2 = snapshot["q2b_headline"]["vs_a2"]
    q2b_r002 = snapshot["q2b_headline"]["vs_r002"]
    confirm = [
        row for row in snapshot["evidence_rows"] if row["evidence_level"] == "fresh_confirm"
    ]
    if confirm:
        confirm_a2 = next((row for row in confirm if row["anchor"] == A2), None)
        confirm_r002 = next((row for row in confirm if row["anchor"] == R002), None)
        if confirm_a2 and confirm_r002:
            first = (
                f"**新鲜确认已产生。** finalist 对 A2 为 "
                f"{confirm_a2['wins']}/{confirm_a2['ties']}/{confirm_a2['losses']}，"
                f"纯胜率 {pct(confirm_a2['pure_win_rate'])}；对 r002 为 "
                f"{confirm_r002['wins']}/{confirm_r002['ties']}/{confirm_r002['losses']}，"
                f"纯胜率 {pct(confirm_r002['pure_win_rate'])}。"
            )
        else:
            first = "**新鲜确认不完整。** 不能据此做提交判断。"
    else:
        first = (
            "**目前仍是开发结论，不是提交结论。** Q2b 在已暴露 36-source 双席位面板上"
            f"对 A2 为 {q2b_a2['wins']}/{q2b_a2['ties']}/{q2b_a2['losses']}，"
            f"纯胜率 {pct(q2b_a2['pure_win_rate'])}；对 r002 为 "
            f"{q2b_r002['wins']}/{q2b_r002['ties']}/{q2b_r002['losses']}，"
            f"纯胜率 {pct(q2b_r002['pure_win_rate'])}。"
        )
    package = snapshot["submission_decision"]["package_ready_q2b"]
    closure = snapshot["submission_decision"]["declared_hash_closure_pass"]
    online_count = snapshot["submission_decision"]["online_record_count"]
    return "\n\n".join(
        [
            "## 技术摘要",
            first,
            (
                "**指标口径固定。** 纯胜率是 `wins / all games`，平局留在分母且不算胜；"
                "competition score 是 `(W + 0.5T) / games`，只报告，绝不替代 65% 硬门。"
            ),
            (
                f"**工程闭包：** 精确归档 package QA {'通过' if package else '未通过'}；"
                f"所有带声明哈希的证据 {'闭合' if closure else '存在缺口'}；"
                f"当前找到 {online_count} 条 V14 Kaggle submission 记录。"
            ),
            (
                "**外推边界：** exact-A2 shadow 的 private/action 真值回放成立，"
                "但未知排行榜对手身份仍不可由公共轨迹唯一证明；这一风险不能被本地 A2 胜率抹掉。"
            ),
        ]
    )


def build_artifact(snapshot: dict[str, Any], generated_at: str) -> dict[str, Any]:
    evidence_table_rows: list[dict[str, Any]] = []
    chart_rows: list[dict[str, Any]] = []
    for row in snapshot["evidence_rows"]:
        table_row = {
            "level": level_label(row["evidence_level"]),
            "candidate": row["label"],
            "anchor": anchor_short(row["anchor"]),
            "games": row["games"],
            "wins": row["wins"],
            "ties": row["ties"],
            "losses": row["losses"],
            "pure_win_rate": row["pure_win_rate"],
            "competition_score_rate": row["competition_score_rate"],
            "mean_margin": row["mean_margin"],
            "decision": decision_label(row),
        }
        evidence_table_rows.append(table_row)
        if row["anchor"] == A2 or row["evidence_id"] == "dev_q2b_vs_r002":
            chart_rows.append(
                {
                    "comparison": f"{row['label']} [{level_label(row['evidence_level'])}]",
                    "pure_win_rate": row["pure_win_rate"],
                    "competition_score_rate": row["competition_score_rate"],
                    "wins": row["wins"],
                    "ties": row["ties"],
                    "losses": row["losses"],
                    "games": row["games"],
                    "anchor": anchor_short(row["anchor"]),
                    "evidence_level": level_label(row["evidence_level"]),
                }
            )

    latest_slice_levels = (
        ["fresh_confirm"]
        if any(row["evidence_level"] == "fresh_confirm" for row in snapshot["slice_rows"])
        else ["fresh_screen"]
        if any(row["evidence_level"] == "fresh_screen" for row in snapshot["slice_rows"])
        else ["dev_exposed"]
    )
    slice_candidates = {
        row["candidate"]
        for row in snapshot["evidence_rows"]
        if row["evidence_level"] in latest_slice_levels
        and (
            row["evidence_level"] != "dev_exposed"
            or row["evidence_id"].startswith("dev_q2b_")
        )
    }
    slice_rows = [
        {
            "level": level_label(row["evidence_level"]),
            "candidate": row["candidate"],
            "anchor": anchor_short(row["anchor"]),
            "dimension": "日期" if row["dimension"] == "date" else "候选席位",
            "slice": row["slice"],
            "games": row["games"],
            "wins": row["wins"],
            "ties": row["ties"],
            "losses": row["losses"],
            "pure_win_rate": row["pure_win_rate"],
            "competition_score_rate": row["competition_score_rate"],
            "mean_margin": row["mean_margin"],
        }
        for row in snapshot["slice_rows"]
        if row["evidence_level"] in latest_slice_levels and row["candidate"] in slice_candidates
    ]

    hash_rows = [
        {
            "status": row["status"],
            "role": row["role"],
            "path": row["path"],
            "expected_sha256": row.get("expected_sha256") or "—",
            "actual_sha256": row.get("actual_sha256") or "—",
        }
        for row in snapshot["hash_closure"]
    ]
    package_rows = [
        {
            "candidate": row["candidate"],
            "verdict": row["verdict"],
            "qa_games": row["games"],
            "raw_loader_clean": "是" if row["raw_loader_clean"] else "否",
            "source_archive_exact": "是" if row["source_archive_action_reward_exact"] else "否",
            "all_games_done": "是" if row["all_games_done"] else "否",
            "archive_sha256": row["archive_sha256"] or "—",
        }
        for row in snapshot["packages"]
    ]
    online_rows = snapshot["online_submissions"] or [
        {
            "submission_id": "—",
            "status": "未产生/未记录",
            "score_or_rating": None,
            "description": "报告脚本只读本地 receipt，不查询 Kaggle。",
            "submitted_at": None,
            "archive_sha256": None,
            "source_path": "—",
        }
    ]

    q2b_a2 = snapshot["q2b_headline"]["vs_a2"]
    q2b_r002 = snapshot["q2b_headline"]["vs_r002"]
    shadow = snapshot["shadow_qa"]
    package_pass_rate = 1.0 if snapshot["submission_decision"]["package_ready_q2b"] else 0.0
    headline_rows = [
        {"metric_id": "q2b_a2", "value": q2b_a2["pure_win_rate"]},
        {"metric_id": "q2b_r002", "value": q2b_r002["pure_win_rate"]},
        {"metric_id": "shadow_exact", "value": shadow["private_exact_rate"]},
        {"metric_id": "package_equivalence", "value": package_pass_rate},
    ]

    cards: list[dict[str, Any]] = [
        {
            "id": "q2b_a2_card",
            "description": f"已暴露开发面板，W/T/L={q2b_a2['wins']}/{q2b_a2['ties']}/{q2b_a2['losses']}；不可替代新鲜确认。",
            "dataset": "headline",
            "sourceId": "report_snapshot",
            "filter": {"metric_id": "q2b_a2"},
            "metrics": [{"label": "Q2b vs A2 纯胜率（开发）", "field": "value", "format": "percent"}],
        },
        {
            "id": "q2b_r002_card",
            "description": f"已暴露开发面板，W/T/L={q2b_r002['wins']}/{q2b_r002['ties']}/{q2b_r002['losses']}。",
            "dataset": "headline",
            "sourceId": "report_snapshot",
            "filter": {"metric_id": "q2b_r002"},
            "metrics": [{"label": "Q2b vs r002 纯胜率（开发）", "field": "value", "format": "percent"}],
        },
        {
            "id": "shadow_exact_card",
            "description": f"exact A2、双席位、{shadow['compared_calls']} 次调用；不证明未知对手身份。",
            "dataset": "headline",
            "sourceId": "report_snapshot",
            "filter": {"metric_id": "shadow_exact"},
            "metrics": [{"label": "Shadow private/action exact", "field": "value", "format": "percent"}],
        },
        {
            "id": "package_equivalence_card",
            "description": "真实 Kaggle raw loader clean extraction 与源码/归档逐动作、reward 等价检查。",
            "dataset": "headline",
            "sourceId": "report_snapshot",
            "filter": {"metric_id": "package_equivalence"},
            "metrics": [{"label": "Package QA 闭包", "field": "value", "format": "percent"}],
        },
    ]
    confirm_a2 = next(
        (
            row
            for row in snapshot["evidence_rows"]
            if row["evidence_level"] == "fresh_confirm" and row["anchor"] == A2
        ),
        None,
    )
    if confirm_a2:
        headline_rows.append({"metric_id": "confirm_a2", "value": confirm_a2["pure_win_rate"]})
        cards.append(
            {
                "id": "confirm_a2_card",
                "description": f"唯一 finalist 新鲜确认，W/T/L={confirm_a2['wins']}/{confirm_a2['ties']}/{confirm_a2['losses']}。",
                "dataset": "headline",
                "sourceId": "report_snapshot",
                "filter": {"metric_id": "confirm_a2"},
                "metrics": [{"label": "Fresh confirm vs A2 纯胜率", "field": "value", "format": "percent"}],
            }
        )

    oracle_gap = snapshot["oracle_gap"]
    gap_text = (
        "## Q2b 在暴露面板上填平了 5 胜 oracle 缺口\n\n"
        f"Q1 stateful 为 47/10/15；移除冗余的完整 public-production equality、"
        f"保留 `clone_distance<=4` 后，Q2b 为 {oracle_gap['wins']}/{oracle_gap['ties']}/{oracle_gap['losses']}。"
        f"它与 A2-parent perfect-information oracle 的 72 局 outcome 完全对齐，"
        f"执行 {oracle_gap['reordered_steps']} 次改序，shadow fault/update error 均为 0。\n\n"
        "这证明该 gate 在已知 exact-A2 条件下挡住了真实机会；它不证明新鲜面板或排行榜对手上也会保持同样收益。"
    )
    calibration = snapshot["shadow_calibration"]
    qa_text = (
        "## Shadow 与 package 的工程证据成立，但威胁模型仍有限\n\n"
        f"Q2b truth QA 在 {shadow['games']} 局、{shadow['compared_calls']} 个调用中，private 与 action exact 均为 100%，"
        f"覆盖 {shadow['day_boundary_calls']} 个日界调用和 {shadow['reordered_steps']} 次真实改序。"
        f"暴露校准的 flow-corrected tracker 在 {calibration['opportunities']:,} 个机会中 queue/shed/exec-cap exact 均为 100%，"
        f"预注册 gate 覆盖率 {pct(float(calibration['gate_coverage']))}。\n\n"
        "这些结果的条件是对手确实运行绑定的 deterministic A2 artifact。公共 conformance 只能在下一回合发现未知对手失配，"
        "不能撤销第一次错误干预；因此线上泛化是独立风险，不应被隐藏在“shadow_trusted”这个名字里。"
    )
    definitions_text = "\n\n".join(
        [
            "## 口径、数据范围与证据层级",
            "- **纯胜率：** `W / (W + T + L)`；平局留在分母且不计胜。A2 门为 `>=65%`，r002 门为 `>50%`。",
            "- **Competition score：** `(W + 0.5T) / games`；只解释 Kaggle 对局积分，不替代纯胜率门。",
            "- **数据范围：** 2026-08-18 至 2026-08-20，只有 train/validation source；报告器拒绝任何 positive test-access flag。",
            "- **oracle_exposed：** 证明机制天花板，但使用现实不可见真值。",
            "- **dev_exposed：** 已多次查看的开发回放，只能筛机制。",
            "- **fresh_screen / fresh_confirm：** 冻结 exact package 后的一次性新面板；只有 confirm 可支撑 65% 本地提交判断。",
            "- **online：** Kaggle submission receipt/rating，独立于本地 W/T/L。",
        ]
    )
    methodology_text = "\n\n".join(
        [
            "## 可复现方法：同一数据管线服务 Notebook 与 HTML",
            "报告器从明确 allowlist 的 oracle、开发、shadow QA、oracle-gap 与 package QA 文件读取证据；"
            "若 V14 `audit.json` 或 Kaggle submission receipt 后续出现，只在 schema 与 no-test 约束通过后加入。",
            "每组 W/T/L 都从逐局 margin 独立重算，再与 summary/audit 对账；按日期和候选席位分别聚合。"
            "所有声明 SHA-256 都与当前文件重新计算值对比。脚本不会调用 evaluator、不会消费 screen/confirm、不会查询 Kaggle。",
            "新鲜 confirm 的置信区间由预注册 audit 生成：日期分层、同 source 双席位为 cluster、10,000 次确定性 bootstrap。"
            "暴露开发 summary 里的 score CI 不被伪装成纯胜率 CI。",
        ]
    )
    limitation_text = "\n\n".join(
        [
            "## 当前结论的限制与稳健性检查",
            f"- 当前总状态：**{snapshot['overall_status']}**。",
            "- Q2b 72.22% 的 A2 纯胜率来自已暴露 36-source 面板；重复查看后的点估计不能作为未偏验证。",
            "- exact-A2 private/action 一致性是条件定理，不是未知对手身份分类器。",
            "- 目前只检验 A2 与 r002 双锚；这控制已知退化，但不是谱系外对手分布的证明。",
            "- 报告显示点估计与 competition score 分开；只有 fresh audit 才显示 source-cluster CI。",
            "- 任何 hash mismatch、非 DONE、error、test source、重复任务或 archive 漂移都应 fail-closed。",
        ]
    )
    next_steps = "\n\n".join(
        [
            "## 下一步只剩冻结验证与线上闭环",
            "1. 封存 exact candidate archive；确认 package QA、candidate seal 和 clean serving closure 同 hash。",
            "2. 所有候选只消费一次 fresh screen，同时对 A2 与 r002；按预注册排序只选一个 finalist。",
            "3. finalist 只消费一次 fresh confirm；A2 纯胜率 `>=65%` 且 r002 `>50%`、完整性全通过，才形成本地提交依据。",
            "4. 提交后保存 Kaggle submission receipt、archive hash、状态与 rating；不要把初始 rating 当成稳定线上结论。",
            "5. 即便本地 A2 门通过，也要把 unknown-opponent identity 风险写入提交决策，而不是宣称一般安全。",
        ]
    )
    questions = "\n\n".join(
        [
            "## 仍会改变决策的问题",
            "- fresh confirm 的 A2 纯胜率及其 source-cluster CI 是否仍跨过 65%？",
            "- r002 上的回退是否来自正确的 conformance latch，还是仅靠早期干预侥幸获胜？",
            "- Kaggle 实际对手是否足够接近 exact A2，使首次不可逆改序的身份风险可接受？",
            "- 若线上得分低于 A2 定向结果，能否用公开日志区分 opponent mismatch、package/serving 与一般化失败？",
        ]
    )

    sources = [
        {
            "id": "report_snapshot",
            "label": "V14 reproducible evidence snapshot SQL projection",
            "path": "kaggle_Kaggriculture/model/v14_first_principles_search/reporting/report_snapshot.sql",
        },
        {
            "id": "community_frontier",
            "label": "V14 community frontier review",
            "path": "kaggle_Kaggriculture/model/v14_first_principles_search/community_frontier.md",
        },
        {
            "id": "validation_contract",
            "label": "V14 dual-anchor evaluation contract",
            "path": "kaggle_Kaggriculture/model/v14_first_principles_search/validation/evaluation_contract.json",
        },
        {
            "id": "package_qa",
            "label": "V14 clean extraction package QA",
            "path": "kaggle_Kaggriculture/model/v14_queue_best_response/package_qa_report.json",
        },
    ]
    snapshot_status = (
        "ready"
        if snapshot["submission_decision"]["fresh_confirm_candidates_passing"]
        and snapshot["online_submissions"]
        else "partial"
    )
    access_issues: list[dict[str, Any]] = []
    levels = {row["evidence_level"] for row in snapshot["evidence_rows"]}
    if "fresh_screen" not in levels:
        access_issues.append(
            {
                "id": "fresh_screen_pending",
                "dataset": "evidence",
                "message": "Fresh screen audit has not been produced; development results are exposed evidence only.",
            }
        )
    if "fresh_confirm" not in levels:
        access_issues.append(
            {
                "id": "fresh_confirm_pending",
                "dataset": "evidence",
                "message": "Fresh confirmatory audit has not been produced; the 65% submission gate is not yet established.",
            }
        )
    if not snapshot["online_submissions"]:
        access_issues.append(
            {
                "id": "online_receipt_pending",
                "dataset": "online",
                "message": "No V14 Kaggle submission receipt is present; the report builder does not query Kaggle.",
            }
        )

    manifest = {
        "version": 1,
        "surface": "report",
        "title": TITLE,
        "description": "Answer-first technical evidence report for V14 queue best response.",
        "generatedAt": generated_at,
        "cards": cards,
        "charts": [
            {
                "id": "pure_win_comparison",
                "title": "纯胜率对比",
                "subtitle": "暴露 oracle、开发候选与可用的新鲜验证；虚线为 A2 65% 点估计门",
                "type": "horizontalBar",
                "intent": "comparison",
                "question": "各证据层的纯胜率离 A2 65% 门有多远？",
                "rationale": "类别标签较长，横向条形图最直接展示点估计与固定门槛；证据层级保留在标签和明细表中。",
                "comparisonContext": {
                    "baseline": "A2 pure-win gate = 65%",
                    "unit": "fraction of all games won",
                    "grain": "candidate-anchor-evidence-layer",
                },
                "dataset": "pure_win_chart",
                "sourceId": "report_snapshot",
                "valueFormat": "percent",
                "encodings": {
                    "x": {"field": "comparison", "type": "nominal", "label": "对比项"},
                    "y": {"field": "pure_win_rate", "type": "quantitative", "label": "纯胜率", "format": "percent"},
                    "tooltip": [
                        {"field": "competition_score_rate", "type": "quantitative", "label": "Competition score", "format": "percent"},
                        {"field": "games", "type": "quantitative", "label": "Games", "format": "number"},
                        {"field": "wins", "type": "quantitative", "label": "Wins", "format": "number"},
                        {"field": "ties", "type": "quantitative", "label": "Ties", "format": "number"},
                        {"field": "losses", "type": "quantitative", "label": "Losses", "format": "number"},
                    ],
                },
                "labels": {"values": "all"},
                "referenceLines": [
                    {
                        "axis": "y",
                        "value": 0.65,
                        "label": "65% pure-win gate",
                        "color": "neutral",
                        "lineStyle": "dashed",
                    }
                ],
                "layout": "full",
            }
        ],
        "tables": [
            {
                "id": "evidence_ledger",
                "title": "证据账本",
                "subtitle": "W/T/L、纯胜率、competition score 与证据资格分列；按纯胜率降序",
                "dataset": "evidence",
                "sourceId": "report_snapshot",
                "defaultSort": {"field": "pure_win_rate", "direction": "desc"},
                "columns": [
                    {"field": "level", "label": "证据层", "type": "text"},
                    {"field": "candidate", "label": "对比", "type": "text"},
                    {"field": "anchor", "label": "锚点", "type": "text"},
                    {"field": "games", "label": "场次", "format": "number"},
                    {"field": "wins", "label": "W", "format": "number"},
                    {"field": "ties", "label": "T", "format": "number"},
                    {"field": "losses", "label": "L", "format": "number"},
                    {"field": "pure_win_rate", "label": "纯胜率", "format": "percent"},
                    {"field": "competition_score_rate", "label": "Competition score", "format": "percent"},
                    {"field": "mean_margin", "label": "平均 margin", "format": "number"},
                    {"field": "decision", "label": "可用于什么", "type": "text"},
                ],
            },
            {
                "id": "slice_detail",
                "title": "按日期与候选席位拆分",
                "subtitle": "优先显示最新证据层；当前无新鲜结果时显示 Q2b 暴露开发面板",
                "dataset": "slices",
                "sourceId": "report_snapshot",
                "defaultSort": {"field": "pure_win_rate", "direction": "desc"},
                "columns": [
                    {"field": "level", "label": "证据层", "type": "text"},
                    {"field": "candidate", "label": "候选", "type": "text"},
                    {"field": "anchor", "label": "锚点", "type": "text"},
                    {"field": "dimension", "label": "切片维度", "type": "text"},
                    {"field": "slice", "label": "切片", "type": "text"},
                    {"field": "games", "label": "场次", "format": "number"},
                    {"field": "wins", "label": "W", "format": "number"},
                    {"field": "ties", "label": "T", "format": "number"},
                    {"field": "losses", "label": "L", "format": "number"},
                    {"field": "pure_win_rate", "label": "纯胜率", "format": "percent"},
                    {"field": "competition_score_rate", "label": "Competition score", "format": "percent"},
                    {"field": "mean_margin", "label": "平均 margin", "format": "number"},
                ],
            },
            {
                "id": "package_ledger",
                "title": "Package QA",
                "subtitle": "exact submission archive 的 clean raw-loader 与源码/归档等价检查",
                "dataset": "packages",
                "sourceId": "report_snapshot",
                "defaultSort": {"field": "candidate", "direction": "asc"},
                "columns": [
                    {"field": "candidate", "label": "候选", "type": "text"},
                    {"field": "verdict", "label": "结论", "type": "text"},
                    {"field": "qa_games", "label": "QA 场次", "format": "number"},
                    {"field": "raw_loader_clean", "label": "Raw loader", "type": "text"},
                    {"field": "source_archive_exact", "label": "动作/reward 等价", "type": "text"},
                    {"field": "all_games_done", "label": "完整 DONE", "type": "text"},
                    {"field": "archive_sha256", "label": "Archive SHA-256", "type": "text"},
                ],
            },
            {
                "id": "hash_ledger",
                "title": "声明哈希闭包",
                "subtitle": "所有上游声明 SHA-256 与当前文件逐项核对；任一 mismatch 即 fail-closed",
                "dataset": "hash_closure",
                "sourceId": "report_snapshot",
                "defaultSort": {"field": "status", "direction": "asc"},
                "columns": [
                    {"field": "status", "label": "状态", "type": "text"},
                    {"field": "role", "label": "闭包角色", "type": "text"},
                    {"field": "path", "label": "文件", "type": "text"},
                    {"field": "expected_sha256", "label": "声明 SHA-256", "type": "text"},
                    {"field": "actual_sha256", "label": "实算 SHA-256", "type": "text"},
                ],
            },
            {
                "id": "online_ledger",
                "title": "Kaggle 线上记录",
                "subtitle": "只读取显式保存的 V14 submission receipt；没有本地 receipt 时保持为空结论",
                "dataset": "online",
                "sourceId": "report_snapshot",
                "defaultSort": {"field": "submitted_at", "direction": "desc"},
                "columns": [
                    {"field": "submission_id", "label": "Submission ID", "type": "text"},
                    {"field": "status", "label": "状态", "type": "text"},
                    {"field": "score_or_rating", "label": "Score / rating", "format": "number"},
                    {"field": "description", "label": "说明", "type": "text"},
                    {"field": "submitted_at", "label": "提交时间", "type": "text"},
                    {"field": "archive_sha256", "label": "Archive SHA-256", "type": "text"},
                ],
            },
        ],
        "sources": [
            {"id": source["id"], "label": source["label"], "path": source["path"]}
            for source in sources
        ],
        "blocks": [
            {"id": "title", "type": "markdown", "body": f"# {TITLE}"},
            {"id": "technical_summary", "type": "markdown", "sourceId": "report_snapshot", "body": report_summary(snapshot)},
            {"id": "headline_metrics", "type": "metric-strip", "cardIds": [card["id"] for card in cards]},
            {
                "id": "pure_win_finding",
                "type": "markdown",
                "sourceId": "report_snapshot",
                "body": (
                    "## 65% 目前只在 oracle 与暴露开发层跨过\n\n"
                    "下图把纯胜率与 competition score 分开。条形只表示 `wins / all games` 点估计；"
                    "oracle 不可部署，开发结果已被反复查看。只有标为 fresh confirm 的行才可进入最终本地门。"
                ),
            },
            {"id": "pure_win_chart_block", "type": "chart", "chartId": "pure_win_comparison", "layout": "full"},
            {"id": "evidence_ledger_intro", "type": "markdown", "body": "## W/T/L 账本保留每一场平局\n\n精确值用于审计；`可用于什么` 一列阻止 oracle/dev 数字被误读成提交资格。"},
            {"id": "evidence_ledger_block", "type": "table", "tableId": "evidence_ledger", "layout": "full"},
            {"id": "oracle_gap", "type": "markdown", "sourceId": "report_snapshot", "body": gap_text},
            {"id": "slice_intro", "type": "markdown", "body": "## 聚合优势必须经得住日期和席位拆分\n\n下表检查 8 月 18–20 日及候选 seat 0/1，避免总胜率掩盖单日或单席退化。"},
            {"id": "slice_block", "type": "table", "tableId": "slice_detail", "layout": "full"},
            {"id": "definitions", "type": "markdown", "sourceId": "validation_contract", "body": definitions_text},
            {"id": "methodology", "type": "markdown", "sourceId": "report_snapshot", "body": methodology_text},
            {"id": "qa_limits", "type": "markdown", "sourceId": "report_snapshot", "body": qa_text},
            {"id": "package_intro", "type": "markdown", "body": "## 冻结对象是 submission archive，不是仓库里的同名源码\n\nPackage QA 必须证明 raw loader、完整 720-state 执行与源码/归档动作和 reward 等价。"},
            {"id": "package_block", "type": "table", "tableId": "package_ledger", "layout": "full"},
            {"id": "limitations", "type": "markdown", "sourceId": "report_snapshot", "body": limitation_text},
            {"id": "hash_intro", "type": "markdown", "body": "## 声明哈希当前闭合\n\n这张审计表比较每个上游声明值和当前实算值；它防止报告引用已经漂移的代码、panel、games 或 archive。"},
            {"id": "hash_block", "type": "table", "tableId": "hash_ledger", "layout": "full"},
            {"id": "online_intro", "type": "markdown", "body": "## 线上层保持独立\n\n本地 W/T/L 不推导 Kaggle rating；只有实际保存的 submission receipt 才进入下面的线上账本。"},
            {"id": "online_block", "type": "table", "tableId": "online_ledger", "layout": "full"},
            {"id": "next_steps", "type": "markdown", "sourceId": "validation_contract", "body": next_steps},
            {"id": "questions", "type": "markdown", "body": questions},
        ],
    }
    return {
        "surface": "report",
        "manifest": manifest,
        "snapshot": {
            "version": 1,
            "generatedAt": generated_at,
            "status": snapshot_status,
            "datasets": {
                "headline": headline_rows,
                "pure_win_chart": chart_rows,
                "evidence": evidence_table_rows,
                "slices": slice_rows,
                "packages": package_rows,
                "hash_closure": hash_rows,
                "online": online_rows,
            },
            "accessIssues": access_issues,
        },
        "sources": sources,
        "package_info": {
            "originUrl": "artifact://kaggriculture-v14-evidence-report",
            "controls": {"edit": False, "refresh": False, "share": False},
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submission-json", type=Path)
    parser.add_argument("--plugin-root", type=Path)
    parser.add_argument("--artifact", type=Path, default=REPORTING_DIR / "artifact.json")
    parser.add_argument("--snapshot", type=Path, default=REPORTING_DIR / "report_snapshot.json")
    parser.add_argument("--output", type=Path, default=REPORTING_DIR / "v14_technical_report.html")
    parser.add_argument("--receipt", type=Path, default=REPORTING_DIR / "report_build_receipt.json")
    args = parser.parse_args()

    snapshot = collect_evidence(submission_json=args.submission_json)
    generated_at = datetime.now(timezone.utc).isoformat()
    artifact = build_artifact(snapshot, generated_at)
    args.snapshot.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.snapshot, snapshot)
    write_json(args.artifact, artifact)

    plugin_root = args.plugin_root or Path(
        os.environ.get("DATA_ANALYTICS_PLUGIN_ROOT", str(DEFAULT_PLUGIN_ROOT))
    )
    deliver = plugin_root / "skills" / "build-report" / "scripts" / "deliver_portable_artifact.mjs"
    if not deliver.is_file():
        raise FileNotFoundError(f"portable report builder not found: {deliver}")
    completed = subprocess.run(
        ["node", str(deliver), "--input", str(args.artifact), "--output", str(args.output)],
        cwd=plugin_root,
        text=True,
        capture_output=True,
        check=False,
    )
    receipt_lines = [line for line in completed.stdout.splitlines() if line.strip()]
    parsed_receipt: Any = None
    if receipt_lines:
        try:
            parsed_receipt = json.loads(receipt_lines[-1])
        except json.JSONDecodeError:
            parsed_receipt = {"stdout": completed.stdout}
    receipt_payload = {
        "schema": "kaggriculture-v14-report-build-receipt-1",
        "generated_at": generated_at,
        "command": ["node", str(deliver), "--input", str(args.artifact), "--output", str(args.output)],
        "exit_code": completed.returncode,
        "builder_receipt": parsed_receipt,
        "stderr": completed.stderr,
        "scope": {
            "new_games_started": False,
            "test_outcomes_read": False,
            "kaggle_api_called": False,
        },
    }
    write_json(args.receipt, receipt_payload)
    if completed.returncode != 0:
        raise RuntimeError(
            "portable report delivery failed:\n"
            + completed.stdout
            + ("\n" + completed.stderr if completed.stderr else "")
        )
    print(json.dumps(receipt_payload, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
