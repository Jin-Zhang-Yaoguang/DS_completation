#!/usr/bin/env python3
"""Build and execute the reproducible V14 online-diagnosis notebook/report bundle.

The script is intentionally read-only outside ``reporting/``. It reads the saved
official/API, metric-audit, and replay-probe artifacts and writes only the
notebook, figures, compact tables, report, and QA receipts in this directory.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient


REPORTING_DIR = Path(__file__).resolve().parent
DIAGNOSIS_DIR = REPORTING_DIR.parent
METRIC_PATH = DIAGNOSIS_DIR / "metric_audit" / "independent_metric_audit.json"
PROBE_PATH = DIAGNOSIS_DIR / "runtime_probe" / "runtime_probe.json"
RUNTIME_ANALYSIS_PATH = DIAGNOSIS_DIR / "runtime_probe" / "runtime_analysis.json"
DATA_INVENTORY_PATH = DIAGNOSIS_DIR / "data_inventory.json"
RULES_PATH = REPORTING_DIR / "evaluation_rules_receipt.json"
NOTEBOOK_PATH = REPORTING_DIR / "v14_online_diagnosis.ipynb"
REPORT_PATH = REPORTING_DIR / "technical_report.md"
SUMMARY_PATH = REPORTING_DIR / "outputs" / "analysis_summary.json"
CHART_MAP_PATH = REPORTING_DIR / "chart_map.json"
QA_PATH = REPORTING_DIR / "qa_receipt.json"
ARTIFACT_PATH = REPORTING_DIR / "artifact.json"
ARTIFACT_DB_PATH = REPORTING_DIR / "outputs" / "artifact_source_tables.sqlite"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pct(value: float, digits: int = 2) -> str:
    return f"{100 * value:.{digits}f}%"


def make_notebook(metric: dict, probe: dict, rules: dict) -> nbf.NotebookNode:
    v14 = metric["online"]["v14"]
    a2 = metric["online"]["a2"]
    v13c = metric["online"]["v13c"]
    local_a2 = metric["local_confirmatory"]["independent_recompute"]["vs_a2"]
    probe_agg = probe["aggregate"]
    data_inventory = load_json(DATA_INVENTORY_PATH)
    current_snapshot = data_inventory["current_snapshot"]
    active_high, active_low = current_snapshot["active_latest_two"]
    active_high_score = float(active_high["publicScore"])
    active_low_score = float(active_low["publicScore"])
    active_copy_gap = active_high_score - active_low_score

    tl_dr = f"""# V14 本地胜 A2、线上 Rating 更低：可复现诊断

## tl;dr

- **不存在未加权胜率崩塌。** V14 本地对固定 A2 为 {local_a2['wins']}/{local_a2['ties']}/{local_a2['losses']}，纯胜率 {pct(local_a2['pure_win_rate'])}；线上公开局为 {v14['overall']['wins']}/{v14['overall']['ties']}/{v14['overall']['losses']}，纯胜率 {pct(v14['overall']['pure_win_rate'])}。
- **表面矛盾来自量纲与赛程不同。** V14 线上纯胜率比 A2 高 {metric['comparison']['online_v14_vs_a2_unadjusted']['v14_minus_a2_outcome_score_rate_pp']:.2f} 个百分点，但 Public Rating 低 {abs(metric['comparison']['online_v14_vs_a2_unadjusted']['v14_minus_a2_public_simulation_rating']):.1f} 分。官方规则说明 Rating 变动取决于胜负和双方 Rating 差，金币差不计入。
- **对手池差异是强描述性解释。** V14 对手当前 Rating 代理均值 {v14['opponent_distribution']['rating_proxy']['mean']:.1f}，A2 为 {a2['opponent_distribution']['rating_proxy']['mean']:.1f}；V14 的 `>=2000` 对手占比仅 {pct(v14['opponent_distribution']['binary_2000_cut']['gte2000']['share'])}，A2 为 {pct(a2['opponent_distribution']['binary_2000_cut']['gte2000']['share'])}。这不是逐局赛前 Rating，不能作因果归因。
- **新增机制线上覆盖很低且不能持续。** 当前 runtime probe 覆盖 {probe_agg['replays']} 局，提交包动作完整复现 {probe_agg['archive_action_exact_reproduced']} 局；exact-A2 对手 {probe_agg['exact_a2_opponent_games']} 局、发生 V14 重排 {probe_agg['games_with_v14_reorder']} 局、终局 shadow trusted {probe_agg['games_shadow_trusted_at_end']} 局。
- **同一 A2 复投也发生路径分叉。** 截至 {current_snapshot['queried_at_taipei']}，团队 rank {current_snapshot['team']['rank']}、Rating {current_snapshot['team']['rating']:.1f}；两个 active 的相同 A2 复投 {active_high['id']}/{active_low['id']} 为 {active_high_score:.1f}/{active_low_score:.1f}，同一快照相差 {active_copy_gap:.1f} 分；旧 V14/A2/V13C 均已 inactive frozen。当前快照未配平两副本游戏数，因此不能把该分差当作通用噪声标准差。
- **543.8 分无法精确分摊。** 原始 episode/replay 不含逐局 pre/post Rating，任何精确 ELO 点数归因都会超出证据。
"""

    context = """## Context & Methods

### 分析问题

解释为何 V14 在本地固定对手回放中胜过 A2，却以更低的 Kaggle Public Rating 结束线上窗口；同时检查 V14 新增的 exact-A2 SELL 队列重排是否在线上真实触发。

### Key Assumptions

1. 公开局只保留 `EPISODE_TYPE_PUBLIC`；validation 不进入 W/T/L。
2. `pure win rate = wins / games`；`outcome score = (wins + 0.5 * ties) / games`。
3. 对手强度使用同一时点团队榜 `Score` 作**赛后代理**，不是不可见的逐局赛前 Rating。
4. `>=2000` 是透明的敏感性切点，不是官方分层，也不是因果校正。
5. 只有提交包动作逐步 100% 复现的 replay 才进入机制归因。

### 官方 Evaluation 规则

本 notebook 使用本地 CLI receipt 校验下列规则：胜/负/平改变 Rating；改变量取决于双方 Rating 差；击败高 Rating 对手涨得更多；金币差不影响 Rating；只追踪最新两个 submission。报告不假设具体 ELO 常数或更新公式。
"""

    setup_code = r'''from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter

plt.rcParams.update({
    "font.family": "Arial Unicode MS",
    "axes.unicode_minus": False,
    "figure.dpi": 130,
    "savefig.dpi": 180,
    "axes.spines.top": False,
    "axes.spines.right": False,
})


def find_diagnosis_dir(start: Path) -> Path:
    for base in [start, *start.parents]:
        candidate = base / "kaggle_Kaggriculture" / "model" / "v14_online_diagnosis"
        if candidate.exists():
            return candidate
        if base.name == "v14_online_diagnosis" and (base / "metric_audit").exists():
            return base
    raise FileNotFoundError("找不到 kaggle_Kaggriculture/model/v14_online_diagnosis")


DIAGNOSIS_DIR = find_diagnosis_dir(Path.cwd().resolve())
REPORTING_DIR = DIAGNOSIS_DIR / "reporting"
OUTPUT_DIR = REPORTING_DIR / "outputs"
FIGURE_DIR = REPORTING_DIR / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

METRIC_PATH = DIAGNOSIS_DIR / "metric_audit" / "independent_metric_audit.json"
PROBE_PATH = DIAGNOSIS_DIR / "runtime_probe" / "runtime_probe.json"
RUNTIME_ANALYSIS_PATH = DIAGNOSIS_DIR / "runtime_probe" / "runtime_analysis.json"
DATA_INVENTORY_PATH = DIAGNOSIS_DIR / "data_inventory.json"
RULES_PATH = REPORTING_DIR / "evaluation_rules_receipt.json"
LEADERBOARD_PATH = DIAGNOSIS_DIR / "raw" / "snapshot" / "kaggriculture_public_leaderboard.csv"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


metric = load_json(METRIC_PATH)
probe = load_json(PROBE_PATH)
runtime_analysis = load_json(RUNTIME_ANALYSIS_PATH)
data_inventory = load_json(DATA_INVENTORY_PATH)
rules = load_json(RULES_PATH)
leaderboard = pd.read_csv(LEADERBOARD_PATH)

print("diagnosis_dir:", DIAGNOSIS_DIR)
print("metric audit:", metric["status"], metric["generated_at_utc"])
print("runtime probe replays:", probe["aggregate"]["replays"])
print("parent-A2 call match:", runtime_analysis["runtime"]["parent_a2_equivalence"]["equal_action_calls"], "/", runtime_analysis["runtime"]["calls"])
print("current team rank/rating:", data_inventory["current_snapshot"]["team"]["rank"], data_inventory["current_snapshot"]["team"]["rating"])
print("Evaluation receipt:", rules["retrieved_at_utc"], rules["content_sha256"])
'''

    data_markdown = """## Data

### 1. 校验官方规则 receipt 与源文件 hash

先验证官方 Evaluation 文本本身的 hash，再验证 metric audit 中列出的可本地解析源文件。hash 不一致时 notebook 直接失败。
"""

    hash_code = r'''assert hashlib.sha256(rules["content"].encode("utf-8")).hexdigest() == rules["content_sha256"]
assert len(rules["content"].encode("utf-8")) == rules["content_bytes_utf8"]

hash_rows = []
for item in metric["source_inventory"]:
    source_path = (DIAGNOSIS_DIR / item["path"]).resolve()
    actual = file_sha256(source_path)
    volatile_snapshot = item["path"].startswith("raw/snapshot/")
    hash_rows.append({
        "path": item["path"],
        "exists": source_path.exists(),
        "volatile_snapshot": volatile_snapshot,
        "expected_sha256": item["sha256"],
        "actual_sha256": actual,
        "match": actual == item["sha256"],
        "bytes": source_path.stat().st_size,
    })

hash_check = pd.DataFrame(hash_rows)
hash_check.to_csv(OUTPUT_DIR / "source_hash_check.csv", index=False)
immutable_mismatch = hash_check.loc[~hash_check["match"] & ~hash_check["volatile_snapshot"]]
assert immutable_mismatch.empty, immutable_mismatch
print("volatile snapshot drift rows:", int((~hash_check["match"] & hash_check["volatile_snapshot"]).sum()))
hash_check[["path", "bytes", "volatile_snapshot", "match"]]
'''

    recompute_markdown = """### 2. 从 official episode payload 独立重算 W/T/L

下列单元不依赖 audit 汇总数：直接从三份 `episodes_full.json` 过滤公开局、识别候选 submission seat、比较最终 reward，并连接同一时点团队榜作为对手当前 Rating 代理。
"""

    recompute_code = r'''TARGETS = {
    "V14": {"key": "v14", "submission_id": 55722630, "public_rating": 1885.2},
    "A2 fixed": {"key": "a2", "submission_id": 55713355, "public_rating": 2429.0},
    "V13C": {"key": "v13c", "submission_id": 55719781, "public_rating": 2062.9},
}

leaderboard_score = leaderboard.set_index("TeamId")["Score"].to_dict()


def episode_rows(label: str, key: str, submission_id: int) -> pd.DataFrame:
    episodes = load_json(DIAGNOSIS_DIR / "raw" / key / "episodes_full.json")
    rows = []
    for episode in episodes:
        if episode.get("type") != "EPISODE_TYPE_PUBLIC":
            continue
        candidate = [a for a in episode["agents"] if int(a["submissionId"]) == submission_id]
        assert len(candidate) == 1, (episode["id"], len(candidate))
        candidate = candidate[0]
        opponent = [a for a in episode["agents"] if a is not candidate][0]
        if candidate["reward"] > opponent["reward"]:
            outcome = "W"
        elif candidate["reward"] < opponent["reward"]:
            outcome = "L"
        else:
            outcome = "T"
        rows.append({
            "model": label,
            "episode_id": int(episode["id"]),
            "end_time": pd.to_datetime(episode["endTime"]),
            "candidate_seat": int(candidate["index"]),
            "candidate_reward": float(candidate["reward"]),
            "opponent_reward": float(opponent["reward"]),
            "margin": float(candidate["reward"] - opponent["reward"]),
            "outcome": outcome,
            "opponent_team_id": int(opponent["teamId"]),
            "opponent_team": opponent["teamName"],
            "opponent_submission_id": int(opponent["submissionId"]),
            "opponent_rating_proxy": float(leaderboard_score[int(opponent["teamId"])]),
        })
    return pd.DataFrame(rows).sort_values(["end_time", "episode_id"]).reset_index(drop=True)


games = pd.concat(
    [episode_rows(label, cfg["key"], cfg["submission_id"]) for label, cfg in TARGETS.items()],
    ignore_index=True,
)


def wilson(wins: int, games_count: int, z: float = 1.959963984540054) -> tuple[float, float]:
    p = wins / games_count
    denom = 1 + z**2 / games_count
    centre = (p + z**2 / (2 * games_count)) / denom
    half = z * np.sqrt(p * (1 - p) / games_count + z**2 / (4 * games_count**2)) / denom
    return centre - half, centre + half


summary_rows = []
for label, cfg in TARGETS.items():
    part = games.loc[games["model"] == label]
    wins = int((part["outcome"] == "W").sum())
    ties = int((part["outcome"] == "T").sum())
    losses = int((part["outcome"] == "L").sum())
    ci_low, ci_high = wilson(wins, len(part))
    audited_dist = metric["online"][cfg["key"]]["opponent_distribution"]
    audited_strong = audited_dist.get("binary_2000_cut", {}).get("gte2000", audited_dist.get("gte2000"))
    summary_rows.append({
        "model": label,
        "submission_id": cfg["submission_id"],
        "public_rating": cfg["public_rating"],
        "games": len(part),
        "wins": wins,
        "ties": ties,
        "losses": losses,
        "pure_win_rate": wins / len(part),
        "outcome_score_rate": (wins + 0.5 * ties) / len(part),
        "ci_low": ci_low,
        "ci_high": ci_high,
        "current_opponent_rating_proxy_mean": part["opponent_rating_proxy"].mean(),
        "current_opponent_rating_proxy_median": part["opponent_rating_proxy"].median(),
        "frozen_audit_opponent_rating_proxy_mean": audited_dist["rating_proxy"]["mean"],
        "frozen_audit_opponent_gte2000_share": audited_strong["share"],
    })

online_summary = pd.DataFrame(summary_rows)
online_summary.to_csv(OUTPUT_DIR / "online_summary.csv", index=False)

for _, row in online_summary.iterrows():
    audited = metric["online"][TARGETS[row["model"]]["key"]]["overall"]
    assert [row["wins"], row["ties"], row["losses"]] == [audited["wins"], audited["ties"], audited["losses"]]
    assert abs(row["pure_win_rate"] - audited["pure_win_rate"]) < 1e-6

online_summary[["model", "public_rating", "games", "wins", "ties", "losses", "pure_win_rate", "ci_low", "ci_high", "frozen_audit_opponent_rating_proxy_mean", "current_opponent_rating_proxy_mean", "frozen_audit_opponent_gte2000_share"]]
'''

    results_markdown = """## Results

### Rating 与胜率方向相反，但并不矛盾

左图按公开 episode 直接重算未加权胜率及 Wilson 95% 区间；右图是各 submission 停止活跃时的 Public Rating。V14 的未加权胜率最高，却不是 Rating 最高者，直接说明这两者不能互换。V13C 以更低胜率获得更高 Rating，是第二个反例。
"""

    chart1_code = r'''order = ["V14", "A2 fixed", "V13C"]
plot_df = online_summary.set_index("model").loc[order].reset_index()
colors = ["#315C8A", "#C58B2A", "#8A8F98"]

fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.5), constrained_layout=True)

ax = axes[0]
x = np.arange(len(plot_df))
y = plot_df["pure_win_rate"].to_numpy()
yerr = np.vstack([y - plot_df["ci_low"].to_numpy(), plot_df["ci_high"].to_numpy() - y])
bars = ax.bar(x, y, color=colors, edgecolor="#28313B", linewidth=0.7, width=0.66)
ax.errorbar(x, y, yerr=yerr, fmt="none", ecolor="#28313B", capsize=5, linewidth=1.2)
ax.set_xticks(x, plot_df["model"])
ax.set_ylim(0, 1)
ax.yaxis.set_major_formatter(PercentFormatter(1.0))
ax.set_ylabel("未加权纯胜率")
ax.set_title("公开局纯胜率")
for bar, rate, n in zip(bars, y, plot_df["games"]):
    ax.text(bar.get_x() + bar.get_width()/2, rate + 0.035, f"{rate:.1%}\nn={n}", ha="center", va="bottom", fontsize=9)
ax.grid(axis="y", color="#D8DDE3", linewidth=0.7, alpha=0.8)

ax = axes[1]
ratings = plot_df["public_rating"].to_numpy()
bars = ax.bar(x, ratings, color=colors, edgecolor="#28313B", linewidth=0.7, width=0.66)
ax.set_xticks(x, plot_df["model"])
ax.set_ylim(0, max(ratings) * 1.18)
ax.set_ylabel("Public Rating")
ax.set_title("冻结的 submission Public Rating")
for bar, rating in zip(bars, ratings):
    ax.text(bar.get_x() + bar.get_width()/2, rating + 45, f"{rating:,.1f}", ha="center", va="bottom", fontsize=10)
ax.grid(axis="y", color="#D8DDE3", linewidth=0.7, alpha=0.8)

fig.suptitle("同一批线上窗口：未加权胜率与 Rating 不是同一量纲", fontsize=15, fontweight="bold")
fig.savefig(FIGURE_DIR / "01_metric_mismatch.png", bbox_inches="tight", facecolor="white")
plt.show()
'''

    opponent_markdown = """### 高总胜率主要伴随更容易的对手构成

V14 约四分之三的对手当前 Rating 代理低于 2000，而 A2 约三分之二的对手在 2000 及以上；在 `>=2000` 段，V14 胜率还低于 A2。两层 Kitagawa 恒等分解把线上未调整的 `+10.78pp` 胜率差拆为 `+12.54pp` 对手构成项和 `-1.76pp` 层内表现项。该分解只描述当前代理分层，不能复原官方逐局 Rating 更新。
"""

    chart2_code = r'''mix_rows = []
for label, key in [("V14", "v14"), ("A2 fixed", "a2")]:
    cut = metric["online"][key]["opponent_distribution"]["binary_2000_cut"]
    mix_rows.append({
        "model": label,
        "lt2000_share": cut["lt2000"]["share"],
        "gte2000_share": cut["gte2000"]["share"],
        "lt2000_score": cut["lt2000"]["score_rate"],
        "gte2000_score": cut["gte2000"]["score_rate"],
        "lt2000_games": cut["lt2000"]["games"],
        "gte2000_games": cut["gte2000"]["games"],
    })
mix_summary = pd.DataFrame(mix_rows)
mix_summary.to_csv(OUTPUT_DIR / "opponent_mix_summary.csv", index=False)

fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.5), constrained_layout=True)
x = np.arange(len(mix_summary))

ax = axes[0]
low = ax.bar(x, mix_summary["lt2000_share"], color="#A9BED6", edgecolor="#315C8A", linewidth=0.8, label="<2000")
high = ax.bar(x, mix_summary["gte2000_share"], bottom=mix_summary["lt2000_share"], color="#C58B2A", edgecolor="#6B4B17", linewidth=0.8, label=">=2000")
ax.set_xticks(x, mix_summary["model"])
ax.set_ylim(0, 1)
ax.yaxis.set_major_formatter(PercentFormatter(1.0))
ax.set_ylabel("对手局数占比")
ax.set_title("对手当前 Rating 代理构成")
ax.legend(frameon=False, ncol=2, loc="upper center")
for i, row in mix_summary.iterrows():
    ax.text(i, row["lt2000_share"] / 2, f"{row['lt2000_share']:.1%}\nn={int(row['lt2000_games'])}", ha="center", va="center", fontsize=9)
    ax.text(i, row["lt2000_share"] + row["gte2000_share"] / 2, f"{row['gte2000_share']:.1%}\nn={int(row['gte2000_games'])}", ha="center", va="center", fontsize=9)

ax = axes[1]
width = 0.34
b1 = ax.bar(x - width/2, mix_summary["lt2000_score"], width, color="#A9BED6", edgecolor="#315C8A", linewidth=0.8, label="<2000")
b2 = ax.bar(x + width/2, mix_summary["gte2000_score"], width, color="#C58B2A", edgecolor="#6B4B17", linewidth=0.8, label=">=2000")
ax.set_xticks(x, mix_summary["model"])
ax.set_ylim(0, 1)
ax.yaxis.set_major_formatter(PercentFormatter(1.0))
ax.set_ylabel("分层 outcome score")
ax.set_title("相同代理分层内的表现")
ax.legend(frameon=False, ncol=2, loc="upper center")
ax.grid(axis="y", color="#D8DDE3", linewidth=0.7, alpha=0.8)
for bars in (b1, b2):
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.025, f"{bar.get_height():.1%}", ha="center", va="bottom", fontsize=9)

fig.suptitle("V14 与 A2 的线上对手池并非同难度赛程", fontsize=15, fontweight="bold")
fig.savefig(FIGURE_DIR / "02_opponent_mix.png", bbox_inches="tight", facecolor="white")
plt.show()
mix_summary
'''

    mechanism_markdown = """### V14 的新增机制在线上只在短暂 A2-compatible 前缀触发

本地 confirm 针对 exact A2：shadow 全程可信，72% 的局至少发生一次 SELL 队列重排。线上 runtime probe 则逐步复现已提交 archive；87 局中没有 exact-A2 或终局 trusted，但 8 局在对手尚未出现可观测偏离前发生过重排，随后 fail-close。机制不是完全未运行，而是覆盖很低且无法持续。

V14 有 62,543/62,553（99.984%）动作等于父 A2，79/87 局全程相同；21 个负局中 20 局为 719/719 父 A2 动作。本地平均 13.00 重排/局，线上只有 0.115/局，激活密度低 113.1 倍。8 局重排样本没有“禁用重排”的同 seed 反事实，不能据其 W/L 判断机制有效或有害。

0818–0820 留出的只是环境 seed；闭环对手仍固定 A2/r002，没有 holdout 对手策略谱系。该结论只适用于 probe 覆盖且 archive 动作 100% 复现的回放。
"""

    mechanism_code = r'''agg = probe["aggregate"]
local = metric["local_confirmatory"]["independent_recompute"]["vs_a2"]
local_ref = probe.get("local_confirmatory_reference", {}).get("by_anchor", {}).get("v12a2_no_shop_gate", {})
local_games = int(local_ref.get("games", local["games"]))

mechanism_summary = pd.DataFrame([
    {
        "cohort": "本地 fixed A2",
        "games": local_games,
        "exact_a2_share": 1.0,
        "shadow_trusted_end_share": local_ref.get("shadow_trusted_games", local_games) / local_games,
        "games_with_reorder_share": local_ref.get("games_with_reorder", 0) / local_games,
        "archive_reproduction_share": np.nan,
    },
    {
        "cohort": "线上 replay probe",
        "games": agg["replays"],
        "exact_a2_share": agg["exact_a2_opponent_games"] / agg["replays"],
        "shadow_trusted_end_share": agg["games_shadow_trusted_at_end"] / agg["replays"],
        "games_with_reorder_share": agg["games_with_v14_reorder"] / agg["replays"],
        "archive_reproduction_share": agg["archive_action_exact_reproduced"] / agg["replays"],
    },
])
mechanism_summary.to_csv(OUTPUT_DIR / "mechanism_summary.csv", index=False)

parent_eq = runtime_analysis["runtime"]["parent_a2_equivalence"]
loss_attr = runtime_analysis["runtime"]["loss_attribution"]
parent_equivalence_summary = pd.DataFrame([{
    "calls": runtime_analysis["runtime"]["calls"],
    "equal_action_calls": parent_eq["equal_action_calls"],
    "equal_action_rate": parent_eq["equal_action_rate"],
    "exact_action_games": parent_eq["exact_action_games"],
    "episodes": runtime_analysis["runtime"]["episodes"],
    "losses": loss_attr["losses"],
    "losses_exact_parent_a2_all_719_calls": loss_attr["losses_exact_parent_a2_all_719_calls"],
    "local_reorders_per_game": runtime_analysis["local_vs_online_mechanism"]["local_reorders_per_game"],
    "online_reorders_per_game": runtime_analysis["local_vs_online_mechanism"]["online_reorders_per_game"],
    "local_activation_multiple_over_online": runtime_analysis["local_vs_online_mechanism"]["local_activation_multiple_over_online"],
}])
parent_equivalence_summary.to_csv(OUTPUT_DIR / "parent_equivalence_summary.csv", index=False)

reorder_episode_rows = []
for episode in probe.get("episodes", []):
    selected = episode["selected_probe"]
    reorder_steps = selected.get("reorder_steps", [])
    if not reorder_steps:
        continue
    first_mismatch = selected.get("first_prediction_mismatch") or {}
    reorder_episode_rows.append({
        "episode_id": episode["episode_id"],
        "outcome": episode["outcome"],
        "margin": episode["margin"],
        "reorder_step_count": len(reorder_steps),
        "first_reorder_step": min(reorder_steps),
        "last_reorder_step": max(reorder_steps),
        "first_observable_mismatch_action_step": first_mismatch.get("action_step"),
        "first_shadow_fault_step": selected.get("first_shadow_fault_step"),
        "wrong_current_shadow_reorder_steps": len(selected.get("reorder_with_wrong_current_shadow_steps", [])),
    })
reorder_episode_summary = pd.DataFrame(reorder_episode_rows)
reorder_episode_summary.to_csv(OUTPUT_DIR / "reorder_episode_summary.csv", index=False)
assert len(reorder_episode_summary) == agg["games_with_v14_reorder"]
assert reorder_episode_summary["wrong_current_shadow_reorder_steps"].sum() == 0
assert (reorder_episode_summary["last_reorder_step"] < reorder_episode_summary["first_observable_mismatch_action_step"]).all()

metrics_to_plot = [
    ("exact_a2_share", "exact-A2 对手"),
    ("shadow_trusted_end_share", "终局 shadow trusted"),
    ("games_with_reorder_share", "至少一次重排"),
]
labels = [label for _, label in metrics_to_plot]
x = np.arange(len(labels))
width = 0.34

fig, ax = plt.subplots(figsize=(9.5, 4.8), constrained_layout=True)
local_vals = [mechanism_summary.loc[0, key] for key, _ in metrics_to_plot]
online_vals = [mechanism_summary.loc[1, key] for key, _ in metrics_to_plot]
b1 = ax.bar(x - width/2, local_vals, width, color="#315C8A", edgecolor="#28313B", linewidth=0.8, label=f"本地 fixed A2 (n={local_games})")
b2 = ax.bar(x + width/2, online_vals, width, color="#C58B2A", edgecolor="#6B4B17", linewidth=0.8, label=f"线上 replay probe (n={agg['replays']})")
ax.set_xticks(x, labels)
ax.set_ylim(0, 1.08)
ax.yaxis.set_major_formatter(PercentFormatter(1.0))
ax.set_ylabel("局数占比")
ax.set_title("V14 新增机制的适用条件与实际触发")
ax.legend(frameon=False, ncol=2, loc="upper right")
ax.grid(axis="y", color="#D8DDE3", linewidth=0.7, alpha=0.8)
for bars in (b1, b2):
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02, f"{bar.get_height():.0%}", ha="center", va="bottom", fontsize=9)
ax.text(0.01, -0.19, f"线上 archive 动作逐步完整复现：{agg['archive_action_exact_reproduced']}/{agg['replays']}；仅完整复现局进入机制归因。", transform=ax.transAxes, fontsize=9, color="#4F5964")
fig.savefig(FIGURE_DIR / "03_mechanism_activation.png", bbox_inches="tight", facecolor="white")
plt.show()
mechanism_summary
'''

    path_markdown = """### 时间路径与席位检查没有推翻主结论

- V14 前 40 局为 34/0/6，41–80 局为 30/0/10，最后 7 局为 2/0/5；最后阶段对手当前 Rating 代理均值升至 2074.2。该序列与后段回撤一致，但没有逐局 pre/post Rating，不能算出损失点数。
- V14 两席胜率仅差 1.47 个百分点，A2 两席仅差 0.81 个百分点；席位不足以解释 543.8 分差。
- V14 与 A2 线上未加权胜率差的 bootstrap 95% 区间为 -3.94pp 至 +25.62pp，包含 0；线上样本不支持“V14 泛化强度已显著胜过 A2”的推断。
"""

    summary_code = r'''comparison = metric["comparison"]
decomp = comparison["opponent_mix_diagnostics"]["two_bin_kitagawa_decomposition_at_2000"]
agg = probe["aggregate"]

analysis_summary = {
    "generated_from_notebook": True,
    "metric_audit_generated_at_utc": metric["generated_at_utc"],
    "runtime_probe_replays": agg["replays"],
    "runtime_probe_archive_exact_reproduced": agg["archive_action_exact_reproduced"],
    "runtime_probe_reorder_episodes": reorder_episode_summary.to_dict(orient="records"),
    "official_evaluation_receipt_sha256": rules["content_sha256"],
    "primary": {
        "v14_online": metric["online"]["v14"]["overall"],
        "a2_online": metric["online"]["a2"]["overall"],
        "v13c_online": metric["online"]["v13c"]["overall"],
        "v14_public_rating": metric["online"]["v14"]["public_simulation_rating"],
        "a2_public_rating": metric["online"]["a2"]["public_simulation_rating"],
        "v13c_public_rating": metric["online"]["v13c"]["public_simulation_rating"],
        "v14_minus_a2_rating": comparison["online_v14_vs_a2_unadjusted"]["v14_minus_a2_public_simulation_rating"],
        "v14_minus_a2_win_rate_pp": comparison["online_v14_vs_a2_unadjusted"]["v14_minus_a2_outcome_score_rate_pp"],
        "v14_minus_a2_win_rate_ci95_pp": comparison["online_v14_vs_a2_unadjusted"]["independent_difference_ci95_bootstrap_pp"],
    },
    "local": metric["local_confirmatory"],
    "opponent_mix": comparison["opponent_mix_diagnostics"],
    "path": comparison["path_diagnostics"],
    "seat": comparison["seat_diagnostics"],
    "runtime_probe": agg,
    "runtime_analysis": runtime_analysis,
    "data_inventory": data_inventory,
    "rating_attribution": metric["rating_attribution"],
    "epistemic_status": metric["epistemic_status"],
    "data_quality": metric["data_quality"],
    "source_inventory": metric["source_inventory"],
    "data_inventory_sha256": file_sha256(DATA_INVENTORY_PATH),
}

with (OUTPUT_DIR / "analysis_summary.json").open("w", encoding="utf-8") as handle:
    json.dump(analysis_summary, handle, ensure_ascii=False, indent=2)

print(json.dumps({
    "v14_wtl": [analysis_summary["primary"]["v14_online"][k] for k in ["wins", "ties", "losses"]],
    "a2_wtl": [analysis_summary["primary"]["a2_online"][k] for k in ["wins", "ties", "losses"]],
    "rating_gap": analysis_summary["primary"]["v14_minus_a2_rating"],
    "mix_component_pp": decomp["opponent_mix_component_pp"],
    "within_bin_component_pp": decomp["within_bin_performance_component_pp"],
    "probe_replays": agg["replays"],
    "probe_exact_a2": agg["exact_a2_opponent_games"],
        "probe_reorder": agg["games_with_v14_reorder"],
        "probe_reorder_wtl": [
            int((reorder_episode_summary["outcome"] == "W").sum()),
            int((reorder_episode_summary["outcome"] == "T").sum()),
            int((reorder_episode_summary["outcome"] == "L").sum()),
        ],
        "probe_reorder_steps": int(reorder_episode_summary["reorder_step_count"].sum()),
        "wrong_current_shadow_reorder_steps": int(reorder_episode_summary["wrong_current_shadow_reorder_steps"].sum()),
    }, ensure_ascii=False, indent=2))
'''

    takeaways = """## Takeaways

### 证据分级

**已证实**

- V14 线上公开局为 66/0/21，未加权胜率没有低于本地 fixed-A2 结果。
- Public Rating 与未加权胜率不是同一指标；金币差不进入 Rating，双方 Rating 差会影响改变量。
- V14 与 A2 经历的是未配对、不同难度、不同时间顺序的赛程。
- V14 与 A2 的共同 opponent submission 为 0；V14 99.984% 动作等于父 A2，21 个负局中 20 局完全是父 A2 动作。
- runtime probe 在提交包动作逐步完整复现的覆盖回放中，新增重排仅在 8/87 局短暂触发，且没有一局保持终局 trusted。
- 0818–0820 只 holdout 环境 seed，没有 holdout 对手策略谱系。

**描述性证据**

- 同一时点团队榜代理显示，V14 对手显著更弱；两层分解显示，较容易的对手构成足以覆盖 V14 未调整胜率优势。
- 最后 7 局 2/5 与终局回撤一致。

**仍未知**

- 543.8 Rating 分分别由对手强度、路径顺序、更新参数与停赛冻结贡献多少。
- 精确更新公式、逐局双方赛前 Rating 与候选赛后 Rating。
- V14 对线上强对手池的真实因果提升；当前没有同 seed、同对手、双席位的线上配对实验。

### 建议的下一步

1. 保留本地 fixed A2/r002 作为“克制性”门槛，但新增按线上强度分层的异质专家联赛作为“泛化性”门槛。
2. 每次线上报告同时列 `W/T/L + outcome score + CI` 与 `Public Rating`，禁止再把两者合并成一个“得分”。
3. 未来若平台可得，逐局保存双方 pre-rating、候选 post-rating 与应用顺序；否则将 Rating 点数归因登记为不可识别。
4. 新增机制必须报告 exact-opponent 覆盖率、shadow trusted 率与触发率；局部克制策略不能只看 fixed-opponent 胜率。

### Further questions

- 线上匹配是否按即时 Rating 主动分层，以及 inactive submission 的冻结规则，现有数据只能观察相关路径。
- V14 在真实 `>=2000` 对手池只有 23 局，区间仍宽；需要预注册更大、同口径的强对手样本。
"""

    cells = [
        nbf.v4.new_markdown_cell(tl_dr),
        nbf.v4.new_markdown_cell(context),
        nbf.v4.new_code_cell(setup_code),
        nbf.v4.new_markdown_cell(data_markdown),
        nbf.v4.new_code_cell(hash_code),
        nbf.v4.new_markdown_cell(recompute_markdown),
        nbf.v4.new_code_cell(recompute_code),
        nbf.v4.new_markdown_cell(results_markdown),
        nbf.v4.new_code_cell(chart1_code),
        nbf.v4.new_markdown_cell(opponent_markdown),
        nbf.v4.new_code_cell(chart2_code),
        nbf.v4.new_markdown_cell(mechanism_markdown),
        nbf.v4.new_code_cell(mechanism_code),
        nbf.v4.new_markdown_cell(path_markdown),
        nbf.v4.new_code_cell(summary_code),
        nbf.v4.new_markdown_cell(takeaways),
    ]

    notebook = nbf.v4.new_notebook(cells=cells)
    notebook.metadata.update(
        {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3"},
            "analysis_contract": {
                "mode": "diagnostic analysis report",
                "audience": "technical",
                "scope": "saved official episodes/replays only; no new games, test access, strategy changes, submissions, or browser",
                "official_rules_receipt_sha256": rules["content_sha256"],
            },
        }
    )
    return notebook


def build_report(metric: dict, probe: dict, rules: dict) -> str:
    runtime_analysis = load_json(RUNTIME_ANALYSIS_PATH)
    data_inventory = load_json(DATA_INVENTORY_PATH)
    runtime = runtime_analysis["runtime"]
    parent_eq = runtime["parent_a2_equivalence"]
    loss_attr = runtime["loss_attribution"]
    current_schedule = runtime_analysis["online_schedule"]
    current_snapshot = data_inventory["current_snapshot"]
    active_high, active_low = current_snapshot["active_latest_two"]
    active_copy_gap = float(active_high["publicScore"]) - float(active_low["publicScore"])
    v14 = metric["online"]["v14"]
    a2 = metric["online"]["a2"]
    v13c = metric["online"]["v13c"]
    local = metric["local_confirmatory"]["independent_recompute"]["vs_a2"]
    comparison = metric["comparison"]
    mix = comparison["opponent_mix_diagnostics"]
    decomp = mix["two_bin_kitagawa_decomposition_at_2000"]
    agg = probe["aggregate"]
    archive_rate = agg["archive_action_exact_reproduced"] / agg["replays"]
    coverage_note = "完整 87 局" if agg["replays"] == 87 else f"部分样本 {agg['replays']}/87 局"
    reorder_episodes = [episode for episode in probe.get("episodes", []) if episode["selected_probe"].get("reorder_steps")]
    reorder_wins = sum(episode["outcome"] == "W" for episode in reorder_episodes)
    reorder_ties = sum(episode["outcome"] == "T" for episode in reorder_episodes)
    reorder_losses = sum(episode["outcome"] == "L" for episode in reorder_episodes)
    reorder_steps_total = sum(len(episode["selected_probe"]["reorder_steps"]) for episode in reorder_episodes)
    wrong_shadow_reorder_steps = sum(
        len(episode["selected_probe"].get("reorder_with_wrong_current_shadow_steps", [])) for episode in reorder_episodes
    )

    return f"""# V14 本地胜 A2、线上 Rating 更低：技术诊断

## 技术摘要

结论不是“V14 线上胜率低”，而是**本地固定对手胜率与线上 Simulation Rating 回答不同问题**。V14 本地对 fixed A2 为 **{local['wins']}/{local['ties']}/{local['losses']}，纯胜率 {pct(local['pure_win_rate'])}**；线上 V14 为 **{v14['overall']['wins']}/{v14['overall']['ties']}/{v14['overall']['losses']}，纯胜率 {pct(v14['overall']['pure_win_rate'])}**，没有未加权胜率崩塌。它甚至比 A2 线上纯胜率高 **{comparison['online_v14_vs_a2_unadjusted']['v14_minus_a2_outcome_score_rate_pp']:.2f}pp**，但 Rating 低 **{abs(comparison['online_v14_vs_a2_unadjusted']['v14_minus_a2_public_simulation_rating']):.1f}** 分，因为 Rating 还取决于对手 Rating 与比赛顺序。

现有数据给出两条互补解释。第一，V14 与 A2 的共同 opponent submission 为 **0**，当前榜映射的对手均分为 **{current_schedule['v14']['opponent_current_score']['mean']:.1f} vs {current_schedule['a2']['opponent_current_score']['mean']:.1f}**，日程明显不同；官方规则下，击败更高 Rating 对手涨得更多。第二，runtime probe 覆盖 **{coverage_note}**，提交包动作完整复现率 **{archive_rate:.1%}**；V14 有 **{parent_eq['equal_action_calls']}/{runtime['calls']}（{parent_eq['equal_action_rate']:.3%}）** 动作等于父 A2，21 个负局中 **{loss_attr['losses_exact_parent_a2_all_719_calls']}/21** 完全是父 A2 动作。因此线上低分不能解释为 Q2b 在同一批对手上输给 A2。

本地 0818–0820 确实留出了未见过的环境 seed，但闭环对手仍固定为 A2/r002；它验证的是**场景外推**，没有验证**对手策略谱系外推**。这正是 74.5% fixed-A2 胜率不能直接推到线上异质池的实验设计缺口。

截至 **{current_snapshot['queried_at_taipei']}**，团队当前为 **rank {current_snapshot['team']['rank']} / Rating {current_snapshot['team']['rating']:.1f}**；两个 active 的相同 A2 复投在同一快照分别为 **{float(active_high['publicScore']):.1f}** 与 **{float(active_low['publicScore']):.1f}**，相差 **{active_copy_gap:.1f}**。这条同模型分叉是路径/对手抽样影响的直接实证，但两个副本游戏数未在当前快照中配平，不能拿 243.9 当作通用噪声标准差。

但 **543.8 Rating 分不能精确拆解**：公开 episode/replay 不含双方逐局 pre/post Rating。下面把结论严格分为已证实、描述性证据与未知。

## 未加权胜率与 Rating 的方向确实相反

![公开局胜率与 Public Rating](figures/01_metric_mismatch.png)

左图是公开 episode 直接重算的纯胜率与 Wilson 95% 区间，右图是各 submission 停止活跃时保留的 Public Rating。V14 的未加权胜率最高，却不是 Rating 最高者；V13C 以 **{pct(v13c['overall']['pure_win_rate'])}** 的更低胜率获得 **{v13c['public_simulation_rating']:.1f}**，也是“Rating 不等于胜率”的反例。V14 与 A2 的线上未加权胜率差 bootstrap 95% CI 为 **{comparison['online_v14_vs_a2_unadjusted']['independent_difference_ci95_bootstrap_pp'][0]:.2f}pp 至 {comparison['online_v14_vs_a2_unadjusted']['independent_difference_ci95_bootstrap_pp'][1]:.2f}pp**，包含 0；不能把现有线上样本升级为“V14 泛化显著优于 A2”。

## 对手构成足以消除高总胜率的表象

![线上对手构成与分层表现](figures/02_opponent_mix.png)

V14 有 **{pct(v14['opponent_distribution']['binary_2000_cut']['gte2000']['share'])}** 的对手当前 Rating 代理达到 2000，A2 为 **{pct(a2['opponent_distribution']['binary_2000_cut']['gte2000']['share'])}**。在该强对手段，V14 为 **11/12，{pct(v14['opponent_distribution']['binary_2000_cut']['gte2000']['score_rate'])}**，A2 为 **25/18，{pct(a2['opponent_distribution']['binary_2000_cut']['gte2000']['score_rate'])}**。

以 2000 为透明切点，Kitagawa 恒等分解把 V14 对 A2 的未调整胜率差 **+{decomp['raw_v14_minus_a2_score_rate_pp']:.2f}pp** 拆成：

- 对手构成项 **+{decomp['opponent_mix_component_pp']:.2f}pp**，bootstrap 95% CI **+{decomp['opponent_mix_component_bootstrap_ci95_pp'][0]:.2f} 至 +{decomp['opponent_mix_component_bootstrap_ci95_pp'][1]:.2f}pp**；
- 层内表现项 **{decomp['within_bin_performance_component_pp']:+.2f}pp**，bootstrap 95% CI **{decomp['within_bin_component_bootstrap_ci95_pp'][0]:+.2f} 至 {decomp['within_bin_component_bootstrap_ci95_pp'][1]:+.2f}pp**。

这是**描述性恒等分解，不是因果校正**。对手分数是 2026-08-24 同一时点的赛后团队级 Score，可能受其其他 submission 和后续比赛影响；它不能替代逐局赛前 Rating。

## 本地高覆盖的新增机制，线上只在短暂 A2-compatible 前缀触发

![V14 机制适用与触发](figures/03_mechanism_activation.png)

本地 fixed-A2 confirm 中，200/200 局 shadow trusted，144/200 局至少发生一次重排；这回答“V14 是否克制 exact A2”。线上 probe 则逐步复现提交 archive 的动作后发现：**{agg['exact_a2_opponent_games']}/{agg['replays']} exact-A2、{agg['games_shadow_trusted_at_end']}/{agg['replays']} 终局 trusted、{agg['games_with_v14_reorder']}/{agg['replays']} 发生重排**。8 局共重排 **{reorder_steps_total} 步**，结果为 **{reorder_wins}/{reorder_ties}/{reorder_losses}**；这些重排都发生在可观测 mismatch 之前，`reorder_with_wrong_current_shadow_steps={wrong_shadow_reorder_steps}`，随后对手才偏离 A2 并触发 fail-close。

这说明机制不是完全未运行，而是**在线上异质对手中覆盖很低且无法持续**。8 局的 7/1 是事后、强选择样本，没有“禁用重排”的同 seed 反事实，不能据此证明机制有效或有害；只能确认本地 72% 的触发覆盖没有线上复现。

更强的归因是：V14 全线上 **{parent_eq['equal_action_calls']}/{runtime['calls']}** 个动作等于父 A2，**{parent_eq['exact_action_games']}/{runtime['episodes']}** 局完全相同；21 个负局中 **{loss_attr['losses_exact_parent_a2_all_719_calls']}** 局是 719/719 父 A2 动作。局部 Q2b 只改了 10 个动作，无法承担 543.8 分差的主要解释。

该机制归因只对 archive 动作完整复现的 replay 有效；本次为完整 **{agg['archive_action_exact_reproduced']}/{agg['replays']}**。

## 范围、数据与指标定义

| 版本 | Submission | 冻结 Public Rating | 公开局 W/T/L | 纯胜率 | Wilson 95% CI |
|---|---:|---:|---:|---:|---:|
| V14 | 55722630 | 1885.2 | 66/0/21（87） | 75.86% | 65.90%–83.64% |
| A2 fixed | 55713355 | 2429.0 | 41/0/22（63） | 65.08% | 52.75%–75.67% |
| V13C（单列） | 55719781 | 2062.9 | 53/0/33（86） | 61.63% | 51.06%–71.20% |

- `pure win rate = wins / public games`，平局不是胜局。
- `outcome score = (wins + 0.5 * ties) / public games`；本样本三版本均无平局，数值等于纯胜率。
- `Public Rating` 是 Kaggle submission 的技能 Rating，不是金币均值、金币差或胜率百分比。
- 本地 confirm 使用 2026-08-18 至 2026-08-20 的 100 个 source，每个 source 对同一固定对手复用双席位，共 200 局；有效独立单位按 100 个 source cluster 处理。
- 0818–0820 只留出环境 seed，闭环对手 lineage 仍是开发时固定的 A2/r002；因此不是对手谱系 holdout。
- 三个线上 submission 均已退出“最新两个”活跃席位；表中分数是停止参赛时保留的历史值，不能和当前团队榜续接成一条路径。
- 2026-08-24 21:29 台北快照的当前团队为 rank 1602、Rating 1519.3；旧 V14/A2/V13C 都是 inactive frozen，不能用当前团队分数覆盖。

官方 Evaluation 页经 Kaggle CLI 于 **{rules['retrieved_at_asia_taipei']}** 读取，receipt SHA256 为 `{rules['content_sha256']}`。规则明确：胜/负/平改变 Rating；改变量取决于双方 Rating 差；击败更高分对手提升更多；金币差不影响 Rating；只追踪最新两个 submission。本文不假设具体 ELO 更新公式。

## 方法与稳健性检查

1. 从三份 official `episodes_full.json` 排除各 1 条 validation，逐局按 submissionId 找到候选 seat，比较 reward 重算 W/T/L。
2. 把对手 teamId 连接到同一时点排行榜，构建后验 Rating 代理；三组连接覆盖率均为 100%。
3. 在线胜率区间使用 Wilson；V14 与 A2 未调整差异使用独立 bootstrap；本地双席位按 source cluster bootstrap。
4. 机制 probe 从实际 `submission.tar.gz` 恢复代码，对每步观测重放并要求候选动作 100% 匹配后才归因。
5. 席位敏感性很小：V14 seat0/seat1 为 76.47%/75.00%，A2 为 65.52%/64.71%。
6. 时间路径显示 V14 前 40 局 34/6、41–80 局 30/10、最后 7 局 2/5；最后 7 局对手代理均值 2074.2。该路径与回撤一致，但不能换算 Rating 点数。
7. metric audit 生成后，`raw/snapshot/` 的排行榜文件被刷新，hash 已漂移；20:55 的两层分解以 audit JSON 内冻结聚合为准，较新的 runtime mapping 为 1769.1/2064.0，方向不变但不能混作同一时点。

## 限制、不确定性与证据分级

**已证实**

- V14 线上没有未加权胜率坍塌；本地 fixed-A2 克制结论仍成立于原实验分布。
- Public Rating 与未加权胜率量纲不同；金币差不进入 Rating。
- V14、A2 线上并未在同 seed、同对手、双席位、同时间下配对。
- 对手当前 Rating 代理的分布明显不同；它只能描述保存快照中的对手构成，不能证明逐局赛前难度。
- runtime probe 覆盖且 100% 复现的回放中，新增重排只在 8/87 局短暂触发，且没有一局保持终局 trusted；V14 99.984% 的动作等于父 A2。

**描述性、较可能但未证明**

- V14 对手代理分布偏低、强对手段表现较差、前期路径分叉与最后 7 局回撤，均与“高总胜率没有转化为更高 Rating”一致，但现有数据不能做因果归因。

**未知**

- 543.8 分分别由对手强度、比赛顺序、更新参数、活跃窗口与冻结时点贡献多少；可精确分摊的点数为 **0**，含义是不可识别，不是这些因素没有作用。
- 线上匹配器的具体算法、逐局赛前 Rating 与精确更新公式。
- V14 对异质强对手池的因果提升。

## 建议的下一步

1. 每次线上验收同时报告 `W/T/L + outcome score + CI` 与 `Public Rating`，不再用一个“得分”混称。
2. 本地保留 fixed A2/r002 克制门槛，同时增加按线上强度分层的异质专家联赛，继续同 seed 双席位。
3. 新增机制必须有三项覆盖指标：exact-opponent 覆盖率、shadow trusted 率、实际触发率；低覆盖也不能把 fixed-opponent uplift 外推到线上。
4. 若平台未来暴露逐局 pre/post Rating，才开展点数归因；否则保持“不可识别”结论。

## 尚待回答

- V14 在真实 `>=2000` 对手池只有 23 局，Wilson 95% CI 为 29.24%–67.04%；需预注册更大的强对手样本。
- 线上匹配是否按即时 Rating 主动分层，以及 inactive submission 如何冻结，当前数据不足以证明。

## 可复现材料

- `v14_online_diagnosis.ipynb`：从 raw episode、排行榜、metric audit 与 runtime probe 重新生成全部表图。
- `outputs/analysis_summary.json`：报告数字的机器可读快照。
- `evaluation_rules_receipt.json`：官方 Evaluation CLI 原文、命令、时间与内容 hash。
- `outputs/source_hash_check.csv`：输入数据 hash 逐项核验。
- `chart_map.json`：三张图的分析问题、字段、结论与限制。
- `qa_receipt.json`：notebook 执行、图像尺寸、关键断言与输出 hash。
"""


def build_artifact(metric: dict, probe: dict, rules: dict) -> dict:
    """Build the canonical bounded MCP report artifact.

    The artifact is the only report delivery payload. Static PNGs and Markdown
    remain notebook/source companions and are not a second rendered surface.
    """

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    runtime_analysis = load_json(RUNTIME_ANALYSIS_PATH)
    data_inventory = load_json(DATA_INVENTORY_PATH)
    runtime = runtime_analysis["runtime"]
    parent_eq = runtime["parent_a2_equivalence"]
    loss_attr = runtime["loss_attribution"]
    current_schedule = runtime_analysis["online_schedule"]
    current_snapshot = data_inventory["current_snapshot"]
    active_high, active_low = current_snapshot["active_latest_two"]
    active_high_score = float(active_high["publicScore"])
    active_low_score = float(active_low["publicScore"])
    active_copy_gap = active_high_score - active_low_score
    v14 = metric["online"]["v14"]
    a2 = metric["online"]["a2"]
    v13c = metric["online"]["v13c"]
    local_a2 = metric["local_confirmatory"]["independent_recompute"]["vs_a2"]
    comparison = metric["comparison"]
    mix_diag = comparison["opponent_mix_diagnostics"]
    decomp = mix_diag["two_bin_kitagawa_decomposition_at_2000"]
    agg = probe["aggregate"]
    local_ref = probe.get("local_confirmatory_reference", {}).get("by_anchor", {}).get("v12a2_no_shop_gate", {})
    local_games = int(local_ref.get("games", local_a2["games"]))
    local_trusted = int(local_ref.get("shadow_trusted_games", local_games))
    local_reorder = int(local_ref.get("games_with_reorder", 0))
    reorder_episode_rows = []
    for episode in probe.get("episodes", []):
        selected = episode["selected_probe"]
        reorder_steps = selected.get("reorder_steps", [])
        if not reorder_steps:
            continue
        first_mismatch = selected.get("first_prediction_mismatch") or {}
        reorder_episode_rows.append(
            {
                "episode_id": episode["episode_id"],
                "outcome": episode["outcome"],
                "margin": episode["margin"],
                "reorder_step_count": len(reorder_steps),
                "first_reorder_step": min(reorder_steps),
                "last_reorder_step": max(reorder_steps),
                "first_observable_mismatch_action_step": first_mismatch.get("action_step"),
                "first_shadow_fault_step": selected.get("first_shadow_fault_step"),
                "wrong_current_shadow_reorder_steps": len(selected.get("reorder_with_wrong_current_shadow_steps", [])),
            }
        )
    reorder_total_steps = sum(row["reorder_step_count"] for row in reorder_episode_rows)
    reorder_wins = sum(row["outcome"] == "W" for row in reorder_episode_rows)
    reorder_ties = sum(row["outcome"] == "T" for row in reorder_episode_rows)
    reorder_losses = sum(row["outcome"] == "L" for row in reorder_episode_rows)
    wrong_shadow_reorder_steps = sum(row["wrong_current_shadow_reorder_steps"] for row in reorder_episode_rows)

    headline_metrics = [
        {
            "local_a2_win_rate": local_a2["pure_win_rate"],
            "local_a2_outcome_score": local_a2["outcome_score_rate"],
            "local_a2_games": local_a2["games"],
            "v14_online_win_rate": v14["overall"]["pure_win_rate"],
            "a2_online_win_rate": a2["overall"]["pure_win_rate"],
            "online_win_rate_delta": comparison["online_v14_vs_a2_unadjusted"]["v14_minus_a2_outcome_score_rate_pp"] / 100,
            "v14_public_rating": v14["public_simulation_rating"],
            "a2_public_rating": a2["public_simulation_rating"],
            "rating_delta": comparison["online_v14_vs_a2_unadjusted"]["v14_minus_a2_public_simulation_rating"],
            "online_reorder_rate": agg["games_with_v14_reorder"] / agg["replays"],
            "archive_reproduction_rate": agg["archive_action_exact_reproduced"] / agg["replays"],
            "probe_replays": agg["replays"],
            "parent_a2_action_match_rate": parent_eq["equal_action_rate"],
            "full_parent_a2_game_share": parent_eq["exact_action_games"] / runtime["episodes"],
            "losses_full_parent_a2_share": loss_attr["losses_exact_parent_a2_all_719_calls"] / loss_attr["losses"],
            "local_activation_multiple": runtime_analysis["local_vs_online_mechanism"]["local_activation_multiple_over_online"],
            "current_team_rank": current_snapshot["team"]["rank"],
            "current_team_rating": current_snapshot["team"]["rating"],
            "active_a2_high_score": active_high_score,
            "active_a2_low_score": active_low_score,
            "active_a2_score_gap": active_copy_gap,
        }
    ]

    online_model_summary = []
    for label, key in [("V14", "v14"), ("A2 fixed", "a2"), ("V13C", "v13c")]:
        item = metric["online"][key]
        overall = item["overall"]
        dist = item["opponent_distribution"]
        strong_segment = dist.get("binary_2000_cut", {}).get("gte2000", dist.get("gte2000"))
        if not strong_segment:
            raise KeyError(f"Missing >=2000 opponent segment for {key}")
        online_model_summary.append(
            {
                "model": label,
                "submission_id": item["submission_id"],
                "public_rating": item["public_simulation_rating"],
                "games": overall["games"],
                "wins": overall["wins"],
                "ties": overall["ties"],
                "losses": overall["losses"],
                "wtl": f"{overall['wins']}/{overall['ties']}/{overall['losses']}",
                "pure_win_rate": overall["pure_win_rate"],
                "outcome_score_rate": overall["outcome_score_rate"],
                "ci_low": overall["ci95"][0],
                "ci_high": overall["ci95"][1],
                "ci95": f"{overall['ci95'][0]:.2%}–{overall['ci95'][1]:.2%}",
                "opponent_rating_proxy_mean": dist["rating_proxy"]["mean"],
                "opponent_rating_proxy_median": dist["rating_proxy"]["median"],
                "opponent_gte2000_share": strong_segment["share"],
                "public_window_hours": item.get("public_window", {}).get("elapsed_hours"),
            }
        )

    opponent_mix_long = []
    for label, key in [("V14", "v14"), ("A2 fixed", "a2")]:
        item = metric["online"][key]
        cut = item["opponent_distribution"]["binary_2000_cut"]
        for tier_key, tier_label in [("lt2000", "<2000"), ("gte2000", ">=2000")]:
            tier = cut[tier_key]
            opponent_mix_long.append(
                {
                    "model": label,
                    "opponent_tier": tier_label,
                    "rating_cut": 2000,
                    "games": tier["games"],
                    "opponent_share": tier["share"],
                    "wins": tier["wins"],
                    "losses": tier["losses"],
                    "score_rate": tier["score_rate"],
                    "total_model_games": item["overall"]["games"],
                    "opponent_rating_proxy_mean": item["opponent_distribution"]["rating_proxy"]["mean"],
                }
            )

    mechanism_long = []
    mechanism_specs = [
        ("exact-A2 对手", local_games, local_games, agg["exact_a2_opponent_games"], agg["replays"]),
        ("终局 shadow trusted", local_trusted, local_games, agg["games_shadow_trusted_at_end"], agg["replays"]),
        ("至少一次重排", local_reorder, local_games, agg["games_with_v14_reorder"], agg["replays"]),
    ]
    for metric_label, local_num, local_den, online_num, online_den in mechanism_specs:
        mechanism_long.extend(
            [
                {
                    "cohort": "本地 fixed A2",
                    "mechanism_metric": metric_label,
                    "numerator": local_num,
                    "games": local_den,
                    "rate": local_num / local_den,
                    "archive_action_reproduction_rate": None,
                },
                {
                    "cohort": "线上 replay probe",
                    "mechanism_metric": metric_label,
                    "numerator": online_num,
                    "games": online_den,
                    "rate": online_num / online_den,
                    "archive_action_reproduction_rate": agg["archive_action_exact_reproduced"] / agg["replays"],
                },
            ]
        )

    path_rows = []
    for label, key in [("V14", "v14"), ("A2 fixed", "a2")]:
        for window_key, values in metric["online"][key]["time_path"].items():
            if not isinstance(values, dict) or "games" not in values:
                continue
            path_rows.append(
                {
                    "model": label,
                    "window": window_key,
                    "games": values["games"],
                    "wins": values["wins"],
                    "ties": values["ties"],
                    "losses": values["losses"],
                    "score_rate": values["score_rate"],
                    "ci_low": values["ci95"][0],
                    "ci_high": values["ci95"][1],
                    "opponent_rating_proxy_mean": values["opponent_rating_proxy_mean"],
                }
            )

    runtime_summary_rows = [
        {
            "episodes": runtime["episodes"],
            "calls": runtime["calls"],
            "parent_equal_action_calls": parent_eq["equal_action_calls"],
            "parent_equal_action_rate": parent_eq["equal_action_rate"],
            "full_parent_a2_games": parent_eq["exact_action_games"],
            "games_with_any_action_difference": parent_eq["games_with_any_difference"],
            "exact_a2_opponent_games": runtime["exact_a2_opponent_games"],
            "terminal_shadow_trusted_games": runtime["first_public_shadow_fault"]["trusted_at_end_games"],
            "reorder_games": agg["games_with_v14_reorder"],
            "reorder_steps": reorder_total_steps,
            "losses": loss_attr["losses"],
            "losses_exact_parent_a2_all_719_calls": loss_attr["losses_exact_parent_a2_all_719_calls"],
            "local_reorders_per_game": runtime_analysis["local_vs_online_mechanism"]["local_reorders_per_game"],
            "online_reorders_per_game": runtime_analysis["local_vs_online_mechanism"]["online_reorders_per_game"],
            "local_activation_multiple_over_online": runtime_analysis["local_vs_online_mechanism"]["local_activation_multiple_over_online"],
            "common_opponent_submission_count": len(current_schedule["common_opponent_submissions"]),
            "v14_current_opponent_score_mean": current_schedule["v14"]["opponent_current_score"]["mean"],
            "a2_current_opponent_score_mean": current_schedule["a2"]["opponent_current_score"]["mean"],
        }
    ]
    submission_metadata = {
        int(item["ref"]): item for item in current_snapshot.get("all_our_submissions", [])
    }
    active_copy_rows = [
        {
            "submission_id": int(item["id"]),
            "submitted_at": item["dateSubmitted"],
            "public_score": float(item["publicScore"]),
            "model_family": "v12 A2 fixed repeat",
            "description": submission_metadata.get(int(item["id"]), {}).get("description"),
            "active_latest_two": True,
        }
        for item in current_snapshot["active_latest_two"]
    ]
    current_team_rows = [
        {
            "queried_at_taipei": current_snapshot["queried_at_taipei"],
            "team_id": current_snapshot["team"]["team_id"],
            "team_name": current_snapshot["team"]["team_name"],
            "rank": current_snapshot["team"]["rank"],
            "rating": current_snapshot["team"]["rating"],
            "active_submission_high": int(active_high["id"]),
            "active_submission_low": int(active_low["id"]),
            "active_a2_high_score": active_high_score,
            "active_a2_low_score": active_low_score,
            "active_a2_score_gap": active_copy_gap,
        }
    ]

    # Materialize the bounded reviewed rows into SQLite, then read them back
    # with the exact SQL carried by the canonical artifact sources. This keeps
    # source.query.sql truthful and runnable instead of inventing pseudo-SQL
    # for Python/JSON transformations.
    import pandas as pd

    source_tables = {
        "headline_metrics": headline_metrics,
        "online_model_summary": online_model_summary,
        "opponent_mix_long": opponent_mix_long,
        "mechanism_long": mechanism_long,
        "runtime_summary": runtime_summary_rows,
        "active_copy_summary": active_copy_rows,
        "current_team_summary": current_team_rows,
        "reorder_episode_summary": reorder_episode_rows,
        "time_path_windows": path_rows,
    }
    with sqlite3.connect(ARTIFACT_DB_PATH) as connection:
        for table_name, rows in source_tables.items():
            pd.DataFrame(rows).to_sql(table_name, connection, if_exists="replace", index=False)
        connection.commit()

        def sql_rows(sql: str) -> list[dict]:
            frame = pd.read_sql_query(sql, connection)
            return json.loads(frame.to_json(orient="records", force_ascii=False))

        headline_metrics = sql_rows("SELECT * FROM headline_metrics")
        online_model_summary = sql_rows("SELECT * FROM online_model_summary ORDER BY public_rating DESC")
        opponent_mix_long = sql_rows("SELECT * FROM opponent_mix_long ORDER BY model, opponent_tier")
        mechanism_long = sql_rows("SELECT * FROM mechanism_long ORDER BY mechanism_metric, cohort")
        runtime_summary_rows = sql_rows("SELECT * FROM runtime_summary")
        active_copy_rows = sql_rows("SELECT * FROM active_copy_summary ORDER BY public_score DESC")
        current_team_rows = sql_rows("SELECT * FROM current_team_summary")
        reorder_episode_rows = sql_rows("SELECT * FROM reorder_episode_summary ORDER BY episode_id")
        path_rows = sql_rows("SELECT * FROM time_path_windows ORDER BY model, window")

    sources = [
        {
            "id": "evaluation_rules",
            "label": "Kaggle official Evaluation CLI receipt",
            "path": "reporting/evaluation_rules_receipt.json",
            "query": {
                "engine": "kaggle-cli",
                "language": "text",
                "description": "Reads the official Kaggriculture Evaluation page through Kaggle CLI.",
                "executed_at": rules["retrieved_at_utc"],
                "filters": ["competition=kaggriculture", "page_name=Evaluation"],
                "metric_definitions": [
                    "Rating rises on wins, falls on losses, and generally moves closer on ties.",
                    "Rating change depends on the rating difference between opponents; coin margin is excluded.",
                    "Only the latest two submissions are tracked and used for final evaluation.",
                ],
                "tables_used": ["Kaggle competition page: kaggriculture/Evaluation"],
            },
        },
        {
            "id": "metric_audit",
            "label": "Independent online metric audit",
            "path": "metric_audit/independent_metric_audit.json",
            "query": {
                "engine": "python",
                "language": "python",
                "description": "Filters public episodes, recomputes W/T/L and intervals, joins opponent teams to one leaderboard snapshot, and performs the descriptive two-bin decomposition.",
                "executed_at": metric["generated_at_utc"],
                "filters": [
                    "episode.type=EPISODE_TYPE_PUBLIC",
                    "submissions=55722630,55713355,55719781",
                    "exclude one validation episode per submission",
                    "opponent proxy snapshot=2026-08-24T20:55:19+08:00",
                    "rating proxy cut=2000",
                ],
                "metric_definitions": [
                    "pure_win_rate=wins/public_games; ties are not wins",
                    "outcome_score_rate=(wins+0.5*ties)/public_games",
                    "opponent_rating_proxy=opponent team's current leaderboard Score at the saved snapshot, not pre-match rating",
                    "Public Rating is the saved submission publicScore and is not a win percentage.",
                ],
                "tables_used": [
                    "raw/v14/episodes_full.json",
                    "raw/a2/episodes_full.json",
                    "raw/v13c/episodes_full.json",
                    "raw/snapshot/kaggriculture_public_leaderboard.csv",
                ],
            },
        },
        {
            "id": "local_confirm",
            "label": "V14 paired fixed-opponent confirmatory replay",
            "path": "kaggle_Kaggriculture/model/v14_first_principles_search/validation/runs/confirmatory/v14_queue_stateful_no_mirror/games.jsonl",
            "query": {
                "engine": "python",
                "language": "python",
                "description": "Recomputes local fixed-A2 and r002 W/T/L by 100 source clusters with both candidate seats.",
                "filters": ["source dates=2026-08-18..2026-08-20", "100 sources", "both seats", "test=0"],
                "metric_definitions": [
                    "local pure win rate=wins/200 games; both seats for one source are a source cluster",
                    "local outcome score=(wins+0.5*ties)/200 games",
                ],
                "tables_used": ["games.jsonl"],
            },
        },
        {
            "id": "runtime_probe",
            "label": "V14 submitted-archive online replay probe",
            "path": "runtime_probe/runtime_probe.json",
            "query": {
                "engine": "python",
                "language": "python",
                "description": "Replays saved online observations through the actual submitted archive and attributes mechanisms only when every candidate action matches the replay.",
                "filters": ["saved public V14 replays only", "test access=false", "archive action exact reproduction required"],
                "metric_definitions": [
                    "exact-A2 opponent requires opponent actions to match fixed A2 throughout the replay",
                    "games_with_v14_reorder counts games with at least one additional SELL queue reorder",
                    "shadow_trusted_at_end counts games whose exact-A2 shadow conformance remained trusted through termination",
                ],
                "tables_used": ["raw/v14/replays/*.json", "v14_queue_best_response/submission.tar.gz"],
            },
        },
        {
            "id": "runtime_analysis",
            "label": "Final V14 runtime attribution",
            "path": "runtime_probe/runtime_analysis.json",
            "query": {
                "engine": "python",
                "language": "python",
                "description": "Aggregates archive-verified replay behavior, parent-A2 action equivalence, loss attribution, opponent overlap, and local-versus-online activation density.",
                "filters": ["87 saved public V14 replays", "archive action exact reproduction required", "no test access"],
                "metric_definitions": [
                    "parent_a2_action_match_rate=V14 calls identical to fixed parent A2 / all V14 calls",
                    "full_parent_a2_game_share=games with 719/719 parent-A2 actions / 87 games",
                    "local activation multiple=(2600/200 reorders per game)/(10/87 reorders per game)",
                    "losses_exact_parent_a2=losses with 719/719 V14 actions equal to parent A2",
                ],
                "tables_used": [
                    "runtime_probe/runtime_probe.json",
                    "raw/v14/episodes_full.json",
                    "raw/a2/episodes_full.json",
                    "raw/snapshot/kaggriculture_public_leaderboard.csv",
                ],
            },
        },
        {
            "id": "data_inventory",
            "label": "Current Kaggle CLI data inventory",
            "path": "data_inventory.json",
            "query": {
                "engine": "kaggle-cli",
                "language": "text",
                "description": "Preserves current team rank/rating, latest-two active submissions, historical target statuses, and source hashes at one bounded CLI snapshot.",
                "executed_at": current_snapshot["queried_at_utc"],
                "filters": ["team_id=16731605", "competition=kaggriculture", "snapshot=2026-08-24T21:29:19+08:00"],
                "metric_definitions": [
                    "current team rating is the leaderboard value at query time",
                    "active latest two are the two submissions tracked by the current leaderboard snapshot",
                    "historical V14/A2/V13C scores are inactive frozen submission values",
                ],
                "tables_used": ["Kaggle CLI submissions", "Kaggle CLI team-submissions", "Kaggle CLI leaderboard"],
            },
        },
        {
            "id": "mechanism_comparison",
            "label": "Local-versus-online mechanism comparison",
            "path": "reporting/outputs/mechanism_summary.csv",
            "query": {
                "engine": "python",
                "language": "python",
                "description": "Combines audited local fixed-A2 mechanism counters with archive-verified online replay probe counters.",
                "filters": ["local opponent=fixed A2", "online attribution requires exact archive action reproduction"],
                "metric_definitions": ["rate=numerator/games for each cohort and mechanism condition"],
                "tables_used": [
                    "metric_audit/independent_metric_audit.json",
                    "runtime_probe/runtime_probe.json",
                    "reporting/outputs/mechanism_summary.csv",
                ],
            },
        },
    ]
    sqlite_source_path = "reporting/outputs/artifact_source_tables.sqlite"
    sources.extend(
        [
            {
                "id": "local_card_sql",
                "label": "Local fixed-A2 headline metrics",
                "path": sqlite_source_path,
                "query": {
                    "engine": "sqlite",
                    "language": "sql",
                    "sql": "SELECT local_a2_win_rate, local_a2_outcome_score, local_a2_games FROM headline_metrics",
                    "description": "Returns the local fixed-A2 card metrics from the reviewed bounded snapshot table.",
                    "executed_at": generated_at,
                    "filters": ["source dates=2026-08-18..2026-08-20", "fixed opponent=A2", "both seats", "test=0"],
                    "metric_definitions": ["local_a2_win_rate=wins/200 games", "local_a2_outcome_score=(wins+0.5*ties)/200 games"],
                    "tables_used": ["headline_metrics"],
                },
            },
            {
                "id": "online_card_sql",
                "label": "V14 online win-rate headline metrics",
                "path": sqlite_source_path,
                "query": {
                    "engine": "sqlite",
                    "language": "sql",
                    "sql": "SELECT v14_online_win_rate, a2_online_win_rate, online_win_rate_delta FROM headline_metrics",
                    "description": "Returns the V14 and A2 public-episode rates and their unweighted difference.",
                    "executed_at": generated_at,
                    "filters": ["public episodes only", "validation excluded"],
                    "metric_definitions": ["win rate=wins/public games", "online_win_rate_delta=V14 win rate-A2 win rate"],
                    "tables_used": ["headline_metrics"],
                },
            },
            {
                "id": "rating_card_sql",
                "label": "Saved submission Public Rating metrics",
                "path": sqlite_source_path,
                "query": {
                    "engine": "sqlite",
                    "language": "sql",
                    "sql": "SELECT v14_public_rating, a2_public_rating, rating_delta FROM headline_metrics",
                    "description": "Returns the saved V14/A2 submission publicScore values and their difference.",
                    "executed_at": generated_at,
                    "filters": ["submission V14=55722630", "submission A2=55713355"],
                    "metric_definitions": ["rating_delta=V14 Public Rating-A2 Public Rating"],
                    "tables_used": ["headline_metrics"],
                },
            },
            {
                "id": "runtime_card_sql",
                "label": "Parent-A2 equivalence headline metrics",
                "path": sqlite_source_path,
                "query": {
                    "engine": "sqlite",
                    "language": "sql",
                    "sql": "SELECT parent_a2_action_match_rate, online_reorder_rate, archive_reproduction_rate, probe_replays FROM headline_metrics",
                    "description": "Returns archive-verified parent-A2 action equivalence and online reorder coverage.",
                    "executed_at": generated_at,
                    "filters": ["87 saved V14 public replays", "archive action exact reproduction required"],
                    "metric_definitions": ["parent_a2_action_match_rate=62543/62553 calls", "online_reorder_rate=8/87 games"],
                    "tables_used": ["headline_metrics"],
                },
            },
            {
                "id": "current_status_sql",
                "label": "Current team leaderboard status",
                "path": sqlite_source_path,
                "query": {
                    "engine": "sqlite",
                    "language": "sql",
                    "sql": "SELECT * FROM current_team_summary",
                    "description": "Returns the current team rank/rating and active latest-two A2 repeat scores at the saved snapshot.",
                    "executed_at": current_snapshot["queried_at_utc"],
                    "filters": ["team_id=16731605", "latest two active submissions"],
                    "metric_definitions": ["active_a2_score_gap=1519.3-1275.4", "rank and rating are the current team leaderboard values at query time"],
                    "tables_used": ["current_team_summary"],
                },
            },
            {
                "id": "active_copy_sql",
                "label": "Active A2 repeat score paths",
                "path": sqlite_source_path,
                "query": {
                    "engine": "sqlite",
                    "language": "sql",
                    "sql": "SELECT * FROM active_copy_summary ORDER BY public_score DESC",
                    "description": "Returns the two active v12 A2 fixed repeats and their same-snapshot public scores.",
                    "executed_at": current_snapshot["queried_at_utc"],
                    "filters": ["submission_id in (55743133,55743125)", "active_latest_two=true"],
                    "metric_definitions": ["score gap=higher repeat publicScore-lower repeat publicScore"],
                    "tables_used": ["active_copy_summary"],
                },
            },
            {
                "id": "online_summary_sql",
                "label": "Online submission comparison table",
                "path": sqlite_source_path,
                "query": {
                    "engine": "sqlite",
                    "language": "sql",
                    "sql": "SELECT * FROM online_model_summary ORDER BY public_rating DESC",
                    "description": "Returns reviewed V14, A2 fixed, and V13C public-episode outcomes, intervals, saved Rating, and frozen opponent proxy fields.",
                    "executed_at": generated_at,
                    "filters": ["public episodes only", "validation excluded", "three target submissions"],
                    "metric_definitions": ["pure_win_rate=wins/games", "ci95=Wilson interval", "opponent proxy fields use the frozen metric-audit snapshot"],
                    "tables_used": ["online_model_summary"],
                },
            },
            {
                "id": "opponent_mix_sql",
                "label": "Frozen opponent-strength proxy composition",
                "path": sqlite_source_path,
                "query": {
                    "engine": "sqlite",
                    "language": "sql",
                    "sql": "SELECT * FROM opponent_mix_long ORDER BY model, opponent_tier",
                    "description": "Returns the frozen <2000 versus >=2000 post-outcome opponent team Score proxy composition and within-tier outcomes.",
                    "executed_at": generated_at,
                    "filters": ["models=V14,A2 fixed", "rating proxy cut=2000", "frozen audit snapshot=2026-08-24T20:55:19+08:00"],
                    "metric_definitions": ["opponent_share=games in tier/all public games", "score_rate=wins/games because ties=0"],
                    "tables_used": ["opponent_mix_long"],
                },
            },
            {
                "id": "mechanism_chart_sql",
                "label": "Local-versus-online mechanism condition rates",
                "path": sqlite_source_path,
                "query": {
                    "engine": "sqlite",
                    "language": "sql",
                    "sql": "SELECT * FROM mechanism_long ORDER BY mechanism_metric, cohort",
                    "description": "Returns exact-A2 coverage, terminal shadow trust, and reorder-game rates for local fixed-A2 and online replay cohorts.",
                    "executed_at": generated_at,
                    "filters": ["local=fixed A2 confirm", "online=archive-verified 87 public replays"],
                    "metric_definitions": ["rate=numerator/games within cohort"],
                    "tables_used": ["mechanism_long"],
                },
            },
            {
                "id": "runtime_summary_sql",
                "label": "Final runtime attribution summary",
                "path": sqlite_source_path,
                "query": {
                    "engine": "sqlite",
                    "language": "sql",
                    "sql": "SELECT * FROM runtime_summary",
                    "description": "Returns parent-A2 action equivalence, loss attribution, activation-density, opponent-overlap, and current schedule proxy fields.",
                    "executed_at": generated_at,
                    "filters": ["87 archive-verified V14 public replays", "A2 submission 55713355", "no test access"],
                    "metric_definitions": ["parent_equal_action_rate=62543/62553", "local_activation_multiple=13.0/0.1149425", "common opponent submission count uses exact submissionId"],
                    "tables_used": ["runtime_summary"],
                },
            },
        ]
    )
    # These are file-backed sources, not SQL queries. The artifact validator
    # requires structured cards/charts to avoid pseudo-SQL in source.query.sql,
    # so keep the exact transformation/definition notes in package_info and
    # expose canonical file paths through sourceId.
    source_notes = {}
    for source in sources:
        query = source.get("query")
        if query and not query.get("sql"):
            source_notes[source["id"]] = source.pop("query")

    title = "V14 本地胜 A2、线上 Rating 更低：技术诊断"
    report_blocks = [
        {"id": "title", "type": "markdown", "body": f"# {title}"},
        {
            "id": "executive_summary",
            "type": "markdown",
            "body": (
                "## Executive Summary\n\n"
                f"- **没有未加权胜率崩塌。** V14 本地对 fixed A2 纯胜率为 {local_a2['pure_win_rate']:.2%}；线上 V14 为 {v14['overall']['pure_win_rate']:.2%}。\n"
                f"- **量纲和赛程不同。** V14 线上纯胜率比 A2 高 {comparison['online_v14_vs_a2_unadjusted']['v14_minus_a2_outcome_score_rate_pp']:.2f}pp，却以低 {abs(comparison['online_v14_vs_a2_unadjusted']['v14_minus_a2_public_simulation_rating']):.1f} 的 Public Rating 收尾；官方规则明确 Rating 还按双方 Rating 差加权，金币差无效。\n"
                f"- **不是同对手检验。** V14/A2 共同 opponent submission 为 0；当前对手分数均值约 {current_schedule['v14']['opponent_current_score']['mean']:.1f}/{current_schedule['a2']['opponent_current_score']['mean']:.1f}，赛程明显不同。\n"
                f"- **V14 线上几乎就是父 A2。** {parent_eq['equal_action_calls']}/{runtime['calls']}（{parent_eq['equal_action_rate']:.3%}）动作相同；21 个负局中 {loss_attr['losses_exact_parent_a2_all_719_calls']} 局为 719/719 父 A2 动作。\n"
                f"- **本地只 holdout 环境 seed。** 0818–0820 的闭环对手仍固定 A2/r002，没有 holdout 对手策略谱系；线上 exact-A2=0，重排仅 {agg['games_with_v14_reorder']}/{agg['replays']} 局。\n"
                f"- **当前路径证据。** 截至 {current_snapshot['queried_at_taipei']}，团队 rank {current_snapshot['team']['rank']}、Rating {current_snapshot['team']['rating']:.1f}；两个 active 的相同 A2 复投为 {active_high_score:.1f}/{active_low_score:.1f}，同一快照相差 {active_copy_gap:.1f} 分；旧 V14/A2/V13C 均已 inactive frozen。\n"
                "- **543.8 分仍不可识别。** episode/replay 不含逐局 pre/post Rating，不能伪造精确 ELO 点数归因。"
            ),
        },
        {"id": "headline_metrics", "type": "metric-strip", "cardIds": ["local_win", "online_win", "public_rating", "current_team", "active_copy_gap", "mechanism_trigger"]},
        {
            "id": "same_copy_path_evidence",
            "type": "markdown",
            "sourceId": "current_status_sql",
            "body": (
                "## 同一个 A2 复投也出现 243.9 分路径分叉\n\n"
                f"截至 {current_snapshot['queried_at_taipei']}，团队当前 rank {current_snapshot['team']['rank']}、Rating {current_snapshot['team']['rating']:.1f}。两个 active 的相同 v12 A2 fixed 复投 55743133/55743125 在同一快照分别为 {active_high_score:.1f}/{active_low_score:.1f}，相差 {active_copy_gap:.1f}。这直接证明 live Rating 会被比赛路径和对手抽样显著分叉；但当前快照没有把两副本游戏数配平，243.9 不能当作通用噪声标准差。"
            ),
        },
        {
            "id": "metric_mismatch_heading",
            "type": "markdown",
            "sourceId": "online_summary_sql",
            "body": (
                "## 未加权胜率与 Rating 的方向确实相反\n\n"
                "V14 的公开局纯胜率最高，但 Rating 低于 A2；V13C 以更低胜率取得更高 Rating，是第二个反例。柱形图只画同单位的胜率，精确 Rating 与样本量放在紧随其后的表中。"
            ),
        },
        {"id": "online_win_chart_block", "type": "chart", "chartId": "online_win_chart"},
        {"id": "online_summary_table_block", "type": "table", "tableId": "online_summary_table"},
        {
            "id": "opponent_mix_heading",
            "type": "markdown",
            "sourceId": "opponent_mix_sql",
            "body": (
                "## 对手构成足以消除高总胜率的表象\n\n"
                f"V14 与 A2 的未调整胜率差为 +{decomp['raw_v14_minus_a2_score_rate_pp']:.2f}pp；两层恒等分解得到对手构成项 +{decomp['opponent_mix_component_pp']:.2f}pp、层内表现项 {decomp['within_bin_performance_component_pp']:+.2f}pp。当前团队 Score 是赛后代理，图表只能作描述性分层，不能复原逐局 Rating。"
            ),
        },
        {"id": "opponent_mix_chart_block", "type": "chart", "chartId": "opponent_mix_chart"},
        {
            "id": "mechanism_heading",
            "type": "markdown",
            "sourceId": "runtime_analysis",
            "body": (
                "## 本地高覆盖的新增机制，线上只在短暂 A2-compatible 前缀触发\n\n"
                f"本地 fixed-A2 中 shadow trusted 为 {local_trusted}/{local_games}，平均 13.00 重排/局；线上 probe 为 {agg['exact_a2_opponent_games']}/{agg['replays']} exact-A2、{agg['games_shadow_trusted_at_end']}/{agg['replays']} 终局 trusted、{agg['games_with_v14_reorder']}/{agg['replays']} 重排局。8 局共 {reorder_total_steps} 个重排步、结果 {reorder_wins}/{reorder_ties}/{reorder_losses}；全部发生在首次可观测 mismatch 前，wrong-current-shadow 重排步为 {wrong_shadow_reorder_steps}。线上激活密度只有 0.115/局，较本地低 113.1 倍。\n\n"
                f"更关键的是，V14 有 {parent_eq['equal_action_calls']}/{runtime['calls']} 个动作等于父 A2，{parent_eq['exact_action_games']}/{runtime['episodes']} 局全程相同；21 个负局中 {loss_attr['losses_exact_parent_a2_all_719_calls']} 局完全是父 A2 动作。重排局没有禁用重排的同 seed 反事实，不能据 7/1 判断机制有效或有害。"
            ),
        },
        {"id": "mechanism_chart_block", "type": "chart", "chartId": "mechanism_chart"},
        {
            "id": "scope_methods",
            "type": "markdown",
            "body": (
                "## 范围、定义与方法\n\n"
                "- 公开局只保留 `EPISODE_TYPE_PUBLIC`；每个 submission 的 validation 均排除。\n"
                "- `pure win rate = wins / public games`；`outcome score = (wins + 0.5 * ties) / public games`。\n"
                "- 本地 confirm 使用 2026-08-18 至 2026-08-20 的 100 个 source、固定 A2/r002、每个 source 双席位；本地置信区间按 source cluster。\n"
                "- 0818–0820 留出的只是环境 seed；闭环对手仍固定 A2/r002，因此没有验证对手策略谱系外推。\n"
                "- 对手强度使用 2026-08-24 同一时点排行榜团队 Score，三组连接率 100%；它不是逐局赛前 Rating。\n"
                "- 官方 Evaluation CLI receipt 说明：胜/负/平改变 Rating；改变量取决于双方 Rating 差；金币差不计入；只追踪最新两个 submission。本文不假设具体 ELO 公式。"
            ),
        },
        {
            "id": "limitations",
            "type": "markdown",
            "body": (
                "## 限制、不确定性与稳健性\n\n"
                f"**已证实：** V14 没有未加权胜率坍塌；V14/A2 没有共同 opponent submission；V14 {parent_eq['equal_action_rate']:.3%} 动作等于父 A2；archive-verified probe 中新增重排仅低覆盖触发，且终局 shadow trusted 为 0。\n\n"
                "**描述性证据：** 更容易的 V14 对手池、强对手段较差表现与最后 7 局 2/5，一致指向高总胜率未转化为高 Rating。\n\n"
                "**数据快照限制：** metric audit 生成后排行榜文件被刷新；20:55 的两层分解以 audit JSON 冻结聚合为准，较新的 runtime mapping 方向相同但不是同一时点。\n\n"
                "**未知：** 543.8 分中对手强度、顺序、更新参数和冻结时点各贡献多少；逐局 pre/post Rating 与精确更新公式不可见。可精确分摊为 0 分，含义是不可识别，不是影响为零。\n\n"
                f"线上未加权胜率差 bootstrap 95% CI 为 {comparison['online_v14_vs_a2_unadjusted']['independent_difference_ci95_bootstrap_pp'][0]:.2f}pp 至 {comparison['online_v14_vs_a2_unadjusted']['independent_difference_ci95_bootstrap_pp'][1]:.2f}pp，包含 0；不能声称 V14 泛化显著优于 A2。"
            ),
        },
        {
            "id": "next_steps",
            "type": "markdown",
            "body": (
                "## 建议的下一步\n\n"
                "1. 线上验收固定双报告：`W/T/L + outcome score + CI` 与 `Public Rating`。\n"
                "2. 保留 fixed A2/r002 克制门槛，同时增加按线上强度分层且 holdout 对手策略谱系的异质专家联赛，继续同 seed 双席位。\n"
                "3. 新增机制必须同时报告 exact-opponent 覆盖率、shadow trusted 率和实际触发率。\n"
                "4. 只有拿到逐局双方 pre-rating、候选 post-rating 与应用顺序后，才做 Rating 点数归因。"
            ),
        },
        {
            "id": "further_questions",
            "type": "markdown",
            "body": (
                "## 尚待回答\n\n"
                "- V14 在真实 `>=2000` 对手池目前只有 23 局，区间仍宽，需要预注册更大的强对手样本。\n"
                "- 匹配器是否按即时 Rating 主动分层，以及 inactive submission 的冻结规则，现有数据只能观察相关路径，不能证明机制。"
            ),
        },
    ]

    manifest = {
        "version": 1,
        "surface": "report",
        "title": title,
        "description": "A technical diagnosis of why V14 beats fixed A2 locally yet ends with a lower online Simulation Rating.",
        "generatedAt": generated_at,
        "cards": [
            {
                "id": "local_win",
                "description": "2026-08-18 to 2026-08-20; 100 source clusters, both seats, fixed A2.",
                "dataset": "headline_metrics",
                "sourceId": "local_card_sql",
                "metrics": [
                    {"label": "本地对A2纯胜率", "field": "local_a2_win_rate", "format": "percent"},
                    {"label": "outcome score", "field": "local_a2_outcome_score", "format": "percent"},
                ],
            },
            {
                "id": "online_win",
                "description": "V14 public episodes only; validation excluded.",
                "dataset": "headline_metrics",
                "sourceId": "online_card_sql",
                "metrics": [
                    {"label": "V14线上纯胜率", "field": "v14_online_win_rate", "format": "percent"},
                    {"label": "相对A2", "field": "online_win_rate_delta", "format": "percent", "signed": True},
                ],
            },
            {
                "id": "public_rating",
                "description": "Saved V14 submission publicScore; not a win percentage.",
                "dataset": "headline_metrics",
                "sourceId": "rating_card_sql",
                "metrics": [
                    {"label": "V14 Public Rating", "field": "v14_public_rating", "format": "number"},
                    {"label": "相对A2", "field": "rating_delta", "format": "number", "signed": True},
                ],
            },
            {
                "id": "mechanism_trigger",
                "description": f"Online replay probe, n={agg['replays']}; attribution requires exact archive action reproduction.",
                "dataset": "headline_metrics",
                "sourceId": "runtime_card_sql",
                "metrics": [
                    {"label": "动作等于父A2", "field": "parent_a2_action_match_rate", "format": "percent"},
                    {"label": "重排局占比", "field": "online_reorder_rate", "format": "percent"},
                ],
            },
            {
                "id": "current_team",
                "description": f"Kaggle CLI snapshot at {current_snapshot['queried_at_taipei']}.",
                "dataset": "current_team_summary",
                "sourceId": "current_status_sql",
                "metrics": [
                    {"label": "当前团队排名", "field": "rank", "format": "number"},
                    {"label": "当前Rating", "field": "rating", "format": "number"},
                ],
            },
            {
                "id": "active_copy_gap",
                "description": "Same-snapshot score gap between two active v12 A2 fixed repeats.",
                "dataset": "current_team_summary",
                "sourceId": "current_status_sql",
                "metrics": [
                    {"label": "A2复投分差", "field": "active_a2_score_gap", "format": "number"},
                    {"label": "较高副本", "field": "active_a2_high_score", "format": "number"},
                    {"label": "较低副本", "field": "active_a2_low_score", "format": "number"},
                ],
            },
        ],
        "charts": [
            {
                "id": "online_win_chart",
                "title": "公开局纯胜率",
                "subtitle": "V14 raw win rate highest, while the following table shows its Rating remains below A2.",
                "showDescription": True,
                "intent": "comparison",
                "question": "How do unweighted public win rates compare across V14, A2 fixed, and V13C?",
                "rationale": "A zero-based bar chart is the most honest comparison for three submission-level rates; Rating is kept out because it has a different unit.",
                "comparisonContext": {"denominator": "completed public episodes", "grain": "submission", "unit": "rate"},
                "type": "bar",
                "dataset": "online_model_summary",
                "sourceId": "online_summary_sql",
                "encodings": {
                    "x": {"field": "model", "type": "nominal", "label": "版本"},
                    "y": {"field": "pure_win_rate", "type": "quantitative", "format": "percent", "label": "纯胜率"},
                    "tooltip": [
                        {"field": "games", "type": "quantitative", "label": "公开局"},
                        {"field": "wins", "type": "quantitative", "label": "胜"},
                        {"field": "losses", "type": "quantitative", "label": "负"},
                        {"field": "public_rating", "type": "quantitative", "label": "Public Rating"},
                        {"field": "opponent_rating_proxy_mean", "type": "quantitative", "label": "对手Rating代理均值"},
                    ],
                },
                "valueFormat": "percent",
                "layout": "full",
                "maxRows": 3,
                "palette": {"kind": "sequential", "name": "blue"},
                "labels": {"values": "all"},
                "settings": {"orientation": "vertical", "groupMode": "single", "showValues": True, "sort": "none"},
                "surface": {"surface": "card", "showControls": True, "viewMode": "both"},
            },
            {
                "id": "opponent_mix_chart",
                "title": "对手当前 Rating 代理构成",
                "subtitle": "V14 faces a materially smaller >=2000 share; the proxy is post-outcome and descriptive only.",
                "showDescription": True,
                "intent": "composition",
                "question": "What share of each submission's opponents falls below or above the 2000 current-rating proxy cut?",
                "rationale": "A 100% stacked bar compares two opponent-strength compositions without mixing the within-bin outcome rates.",
                "comparisonContext": {"denominator": "all completed public episodes for each submission", "grain": "submission by proxy tier", "unit": "share"},
                "type": "stackedBar100",
                "dataset": "opponent_mix_long",
                "sourceId": "opponent_mix_sql",
                "encodings": {
                    "x": {"field": "model", "type": "nominal", "label": "版本"},
                    "y": {"field": "opponent_share", "type": "quantitative", "format": "percent", "label": "对手占比"},
                    "color": {"field": "opponent_tier", "type": "nominal", "label": "当前Rating代理分层"},
                    "tooltip": [
                        {"field": "games", "type": "quantitative", "label": "局数"},
                        {"field": "wins", "type": "quantitative", "label": "胜"},
                        {"field": "losses", "type": "quantitative", "label": "负"},
                        {"field": "score_rate", "type": "quantitative", "format": "percent", "label": "分层score"},
                    ],
                },
                "valueFormat": "percent",
                "layout": "full",
                "maxRows": 4,
                "palette": {"kind": "categorical", "name": "blue-orange"},
                "legend": {"position": "bottom", "sort": "spec", "title": "当前Rating代理分层"},
                "labels": {"values": "all"},
                "settings": {"orientation": "vertical", "groupMode": "stacked100", "showPercent": True, "showValues": True, "sort": "none"},
                "surface": {"surface": "card", "showControls": True, "viewMode": "both"},
            },
            {
                "id": "mechanism_chart",
                "title": "V14 新增机制的适用条件与实际触发",
                "subtitle": f"Local fixed-A2 n={local_games}; online archive-verified replay probe n={agg['replays']}.",
                "showDescription": True,
                "intent": "comparison",
                "question": "How often do the exact-A2 condition, terminal trusted shadow, and reorder activation occur locally versus online?",
                "rationale": "Grouped bars compare the same three condition rates across the two cohorts.",
                "comparisonContext": {"denominator": "games in each cohort", "grain": "cohort by mechanism condition", "unit": "share"},
                "type": "bar",
                "dataset": "mechanism_long",
                "sourceId": "mechanism_chart_sql",
                "encodings": {
                    "x": {"field": "mechanism_metric", "type": "nominal", "label": "机制条件"},
                    "y": {"field": "rate", "type": "quantitative", "format": "percent", "label": "局数占比"},
                    "color": {"field": "cohort", "type": "nominal", "label": "样本"},
                    "tooltip": [
                        {"field": "numerator", "type": "quantitative", "label": "满足局数"},
                        {"field": "games", "type": "quantitative", "label": "总局数"},
                        {"field": "archive_action_reproduction_rate", "type": "quantitative", "format": "percent", "label": "archive复现率"},
                    ],
                },
                "valueFormat": "percent",
                "layout": "full",
                "maxRows": 6,
                "palette": {"kind": "categorical", "name": "blue-orange"},
                "legend": {"position": "bottom", "sort": "spec", "title": "样本"},
                "labels": {"values": "all"},
                "settings": {"orientation": "vertical", "groupMode": "grouped", "showValues": True, "sort": "none"},
                "surface": {"surface": "card", "showControls": True, "viewMode": "both"},
            },
        ],
        "tables": [
            {
                "id": "online_summary_table",
                "title": "三个版本的公开局与冻结 Rating",
                "subtitle": "Validation excluded; opponent strength uses one post-outcome team leaderboard snapshot.",
                "showDescription": True,
                "dataset": "online_model_summary",
                "defaultSort": {"field": "public_rating", "direction": "desc"},
                "density": "spacious",
                "sourceId": "online_summary_sql",
                "layout": "full",
                "columns": [
                    {"field": "model", "label": "版本", "type": "text"},
                    {"field": "submission_id", "label": "Submission", "format": "number"},
                    {"field": "public_rating", "label": "Public Rating", "format": "number"},
                    {"field": "wtl", "label": "W/T/L", "type": "text"},
                    {"field": "pure_win_rate", "label": "纯胜率", "format": "percent"},
                    {"field": "ci95", "label": "Wilson 95% CI", "type": "text"},
                    {"field": "opponent_rating_proxy_mean", "label": "对手Rating代理均值", "format": "number"},
                    {"field": "opponent_gte2000_share", "label": ">=2000占比", "format": "percent"},
                ],
            }
        ],
        "sources": sources,
        "blocks": report_blocks,
    }

    snapshot = {
        "version": 1,
        "generatedAt": generated_at,
        "status": "ready",
        "datasets": {
            "headline_metrics": headline_metrics,
            "online_model_summary": online_model_summary,
            "opponent_mix_long": opponent_mix_long,
            "mechanism_long": mechanism_long,
            "runtime_summary": runtime_summary_rows,
            "active_copy_summary": active_copy_rows,
            "current_team_summary": current_team_rows,
            "reorder_episode_summary": reorder_episode_rows,
            "time_path_windows": path_rows,
        },
    }

    return {
        "surface": "report",
        "manifest": manifest,
        "snapshot": snapshot,
        "sources": sources,
        "package_info": {
            "artifact_kind": "technical_report",
            "notebook": "reporting/v14_online_diagnosis.ipynb",
            "analysis_summary": "reporting/outputs/analysis_summary.json",
            "evaluation_receipt_sha256": rules["content_sha256"],
            "metric_audit_sha256": sha256(METRIC_PATH),
            "runtime_probe_sha256": sha256(PROBE_PATH),
            "runtime_analysis_sha256": sha256(RUNTIME_ANALYSIS_PATH),
            "data_inventory_sha256": sha256(DATA_INVENTORY_PATH),
            "scope_guard": "saved data only; no new games, test access, strategy changes, Kaggle submission, or browser",
            "source_notes": source_notes,
        },
    }


def main() -> None:
    REPORTING_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTING_DIR / "figures").mkdir(exist_ok=True)
    (REPORTING_DIR / "outputs").mkdir(exist_ok=True)

    metric = load_json(METRIC_PATH)
    probe = load_json(PROBE_PATH)
    rules = load_json(RULES_PATH)

    notebook = make_notebook(metric, probe, rules)
    nbf.write(notebook, NOTEBOOK_PATH)

    client = NotebookClient(
        notebook,
        timeout=900,
        kernel_name="python3",
        resources={"metadata": {"path": str(REPORTING_DIR)}},
        allow_errors=False,
    )
    executed = client.execute()
    nbf.write(executed, NOTEBOOK_PATH)

    report_text = build_report(metric, probe, rules)
    REPORT_PATH.write_text(report_text, encoding="utf-8")

    artifact = build_artifact(metric, probe, rules)
    ARTIFACT_PATH.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")

    chart_map = {
        "schema": "v14-online-diagnosis-chart-map-v1",
        "charts": [
            {
                "path": "figures/01_metric_mismatch.png",
                "segment": "未加权胜率与 Rating 的方向确实相反",
                "question": "三个 submission 的未加权胜率与冻结 Rating 是否同序？",
                "family": "comparison",
                "type": "two-panel bar with Wilson intervals",
                "fields": ["model", "pure_win_rate", "ci_low", "ci_high", "public_rating", "games"],
                "claim": "V14 raw win rate highest but Rating below A2; metrics are not interchangeable.",
                "source": "official episodes_full.json plus saved submission publicScore",
            },
            {
                "path": "figures/02_opponent_mix.png",
                "segment": "对手构成足以消除高总胜率的表象",
                "question": "V14 与 A2 是否面对同难度对手，且同层表现如何？",
                "family": "composition and comparison",
                "type": "stacked bar plus grouped bar",
                "fields": ["model", "opponent_rating_proxy_bin", "games", "share", "score_rate"],
                "claim": "V14 sees fewer >=2000 proxy opponents and is weaker within that segment.",
                "limitation": "Current post-outcome team Score proxy, not per-game pre-rating; descriptive only.",
                "source": "official episodes_full.json plus leaderboard snapshot",
            },
            {
                "path": "figures/03_mechanism_activation.png",
                "segment": "本地高覆盖的新增机制，线上只在短暂 A2-compatible 前缀触发",
                "question": "V14 exact-A2 specialization conditions and reorder trigger occur how often locally vs online?",
                "family": "comparison",
                "type": "grouped bar",
                "fields": ["cohort", "exact_a2_share", "shadow_trusted_end_share", "games_with_reorder_share"],
                "claim": "Online probed replays contain no exact A2 or trusted terminal shadow, and reorder activates in only 8 of 87 games.",
                "validation": "Only archive action 100% reproduced replay games are attributed.",
                "source": "local confirmatory games plus runtime_probe.json",
            },
        ],
        "palette_policy": "hard two-root cap plus neutral",
        "qa_notes": "All percentage axes start at zero; direct labels include denominator or n; no causal title is used for the proxy decomposition.",
    }
    CHART_MAP_PATH.write_text(json.dumps(chart_map, ensure_ascii=False, indent=2), encoding="utf-8")

    expected_outputs = [
        NOTEBOOK_PATH,
        REPORT_PATH,
        ARTIFACT_PATH,
        SUMMARY_PATH,
        RULES_PATH,
        CHART_MAP_PATH,
        REPORTING_DIR / "figures" / "01_metric_mismatch.png",
        REPORTING_DIR / "figures" / "02_opponent_mix.png",
        REPORTING_DIR / "figures" / "03_mechanism_activation.png",
        REPORTING_DIR / "outputs" / "online_summary.csv",
        REPORTING_DIR / "outputs" / "opponent_mix_summary.csv",
        REPORTING_DIR / "outputs" / "mechanism_summary.csv",
        REPORTING_DIR / "outputs" / "parent_equivalence_summary.csv",
        REPORTING_DIR / "outputs" / "reorder_episode_summary.csv",
        REPORTING_DIR / "outputs" / "source_hash_check.csv",
        ARTIFACT_DB_PATH,
    ]
    missing = [str(path) for path in expected_outputs if not path.exists()]
    if missing:
        raise FileNotFoundError(missing)

    from PIL import Image

    figure_dimensions = {}
    for path in expected_outputs:
        if path.suffix == ".png":
            with Image.open(path) as image:
                figure_dimensions[path.name] = {"width": image.width, "height": image.height}
                if image.width < 1200 or image.height < 600:
                    raise AssertionError(f"Figure too small: {path} {image.size}")

    executed_code_cells = [cell for cell in executed.cells if cell.cell_type == "code"]
    error_outputs = [
        output
        for cell in executed_code_cells
        for output in cell.get("outputs", [])
        if output.get("output_type") == "error"
    ]
    if error_outputs:
        raise AssertionError(error_outputs)

    summary = load_json(SUMMARY_PATH)
    if summary["runtime_probe_replays"] != probe["aggregate"]["replays"]:
        raise AssertionError("Notebook/report runtime probe snapshot mismatch")

    artifact_check = load_json(ARTIFACT_PATH)
    source_hash_check = __import__("pandas").read_csv(REPORTING_DIR / "outputs" / "source_hash_check.csv")
    immutable_hash_mismatches = source_hash_check.loc[
        (~source_hash_check["match"]) & (~source_hash_check["volatile_snapshot"])
    ]
    if not immutable_hash_mismatches.empty:
        raise AssertionError(immutable_hash_mismatches)
    volatile_snapshot_drift_rows = int(
        ((~source_hash_check["match"]) & source_hash_check["volatile_snapshot"]).sum()
    )
    if artifact_check["surface"] != "report":
        raise AssertionError("artifact surface must be report")
    if artifact_check["manifest"]["blocks"][0].get("body") != f"# {artifact_check['manifest']['title']}":
        raise AssertionError("first reader-facing block must be the visible title")
    if not artifact_check["manifest"]["blocks"][1].get("body", "").startswith("## Executive Summary"):
        raise AssertionError("second reader-facing block must be Executive Summary")
    if not artifact_check["manifest"].get("charts"):
        raise AssertionError("artifact must contain at least one native chart")
    if not artifact_check["manifest"].get("cards") or not artifact_check["manifest"].get("tables"):
        raise AssertionError("artifact must contain metric cards and a table")
    source_ids = {source["id"] for source in artifact_check["manifest"]["sources"]}
    for item_type in ["cards", "charts", "tables"]:
        for item in artifact_check["manifest"].get(item_type, []):
            if item.get("sourceId") not in source_ids and not item.get("source"):
                raise AssertionError(f"Missing canonical provenance: {item_type}/{item.get('id')}")

    qa = {
        "schema": "v14-online-diagnosis-reporting-qa-v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "PASS",
        "notebook": {
            "path": NOTEBOOK_PATH.name,
            "executed_top_to_bottom": True,
            "code_cells": len(executed_code_cells),
            "error_outputs": len(error_outputs),
            "sha256": sha256(NOTEBOOK_PATH),
        },
        "canonical_artifact": {
            "path": ARTIFACT_PATH.name,
            "surface": artifact_check["surface"],
            "visible_title": artifact_check["manifest"]["title"],
            "blocks": len(artifact_check["manifest"]["blocks"]),
            "cards": len(artifact_check["manifest"]["cards"]),
            "charts": len(artifact_check["manifest"]["charts"]),
            "tables": len(artifact_check["manifest"]["tables"]),
            "source_count": len(source_ids),
            "snapshot_status": artifact_check["snapshot"]["status"],
            "snapshot_dataset_rows": {
                key: len(rows) for key, rows in artifact_check["snapshot"]["datasets"].items()
            },
            "sha256": sha256(ARTIFACT_PATH),
            "portable_html_created": False,
        },
        "runtime_probe_snapshot": {
            "replays": probe["aggregate"]["replays"],
            "archive_action_exact_reproduced": probe["aggregate"]["archive_action_exact_reproduced"],
            "exact_a2_opponent_games": probe["aggregate"]["exact_a2_opponent_games"],
            "games_with_v14_reorder": probe["aggregate"]["games_with_v14_reorder"],
            "games_shadow_trusted_at_end": probe["aggregate"]["games_shadow_trusted_at_end"],
        },
        "official_rules": {
            "receipt_content_sha256": rules["content_sha256"],
            "content_hash_revalidated_in_notebook": True,
        },
        "input_hashes": {
            "metric_audit": sha256(METRIC_PATH),
            "runtime_probe": sha256(PROBE_PATH),
            "runtime_analysis": sha256(RUNTIME_ANALYSIS_PATH),
            "data_inventory": sha256(DATA_INVENTORY_PATH),
            "evaluation_rules_receipt": sha256(RULES_PATH),
        },
        "data_drift": {
            "immutable_hash_mismatches": len(immutable_hash_mismatches),
            "volatile_snapshot_drift_rows": volatile_snapshot_drift_rows,
            "interpretation": "Leaderboard snapshot files refreshed after the frozen metric audit. The audit JSON preserves the earlier aggregate decomposition; current runtime mapping is reported separately.",
        },
        "figure_dimensions": figure_dimensions,
        "outputs": {str(path.relative_to(REPORTING_DIR)): sha256(path) for path in expected_outputs},
        "assertions": [
            "All immutable source_inventory SHA256 values matched; volatile leaderboard snapshot drift was detected and preserved as a caveat.",
            "Official Evaluation content SHA256 and UTF-8 byte length matched the receipt.",
            "W/T/L was recomputed from raw public episodes and matched the independent metric audit.",
            "Notebook executed top-to-bottom without error outputs.",
            "All three figures exceeded the minimum 1200x600 raster size.",
            "Report and notebook used the same runtime_probe replay count.",
            "All online reorder steps occurred before the first observable mismatch, and wrong-current-shadow reorder steps were zero.",
            "Canonical artifact has visible title, Executive Summary, metric cards, three native charts, a table, canonical sourceIds, and bounded snapshot datasets.",
            "No portable HTML report was created.",
        ],
        "scope_guard": "No new games, test access, strategy changes, Kaggle submission, or browser usage.",
    }
    QA_PATH.write_text(json.dumps(qa, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "PASS", "artifact": str(ARTIFACT_PATH), "report_source": str(REPORT_PATH), "notebook": str(NOTEBOOK_PATH), "probe_replays": probe["aggregate"]["replays"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
