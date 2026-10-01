# Predicting EV Purchases — Kaggle Playground Series S6E9

Binary classification project for [Kaggle Playground Series - Season 6, Episode 9](https://www.kaggle.com/competitions/playground-series-s6e9): predict the **probability** that a person will buy an electric vehicle (`Will_Buy_EV`). Submissions are scored on **ROC-AUC**.

## Result

**XGBoost** (`max_depth=4, n_estimators=500, learning_rate=0.1`) — **5-fold CV ROC-AUC: 0.9419 ± 0.0008**, chosen over CatBoost, LightGBM, Logistic Regression and Random Forest.

## Data

668,665 training rows / 286,571 test rows, 13 features (demographics, income, commute, charging infrastructure, subsidy availability, range anxiety) plus the binary target `Will_Buy_EV` (17.46% positive class).

Competition data (`train.csv`, `test.csv`, `sample_submission.csv`) is **not included** in this repo — download it from the [competition data page](https://www.kaggle.com/competitions/playground-series-s6e9/data) and place the files in the project root.

## Notebook

[`s6e9-predicting-electric-vehicule-purchases.ipynb`](s6e9-predicting-electric-vehicule-purchases.ipynb), originally developed on Kaggle (data paths point to `/kaggle/input/...`; adjust if running locally), structured in 6 phases:

1. **Data checks** — shape, dtypes, missing values, duplicates, target balance
2. **EDA** — univariate/bivariate analysis, correlations. Identifies `Subsidy_Available`, `Range_Anxiety_Level`, `Environmental_Concern_Level` and `Annual_Income_USD` as the dominant predictors
3. **Modeling** — compares Logistic Regression, Random Forest, XGBoost, LightGBM and CatBoost via holdout + 5-fold CV, then tunes the winner
4. **Final model & submission** — refits on 100% of training data, generates `submission.csv`
5. **Feature engineering** — tests interaction terms and clipping-floor flags motivated by the EDA; empirically no improvement for XGBoost (the tree already captures these interactions internally), small gain for Logistic Regression
6. **Data quality deep-dive** — investigates a suspicious spike at `Annual_Income_USD == 30000`; confirms it's a placeholder value rather than organic income (via a distribution-gap and stratified buy-rate analysis), but shows the model already handles it optimally without extra treatment

## Key findings

| Feature | Effect on purchase rate |
|---|---|
| `Subsidy_Available` | 0.6% (No) → 27.5% (Yes) |
| `Range_Anxiety_Level` | 18.9% (Low) → 0.14% (High) |
| `Environmental_Concern_Level` | 0.6% (level 1) → 51.8% (level 5) |
| `Home_Charging_Possible` | 12.7% (No) → 19.6% (Yes) |
| `Annual_Income_USD` | buyers earn noticeably more on average |

Age, car type, city type, gender, charging-station density and commute distance have little to no effect.

## Setup

```bash
pip install pandas numpy scikit-learn xgboost lightgbm catboost matplotlib seaborn
```

Run the notebook top to bottom (e.g. in Jupyter or on Kaggle) after placing the competition CSVs as described above.
