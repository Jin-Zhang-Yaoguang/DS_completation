import pandas as pd
import matplotlib.pyplot as plt

evaluation = pd.DataFrame([
    ["latest v57 streams", 58, 58, 17136.7, 700],
    ["v55 archive A", 40, 40, 3908.0, 10],
    ["v55 archive B", 58, 58, 6885.1, 198],
    ["v56 hotfix archive", 40, 40, 36720.9, 2097],
    ["Akira archive", 42, 42, 23883.2, 2126],
], columns=["panel", "wins", "games", "mean_margin", "worst_margin"])
evaluation["win_rate"] = evaluation.wins / evaluation.games
display(evaluation)

fig, axes = plt.subplots(1, 2, figsize=(11, 4))
evaluation.plot.bar(x="panel", y="win_rate", ylim=(0, 1.05), ax=axes[0],
                    legend=False, color="#2563eb", title="Known frozen win rate")
evaluation.plot.bar(x="panel", y="worst_margin", ax=axes[1],
                    legend=False, color="#0f766e", title="Worst margin")
for ax in axes:
    ax.set_xlabel("")
    ax.grid(axis="y", alpha=0.2)
    ax.tick_params(axis="x", rotation=18)
plt.tight_layout()