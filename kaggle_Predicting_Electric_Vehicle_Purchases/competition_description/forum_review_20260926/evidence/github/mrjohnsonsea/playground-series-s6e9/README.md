# Predicting Electric Vehicle Purchases

A binary classification project for Kaggle's [Playground Series – Season 6, Episode 9](https://www.kaggle.com/competitions/playground-series-s6e9). The goal is to predict whether a consumer will buy an electric vehicle (`Will_Buy_EV`) from demographic, commuting, charging-access, and attitude features. Submissions are scored on **ROC-AUC**.

## Highlights

- **Dev ROC-AUC of 0.9426** with a tuned XGBoost model (5-fold CV ROC-AUC 0.9419 on the training split).
- Compared **four model families** in one reproducible scikit-learn pipeline: Logistic Regression, LightGBM, CatBoost, and XGBoost.
- Ran **50 Optuna trials** with stratified 5-fold cross-validation, including `scale_pos_weight` to handle the 17% positive class.
- **Minority-class recall went from 0.67 to 0.80** after tuning, with dev AUC holding steady.
- EDA findings were confirmed by the model: subsidy availability and range anxiety are the strongest signals.

## Dataset

| Split | Rows | Columns |
|---|---|---|
| Train | 668,665 | 13 features + target |
| Test | 286,571 | 13 features |

As in other Playground Series competitions, the data is synthetic. It has **no missing values**. The target is imbalanced: **17.5%** of training rows are buyers.

**Features**

- **Numeric:** `Age`, `Annual_Income_USD`, `Daily_Commute_km`, `Number_of_Cars_Owned`, `Charging_Stations_Near_Home`, `Charging_Stations_Near_Work`, `Environmental_Concern_Level`
- **Categorical:** `Gender`, `City_Type`, `Current_Car_Type`, `Home_Charging_Possible`, `Subsidy_Available`, `Range_Anxiety_Level`

## Approach

### 1. Validation strategy
An 80/20 **stratified** train/dev split (`random_state=206`) keeps the class balance the same in both sets. All EDA runs on the training portion only, so nothing leaks from the dev set.

### 2. Exploratory analysis
EV purchase rate by category (training split):

| Feature | Purchase rate |
|---|---|
| `Subsidy_Available` | **No: 1%** · Yes: 27% |
| `Range_Anxiety_Level` | **High: 0%** · Medium: 4% · Low: 19% |
| `Home_Charging_Possible` | No: 13% · Yes: 20% |
| `City_Type` | Rural: 19% · Suburban: 18% · Urban: 16% |
| `Gender`, `Current_Car_Type` | Roughly flat (16–18%) |

The pairplot of numeric features pointed to `Environmental_Concern_Level` as the main numeric driver: the purchase rate rises with concern level.

### 3. Preprocessing
A `ColumnTransformer` one-hot encodes the categorical columns and passes the numeric columns through unchanged. It sits inside a shared `make_pipeline()` helper, so every model gets identical preprocessing and the dev set never influences fitted transforms. Standard scaling is added only for Logistic Regression.

### 4. Model comparison
Each model was fit on the training split and scored on the held-out dev set:

| Model | Dev ROC-AUC | Fit time |
|---|---|---|
| **XGBoost** | **0.9423** | 6.4s |
| LightGBM | 0.9423 | 4.5s |
| CatBoost | 0.9419 | 11.5s |
| Logistic Regression (balanced) | 0.9388 | 0.7s |

The top three gradient-boosted models finished within 0.0004 AUC of each other, which suggests the result is limited by the features rather than by model choice. Even the linear baseline was competitive, but its minority-class precision was only 0.56.

### 5. Cross-validation and tuning
The top XGBoost model was checked with stratified 5-fold CV:

| Metric | Mean ± SD |
|---|---|
| ROC-AUC | 0.9416 ± 0.0006 |
| Accuracy | 0.8985 ± 0.0008 |
| Precision | 0.7260 ± 0.0031 |
| Recall | 0.6724 ± 0.0027 |
| F1 | 0.6982 ± 0.0020 |

The small standard deviations show the model is stable across folds. Optuna then searched 10 XGBoost hyperparameters over 50 trials, scoring each trial on mean 5-fold CV AUC. Folds ran in parallel and each model was single-threaded to avoid oversubscribing the CPU. The search converged on **shallow trees** (`max_depth=3`, ~1,400 estimators, `learning_rate≈0.06`, `scale_pos_weight≈1.83`).

## Results

The final tuned XGBoost model on the dev set:

| Metric | Baseline XGBoost | Tuned XGBoost |
|---|---|---|
| ROC-AUC | 0.9423 | **0.9426** |
| Precision (buyers) | 0.73 | 0.65 |
| Recall (buyers) | 0.67 | **0.80** |
| F1 (buyers) | 0.70 | **0.72** |
| Accuracy | 0.90 | 0.89 |

Tuning barely changed AUC. The main effect came from `scale_pos_weight`, which shifted the default 0.5 threshold toward catching buyers: the tuned model finds **18,695 of 23,356** actual buyers in the dev set, compared with about 15,600 before tuning. This trade-off does not affect the competition metric, but it matters in practice when missing a likely buyer costs more than a false lead.

**Top feature importances** (XGBoost gain):
1. `Subsidy_Available` (both one-hot levels together, clearly the dominant feature)
2. `Environmental_Concern_Level`
3. `Range_Anxiety_Level`
4. `Annual_Income_USD` and `Home_Charging_Possible` (minor)

The model's ranking matches the EDA: **financial incentives and range confidence matter much more than demographics**. Gender, car type, and age contribute almost nothing.

## Tech Stack

- **Language:** Python 3.14, managed with [uv](https://docs.astral.sh/uv/)
- **Data and visualization:** pandas, NumPy, seaborn, matplotlib
- **Modeling:** scikit-learn, XGBoost, LightGBM, CatBoost
- **Tuning:** Optuna
- **Data access:** kagglehub

## Project Structure

```
playground-series-s6e9/
├── data/                  # Competition data (downloaded by the notebook via kagglehub)
├── notebooks/
│   └── 01_predicting_electric_vehicle_purchases.ipynb   # Full workflow: EDA → modeling → submission
├── submissions/
│   └── submission.csv     # Test-set probabilities for Kaggle
├── pyproject.toml         # Project dependencies
└── uv.lock                # Locked dependency versions
```

## Reproducing

1. **Install dependencies** (requires [uv](https://docs.astral.sh/uv/)):
   ```bash
   uv sync
   ```
2. **Set up Kaggle credentials.** Put your API token at `~/.kaggle/kaggle.json` and accept the [competition rules](https://www.kaggle.com/competitions/playground-series-s6e9/rules) so `kagglehub` can download the data.
3. **Run the notebook.** Open `notebooks/01_predicting_electric_vehicle_purchases.ipynb` in VS Code or Jupyter, select the project's `.venv` kernel, and run all cells. The notebook downloads the data to `data/` and writes `submissions/submission.csv`.
   ```bash
   uv run --with jupyter jupyter lab
   ```

## Next Steps

- **Refit on all labeled data.** The final model is currently fit on the 80% training split only. Refitting on train + dev before predicting on the test set should add a small boost.
- **Ensemble models.** XGBoost, LightGBM, and CatBoost score almost identically, so a rank-averaged or stacked blend of the three is a low-risk way to gain AUC.
- **Engineer features.** Try interactions between the dominant signals (for example, subsidy × range anxiety, or concern level × home charging) and ratio features such as income per car owned.
- **Use native categorical handling.** Pass the categorical columns directly to CatBoost and LightGBM instead of one-hot encoding them.
- **Tune the decision threshold.** For a real use case, choose the classification threshold from the business cost of false positives versus false negatives rather than using 0.5.

## Author

**Mike Johnson** · September 2026
