"""诊断：同一收入值组内，当前最佳融合 OOF 的残差是否随「其他列相似度」相关。

若组内相似行的残差乘积均值明显高于不相似行，说明存在「组内近邻标签」信号，值得建特征；否则不建。
残差 r = y − p，p 为 v110_blend_compact/v109 的 OOF 秩映射到与正类率一致的概率尺度（只看相对结构）。
"""
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata

HERE = Path(__file__).resolve().parent
tr = pd.read_csv(HERE.parent.parent / "data" / "train.csv")
y = (tr["Will_Buy_EV"] == "Yes").to_numpy(float)
oof = np.load(HERE.parent / "v110_blend_compact" / "v109" / "oof_proba.npy")
# 用分位数校准到概率：按秩分 200 箱取实际正类率
r = rankdata(oof) / len(oof)
b = np.minimum((r * 200).astype(int), 199)
p = (np.bincount(b, weights=y, minlength=200) / np.bincount(b, minlength=200))[b]
res = y - p
cols = ["Environmental_Concern_Level", "Subsidy_Available", "Range_Anxiety_Level", "Home_Charging_Possible", "City_Type",
        "Current_Car_Type", "Gender", "Number_of_Cars_Owned", "Charging_Stations_Near_Home", "Charging_Stations_Near_Work"]
codes = np.column_stack([pd.factorize(tr[c])[0] for c in cols])
age = tr["Age"].to_numpy()
cmt = tr["Daily_Commute_km"].to_numpy()
key = pd.factorize(tr["Annual_Income_USD"])[0]
order = np.argsort(key, kind="stable")
bounds = np.r_[0, np.cumsum(np.bincount(key))]
S = len(cols) + 2
num = np.zeros(S + 1)
cnt = np.zeros(S + 1)
for g in range(len(bounds) - 1):
    idx = order[bounds[g]:bounds[g + 1]]
    if len(idx) < 2 or len(idx) > 3000:
        continue
    sim = (codes[idx][:, None, :] == codes[idx][None, :, :]).sum(-1)
    sim += (np.abs(age[idx][:, None] - age[idx][None, :]) <= 2).astype(int)
    sim += (np.abs(cmt[idx][:, None] - cmt[idx][None, :]) <= 2).astype(int)
    iu = np.triu_indices(len(idx), 1)
    s = sim[iu]
    prod = (res[idx][:, None] * res[idx][None, :])[iu]
    num += np.bincount(s, weights=prod, minlength=S + 1)
    cnt += np.bincount(s, minlength=S + 1)
rng = np.random.default_rng(0)
i, j = rng.integers(0, len(y), 2_000_000), rng.integers(0, len(y), 2_000_000)
print(f"跨组随机对 残差乘积均值 {np.mean(res[i] * res[j]):+.6f}")
print("组内：相似列数 | 对数 | 残差乘积均值 | 标准误")
for s in range(S + 1):
    if cnt[s] > 1000:
        print(f"  {s:2d} | {int(cnt[s]):>10,} | {num[s] / cnt[s]:+.6f} | {res.var() / np.sqrt(cnt[s]):.6f}")
