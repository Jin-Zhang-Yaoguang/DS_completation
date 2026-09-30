# PPO v2 top-days residual challenger

This isolated package keeps the existing NumPy PPO checkpoint and V1 safety
executor, while enabling the screened animal-product sell residual on days
12, 15, 18, 20, 23, 24 and 28. It is uploaded as an independent Kaggle
challenger; it does not replace the existing V1–V5 submissions.

Evidence in the parent directory:

- 2,000 V1-paired games: 71.425%, bootstrap CI `[69.20%,73.70%]`.
- 2,000 V2 games: 78.10% versus the V1 baseline 50.05%.
- 64-seed six-family pool: no opponent-family decline and zero errors.
- Hard-V3 128-game check: +28.91pp, CI `[19.53%,38.28%]`.
- Action audit: 9.49% actual action changes, 20% non-default macro days,
  zero errors.

The residual is causally screened but is not claimed to be learned by PPO
logits. Kaggle submission `55612090` is `COMPLETE` with an initial public
score of `600.0`; the required online 80-game monitoring window is still
pending.

The enlarged G5 pool contains 4,662 complete games across seven opponent
families, with zero errors and no family decline. The gate report records all
14 local checks as true.
