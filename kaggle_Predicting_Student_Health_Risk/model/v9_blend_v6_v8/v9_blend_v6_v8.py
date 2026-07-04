# -*- coding: utf-8 -*-
"""
方案 v9：v6 (TE-HGBC) × v8 (Emb-MLP) 跨家族融合

背景：v8 与 v6 分歧率仅 1.19%（Entity Embedding + logloss 早停仍无法制造
差异化），跨家族融合的常识性假设在本题被数据规则物理压死——生成器只用
3 个字段决定标签，74% 送分行任何模型都同答，26% 缺失行任何模型都只能猜先验。

本方案是**探底实验**：即使分歧微弱，只要 v8 在 v6 错的样本上刚好挽回一部分，
融合就有净增益；如果 OOF 都不涨，则跨家族路线可判死。

性能：类别权重搜索改为 torch/MPS 批量网格评估——把整个 (w1,w2) 网格
广播到 GPU 一次算完（此前 numpy 逐点评估需数小时，现在全程 <1 分钟）。
"""

import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

SEED = 42
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
OUT_DIR = Path(__file__).resolve().parent
TARGET = "health_condition"
EPS = 1e-9

DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
CHUNK = 32  # 每批网格点数（32 × 690k × 3 × 4B ≈ 265MB，MPS 可承受）


class GridSearcher:
    """GPU 批量评估：给定固定概率矩阵，对一批类别权重同时算 balanced accuracy。"""

    def __init__(self, y):
        self.y = torch.from_numpy(y.astype(np.int64)).to(DEVICE)
        self.class_idx = [torch.nonzero(self.y == k).squeeze(1) for k in range(3)]

    def bacc_grid(self, P, weights):
        """P: (n,3) GPU float32；weights: (m,3) GPU float32 → (m,) numpy bacc"""
        out = np.empty(len(weights), dtype=np.float64)
        for s in range(0, len(weights), CHUNK):
            W = weights[s:s + CHUNK]                              # (c,3)
            pred = (P.unsqueeze(0) * W.unsqueeze(1)).argmax(2)    # (c,n)
            rec = torch.stack(
                [(pred[:, self.class_idx[k]] == k).float().mean(1) for k in range(3)]
            ).mean(0)                                             # (c,)
            out[s:s + len(W)] = rec.cpu().numpy()
        return out

    def search_class_weights(self, P, coarse=45, fine=25):
        """两阶段网格：粗 [1,12]² → 细 [best±0.3]²。P 为 (n,3) GPU 张量。"""
        g = torch.linspace(1, 12, coarse)
        W = torch.stack(torch.meshgrid(g, g, indexing="ij"), -1).reshape(-1, 2)
        W = torch.cat([torch.ones(len(W), 1), W], 1).to(DEVICE)
        # 加入 (1,1,1) 基准点
        W = torch.cat([torch.ones(1, 3).to(DEVICE), W], 0)
        scores = self.bacc_grid(P, W)
        i = scores.argmax()
        best_s, best_w = scores[i], W[i].cpu().numpy()

        g1 = torch.linspace(max(0.5, best_w[1] - 0.3), best_w[1] + 0.3, fine)
        g2 = torch.linspace(max(0.5, best_w[2] - 0.3), best_w[2] + 0.3, fine)
        W2 = torch.stack(torch.meshgrid(g1, g2, indexing="ij"), -1).reshape(-1, 2)
        W2 = torch.cat([torch.ones(len(W2), 1), W2], 1).to(DEVICE)
        scores2 = self.bacc_grid(P, W2)
        j = scores2.argmax()
        if scores2[j] > best_s:
            best_s, best_w = scores2[j], W2[j].cpu().numpy()
        return float(best_s), best_w.astype(np.float64)


def main():
    t0 = time.time()
    train = pd.read_csv(DATA_DIR / "train.csv")
    sub = pd.read_csv(DATA_DIR / "sample_submission.csv")
    classes = sorted(train[TARGET].unique())
    y = train[TARGET].map({c: i for i, c in enumerate(classes)}).values

    v6_oof = np.load(ROOT / "v6_te_hgbc/oof_proba.npy")
    v6_test = np.load(ROOT / "v6_te_hgbc/test_proba.npy")
    v8_oof = np.load(ROOT / "v8_mlp_emb/oof_proba.npy")
    v8_test = np.load(ROOT / "v8_mlp_emb/test_proba.npy")

    searcher = GridSearcher(y)
    P6 = torch.from_numpy(v6_oof.astype(np.float32)).to(DEVICE)
    P8 = torch.from_numpy(v8_oof.astype(np.float32)).to(DEVICE)
    L6 = torch.log(P6 + EPS)
    L8 = torch.log(P8 + EPS)

    # ---------- 单模基准 ----------
    s6, w6 = searcher.search_class_weights(P6)
    s8, w8 = searcher.search_class_weights(P8)
    print(f"v6 单模加权 OOF: {s6:.5f} (w={w6.round(3)})")
    print(f"v8 单模加权 OOF: {s8:.5f} (w={w8.round(3)})")
    d = ((P6 * torch.tensor(w6, dtype=torch.float32, device=DEVICE)).argmax(1)
         != (P8 * torch.tensor(w8, dtype=torch.float32, device=DEVICE)).argmax(1))
    print(f"v6 vs v8 加权预测分歧率: {d.float().mean().item() * 100:.2f}%")

    # ---------- 融合 α 扫描（GPU 上现算 blend，逐 α 搜类别权重） ----------
    def blend_gpu(alpha, mode):
        if mode == "arith":
            return alpha * P6 + (1 - alpha) * P8
        return torch.exp(alpha * L6 + (1 - alpha) * L8)

    results = {}
    for mode in ["arith", "geo"]:
        best = (-1.0, None, None)
        for alpha in np.linspace(0.3, 1.0, 71):
            s, cw = searcher.search_class_weights(blend_gpu(float(alpha), mode),
                                                  coarse=23, fine=25)
            if s > best[0]:
                best = (s, float(alpha), cw)
        results[mode] = best
        s, alpha, cw = best
        print(f"[{mode}] 最优 α(v6权重) = {alpha:.3f}, 加权 OOF = {s:.5f}, "
              f"类别权重 = {cw.round(3)}")

    # ---------- 挑最优 ----------
    best_mode = max(results, key=lambda k: results[k][0])
    cv, alpha, cw = results[best_mode]
    delta_v6 = cv - s6
    print(f"\n>>> 最优 {best_mode}, alpha = {alpha:.3f}, CV = {cv:.5f}")
    print(f"    vs v6 单模: {'+' if delta_v6 >= 0 else ''}{delta_v6:.5f}")

    # ---------- 生成提交 ----------
    if delta_v6 <= 0:
        print("\n！！！ 融合 OOF 未跑赢 v6 单模，本次不生成提交（避免消耗提交额度）")
        print(f"完成，耗时 {time.time() - t0:.0f}s")
        return

    if best_mode == "arith":
        test_blend = alpha * v6_test + (1 - alpha) * v8_test
    else:
        test_blend = np.exp(alpha * np.log(v6_test + EPS)
                            + (1 - alpha) * np.log(v8_test + EPS))
    sub[TARGET] = [classes[i] for i in (test_blend * cw).argmax(1)]
    sub.to_csv(OUT_DIR / "submission.csv", index=False)
    print("\n提交预测分布:")
    print(sub[TARGET].value_counts(normalize=True).round(4))

    with open(OUT_DIR / "config.txt", "w") as f:
        f.write(f"mode={best_mode}\nalpha_v6={alpha}\nclass_weights={cw.tolist()}\ncv={cv:.5f}\n")

    print(f"\n完成，耗时 {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
