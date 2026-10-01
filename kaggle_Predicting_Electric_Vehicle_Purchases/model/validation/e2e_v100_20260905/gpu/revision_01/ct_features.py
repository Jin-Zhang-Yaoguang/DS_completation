"""Verbatim feature functions from frozen historical CT notebook."""
import hashlib
import numpy as np
import pandas as pd
from sklearn.preprocessing import TargetEncoder

def binary_target(values):
    values = pd.Series(np.asarray(values).reshape(-1))
    if not pd.api.types.is_numeric_dtype(values.dtype):
        values = values.map({"Yes": 1, "No": 0, "1": 1, "0": 0})
    if values.isna().any() or not set(values.unique()).issubset({0, 1}):
        raise ValueError("The target must contain only Yes/No or 1/0.")
    return values.to_numpy(dtype=np.int8)

def numeric_values(values):
    return pd.to_numeric(values, errors="coerce").replace([np.inf, -np.inf], np.nan)

def category_keys(values):
    # A prefix keeps a missing value distinct from an ordinary category name.
    return ("V:" + values.astype("string")).fillna("M:").astype(object)

def base_features(data, state):
    missing = set(state["input_columns"]).difference(data.columns)
    if missing:
        raise ValueError(f"Missing input columns: {sorted(missing)}")
    columns = {}
    for name in state["input_columns"]:
        if name in state["category_maps"]:
            columns[name] = category_keys(data[name]).map(state["category_maps"][name]).fillna(-1)
        else:
            columns[name] = numeric_values(data[name])
    for name in state["input_columns"]:
        if name in state["category_maps"]:
            continue
        values = numeric_values(data[name]).fillna(0).to_numpy(dtype=np.float64)
        for digit in range(-4, 4):
            # Keep floor division: changing this arithmetic changes the recipe.
            columns[f"{name}_digit{digit}"] = values // (10.0 ** digit) % 10
    income = pd.to_numeric(data["Annual_Income_USD"], errors="coerce")
    concern = pd.to_numeric(data["Environmental_Concern_Level"], errors="coerce")
    columns["is_30k_spike"] = income == 30000.0
    columns["is_millionaire_cliff"] = income >= 170537.0
    columns["is_dead_zone"] = income.between(38000.0, 42000.0)
    columns["is_env_hater"] = concern == 1
    return pd.DataFrame(columns, index=data.index, dtype=np.float32)

def unique_columns(frame):
    """Remove constants and exact duplicates, using training rows only."""
    keep, seen = [], set()
    for name in frame:
        if frame[name].nunique(dropna=False) <= 1:
            continue
        values = frame[name].to_numpy(dtype=np.float32, copy=True)
        values[values == 0] = 0
        values[np.isnan(values)] = np.nan
        digest = hashlib.blake2b(values.tobytes(), digest_size=16).digest()
        if digest not in seen:
            keep.append(name)
            seen.add(digest)
    return keep

def smooth_keys(data):
    income = numeric_values(data["Annual_Income_USD"])
    commute = numeric_values(data["Daily_Commute_km"])
    values = {
        "income_exact_integer": income,
        "income100_floor": np.floor(income / 100),
        "income1000_floor": np.floor(income / 1000),
        "commute_integer": np.floor(commute),
    }
    return pd.DataFrame({
        name: category_keys(numeric_values(value).round().astype("Int64"))
        for name, value in values.items()
    }, index=data.index)

def fit_maps(data, base, original, state):
    original = original.assign(Will_Buy_EV=binary_target(original["Will_Buy_EV"]))
    state["original_mean"] = float(original["Will_Buy_EV"].mean())
    state["original_maps"] = {
        name: original.groupby(name, observed=True, dropna=False)["Will_Buy_EV"].mean().to_dict()
        for name in state["input_columns"] if name in original
    }
    state["core_columns"] = unique_columns(base)
    state["encoding_columns"] = [name for name in state["core_columns"] if not name.startswith("is_")]
    state["frequency_maps"] = {
        name: base[name].value_counts(normalize=True, dropna=False).to_dict()
        for name in state["encoding_columns"]
    }

def encoded_features(data, base, state, y=None):
    columns = {
        name: base[name].to_numpy(dtype=np.float32, copy=False)
        for name in state["core_columns"] if name not in state["category_maps"]
    }
    for name, mapping in state["original_maps"].items():
        columns[f"{name}_org_mean"] = data[name].map(mapping).fillna(state["original_mean"])
    for name in state["encoding_columns"]:
        columns[f"{name}_fe"] = base[name].map(state["frequency_maps"][name]).fillna(0)
    codes = base[state["encoding_columns"]]
    for label in ("auto", "10"):
        encoder = state["encoders"][label]
        values = encoder.fit_transform(codes, y) if y is not None else encoder.transform(codes)
        for index, name in enumerate(codes.columns):
            columns[f"{name}_TE_{label}"] = values[:, index]
    keys = smooth_keys(data)
    encoder = state["encoders"]["100"]
    values = encoder.fit_transform(keys, y) if y is not None else encoder.transform(keys)
    for index, name in enumerate(keys.columns):
        columns[f"enc_smooth_{name}_TE_100"] = values[:, index]
    return pd.DataFrame(columns, index=data.index, dtype=np.float32)

def transform_features(data, state):
    """Apply training mappings to validation or test rows without fitting."""
    features = encoded_features(data, base_features(data, state), state)
    return features[state["feature_names"]]

def fit_features(data, y, original_frame, seed=20260904):
    """Return cross-fitted training features and a portable dictionary of state."""
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Training data must be a pandas DataFrame.")
    y = binary_target(y)
    if len(data) != len(y):
        raise ValueError("Training data and target have different lengths.")
    folds = min(5, int(np.bincount(y, minlength=2).min()))
    if folds < 2:
        raise ValueError("Target encoding needs at least two examples of each class.")
    excluded = {"id", "Will_Buy_EV", "is_train", "Number_of_Cars_Owned"}
    names = [name for name in data if name not in excluded]
    categories = [name for name in names if not pd.api.types.is_numeric_dtype(data[name].dtype)]
    state = {"input_columns": names, "category_maps": {}, "encoders": {}, "seed": seed}
    for name in categories:
        values = sorted(category_keys(data[name]).unique())
        state["category_maps"][name] = {value: index for index, value in enumerate(values)}
    base = base_features(data, state)
    fit_maps(data, base, original_frame, state)
    for label, smooth in (("auto", "auto"), ("10", 10.0), ("100", 100.0)):
        state["encoders"][label] = TargetEncoder(
            target_type="binary", smooth=smooth, cv=5 if label == "100" else folds,
            shuffle=True, random_state=seed,
        )
    features = encoded_features(data, base, state, y)
    state["feature_names"] = list(features.columns)
    return features, state
