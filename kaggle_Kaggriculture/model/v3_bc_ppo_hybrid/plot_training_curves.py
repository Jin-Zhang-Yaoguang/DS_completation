"""Render an auditable summary of the v3 PPO training run."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "training_report.json"
OUTPUT = ROOT / "ppo_learning_curves.png"


def moving_average(values: np.ndarray, window: int = 5) -> np.ndarray:
    result = np.full(values.shape, np.nan, dtype=np.float64)
    if len(values) >= window:
        result[window - 1 :] = np.convolve(values, np.ones(window) / window, mode="valid")
    return result


def main() -> None:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    history = report["history"]
    validation = report["snapshot_qualifications"]

    iterations = np.asarray([row["iteration"] for row in history])
    train_win = np.asarray([row["win_rate"] for row in history])
    train_win_ma = moving_average(train_win)
    kl = np.asarray([row["update"]["approximate_kl"] for row in history])
    clip_fraction = np.asarray([row["update"]["clip_fraction"] for row in history])
    throughput = np.asarray([row["episodes_per_second"] for row in history])

    val_iterations = np.asarray([row["iteration"] for row in validation])
    val_score = np.asarray([row["score_rate"] for row in validation])
    val_margin = np.asarray([row["mean_margin"] for row in validation])

    blue = "#1F5A85"
    gold = "#D49A00"
    orange = "#C65F24"
    gray = "#7B8794"
    green = "#318B5B"

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "axes.titlesize": 12,
            "axes.labelsize": 10,
            "xtick.labelsize": 9,
            "ytick.labelsize": 9,
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(13.5, 8.2), layout="constrained")
    fig.get_layout_engine().set(rect=(0.02, 0.045, 0.98, 0.90))
    fig.suptitle("Kaggriculture v3 — BC + PPO training evidence", y=0.985, fontsize=17, weight="bold")
    fig.text(
        0.5,
        0.943,
        "102,400 PPO episodes; validation every 5 rounds (64 games); selected checkpoint: round 40",
        ha="center",
        fontsize=10,
        color="#4A5560",
    )

    ax = axes[0, 0]
    ax.plot(iterations, train_win, color=blue, alpha=0.20, linewidth=1, label="Rollout win rate (raw)")
    ax.plot(iterations, train_win_ma, color=blue, linewidth=2.3, label="Rollout win rate (5-round avg)")
    ax.plot(val_iterations, val_score, color=gold, marker="o", linewidth=2.2, label="Fixed validation score rate")
    ax.scatter([40], [val_score[val_iterations.tolist().index(40)]], s=100, color=orange, zorder=5, label="Selected round 40")
    ax.axhline(0.8455, color=green, linestyle="--", linewidth=1.4, label="Independent test: 84.55%")
    ax.set_title("Policy performance")
    ax.set_xlabel("PPO round")
    ax.set_ylabel("Win / score rate")
    ax.set_ylim(0.45, 1.0)
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.legend(loc="lower right", fontsize=8, frameon=False)

    ax = axes[0, 1]
    ax.plot(val_iterations, val_margin, color=gold, marker="o", linewidth=2.2)
    ax.scatter([40], [val_margin[val_iterations.tolist().index(40)]], s=100, color=orange, zorder=5)
    ax.axhline(0, color=gray, linewidth=1)
    ax.annotate(
        "selected\n+894 coins/game",
        xy=(40, val_margin[val_iterations.tolist().index(40)]),
        xytext=(31, 420),
        arrowprops={"arrowstyle": "->", "color": orange},
        fontsize=9,
        color=orange,
    )
    ax.set_title("Fixed-validation mean margin vs v2")
    ax.set_xlabel("PPO round")
    ax.set_ylabel("Mean terminal coin margin")

    ax = axes[1, 0]
    ax.plot(iterations, kl, color=orange, linewidth=1.7, label="Approximate KL")
    ax.plot(iterations, clip_fraction, color=blue, linewidth=1.7, label="Clip fraction")
    ax.axhline(0.02, color=gray, linestyle="--", linewidth=1.2, label="Target KL = 0.02")
    ax.set_title("PPO update stability")
    ax.set_xlabel("PPO round")
    ax.set_ylabel("Fraction")
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper right", fontsize=8, frameon=False)

    ax = axes[1, 1]
    ax.plot(iterations, throughput, color=green, linewidth=1.8)
    trend = np.polyfit(iterations, throughput, 1)
    ax.plot(iterations, np.polyval(trend, iterations), color=gray, linestyle="--", linewidth=1.2, label="Linear trend")
    ax.set_title("Rollout throughput")
    ax.set_xlabel("PPO round")
    ax.set_ylabel("Episodes / second")
    ax.legend(loc="upper right", fontsize=8, frameon=False)

    for ax in axes.flat:
        ax.grid(axis="y", color="#DDE3E8", linewidth=0.7)
        ax.spines[["top", "right"]].set_visible(False)

    fig.text(
        0.01,
        0.012,
        "Source: training_report.json and evaluation_report.json. Training rollout rates are not directly comparable across rounds because the opponent league changes.",
        fontsize=8,
        color="#59636E",
    )
    fig.savefig(OUTPUT, dpi=180, bbox_inches="tight", facecolor="white")
    print(OUTPUT)


if __name__ == "__main__":
    main()
