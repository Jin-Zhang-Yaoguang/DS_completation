# Kaggriculture PPO v2 — audited BC + league PPO candidate

This challenger uses V1 as the frozen primary baseline and low-level safety
executor. V2 is retained only as a safety-regression comparator. The recurrent
policy acts at daily macro boundaries; all low-level actions stay inside the V1
schedule and invalid/OOD model output falls back to V1 for the rest of the game.
The PPO v2 audit makes group lineage, strategy-family deduplication, nested
validation and the 0.02 terminal gold-difference weight explicit. It does not
claim the missing champion top-ten replays are available.

## Files

- `main.py`: Kaggle `agent(obs)`, 180-feature encoder and NumPy inference.
- `base_agent.py`: frozen V1 executor.
- `model_jax.py`: Flax training model and NumPy export.
- `collect_bc.py`, `train_bc.py`, `train_ppo.py`: reproducible training pipeline.
- `baseline_eval.py`: paired V1/V2 baseline matrix.
- `evaluate.py`: paired V1 and opponent-pool evaluation with bootstrap CI.
- `audit_data.py`, `action_audit.py`, `counterfactual_audit.py`, `residual_gate.py`: G0 lineage/split, causal intervention, and residual-gate audits.
- `smoke_test.py`, `build_submission.py`: acceptance checks and deterministic package.
- `policy_weights.npz`: BC-initialized PPO pilot NumPy weights, wrapped by the screened residual guard.
- `data_manifest.json`, `bc_report.json`, `training_report.json`,
  `model_selection_report.json`: provenance, training, and validation-only selection evidence.
- `evaluation_report.json`, `evaluation_residual.json`, `counterfactual_audit_report.json`, `residual_gate_report.json`, `replay_regression_report.json`, `smoke_report.json`: staged holdout evidence.
- `action_audit_no_residual.json`: deployment-closure control showing the PPO argmax alone is still default-macro.
- `qualification_day10.json`: fixed single-day head-3 ablation on the 28-opponent qualification pool.
- `action_closure_audit.json`: same-state stochastic-training versus deterministic-deployment macro comparison.
- `collect_route_cf.py`, `data/route_cf_512.npz`, `checkpoints/bc_route_cf_512/`: paired low/high route-label pilot; rejected after V1 holdout evaluation.
- `counterfactual_v3_4seed.json`, `residual_eval_v3.json`: hard-V3 intervention and end-to-end residual audits.
- `checkpoints/ppo_route_cf_512/`, `evaluation_ppo_route_cf_512.json`: 512-row deployable low/high route BC followed by a 3×512 PPO pilot; rejected on the independent V1 paired gate.
- `search_route_switch.py`, `route_switch_search_8.json`: 12 mechanically generated single-switch season routes; all were rejected against V1 across 768 complete paired games.
- `search_early_market.py`, `early_market_cow_delayed_16.json`: mechanics-only early market-order variant; rejected after 128 paired games.
- `search_head_days.py`, `head_day_scan_v3_head3_2seed.json`: all-day single-head causal scan against hard-V3.
- `evaluate_topdays_pool.py`, `evaluation_topdays_pool_64.json`, `evaluation_topdays_v2_2000.json`, `evaluation_topdays_v3_64.json`: pooled and V2/V3 paired validation for the screened top-days residual.
- `action_audit_topdays.json`, `replay_regression_topdays.json`, `topdays_gate_report.json`: deployment, public Replay, and candidate-gate evidence.
- `v5_ppo_v2_topdays/`: isolated challenger archive with the top-days residual baked into its default configuration; not uploaded.

Large BC shards and intermediate checkpoints live under ignored `data/` and
`checkpoints/`. Training configuration is recorded in `training_config.json`.

## Commands

Run these from this directory with the project Python environment:

```bash
../../../.venv/bin/python audit_data.py
../../../.venv/bin/python baseline_eval.py --seeds 20 --workers 8
../../../.venv/bin/python collect_bc.py --episodes 20000 --workers 12 --output data/bc_v2
../../../.venv/bin/python train_bc.py --data data/bc_v2 --output checkpoints/bc_v2
../../../.venv/bin/python train_ppo.py --iterations 5 --episodes-per-iteration 256 --workers 12
../../../.venv/bin/python smoke_test.py
../../../.venv/bin/python evaluate.py --output evaluation_report.json
../../../.venv/bin/python build_submission.py
```

Building a challenger does not submit it to Kaggle. Online submission requires
separate authorization after all local acceptance gates pass.

## Current status

G0/G1/G2 are complete. The 20,000-game BC run passed grouped leakage, 100%
macro test accuracy and NumPy parity. The first pure PPO pilot was neutral and
the stochastic-sampling variant was rejected. A separate paired
counterfactual audit (448 interventions, zero errors) screened one narrow
animal-product residual; the residual gate currently passes its pilot
criteria (5.61% actual action changes, 100 paired games at 65.5% with
bootstrap CI [55.0%, 75.5%], and a 240-game pool uplift of +6.25pp). This is
pilot evidence only: the untouched G4/G5 test is still pending. No online
submission is authorized or performed.

The corrected `full28_s17/29/41` and weighted-quota `full28q_s17/29/41` runs
reached round five. The expanded evaluator uses the same 28-opponent pool;
the weighted run was stopped there after its hard-opponent qualification
failed (V3 score 16.406% on the 64-seed set).

The first full-training launch (`full_s17/29/41`) was intentionally discarded:
its fixed pool contained only 16 unique opponents, below the revised 24–32
requirement. The corrected run is `full28_s17/29/41`, with 28 unique executable
variants and the same seed/seat randomization. The discarded-run decision is
recorded in `full_s_invalid_pool_report.json`.

The 2026-08-19 family-gate ablation used the same weighted round-five
checkpoint, 16 validation seeds and 28 opponents. Keeping the gate versus
forcing it off produced identical V3 score (9.375%) and deterministic audit
(5.716% action changes, 6.667% non-default macros, zero errors). This rules
out the gate as the primary explanation on that slice. The non-default macros
come from the hand-screened SAFE_RESIDUAL, not demonstrably learned PPO
argmax actions, so G4 is paused for an action-closure/data audit; no G4/G5
challenger has passed and no online submission was made.

The route-counterfactual pilot is also rejected: after BC on 512 paired
low/high labels and three 512-game PPO rounds, the final 128-game V1 paired
score was 52.73% (bootstrap CI [42.58%, 62.89%], mean margin −4,333), while
the hard-V3 qualification score was 18.75%. This is evidence that the current
two-route action space is insufficient; adding more PPO rounds on the same
labels is paused. The next experiment must introduce independently generated,
deployable opening/season templates and retain V1 as the primary safety
baseline.

The subsequent route-switch search also failed: every low/high single-switch
template (steps 168–576, both directions) lost to V1; the best candidate scored
37.50% versus the 54.69% baseline and had mean margin −6,504. Therefore the
next action-space revision must add a genuinely new deployable opening or
production template, not merely splice the existing two routes.

A mechanics-only early-market candidate (`cow_delayed`) also failed its
expanded check: 53.91% versus V1's 56.25% over 128 paired games, mean margin
uplift −4,508, with zero execution errors. No opening template has yet met the
promotion gate, so PPO v2 remains a research candidate and no challenger is
built or submitted.

The hard-V3 all-day scan then found a distinct, deployable residual: set the
animal-product sell multiplier to 0.5 on days 12, 15, 18, 20, 23, 24 and 28.
The screened candidate passed the current local gate: 2,000 V1-paired games
scored 71.425% (bootstrap CI [69.20%, 73.70%]), 2,000 V2 games scored 78.10%,
the 64-seed six-family pool had no decline, and the hard-V3 128-game check
improved by 28.91pp. Action audit measured 9.49% actual action changes with
zero errors; public Replay regression was neutral. This is a causal residual
wrapped around the existing PPO checkpoint, not evidence that the PPO logits
learned the residual. It is packaged as `v5_ppo_v2_topdays/` for separate
authorization and online testing; no Kaggle submission has been made.

The enlarged G5 pool contains 4,662 complete games (333 seeds, seven opponent
families, both seats). It has zero errors and no family decline: v1/v2 improve
by 28.68pp, forced-low by 21.47pp and forced-high by 6.91pp, while v0,
starter and random remain unchanged in score. `topdays_gate_report.json`
records all 14 local gates as true.
