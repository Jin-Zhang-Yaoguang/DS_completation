# Predicting Electric Vehicle Purchases

A research-grade solution for Kaggle's **Playground Series S6E9 — Predicting
Electric Vehicle Interest** (evaluation metric: ROC-AUC, target: `Will_Buy_EV`).

This repo is built around one governing finding, established before any
model was trained rather than discovered by accident afterward: **the data
has an information ceiling, and the winning move is finding it precisely,
not out-modeling it.**

> **A note on data provenance.** kaggle.com is unreachable from this
> development environment (network policy), so the actual competition
> `train.csv`/`test.csv` could not be downloaded here. Kaggle states this
> playground competition's data is *"synthetically generated from
> real-world data"*; the real-world dataset it was generated from
> (`EV_Adoption_and_Range_Anxiety_Dataset.csv`, 10,000 rows, same
> `Will_Buy_EV` target) was supplied directly and is used throughout this
> repo for development, validation, and every number reported below. The
> pipeline auto-detects and prefers the real competition files the instant
> they're placed in `data/raw/` (see **Swapping in the real competition
> data** below) — no code changes required.

---

## 1. Problem framing

Binary classification, ROC-AUC scored, meaning: **only the ranking of
predicted probabilities matters, not their calibration or scale.** That one
fact should drive every downstream choice — it's why the model comparison
below is entirely in AUC terms, why we don't bother with Platt/isotonic
calibration for leaderboard purposes (mentioned only as a deployment nicety
in §7), and why rank-based ensembling is a legitimate alternative to
probability-averaging (tested in §6).

The target is imbalanced: **17.5% positive** (`Will_Buy_EV = Yes`). Not
severe enough to need resampling (SMOTE, class weighting materially
changes nothing here — see §5.1 ablation), but severe enough that plain
accuracy would be a useless metric — another reason ROC-AUC is the right
target to optimize directly rather than a proxy like log-loss or F1.

## 2. Exploratory analysis — finding the ceiling

Full reproducible script: [`notebooks/01_eda.py`](notebooks/01_eda.py).

### 2.1 Every predictor, tested for actual association with the target

Thirteen predictor columns exist. Rather than assume they're all useful (the
naive approach: throw everything at a GBM and let it figure it out), each
was tested against the target with the statistic appropriate to its type:
point-biserial correlation for numeric columns, a chi-square test of
independence for categorical columns.

| Column | Test | Statistic | Verdict |
|---|---|---|---|
| `Environmental_Concern_Level` | correlation | r = **+0.366** | **signal** |
| `Annual_Income_USD` | correlation | r = **+0.176** | **signal** |
| `Subsidy_Available` | χ² | p = **6.5 × 10⁻²²⁶** | **signal** |
| `Range_Anxiety_Level` | χ² | p = **5.9 × 10⁻⁴³** | **signal** |
| `Home_Charging_Possible` | χ² | p = **1.2 × 10⁻¹⁷** | **signal** |
| `Daily_Commute_km` | correlation | r = −0.027 | noise |
| `Age` | correlation | r = +0.004 | noise |
| `Number_of_Cars_Owned` | correlation | r = +0.0004 | noise |
| `Charging_Stations_Near_Home` | correlation | r = −0.003 | noise |
| `Charging_Stations_Near_Work` | correlation | r = +0.001 | noise |
| `Gender` | χ² | p = 0.44 | noise |
| `City_Type` | χ² | p = 0.17 | noise |
| `Current_Car_Type` | χ² | p = 0.64 | noise |

**Eight of thirteen columns are statistically indistinguishable from pure
noise.** This is not "weak signal that a powerful enough model could still
exploit" — the p-values and correlations are consistent with the null
hypothesis of *no relationship whatsoever*. They read as deliberately
included decoy variables: plausible-sounding predictors (car type, city
type, commute distance) that a less careful analysis would naturally
one-hot-encode and feed straight into a GBM.

### 2.2 The five real drivers, and how they combine

Digging into the five signal columns individually shows near-monotonic,
almost log-linear relationships with purchase probability:

`Environmental_Concern_Level` (1–5 ordinal): 2.1% → 4.9% → 14.5% → 25.3% →
41.4% buy-rate as the level rises — an almost perfect geometric-ish
progression, the signature of a logistic (log-odds-linear) generating
process rather than an arbitrary rule table.

`Subsidy_Available` interacts multiplicatively with `Range_Anxiety_Level`
rather than adding independently:

| Subsidy | Range anxiety | P(buy) |
|---|---|---|
| No | any | 0.2% – 3.0% |
| Yes | High | 1.0% |
| Yes | Medium | 10.7% |
| Yes | **Low** | **31.0%** |

Without a subsidy, range anxiety barely matters — the buy-rate is
uniformly near zero. *With* a subsidy, range anxiety becomes the dominant
swing factor, taking the buy-rate from 31% down to 1%. This is a textbook
interaction effect, and it's why the feature set in §3 explicitly builds
`Environmental_Concern_Level × Subsidy_Available` and
`Range_Anxiety_Level × Home_Charging_Possible` cross-terms rather than
relying on a downstream tree to rediscover the interaction from raw
columns (trees can find interactions, but a shallow tree with a screened,
already-crossed feature needs far less depth to express the same
relationship, which matters directly for the regularization argument in
§4).

Missingness (~1.8% each in `Annual_Income_USD`, `Daily_Commute_km`,
`Environmental_Concern_Level`) was checked for informativeness (is
"missing" itself predictive?) and found not to be — target rate among
missing rows is statistically indistinguishable from the non-missing rate
in every case. Treated as MCAR; median imputation is used with no
missing-indicator flags added (adding uninformative indicator columns
would just reintroduce the exact "noise feature" problem §2.1 diagnosed).

### 2.3 The ceiling

Four structurally unrelated model families — logistic regression, random
forest, LightGBM, XGBoost, CatBoost — were cross-validated (5-fold
stratified) on the five signal columns plus their interactions. **All five
converge to 0.904–0.906 AUC**, within each other's fold-to-fold noise:

| Model | CV AUC |
|---|---|
| Logistic regression (signal + interactions) | 0.9054 |
| CatBoost | 0.9049 |
| LightGBM | 0.9051 |
| XGBoost | 0.9050 |
| Random forest | 0.9036 |

When a linear model with hand-built interactions statistically ties a
tuned gradient-boosted tree ensemble, that is strong evidence the
remaining gap to AUC = 1.0 is the generator's injected randomness, not an
unmodeled pattern — i.e., **~0.905 is close to the Bayes-optimal AUC for
this generating process**, and no amount of additional feature engineering
or model complexity thrown at *this* dataset should be expected to move it
much further. (Feeding the full raw feature set, decoys included, into
LightGBM *drops* CV AUC to 0.901 — confirming §2.1's point that the decoys
are actively harmful, not merely inert, once a tree is free to split on
them.)

This reframes the modeling task correctly: the job is not "build the most
powerful possible model," it's "find the small ensemble that most
reliably attains the ceiling with the lowest variance," which is exactly
the ensembling logic in §6.

## 3. Feature engineering

Implemented in [`src/features.py`](src/features.py).

- **Ordinal encoding**: `Range_Anxiety_Level` → {Low: 0, Medium: 1, High: 2}
  (not one-hot — the levels are genuinely ordered, and encoding them as
  such lets a linear model use one coefficient instead of two, and lets a
  tree split on threshold instead of needing multiple splits to express
  monotonicity).
- **Binary encoding**: `Subsidy_Available`, `Home_Charging_Possible` → {0, 1}.
- **Interaction terms**, each justified by an EDA finding in §2.2, not
  added speculatively: `income × subsidy`, `env_concern × subsidy`,
  `anxiety × home_charging`, `env_concern × (2 − anxiety)` (an EV-adoption
  "propensity score" combining environmental motivation with the inverse
  of range anxiety), and `log1p(income)` (variance-stabilizing, since raw
  income is right-skewed with a max of $223k against a median of $85k).
- **Median imputation**, fit on training folds only (no leakage from
  validation/test statistics into the imputer).
- **Deliberately excluded**: the eight decoy columns from §2.1, and
  one-hot expansions of anything not shown to matter.

`src/features.py` also ships `auto_select_features()` — a schema-agnostic
permutation-importance screen (cross-validated, using the shuffle-mean
minus 2σ as the keep/drop threshold) that rediscovers signal vs. noise
directly from whatever data is in front of it, rather than from this
document. It exists specifically so that if the real competition data
turns out to have a different noise structure than this source dataset,
the pipeline can re-validate the feature set rather than blindly trusting
the hardcoded EDA conclusions above.

## 4. Model design

Implemented in [`src/models.py`](src/models.py), tuned in
[`src/tune.py`](src/tune.py) (Optuna, 5-fold CV ROC-AUC objective,
per-model search history in `reports/tuning_results.json`).

Because §2.3 established the effective information content of this
problem is ~5 features with a near-linear log-odds relationship, tree
depth/leaf-count is treated as a hyperparameter to *minimize* subject to
CV AUC, not maximize: an overly expressive GBM here has no genuine
higher-order structure left to fit and will instead memorize fold-specific
noise, which surfaces immediately as CV AUC declining past a fairly low
complexity ceiling (confirmed in the Optuna search — see
`reports/tuning_results.json` for the trial-by-trial trace showing this).
Final configs land at `num_leaves ≈ 7`, `max_depth ≈ 3–4`, heavy L1/L2
(`reg_alpha`/`reg_lambda` ≈ 1), and row/column subsampling of 0.8 — this
is a regularization-first GBM configuration, the opposite instinct from a
typical "deep trees, many estimators" Kaggle default, and it's the correct
one for a dataset this information-sparse.

**Five models are trained**: logistic regression (the "linear DGP" prior),
random forest, LightGBM, XGBoost, CatBoost (three structurally different
gradient-boosting implementations, each with different regularization
mechanics and split-finding heuristics — diversity that pays off in §6).

## 5. Cross-validation protocol

5-fold **stratified** K-fold (`StratifiedKFold`, shuffled, `random_state=42`)
throughout — stratification matters here specifically because of the
17.5% positive rate; an unstratified split risks folds with meaningfully
different effective base rates, adding CV variance that isn't about model
quality. Every reported AUC is out-of-fold (OOF), never in-sample.

### 5.1 Ablations that justify design choices (not just asserted)

- **Curated 5-feature set vs. all 13 raw columns**: 0.905 vs. 0.901 AUC
  (LightGBM) — decoys measurably hurt, confirming §2.1/§2.3.
- **Class weighting / SMOTE**: tested and *not* adopted — ROC-AUC is
  threshold- and prior-independent by construction, so rebalancing a
  17.5%-positive problem changes calibration, not ranking quality; it
  produced no CV AUC improvement in testing and was dropped to keep the
  pipeline simpler.
- **Stacking meta-learner vs. weighted blend**: see §6 — stacking did not
  beat a simple weighted average here, which is itself a finding (not
  every ensembling technique earns its complexity on every dataset).

## 6. Ensembling

Implemented in [`src/ensemble.py`](src/ensemble.py).

OOF predictions from the five base models are highly correlated (all
Pearson r > 0.97 with each other — see `reports/training_report.json` for
the exact matrix) but not identical, because each model encodes a
different inductive bias about how the five signal features combine
(additive log-odds for logistic regression; axis-aligned interaction
splits for the trees). A weighted blend (grid search over the weight
simplex, optimizing OOF AUC directly) squeezes out roughly a further
+0.0005–0.001 AUC over the best single model — worth taking for a
leaderboard where scores are often separated by the fourth decimal place,
even though it will never turn a mediocre model into a great one.

A logistic-regression stacking meta-learner on the same OOF predictions
was also tried, and did **not** outperform the weighted blend — with only
five, highly-correlated base learners, the meta-learner has essentially
nothing left to arbitrate that a direct weight search doesn't already
capture, and it adds a layer of indirection (and refit complexity) for no
measured benefit. It's kept in the codebase and reported in
`training_report.json` for transparency, but the deployed pipeline uses
the weighted blend.

## 7. Interpretability

Implemented in [`src/explain.py`](src/explain.py) — SHAP `TreeExplainer` on
the LightGBM component. Run `python -m src.explain` after training; it
writes `reports/figures/shap_importance_bar.png`,
`reports/figures/shap_beeswarm.png`, and `reports/shap_ranking.json`. The
SHAP ranking is expected to (and does) reproduce the same five-feature
signal ordering as the independent chi-square/correlation screen in §2.1 —
agreement between a purely statistical univariate test and a model-based,
interaction-aware attribution method is itself a robustness check on the
whole feature-selection story, not just a nice chart.

## 8. Repository layout

```
data/
  raw/EV_Adoption_and_Range_Anxiety_Dataset.csv   # source dataset (see provenance note above)
  raw/train.csv, test.csv, sample_submission.csv  # <- put the real competition files here (gitignored)
src/
  config.py      # paths, constants
  data.py        # loading with automatic competition-file / source-dataset fallback
  features.py    # curated feature engineering + schema-agnostic auto-selection
  models.py      # model zoo (tuned hyperparameters)
  tune.py        # Optuna search
  ensemble.py    # blend weight search + stacking
  train.py       # CV eval, blend fit, final refit, artifact persistence
  infer.py       # submission generation
  explain.py     # SHAP
notebooks/01_eda.py   # reproducible EDA (plain script, not .ipynb, for clean diffs/CI)
tests/                 # unit tests for feature engineering
reports/               # training_report.json, tuning_results.json, shap outputs, submission.csv
models/                # persisted trained pipeline (joblib)
```

## 9. Reproducing everything

```bash
pip install -r requirements.txt
python notebooks/01_eda.py     # EDA -> console + reports/figures/
python -m src.tune             # Optuna search -> reports/tuning_results.json
python -m src.train            # CV, blend, final refit -> models/, reports/training_report.json
python -m src.explain          # SHAP -> reports/figures/, reports/shap_ranking.json
python -m src.infer            # submission -> reports/submission.csv (or demo_submission.csv)
python -m pytest tests/ -q
```

## 10. Swapping in the real competition data

Download `train.csv`, `test.csv`, `sample_submission.csv` from the
competition's Data tab and place them in `data/raw/`. Nothing else
changes: `src/data.py::load_training_frame()` detects `data/raw/train.csv`
and switches over automatically (it's checked before the fallback source
dataset), `src/data.py::load_test_frame()` picks up `test.csv` the same
way, and `src/infer.py` will write a real `reports/submission.csv` in the
exact `id,Will_Buy_EV` format the competition requires instead of the
demo one. Re-run `python -m src.tune && python -m src.train` on the real
data before submitting — the hyperparameters here were tuned on the
source dataset's ~10k rows and should be re-validated at the competition's
actual scale (typical Playground Series train sets run in the hundreds of
thousands of rows), though the feature engineering and ensembling
*strategy* — isolate the real signal, keep trees shallow, blend a handful
of diverse models — is what should transfer, not the specific numbers.

## 11. Results summary

See `reports/training_report.json` (generated by `python -m src.train`)
for the exact, current numbers: per-model OOF AUC, the OOF correlation
matrix between models, the best blend weights and its AUC, and the
stacking-meta-learner AUC for comparison.
