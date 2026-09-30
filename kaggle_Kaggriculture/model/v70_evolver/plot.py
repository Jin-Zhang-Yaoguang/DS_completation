"""评估曲线:runs/<run>/history.jsonl -> evolution_curve.png(类比 loss 曲线)。
用法: python plot.py [run 名,默认 default]
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
run = sys.argv[1] if len(sys.argv) > 1 else "default"
rows = [json.loads(l) for l in (HERE / "runs" / run / "history.jsonl").open()]
gens = [r["gen"] for r in rows]
plt.figure(figsize=(8, 4.5))
plt.plot(gens, [r["best_avg"] for r in rows], marker="o", label="best_avg")
plt.plot(gens, [r["pop_mean"] for r in rows], marker=".", alpha=0.6, label="pop_mean")
plt.axhline(0, color="gray", lw=0.8, ls="--")
plt.xlabel("generation")
plt.ylabel("avg margin vs opponent pool")
plt.title(f"evolution curve ({run})")
plt.legend()
plt.grid(alpha=0.3)
out = HERE / "runs" / run / "evolution_curve.png"
plt.tight_layout()
plt.savefig(out, dpi=120)
print(out)
