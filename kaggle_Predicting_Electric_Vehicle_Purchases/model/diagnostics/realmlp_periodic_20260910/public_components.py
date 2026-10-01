# 来源和改动见preregistration.json；只抽取导入、函数、类和配置，不执行原Notebook数据/训练流程。
import math
import random
import warnings
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.utils.class_weight import compute_class_weight
from sklearn.preprocessing import KBinsDiscretizer, TargetEncoder
import torch
import torch.nn as nn
import torch.nn.functional as F

def seed_everything(seed: int):
    np.random.seed(seed)
    random.seed(seed)
    torch.manual_seed(seed)

def feature_engineering(df, fit=False):
    for col in cat_cols:
        df[col] = df[col].fillna('missing')
    for col in num_cols:
        df[col] = df[col].fillna(0.0)
    for col in cat_cols:
        if fit:
            codes, uniques = df[col].factorize()
            category_map[col] = uniques
        else:
            uniques = category_map[col]
            code_map = {cat: i for i, cat in enumerate(uniques)}
            codes = df[col].map(code_map).fillna(-1).astype('int32')
        df[col] = codes
        df[col] = df[col].astype('category')
    df['_Daily_Commute_km_/_Age'] = (df['Daily_Commute_km'] / (df['Age'] + 1e-06)).astype('float32')
    df['Income_/_100_floor_'] = np.floor(df['Annual_Income_USD'] / 100.0).astype('float32').astype('category')
    df['Income_/_1000_floor_'] = np.floor(df['Annual_Income_USD'] / 1000.0).astype('float32').astype('category')
    df['Income_/_10000_floor_'] = np.floor(df['Annual_Income_USD'] / 10000.0).astype('float32').astype('category')
    df['Daily_km_/_5_floor_'] = np.floor(df['Daily_Commute_km'] / 5.0).astype('float32').astype('category')
    for col in num_cols:
        cat_name = f'{col}_cat_'
        if fit:
            codes, uniques = np.floor(df[col]).factorize()
            category_map[col] = uniques
        else:
            uniques = category_map[col]
            code_map = {cat: i for i, cat in enumerate(uniques)}
            codes = np.floor(df[col]).map(code_map).fillna(-1).astype('int32')
        df[cat_name] = codes
        df[cat_name] = df[cat_name].astype('category')
    for col in ['Daily_Commute_km']:
        decimal_name = f'_{col}_decimal'
        df[decimal_name] = (df[col] % 1).round(2).astype('float32')
    df['Annual_Income_USD_is_multiple_10_'] = (np.floor(df['Annual_Income_USD']) % 10 == 0).astype('category')
    for col in ['Annual_Income_USD']:
        orig_enc_name = f'_{col}_mean_target_orig'
        df[orig_enc_name] = df[col].map(orig.groupby(col)[TARGET].mean()).fillna(orig[TARGET].mean()).astype('float32')
    for col in ['Annual_Income_USD']:
        count_name = f'_{col}_count'
        if fit:
            count_map = df[col].value_counts()
            category_map[count_name] = count_map
        else:
            count_map = category_map[count_name]
        df[count_name] = df[col].astype(object).map(count_map).fillna(0).astype('int32')
    bin_config = {'Annual_Income_USD': [400, 600, 800, 900, 1100]}
    for col, bins_list in bin_config.items():
        for n_bins in bins_list:
            for strategy in ['quantile']:
                bin_name = f'{col}_{n_bins}_{strategy}_bin_'
                if fit:
                    kb = KBinsDiscretizer(n_bins=n_bins, encode='ordinal', strategy=strategy, subsample=None)
                    binned = kb.fit_transform(df[[col]]).ravel().astype('int32')
                    category_map[bin_name] = kb
                else:
                    kb = category_map[bin_name]
                    binned = kb.transform(df[[col]]).ravel().astype('int32')
                df[bin_name] = binned
                df[bin_name] = df[bin_name].astype('category')
    combo_names = []
    for cols in important_combos:
        combo_name = '_'.join(cols) + '_'
        combo_names.append(combo_name)
        combo_series = df[cols[0]].astype(str)
        for col in cols[1:]:
            combo_series = combo_series + '_' + df[col].astype(str)
        if fit:
            codes, uniques = pd.factorize(combo_series, sort=False)
            category_map[combo_name] = uniques
        else:
            uniques = category_map[combo_name]
            code_map = {cat: i for i, cat in enumerate(uniques)}
            codes = combo_series.map(code_map).fillna(-1).astype('int32')
        df[combo_name] = codes
        df[combo_name] = df[combo_name].astype('category')
    new_cat_cols = [col for col in df.columns if col.endswith('_')]
    new_num_cols = [col for col in df.columns if col.startswith('_')]
    return (df, new_cat_cols, new_num_cols, combo_names)

class NumericalPreprocessor(BaseEstimator, TransformerMixin):
    """
    Applies a configurable sequence of numerical transforms from CONFIG["tfms"].
    Supported: 'median_center', 'robust_scale', 'smooth_clip', 'l2_normalize'.
    'one_hot' and 'embedding' are recognised but skipped (handled by the model).
    """

    def __init__(self, tfms):
        self._tfms = [t for t in tfms if t in ('median_center', 'robust_scale', 'smooth_clip', 'l2_normalize')]

    def fit(self, X: np.ndarray, y=None):
        if 'median_center' in self._tfms or 'robust_scale' in self._tfms:
            self._median = np.median(X, axis=0)
            q_diff = np.quantile(X, 0.75, axis=0) - np.quantile(X, 0.25, axis=0)
            zero_idx = q_diff == 0.0
            q_diff[zero_idx] = 0.5 * (X.max(axis=0)[zero_idx] - X.min(axis=0)[zero_idx])
            self._iqr_factors = 1.0 / (q_diff + 1e-30)
            self._iqr_factors[q_diff == 0.0] = 0.0
        return self

    def transform(self, X: np.ndarray, y=None) -> np.ndarray:
        X = X.copy().astype(np.float32)
        for tfm in self._tfms:
            if tfm == 'median_center':
                X -= self._median[None, :]
            elif tfm == 'robust_scale':
                X *= self._iqr_factors[None, :]
            elif tfm == 'smooth_clip':
                X = X / np.sqrt(1 + (X / 3) ** 2)
            elif tfm == 'l2_normalize':
                norms = np.linalg.norm(X, axis=1, keepdims=True)
                X /= np.where(norms == 0, 1.0, norms)
        return X

class CategoricalFeatureLayer(nn.Module):

    def __init__(self, n_ens: int, cat_dims, embed_dim: int=8, onehot_thresh: int=8, device=None):
        super().__init__()
        self.n_ens = n_ens
        self.cat_dims = cat_dims
        self.onehot_features = []
        self.embed_layers = nn.ModuleList()
        self._embed_feature_indices = []
        for i, dim in enumerate(cat_dims):
            if dim <= onehot_thresh:
                self.onehot_features.append(i)
            else:
                emb = nn.ModuleList([nn.Embedding(dim, embed_dim) for _ in range(n_ens)])
                self.embed_layers.append(emb)
                self._embed_feature_indices.append(i)

    def forward(self, x):
        batch_size, n_ens, _ = x.shape
        features = []
        if self.onehot_features:
            onehot_x = x[:, :, self.onehot_features]
            onehot_dims = [self.cat_dims[i] for i in self.onehot_features]
            total_oh = sum(onehot_dims)
            encoded = torch.zeros(batch_size, n_ens, total_oh, device=x.device)
            start = 0
            for idx, dim in enumerate(onehot_dims):
                pos = onehot_x[:, :, idx:idx + 1].long()
                encoded.scatter_(2, pos + start, 1.0)
                start += dim
            features.append(encoded)
        for emb_list, feat_idx in zip(self.embed_layers, self._embed_feature_indices):
            feat_embs = []
            for model_idx in range(self.n_ens):
                indices = x[:, model_idx, feat_idx:feat_idx + 1].long()
                feat_embs.append(emb_list[model_idx](indices))
            feat_combined = torch.cat(feat_embs, dim=1)
            features.append(feat_combined)
        return torch.cat(features, dim=2)

class ScalingLayer(nn.Module):

    def __init__(self, n_ens: int, n_features: int):
        super().__init__()
        self.scale = nn.Parameter(torch.ones(n_ens, n_features))

    def forward(self, x):
        return x * self.scale[None, :, :]

class NTPLinear(nn.Module):

    def __init__(self, n_ens: int, in_features: int, out_features: int, bias: bool=True):
        super().__init__()
        self.in_features = in_features
        self.out_features = out_features
        self.weight = nn.Parameter(torch.randn(n_ens, in_features, out_features))
        self.bias = nn.Parameter(torch.randn(n_ens, out_features)) if bias else None

    def forward(self, x):
        x = torch.einsum('bki,kio->bko', x, self.weight) / math.sqrt(self.in_features)
        if self.bias is not None:
            x = x + self.bias
        return x

class ResidualBlock(nn.Module):

    def __init__(self, n_ens: int, dim: int, dropout: float, activation=nn.SiLU):
        super().__init__()
        self.linear = NTPLinear(n_ens=n_ens, in_features=dim, out_features=dim)
        self.act = activation()
        self.drop = nn.Dropout(dropout)
        self.res_scale = nn.Parameter(torch.ones(n_ens, dim) * 0.1)

    def forward(self, x):
        residual = x
        x = self.linear(x)
        x = self.act(x)
        x = self.drop(x)
        return residual + x * self.res_scale.unsqueeze(0)

class PBLDEmbedding(nn.Module):
    """Periodic Basis with Learned Decay embedding for numerical features."""

    def __init__(self, n_ens: int, n_features: int, hidden_dim: int=16, out_dim: int=4, freq_scale: float=0.1, activation=nn.GELU):
        super().__init__()
        self.n_ens = n_ens
        self.n_features = n_features
        self.out_dim = out_dim
        self.w1 = nn.Parameter(torch.empty(n_ens, n_features, hidden_dim))
        nn.init.normal_(self.w1, mean=0.0, std=freq_scale / math.sqrt(hidden_dim))
        self.b1 = nn.Parameter(torch.randn(n_ens, n_features, hidden_dim))
        self.w2 = nn.Parameter(torch.randn(n_ens, n_features, hidden_dim, out_dim - 1) / math.sqrt(hidden_dim))
        self.b2 = nn.Parameter(torch.zeros(n_ens, n_features, out_dim - 1))
        self.act = activation()
        nn.init.uniform_(self.b1, -math.pi, math.pi)

    def forward(self, x):
        periodic = (torch.cos if self.periodic else torch.tanh)(2 * math.pi * (x.unsqueeze(-1) * self.w1.unsqueeze(0) + self.b1.unsqueeze(0)))
        transformed = self.act(torch.einsum('bkfh,kfhd->bkfd', periodic, self.w2) + self.b2.unsqueeze(0))
        feat = torch.cat([x.unsqueeze(-1), transformed], dim=-1)
        return feat.flatten(start_dim=2)

class RealMLP(nn.Module):

    def __init__(self, output_dim: int, cat_dims, n_numerical: int, cfg: dict):
        super().__init__()
        n_ens = cfg['n_ens']
        embed_dim = cfg['embed_dim']
        self.n_ens = n_ens
        self.cate = CategoricalFeatureLayer(n_ens=n_ens, cat_dims=cat_dims, embed_dim=embed_dim, onehot_thresh=cfg['onehot_thresh'])
        self.num_embed = PBLDEmbedding(n_ens=n_ens, n_features=n_numerical, hidden_dim=cfg['pbld_hidden_dim'], out_dim=cfg['pbld_out_dim'], freq_scale=cfg['pbld_freq_scale'], activation=cfg['pbld_activation'])
        num_emb_dim = n_numerical * cfg['pbld_out_dim']
        cat_emb_dim = sum((c if c <= cfg['onehot_thresh'] else embed_dim for c in cat_dims))
        total_dim = num_emb_dim + cat_emb_dim
        hidden_dims = cfg['hidden_dims']
        act = cfg['activation']
        self._dropout_modules = []
        layers = []
        if cfg['add_front_scale']:
            layers.append(ScalingLayer(n_ens=n_ens, n_features=total_dim))
        in_dim = total_dim
        first_linear = NTPLinear(n_ens=n_ens, in_features=in_dim, out_features=hidden_dims[0])
        self.first_linear = first_linear
        layers.extend([first_linear, act()])
        in_dim = hidden_dims[0]
        for hdim in hidden_dims[1:]:
            if in_dim != hdim:
                layers.extend([NTPLinear(n_ens=n_ens, in_features=in_dim, out_features=hdim), act()])
                in_dim = hdim
            block = ResidualBlock(n_ens=n_ens, dim=hdim, dropout=cfg['dropout'], activation=act)
            self._dropout_modules.append(block.drop)
            layers.append(block)
        self.hidden = nn.Sequential(*layers)
        self.output_layer = NTPLinear(n_ens=n_ens, in_features=in_dim, out_features=output_dim)
        with torch.no_grad():
            self.output_layer.weight.mul_(0.1)
            if self.output_layer.bias is not None:
                self.output_layer.bias.zero_()

    def forward(self, x_num, x_cat):
        x_num = x_num.unsqueeze(1).expand(-1, self.n_ens, -1)
        x_cat = x_cat.unsqueeze(1).expand(-1, self.n_ens, -1)
        x_num = self.num_embed(x_num)
        x_cat = self.cate(x_cat)
        combined = torch.cat([x_num, x_cat], dim=2)
        x = self.hidden(combined)
        x = self.output_layer(x)
        return x

def apply_schedule(init_value: float, progress: float, sched: str, flat_ratio: float=0.3) -> float:
    """
    Supported schedules:
      'constant'    – no decay
      'cos'         – cosine from init to 0
      'flat_cos'    – flat for flat_ratio, then cosine to 0
      'flat_anneal' – flat for flat_ratio, then linear to 0
      'sqrt_cos'    – sqrt of cosine annealing (slower decay)
      'expm4t'      – exponential decay: init * exp(-4 * progress)
    """
    if sched == 'constant':
        return init_value
    elif sched == 'cos':
        return init_value * (math.cos(math.pi * progress) + 1) / 2
    elif sched == 'flat_cos':
        if progress < flat_ratio:
            return init_value
        t = (progress - flat_ratio) / (1 - flat_ratio)
        return init_value * (math.cos(math.pi * t) + 1) / 2
    elif sched == 'flat_anneal':
        if progress < flat_ratio:
            return init_value
        t = (progress - flat_ratio) / (1 - flat_ratio)
        return init_value * (1 - t)
    elif sched == 'sqrt_cos':
        return init_value * math.sqrt((math.cos(math.pi * progress) + 1) / 2)
    elif sched == 'expm4t':
        return init_value * math.exp(-4 * progress)
    else:
        raise ValueError(f"Unknown schedule: '{sched}'")

def get_parameter_groups(model: RealMLP, p: dict):
    """
    Five groups with independent lr / wd:
      0 – ScalingLayer params  (scale.*)
      1 – PBLD / num_embed params
      2 – first hidden linear weight
      3 – all other weights
      4 – all biases (excluding those already in groups 0-2)
    Note: PBLD has its own bias params (b1, b2) which belong to group 1, not 4.
    The ordering of checks therefore is: scale → num_embed → first_w → bias → other_w.
    """
    first_linear_weight_id = id(model.first_linear.weight)
    scale_p, pbld_p, first_w_p, other_w_p, bias_p = ([], [], [], [], [])
    for name, param in model.named_parameters():
        if 'num_embed' in name:
            pbld_p.append(param)
        elif 'scale' in name:
            scale_p.append(param)
        elif id(param) == first_linear_weight_id:
            first_w_p.append(param)
        elif 'bias' in name:
            bias_p.append(param)
        else:
            other_w_p.append(param)
    LR = p['lr']
    WD = p['weight_decay']
    return [{'params': scale_p, 'lr': LR * p['lr_scale_mult'], 'weight_decay': WD * p['wd_scale_mult'], 'group': 'scale'}, {'params': pbld_p, 'lr': LR * p['pbld_lr_factor'], 'weight_decay': WD, 'group': 'pbld'}, {'params': first_w_p, 'lr': LR * p['first_layer_lr_factor'], 'weight_decay': WD * p['first_layer_wd_factor'], 'group': 'first_w'}, {'params': other_w_p, 'lr': LR, 'weight_decay': WD, 'group': 'other_w'}, {'params': bias_p, 'lr': LR * p['lr_bias_mult'], 'weight_decay': WD * p['wd_bias_mult'], 'group': 'bias'}]

def binary_bce_loss(y_true: torch.Tensor, logits: torch.Tensor, ls: float=0.0, pos_weight: torch.Tensor=None) -> torch.Tensor:
    """
    y_true : (N,) float {0,1}
    y_pred : (N,) sigmoid probabilities
    """
    if ls > 0.0:
        y_true = y_true * (1.0 - ls) + 0.5 * ls
    if pos_weight is None:
        loss = (1.0 - y_true) * logits + F.softplus(-logits)
    else:
        loss = (1.0 - y_true) * logits + (1.0 + (pos_weight - 1.0) * y_true) * F.softplus(-logits)
    return loss.mean()
CONFIG = {'n_ens': 8, 'embed_dim': 6, 'onehot_thresh': 4, 'hidden_dims': [256, 256, 256], 'dropout': 0.05, 'p_drop_sched': 'expm4t', 'activation': nn.SiLU, 'add_front_scale': True, 'pbld_hidden_dim': 20, 'pbld_out_dim': 5, 'pbld_freq_scale': 5.0, 'pbld_activation': nn.PReLU, 'pbld_lr_factor': 0.093, 'lr': 0.01, 'mom': 0.9, 'sq_mom': 0.99, 'lr_sched': 'flat_anneal', 'flat_ratio': 0.3, 'first_layer_lr_factor': 1.2, 'first_layer_wd_factor': 0.1, 'lr_scale_mult': 10.0, 'lr_bias_mult': 0.1, 'weight_decay': 0.013, 'wd_scale_mult': 0.1, 'wd_bias_mult': 0.5, 'ema_decay': 0.997875, 'grad_clip': 1.0, 'ls_eps': 0.04, 'ls_eps_sched': 'cos', 'tfms': ['median_center', 'robust_scale', 'smooth_clip'], 'epochs': 2, 'train_bs': 256, 'eval_bs': 10240, 'verbosity': 2, 'use_early_stopping': False, 'early_stopping_additive_patience': 10, 'early_stopping_multiplicative_patience': 1, 'device': 'cuda', 'random_state': 42}
