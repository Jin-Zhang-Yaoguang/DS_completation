# Kaggriculture v3 — BC + PPO hybrid

This challenger keeps the submitted v2 strategy frozen as the low-level safety
executor. A small recurrent policy acts only at `hour == 0`: it chooses the
production route on day 7 and applies bounded residual controls to v2's existing
sell orders. On day 3 a public-state guard enables the neural residual only when
the opponent has the same structural opening as the v1/v2 strategy family
(distance at most 4); unfamiliar openings continue with v2 unchanged. The guard
does not use player identity, private opponent state, or replay-specific data.
Invalid models, features, or actions permanently fall back to v2 for the current
game. The final four actions always use v2 unchanged.

## Files

- `main.py`: Kaggle `agent(obs)`, 180-feature encoder and NumPy inference.
- `base_agent.py`: byte-identical v2 executor.
- `model_jax.py`: Flax training model and NumPy export.
- `collect_bc.py`, `train_bc.py`, `train_ppo.py`: reproducible training pipeline.
- `evaluate.py`: paired v2 and opponent-pool evaluation with bootstrap CI.
- `smoke_test.py`, `build_submission.py`: acceptance checks and deterministic package.
- `policy_weights.npz`: validation-selected iteration-40 NumPy weights.
- `data_manifest.json`, `bc_report.json`, `training_report.json`,
  `model_selection_report.json`: provenance, training, and validation-only selection evidence.
- `evaluation_report.json`, `replay_regression_report.json`, `smoke_report.json`: final holdout evidence.

Large BC shards and intermediate checkpoints live under ignored `data/` and
`checkpoints/`. Training configuration is recorded in `training_config.json`.

## Commands

Run these from this directory with the project Python environment:

```bash
../../../.venv/bin/python collect_bc.py --episodes 10000 --workers 12
../../../.venv/bin/python train_bc.py
../../../.venv/bin/python train_ppo.py --iterations 50 --episodes-per-iteration 2048 --workers 12
../../../.venv/bin/python smoke_test.py
../../../.venv/bin/python evaluate.py --output evaluation_report.json
../../../.venv/bin/python build_submission.py
```

Building a challenger does not submit it to Kaggle. Online submission requires
separate authorization after all local acceptance gates pass.

## Final acceptance

- BC data: 10,000 games, 5,000 per seat, 10 verified compressed shards (31.2 MB).
- BC test: route and all default macro heads 100%; JAX/NumPy max error `7.15e-7`.
- PPO: 50 × 2,048 = 102,400 games; iteration 40 selected solely by validation score.
- Direct holdout: 1,000 unseen seeds and both seats (2,000 games), score rate 84.55%,
  paired bootstrap 95% CI `[82.925%, 86.175%]`, mean margin +855.69 versus v2.
- Holdout pool: mean score-rate delta +13.92 percentage points; no opponent class
  lost score rate relative to v2.
- Eleven public replay traces: total reward/margin delta 0; animal loss, shed
  overflow, and terminal unsold inventory exactly match v2.
- NumPy inference: 0.035 ms per daily macro step on the development machine.
- Submission: three root files, 307,379 bytes, SHA256
  `c6eaae2bb494da9bbab745bdf8cd2988b4f9638230179b32027b0e4b979905de`.
