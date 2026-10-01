# -*- coding: utf-8 -*-
"""v39：在 v6 的严格折内多尺度 TE 特征上做固定第一折 TabM 探针。"""

from __future__ import annotations

import copy
import importlib.util
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from tabm import TabM


SEED = 42
FOLD = 1
EPOCHS = 24
PATIENCE = 4
BATCH_SIZE = 2048
EVAL_BATCH_SIZE = 8192
LR = 2e-3
WEIGHT_DECAY = 3e-4

OUT_DIR = Path(__file__).resolve().parent
BASE_PATH = OUT_DIR.parent / "v6_multiscale_te_lgbm" / "v6_multiscale_te_lgbm.py"
SPEC = importlib.util.spec_from_file_location("v6_multiscale_te_lgbm_base", BASE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"无法载入 {BASE_PATH}")
base = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(base)


@torch.inference_mode()
def predict(model: TabM, x: torch.Tensor) -> np.ndarray:
    model.eval()
    parts: list[np.ndarray] = []
    for start in range(0, len(x), EVAL_BATCH_SIZE):
        logits = model(x[start : start + EVAL_BATCH_SIZE]).squeeze(-1)
        probabilities = torch.sigmoid(logits).mean(dim=1)
        parts.append(probabilities.float().cpu().numpy())
    return np.concatenate(parts)


def main() -> None:
    start = time.time()
    if not torch.backends.mps.is_available():
        raise RuntimeError("本探针需要 Apple MPS")
    device = torch.device("mps")
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    train, test, _ = base.load_data()
    y = (train[base.TARGET] == base.POS_LABEL).to_numpy(np.int8)
    x_train, x_test, keys_train, keys_test = base.build_static_features(train, test)
    folds = list(
        StratifiedKFold(base.N_FOLDS, shuffle=True, random_state=base.SEED).split(
            x_train, y
        )
    )
    fit_idx, valid_idx = folds[FOLD - 1]
    inner = list(
        StratifiedKFold(base.N_INNER, shuffle=True, random_state=base.SEED + FOLD).split(
            np.zeros(len(fit_idx)), y[fit_idx]
        )
    )
    fit_te: list[np.ndarray] = []
    valid_te: list[np.ndarray] = []
    test_te: list[np.ndarray] = []
    for key in base.TE_KEYS:
        fit_block, valid_block, test_block = base.encode_key(
            keys_train[key], keys_test[key], y, fit_idx, valid_idx, inner
        )
        fit_te.append(fit_block)
        valid_te.append(valid_block)
        test_te.append(test_block)

    x_fit = np.column_stack(
        [x_train.iloc[fit_idx].to_numpy(np.float32), *fit_te]
    ).astype(np.float32)
    x_valid = np.column_stack(
        [x_train.iloc[valid_idx].to_numpy(np.float32), *valid_te]
    ).astype(np.float32)
    x_tst = np.column_stack([x_test.to_numpy(np.float32), *test_te]).astype(np.float32)
    mean = x_fit.mean(axis=0, dtype=np.float64).astype(np.float32)
    std = x_fit.std(axis=0, dtype=np.float64).astype(np.float32)
    std[std < 1e-6] = 1.0
    x_fit = np.clip((x_fit - mean) / std, -12.0, 12.0)
    x_valid = np.clip((x_valid - mean) / std, -12.0, 12.0)
    x_tst = np.clip((x_tst - mean) / std, -12.0, 12.0)

    fit_tensor = torch.from_numpy(x_fit).to(device)
    valid_tensor = torch.from_numpy(x_valid).to(device)
    test_tensor = torch.from_numpy(x_tst).to(device)
    target_tensor = torch.from_numpy(y[fit_idx].astype(np.float32)).to(device)

    model = TabM.make(
        n_num_features=x_fit.shape[1],
        cat_cardinalities=None,
        d_out=1,
        arch_type="tabm-mini",
        k=16,
        n_blocks=3,
        d_block=256,
        dropout=0.15,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)

    best_auc = -np.inf
    best_epoch = 0
    best_state: dict[str, torch.Tensor] | None = None
    best_valid: np.ndarray | None = None
    bad_epochs = 0
    for epoch in range(1, EPOCHS + 1):
        model.train()
        order = torch.randperm(len(fit_tensor), device=device)
        loss_sum = 0.0
        seen = 0
        for batch_idx in order.split(BATCH_SIZE):
            optimizer.zero_grad(set_to_none=True)
            logits = model(fit_tensor[batch_idx]).squeeze(-1)
            labels = target_tensor[batch_idx, None].expand_as(logits)
            loss = F.binary_cross_entropy_with_logits(logits, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            loss_sum += float(loss.detach().cpu()) * len(batch_idx)
            seen += len(batch_idx)

        valid_pred = predict(model, valid_tensor)
        auc = float(roc_auc_score(y[valid_idx], valid_pred))
        improved = auc > best_auc + 1e-7
        print(
            f"epoch={epoch} loss={loss_sum / seen:.6f} auc={auc:.9f} "
            f"best={max(best_auc, auc):.9f} elapsed={time.time() - start:.1f}s",
            flush=True,
        )
        if improved:
            best_auc = auc
            best_epoch = epoch
            best_valid = valid_pred.copy()
            best_state = {
                name: value.detach().cpu().clone()
                for name, value in model.state_dict().items()
            }
            bad_epochs = 0
        else:
            bad_epochs += 1
            if bad_epochs >= PATIENCE:
                break

    if best_state is None or best_valid is None:
        raise RuntimeError("TabM 未产生有效检查点")
    model.load_state_dict(best_state)
    test_pred = predict(model, test_tensor)
    np.save(OUT_DIR / "fold1_valid_proba.npy", best_valid)
    np.save(OUT_DIR / "fold1_valid_idx.npy", valid_idx)
    np.save(OUT_DIR / "fold1_test_proba.npy", test_pred)

    results = {
        "competition": "playground-series-s6e9",
        "model": "TabM-mini fixed-fold probe on v6 multiscale nested-TE features",
        "fold": FOLD,
        "fold_auc": best_auc,
        "best_epoch": best_epoch,
        "fit_rows": len(fit_idx),
        "valid_rows": len(valid_idx),
        "feature_count": x_fit.shape[1],
        "device": str(device),
        "hyperparameters": {
            "k": 16,
            "n_blocks": 3,
            "d_block": 256,
            "dropout": 0.15,
            "batch_size": BATCH_SIZE,
            "learning_rate": LR,
            "weight_decay": WEIGHT_DECAY,
            "patience": PATIENCE,
        },
        "elapsed_seconds": time.time() - start,
    }
    (OUT_DIR / "probe_results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(results, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
