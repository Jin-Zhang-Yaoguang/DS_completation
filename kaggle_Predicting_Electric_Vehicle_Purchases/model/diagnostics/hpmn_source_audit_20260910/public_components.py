# Extracted definitions only; no notebook top-level execution.
import os
import gc
import glob
import math
import copy
import random
import warnings
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import TargetEncoder
from sklearn.metrics import roc_auc_score
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
SEED = 21
ID = 'id'
TARGET = 'Will_Buy_EV'
N_SPLITS = 5
RAW_NUMS = ['Age', 'Annual_Income_USD', 'Daily_Commute_km', 'Number_of_Cars_Owned', 'Charging_Stations_Near_Home', 'Charging_Stations_Near_Work', 'Environmental_Concern_Level']
RAW_CATS = ['Gender', 'City_Type', 'Current_Car_Type', 'Home_Charging_Possible', 'Subsidy_Available', 'Range_Anxiety_Level']
DIGIT_KS = list(range(-4, 4))
N_MATCH1 = 256
N_MATCH2 = 128
PATTERN_HIDDEN = 8
ROUTING_RANK = 12
LAMBDA_ROUTING = 1e-06
N_FIRE_KNOTS = 8
GEOMETRY_MIX_TEMP = 1.0
INIT_TARGET_M1 = 20.0
INIT_TARGET_M2 = 30.0
MASK_TEMP_START = 0.9
MASK_TEMP_END = 0.3
LOCAL_T_MIN = 0.03
LOCAL_T_MAX = 1.5
LOCAL_T_LOG_SCALE_INIT_STD = 0.0
LAMBDA_LOCAL_T = 1e-06
LAMBDA_GATE_DIVERSITY = 2e-06
MAX_EPOCHS = 40
PATIENCE = 9
BATCH_SIZE = 2048
PRED_BATCH_SIZE = 8192
LR = 0.0015
WEIGHT_DECAY = 2e-05
GRAD_CLIP = 5.0
LAMBDA_MASK_SIZE = 2e-06
LAMBDA_MASK_BINARY = 1e-06
LAMBDA_FIRE_SMOOTH = 1e-05
LAMBDA_HEAD_L2 = 1e-05
CENTER_INIT_ROWS = 8192

def safe_numeric(series):
    """Convert a column to float while preserving missing values."""
    return pd.to_numeric(series, errors='coerce').astype(np.float64)

def stringify_values(values):
    """Convert arbitrary values into stable categorical strings."""
    s = pd.Series(values, copy=False).astype('object')
    s = s.where(~pd.isna(s), '__NA__')
    return s.astype(str).to_numpy(dtype=object)

def build_base_frame(df):
    """
    Build the 67 base numerical features:
      - 7 raw numerics
      - 56 extracted decimal digits
      - 4 domain flags
    """
    out = pd.DataFrame(index=np.arange(len(df)))
    for col in RAW_NUMS:
        out[col] = safe_numeric(df[col]).to_numpy()
    for col in RAW_NUMS:
        x = safe_numeric(df[col]).to_numpy()
        for k in DIGIT_KS:
            scale = 10.0 ** k
            digit = np.floor(x / scale)
            digit = np.mod(digit, 10.0)
            out[f'{col}__digit_k{k}'] = digit
    income = safe_numeric(df['Annual_Income_USD']).to_numpy()
    concern = safe_numeric(df['Environmental_Concern_Level']).to_numpy()
    out['flag_income_eq_30000'] = (income == 30000).astype(np.float64)
    out['flag_income_ge_170537'] = (income >= 170537).astype(np.float64)
    out['flag_income_38k_42k'] = ((income >= 38000) & (income <= 42000)).astype(np.float64)
    out['flag_env_concern_eq_1'] = (concern == 1).astype(np.float64)
    return out

def fill_base_from_train(train_base, valid_base, test_base):
    """Median-impute base features using outer-fold training rows only."""
    for col in train_base.columns:
        median = np.nanmedian(train_base[col].to_numpy(dtype=np.float64))
        if not np.isfinite(median):
            median = 0.0
        train_base[col] = train_base[col].fillna(median)
        valid_base[col] = valid_base[col].fillna(median)
        test_base[col] = test_base[col].fillna(median)

def source_values(raw_df, base_df, source_name):
    """Return one of the 69 categorical sources used for frequency/target encoding."""
    kind, col = source_name.split('::', 1)
    if kind == 'rawcat':
        return stringify_values(raw_df[col].to_numpy())
    if kind == 'numcat':
        return stringify_values(safe_numeric(raw_df[col]).to_numpy())
    if kind == 'digitcat':
        return stringify_values(base_df[col].to_numpy())
    raise ValueError(source_name)

def make_single_col_matrix(values):
    return np.asarray(values, dtype=object).reshape(-1, 1)

def target_encode_builtin(train_values, valid_values, test_values, y_train, smooth, seed):
    """
    Fold-safe sklearn TargetEncoder.

    fit_transform() produces OOF values for the current outer-fold training rows.
    transform() is then applied to outer validation and competition test rows.
    """
    encoder = TargetEncoder(smooth=smooth, cv=5, shuffle=True, random_state=seed, target_type='binary')
    train_encoded = encoder.fit_transform(make_single_col_matrix(train_values), y_train).reshape(-1)
    valid_encoded = encoder.transform(make_single_col_matrix(valid_values)).reshape(-1)
    test_encoded = encoder.transform(make_single_col_matrix(test_values)).reshape(-1)
    return (train_encoded, valid_encoded, test_encoded)

def build_fold_features(train_raw, test_raw, train_idx, valid_idx, fold_number):
    """
    Rebuild the complete record representation independently for one outer fold.

    Expected Fold-1 accounting:
        67 base
      + 69 frequency
      + 69 TE(auto)
      + 69 TE(10)
      = 274 numerical candidates

    Historical constant removal:
        274 - 76 = 198 numerical features

    Plus 6 raw categorical IDs:
        198 + 6 = 204 final features
    """
    fold_train = train_raw.iloc[train_idx].reset_index(drop=True)
    fold_valid = train_raw.iloc[valid_idx].reset_index(drop=True)
    y_train = fold_train[TARGET].to_numpy(dtype=np.float32)
    y_valid = fold_valid[TARGET].to_numpy(dtype=np.float32)
    base_train = build_base_frame(fold_train)
    base_valid = build_base_frame(fold_valid)
    base_test = build_base_frame(test_raw)
    fill_base_from_train(base_train, base_valid, base_test)
    digit_cols = [col for col in base_train.columns if '__digit_k' in col]
    encoding_sources = [f'rawcat::{col}' for col in RAW_CATS] + [f'numcat::{col}' for col in RAW_NUMS] + [f'digitcat::{col}' for col in digit_cols]
    assert len(encoding_sources) == 69
    freq_train = pd.DataFrame(index=np.arange(len(fold_train)))
    freq_valid = pd.DataFrame(index=np.arange(len(fold_valid)))
    freq_test = pd.DataFrame(index=np.arange(len(test_raw)))
    for source in encoding_sources:
        train_values = source_values(fold_train, base_train, source)
        valid_values = source_values(fold_valid, base_valid, source)
        test_values = source_values(test_raw, base_test, source)
        frequency_map = pd.Series(train_values).value_counts(dropna=False, normalize=True).to_dict()
        name = f'freq::{source}'
        freq_train[name] = pd.Series(train_values).map(frequency_map).fillna(0.0).to_numpy(np.float64)
        freq_valid[name] = pd.Series(valid_values).map(frequency_map).fillna(0.0).to_numpy(np.float64)
        freq_test[name] = pd.Series(test_values).map(frequency_map).fillna(0.0).to_numpy(np.float64)
    catid_train = pd.DataFrame(index=np.arange(len(fold_train)))
    catid_valid = pd.DataFrame(index=np.arange(len(fold_valid)))
    catid_test = pd.DataFrame(index=np.arange(len(test_raw)))
    for col in RAW_CATS:
        train_values = stringify_values(fold_train[col].to_numpy())
        valid_values = stringify_values(fold_valid[col].to_numpy())
        test_values = stringify_values(test_raw[col].to_numpy())
        unique_values = pd.Index(pd.unique(train_values))
        mapping = {value: i + 1 for i, value in enumerate(unique_values)}
        name = f'catid::{col}'
        catid_train[name] = pd.Series(train_values).map(mapping).fillna(0).astype(np.float64).to_numpy()
        catid_valid[name] = pd.Series(valid_values).map(mapping).fillna(0).astype(np.float64).to_numpy()
        catid_test[name] = pd.Series(test_values).map(mapping).fillna(0).astype(np.float64).to_numpy()
    te_auto_train = pd.DataFrame(index=np.arange(len(fold_train)))
    te_auto_valid = pd.DataFrame(index=np.arange(len(fold_valid)))
    te_auto_test = pd.DataFrame(index=np.arange(len(test_raw)))
    te_10_train = pd.DataFrame(index=np.arange(len(fold_train)))
    te_10_valid = pd.DataFrame(index=np.arange(len(fold_valid)))
    te_10_test = pd.DataFrame(index=np.arange(len(test_raw)))
    encoder_seed = SEED + (fold_number - 1)
    print(f'Fold {fold_number}: building 2 x 69 target encodings...')
    for j, source in enumerate(encoding_sources):
        train_values = source_values(fold_train, base_train, source)
        valid_values = source_values(fold_valid, base_valid, source)
        test_values = source_values(test_raw, base_test, source)
        auto_train, auto_valid, auto_test = target_encode_builtin(train_values, valid_values, test_values, y_train, smooth='auto', seed=encoder_seed)
        ten_train, ten_valid, ten_test = target_encode_builtin(train_values, valid_values, test_values, y_train, smooth=10.0, seed=encoder_seed)
        te_auto_train[f'te_auto::{source}'] = auto_train
        te_auto_valid[f'te_auto::{source}'] = auto_valid
        te_auto_test[f'te_auto::{source}'] = auto_test
        te_10_train[f'te_10::{source}'] = ten_train
        te_10_valid[f'te_10::{source}'] = ten_valid
        te_10_test[f'te_10::{source}'] = ten_test
        if (j + 1) % 10 == 0 or j + 1 == len(encoding_sources):
            print(f'  encoded {j + 1}/{len(encoding_sources)} sources')
    numeric_train = pd.concat([base_train.reset_index(drop=True), freq_train, te_auto_train, te_10_train], axis=1)
    numeric_valid = pd.concat([base_valid.reset_index(drop=True), freq_valid, te_auto_valid, te_10_valid], axis=1)
    numeric_test = pd.concat([base_test.reset_index(drop=True), freq_test, te_auto_test, te_10_test], axis=1)
    assert numeric_train.shape[1] == 274, numeric_train.shape
    numeric_train = numeric_train.replace([np.inf, -np.inf], np.nan)
    numeric_valid = numeric_valid.replace([np.inf, -np.inf], np.nan)
    numeric_test = numeric_test.replace([np.inf, -np.inf], np.nan)
    for col in numeric_train.columns:
        median = np.nanmedian(numeric_train[col].to_numpy(dtype=np.float64))
        if not np.isfinite(median):
            median = 0.0
        numeric_train[col] = numeric_train[col].fillna(median)
        numeric_valid[col] = numeric_valid[col].fillna(median)
        numeric_test[col] = numeric_test[col].fillna(median)
    unique_counts = numeric_train.nunique(dropna=False)
    keep_numeric_cols = unique_counts[unique_counts > 1].index.tolist()
    dropped_numeric_cols = unique_counts[unique_counts <= 1].index.tolist()
    numeric_train = numeric_train[keep_numeric_cols]
    numeric_valid = numeric_valid[keep_numeric_cols]
    numeric_test = numeric_test[keep_numeric_cols]
    full_train = pd.concat([numeric_train.reset_index(drop=True), catid_train], axis=1)
    full_valid = pd.concat([numeric_valid.reset_index(drop=True), catid_valid], axis=1)
    full_test = pd.concat([numeric_test.reset_index(drop=True), catid_test], axis=1)
    feature_names = full_train.columns.tolist()
    print(f'Fold {fold_number}: {len(keep_numeric_cols)} numerical + {catid_train.shape[1]} categorical IDs = {len(feature_names)} final features')
    if fold_number == 1:
        print('Historical Fold-1 target: 198 numerical + 6 categorical IDs = 204.')
        if len(feature_names) != 204:
            print('WARNING: Fold 1 did not reproduce 204 features. Do not treat this run as an exact record-feature reproduction.')
        print(f'Fold 1 numerical constants removed: {len(dropped_numeric_cols)}')
    x_train_raw = full_train.to_numpy(dtype=np.float32)
    x_valid_raw = full_valid.to_numpy(dtype=np.float32)
    x_test_raw = full_test.to_numpy(dtype=np.float32)
    mean = x_train_raw.mean(axis=0, dtype=np.float64).astype(np.float32)
    std = x_train_raw.std(axis=0, dtype=np.float64).astype(np.float32)
    mean = np.where(np.isfinite(mean), mean, 0.0).astype(np.float32)
    std = np.where(np.isfinite(std) & (std > 1e-07), std, 1.0).astype(np.float32)
    x_train = np.clip((x_train_raw - mean) / std, -8.0, 8.0).astype(np.float32)
    x_valid = np.clip((x_valid_raw - mean) / std, -8.0, 8.0).astype(np.float32)
    x_test = np.clip((x_test_raw - mean) / std, -8.0, 8.0).astype(np.float32)
    return (x_train, y_train, x_valid, y_valid, x_test, feature_names)

def logit_scalar(p):
    p = float(np.clip(p, 1e-05, 1 - 1e-05))
    return math.log(p / (1.0 - p))

class PrototypeMatchingLayer(nn.Module):
    """
    Prototype matching layer with a learned soft feature subset per neuron.

    Each matcher combines:
      1) Euclidean proximity
      2) cosine-direction similarity
      3) a learned signed mismatch-pattern score
      4) an M_eff-normalized weighted dot-product score
    """

    def __init__(self, input_dim, n_units, init_target_m, n_fire_knots=N_FIRE_KNOTS, pattern_hidden=PATTERN_HIDDEN):
        super().__init__()
        self.input_dim = int(input_dim)
        self.n_units = int(n_units)
        self.n_fire_knots = int(n_fire_knots)
        self.pattern_hidden = int(pattern_hidden)
        self.mask_temperature = float(MASK_TEMP_START)
        self.log_temperature_scale = nn.Parameter(torch.randn(n_units) * LOCAL_T_LOG_SCALE_INIT_STD)
        self.centers = nn.Parameter(torch.randn(n_units, input_dim) * 0.15)
        self.feature_scores = nn.Parameter(torch.randn(n_units, input_dim) * 0.03)
        init_p = np.clip(init_target_m / max(input_dim, 1), 0.0001, 1 - 0.0001)
        tau0 = -MASK_TEMP_START * logit_scalar(init_p)
        self.raw_tau = nn.Parameter(torch.full((n_units,), float(tau0)))
        inv_softplus_one = math.log(math.expm1(1.0))
        self.raw_fire_increments = nn.Parameter(torch.full((n_units, 4, n_fire_knots - 1), inv_softplus_one))
        self.geometry_logits = nn.Parameter(torch.zeros(n_units, 4))
        scale1 = 0.2 / max(input_dim, 1) ** 0.5
        scale2 = 0.2 / max(pattern_hidden, 1) ** 0.5
        self.pattern_w1 = nn.Parameter(torch.randn(n_units, pattern_hidden, input_dim) * scale1)
        self.pattern_b1 = nn.Parameter(torch.zeros(n_units, pattern_hidden))
        self.pattern_w2 = nn.Parameter(torch.randn(n_units, pattern_hidden) * scale2)
        self.pattern_b2 = nn.Parameter(torch.zeros(n_units))

    def set_mask_temperature(self, temperature):
        self.mask_temperature = float(temperature)

    def centered_log_temperature_scale(self):
        """
        Zero-center the learned log-temperature offsets within this layer.

        This removes the common/global drift direction. Individual matchers can
        still become harder or softer, but the layer as a whole remains anchored
        to the global annealing schedule.
        """
        return self.log_temperature_scale - self.log_temperature_scale.mean()

    def local_temperatures(self):
        """
        Return one relative learned mask temperature per matcher.

        T_i(t) = clip(
            T_global(t) * exp(alpha_i - mean(alpha)),
            LOCAL_T_MIN,
            LOCAL_T_MAX
        )

        Before clipping, the geometric mean of the local temperatures is exactly
        the current global temperature.
        """
        global_temperature = max(float(self.mask_temperature), 0.0001)
        centered_alpha = self.centered_log_temperature_scale()
        local_temperature = global_temperature * torch.exp(centered_alpha)
        return local_temperature.clamp(LOCAL_T_MIN, LOCAL_T_MAX)

    def gates(self):
        local_temperature = self.local_temperatures().unsqueeze(1)
        return torch.sigmoid((self.feature_scores - self.raw_tau.unsqueeze(1)) / local_temperature)

    def fire_values(self):
        increments = F.softplus(self.raw_fire_increments) + 1e-06
        cumulative = torch.cumsum(increments, dim=2)
        cumulative = cumulative / cumulative[:, :, -1:].clamp_min(1e-08)
        zero = torch.zeros((self.n_units, 4, 1), device=cumulative.device, dtype=cumulative.dtype)
        return torch.cat([zero, cumulative], dim=2)

    def apply_fire_curve(self, match_score):
        """
        Apply independent monotonic calibration to Euclid, cosine, pattern and dot-product.

        match_score shape: [batch, units, 4]
        """
        position = match_score.clamp(0.0, 1.0) * (self.n_fire_knots - 1)
        idx0 = torch.floor(position).long().clamp(0, self.n_fire_knots - 2)
        frac = position - idx0.to(position.dtype)
        values = self.fire_values()
        values_b = values.unsqueeze(0).expand(match_score.shape[0], -1, -1, -1)
        y0 = torch.gather(values_b, dim=3, index=idx0.unsqueeze(3)).squeeze(3)
        y1 = torch.gather(values_b, dim=3, index=(idx0 + 1).unsqueeze(3)).squeeze(3)
        return y0 + frac * (y1 - y0)

    def forward(self, x):
        weights = self.gates()
        centers = self.centers
        effective_m = weights.sum(dim=1).clamp_min(0.001)
        weighted_centers = weights * centers
        x2 = x.pow(2) @ weights.t()
        cross = 2.0 * (x @ weighted_centers.t())
        c2 = (weights * centers.pow(2)).sum(dim=1).unsqueeze(0)
        distance2 = ((x2 - cross + c2) / effective_m.unsqueeze(0)).clamp_min(0.0)
        euclidean_match = 1.0 / (1.0 + distance2)
        dot = x @ weighted_centers.t()
        x_norm = torch.sqrt((x.pow(2) @ weights.t()).clamp_min(1e-08))
        center_norm = torch.sqrt((weights * centers.pow(2)).sum(dim=1).clamp_min(1e-08)).unsqueeze(0)
        cosine = (dot / (x_norm * center_norm)).clamp(-1.0, 1.0)
        cosine_match = 0.5 * (cosine + 1.0)
        normalized_dot = dot / effective_m.unsqueeze(0)
        dot_match = torch.sigmoid(normalized_dot)
        effective_pattern_w1 = self.pattern_w1 * weights[:, None, :]
        hidden = torch.einsum('bd,uhd->buh', x, effective_pattern_w1)
        center_offset = (effective_pattern_w1 * centers[:, None, :]).sum(dim=2)
        hidden = hidden - center_offset.unsqueeze(0) + self.pattern_b1.unsqueeze(0)
        hidden = F.gelu(hidden)
        pattern_logit = (hidden * self.pattern_w2.unsqueeze(0)).sum(dim=2) + self.pattern_b2.unsqueeze(0)
        pattern_match = torch.sigmoid(pattern_logit)
        components = torch.stack([euclidean_match, cosine_match, pattern_match, dot_match], dim=2)
        fired_components = self.apply_fire_curve(components)
        geometry_weights = F.softmax(self.geometry_logits / GEOMETRY_MIX_TEMP, dim=1)
        return (fired_components * geometry_weights.unsqueeze(0)).sum(dim=2)

    def regularization(self):
        weights = self.gates()
        size_penalty = weights.mean()
        binary_penalty = (weights * (1.0 - weights)).mean()
        fire = self.fire_values()
        second_difference = fire[:, :, 2:] - 2.0 * fire[:, :, 1:-1] + fire[:, :, :-2]
        fire_smoothness = second_difference.pow(2).mean()
        centered_alpha = self.centered_log_temperature_scale()
        local_t_penalty = centered_alpha.pow(2).mean()
        normalized_gates = weights / weights.norm(dim=1, keepdim=True).clamp_min(1e-08)
        gate_similarity = normalized_gates @ normalized_gates.t()
        n = gate_similarity.shape[0]
        if n > 1:
            eye = torch.eye(n, device=gate_similarity.device, dtype=gate_similarity.dtype)
            gate_diversity = (gate_similarity * (1.0 - eye)).pow(2).sum() / (n * (n - 1))
        else:
            gate_diversity = torch.zeros((), device=weights.device, dtype=weights.dtype)
        return LAMBDA_MASK_SIZE * size_penalty + LAMBDA_MASK_BINARY * binary_penalty + LAMBDA_FIRE_SMOOTH * fire_smoothness + LAMBDA_LOCAL_T * local_t_penalty + LAMBDA_GATE_DIVERSITY * gate_diversity

    @torch.no_grad()
    def initialize_centers_from_rows(self, rows, seed):
        rng = np.random.default_rng(seed)
        n_rows = rows.shape[0]
        idx = rng.choice(n_rows, size=self.n_units, replace=n_rows < self.n_units)
        chosen = rows[idx]
        if not torch.is_tensor(chosen):
            chosen = torch.as_tensor(chosen, dtype=self.centers.dtype, device=self.centers.device)
        else:
            chosen = chosen.to(self.centers.device, dtype=self.centers.dtype)
        self.centers.copy_(chosen)

    @torch.no_grad()
    def diagnostics(self):
        weights = self.gates()
        effective_m = weights.sum(dim=1)
        geometry = F.softmax(self.geometry_logits, dim=1)
        local_t = self.local_temperatures()
        return {'m_mean': float(effective_m.mean().cpu()), 'geometry_mean': geometry.mean(dim=0).cpu().numpy(), 't_global': float(self.mask_temperature), 't_mean': float(local_t.mean().cpu()), 't_min': float(local_t.min().cpu()), 't_max': float(local_t.max().cpu())}

class HierarchicalMatcher(nn.Module):

    def __init__(self, input_dim):
        super().__init__()
        self.match1 = PrototypeMatchingLayer(input_dim=input_dim, n_units=N_MATCH1, init_target_m=INIT_TARGET_M1)
        self.match2 = PrototypeMatchingLayer(input_dim=N_MATCH1, n_units=N_MATCH2, init_target_m=INIT_TARGET_M2)
        self.route_down = nn.Linear(N_MATCH1, ROUTING_RANK, bias=True)
        self.route_up = nn.Linear(ROUTING_RANK, N_MATCH1, bias=True)
        nn.init.normal_(self.route_down.weight, mean=0.0, std=0.02 / max(N_MATCH1, 1) ** 0.5)
        nn.init.zeros_(self.route_down.bias)
        nn.init.zeros_(self.route_up.weight)
        nn.init.zeros_(self.route_up.bias)
        self.head = nn.Linear(N_MATCH1 + N_MATCH2, 1)

    def set_mask_temperature(self, temperature):
        self.match1.set_mask_temperature(temperature)
        self.match2.set_mask_temperature(temperature)

    def routing_weights(self, h1):
        """
        Sample-dependent multiplicative routing over h1.

        Returns positive weights with per-sample mean ~= 1.0.
        At initialization every route is exactly 1.0.
        """
        context = torch.tanh(self.route_down(h1))
        route_logits = self.route_up(context)
        route = 2.0 * torch.sigmoid(route_logits)
        route = route / route.mean(dim=1, keepdim=True).clamp_min(1e-06)
        return route

    def forward(self, x):
        h1 = self.match1(x)
        route = self.routing_weights(h1)
        routed_h1 = h1 * route
        h2 = self.match2(routed_h1)
        readout = torch.cat([h1, h2], dim=1)
        return self.head(readout).squeeze(1)

    def regularization(self):
        routing_penalty = self.route_up.weight.pow(2).mean() + self.route_up.bias.pow(2).mean()
        return self.match1.regularization() + self.match2.regularization() + LAMBDA_HEAD_L2 * self.head.weight.pow(2).mean() + LAMBDA_ROUTING * routing_penalty

    @torch.no_grad()
    def initialize_centers(self, x_train, seed):
        rng = np.random.default_rng(seed)
        n_rows = min(CENTER_INIT_ROWS, len(x_train))
        idx = rng.choice(len(x_train), size=n_rows, replace=False)
        rows = torch.from_numpy(x_train[idx]).to(DEVICE)
        self.match1.initialize_centers_from_rows(rows, seed + 1)
        layer1_parts = []
        for start in range(0, len(rows), 2048):
            layer1_parts.append(self.match1(rows[start:start + 2048]).detach())
        layer1_rows = torch.cat(layer1_parts, dim=0)
        self.match2.initialize_centers_from_rows(layer1_rows, seed + 2)

class BinaryDataset(Dataset):

    def __init__(self, x, y):
        self.x = x
        self.y = y.astype(np.float32)

    def __len__(self):
        return len(self.x)

    def __getitem__(self, index):
        return (torch.from_numpy(self.x[index]), torch.tensor(self.y[index], dtype=torch.float32))

@torch.no_grad()
def predict_logits(model, x, batch_size=PRED_BATCH_SIZE):
    model.eval()
    output = np.empty(len(x), dtype=np.float32)
    for start in range(0, len(x), batch_size):
        end = min(start + batch_size, len(x))
        xb = torch.from_numpy(x[start:end]).to(DEVICE, non_blocking=True)
        output[start:end] = model(xb).float().cpu().numpy()
    return output

def sigmoid_np(x):
    x = np.clip(x, -30.0, 30.0)
    return 1.0 / (1.0 + np.exp(-x))
