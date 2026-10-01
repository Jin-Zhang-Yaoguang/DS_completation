# Kaggle Playground S6E9 — Predicting Electric Vehicle Purchases

Full pipeline for the Kaggle competition [Playground Series S6E9](https://www.kaggle.com/competitions/playground-series-s6e9)
(binary target `Will_Buy_EV`, metric ROC AUC, September 2026).

**Result:** out-of-fold AUC 0.94648, public leaderboard 0.94649 (hedge entry) / 0.94642 (best validated entry), against a
leader at 0.94674 and a top-50 line at 0.94652. The more useful content is the measurement ledger: 190+ experiments with
paired significance tests, most of them negative, plus a ceiling analysis showing the dataset's own label noise leaves
roughly 0.001 of headroom above 0.9464.

## What the data is

Train (668,665 rows) and test (286,571 rows) are synthetic, generated from a 10,000-row original dataset that is itself
synthetic — features drawn with `np.random.RandomState(101)`, label from a probit formula on income, environmental
concern, subsidy and range anxiety. Every point of AUC above about 0.942 comes from the **generator's artifacts**: a few
thousand income and commute values are heavily over-produced, and the label rate at those values deviates from the
formula. Modelling how the data was made beats modelling what it represents.

## What worked (per-model out-of-fold AUC, 10 folds)

| Step | AUC |
|---|---|
| LightGBM on the 13 raw columns | 0.9419 |
| plus per-value frequency, lift vs. the original, novelty, nearest-original distance | 0.9436 |
| plus nested target encoding of income and commute at several bin widths | 0.9459 |
| plus shallow column-subsampled trees (depth 5, 30% of columns) and target encodings on **every** column at two smoothings | 0.9462 |
| 20 folds, encoding-seed bags, logit blend of LightGBM + CatBoost + a 15-seed MLP | 0.9464 |
| plus weights hill-climbed over public out-of-fold libraries | 0.9465 |

## What did not work

All measured with paired DeLong tests against a fixed reference, all within ±0.00005 or negative: interaction encodings
in every form (pairs, triples, binned), similarity to original rows, local density windows, digit residues, residual
encodings, neighbourhood target statistics, native categorical handling, pseudo-labelling (including a class-balanced
gate), deeper or tuned trees, neural-net value embeddings / piecewise-linear encoding / weight averaging, bagged
training-side encodings, segment-wise calibration, segment-wise blend weights, a synthetic-ness feature, row-level keys.

Full numbers in `experiments/results.csv`; the reasoning and the accept/reject rule in `RERUN.md`.

## Why it stops near 0.9465

Resampling labels from the model's own calibrated probabilities gives a *perfect* model an AUC of 0.9459 ± 0.0003, and
per cell of concern × subsidy × anxiety the real score equals that ceiling within ±0.001 in every cell. A fresh model
trained to predict the blend's errors explains none of them (R² = −0.003). What remains is label noise the generator put
there on purpose.

## Layout

```
src/                config, data loading, frozen folds, nested target encodings (TESpec / NTESpec),
                    model wrappers, experiment runner with cached predictions and paired DeLong tests,
                    blending, hard-edge post-processing, submission helpers
scripts_*.py        every experiment batch in the order they were run (phase0 → final → megablend)
tests/              dataset-fact assertions, leak-freeness of the encodings, synthetic end-to-end smoke test
experiments/        results ledger (results.csv), leaderboard log (lb_log.csv), watch reports
RERUN.md            playbook for continuing: harness, current best members, evaluation and submission rules
```

## Running it

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python pandas polars pyarrow numpy scikit-learn \
    lightgbm xgboost catboost torch optuna kaggle scipy pytest
make data     # needs a Kaggle API token; downloads train/test and the original dataset
make test
.venv/bin/python scripts_phase0.py base    # baseline plus noise-floor control
.venv/bin/python scripts_final_gbdt.py check
.venv/bin/python scripts_nn_final.py 0     # one neural-net seed (Apple MPS or CPU)
.venv/bin/python scripts_final.py final lgb_final_bag10 cb_final_bag8 nn_final_bag15
```

On Apple silicon, LightGBM needs `brew install libomp`.

## Credits

Third-party public notebooks and shared prediction libraries that were studied or blended are **not** redistributed here.
They are credited where used, in `RERUN.md` and `scripts_megablend2.py`: megayak, najiama, jazivxt, yekenot,
tamerlanomralinov, dariushafshar, legtarrr, taeyangg4, starkhushi, tilii7 and Chris Deotte.

## License

GPL-3.0 — see `LICENSE`.
