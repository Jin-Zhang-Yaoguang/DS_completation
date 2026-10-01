# Kaggle Playground S6E9 — Predicting Electric Vehicle Purchases

Work in progress for the [Kaggle Playground Series S6E9](https://www.kaggle.com/competitions/playground-series-s6e9)
competition: predicting whether a person will buy an electric vehicle.

This repository holds the exploratory analysis and the notebooks for that competition.

**Main notebook on Kaggle:** [S6E9 Step by Step: Every Concept Explained](https://www.kaggle.com/code/nicolsbarcel/s6e9-step-by-step-every-concept-explained)

## The competition

| | |
|---|---|
| Metric | ROC AUC on the predicted probability of `Will_Buy_EV` |
| Deadline | 30 September 2026, 23:59 UTC |
| Data | 668,665 training rows, 286,571 test rows, 13 features |
| Target | Binary, 17.46% positives |
| Source | Synthetic, inspired by [EV Adoption Behavior and Range Anxiety](https://www.kaggle.com/datasets/itzzomkar/ev-adoption-behavior-and-range-anxiety) |

## Setup

Requires Python 3.12 (see `.python-version`) and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/ferreret/kaggle-playground-s6e9.git
cd kaggle-playground-s6e9
uv sync
```

`uv sync` creates the virtual environment and installs the pinned versions from `uv.lock`,
including the dev group (JupyterLab).

## Getting the data

The competition data is **not tracked in this repository** — Kaggle's rules do not allow
redistributing it. Download it with the Kaggle API:

1. Create an API token at <https://www.kaggle.com/settings> ("Create New Token").
2. Save the downloaded `kaggle.json` to `~/.kaggle/kaggle.json` and restrict its permissions:

   ```bash
   mkdir -p ~/.kaggle && mv ~/Downloads/kaggle.json ~/.kaggle/kaggle.json
   chmod 600 ~/.kaggle/kaggle.json
   ```

3. Accept the competition rules on the competition page, then download:

   ```bash
   uv run kaggle competitions download -c playground-series-s6e9 -p data --unzip
   ```

This leaves `data/train.csv`, `data/test.csv` and `data/sample_submission.csv` in place.

## Running the notebooks

```bash
uv run jupyter lab
```

## Results

5-fold stratified CV (seed 42); public leaderboard where submitted.

| Model | CV AUC | Public LB |
|---|---|---|
| Logistic regression | 0.93810 ± 0.00081 | — |
| LightGBM, raw features | 0.94189 ± 0.00076 | 0.94173 |
| LightGBM + fold-safe income target encoding + counts | 0.94578 ± 0.00060 | 0.94598 |

## Layout

```
notebooks/
  s6e9-step-by-step.ipynb   main notebook: EDA, metric, CV, models, SHAP, every concept explained
experiments/     exploratory work, not part of the deliverable
  00_roc_auc.ipynb          ROC AUC walkthrough on this dataset
  01_eda_detallado.ipynb    detailed EDA and data dictionary
  02_baseline.py            logistic regression vs LightGBM under the same CV
  03_income_te.py           count and target encoding of the exact income value
  04_feature_selection.py   does dropping features help?
src/             reusable code
data/            competition data (not tracked)
submissions/     submission files (not tracked)
```

## Notes

- Notebooks under `experiments/` are exploratory and written in Spanish. The main notebook
  under `notebooks/` is in English.
- Notebooks are committed with their outputs so they can be read without running them.
- Fixed random seed (42) wherever randomness is involved.

## Author

Nicolás Barceló — [Kaggle](https://www.kaggle.com/nicolsbarcel) · [GitHub](https://github.com/ferreret)
