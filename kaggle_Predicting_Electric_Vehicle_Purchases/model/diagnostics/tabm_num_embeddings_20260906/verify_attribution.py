"""只读复算折间样本对归因；不拟合或变换预测。"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
P = Path(__file__).resolve().parent
raw = pd.read_csv(P.parents[2] / 'data/train.csv')
y = raw.Will_Buy_EV.map({'No': 0, 'Yes': 1}).to_numpy()
with np.load(P / 'diagnostic_oof.npz') as z:
    np.testing.assert_array_equal(z['ids'], raw.id.to_numpy())
    pred, fold = z['pred'].copy(), z['fold'].copy()
a = json.loads((P / 'crossfold_attribution.json').read_text())
r = json.loads((P / 'result.json').read_text())
den = int(y.sum()) * int(len(y) - y.sum())
mass = np.zeros((5, 5))
contribution = np.zeros((2, 5, 5))
for i in range(5):
    pos = (y == 1) & (fold == i + 1)
    for j in range(5):
        neg = (y == 0) & (fold == j + 1)
        mass[i, j] = int(pos.sum()) * int(neg.sum()) / den
        for arm in range(2):
            p = pred[pos, arm]
            n = np.sort(pred[neg, arm])
            less = np.searchsorted(n, p, side='left')
            equal = np.searchsorted(n, p, side='right') - less
            contribution[arm, i, j] = (less.sum() + .5 * equal.sum()) / den
np.testing.assert_allclose(contribution.sum(axis=(1, 2)), r['auc'], rtol=0, atol=1e-12)
gain = contribution[1] - contribution[0]
np.testing.assert_allclose(gain, a['pair_gain_matrix'], rtol=0, atol=1e-12)
assert abs(np.trace(mass) - a['same_fold_pair_mass']) < 1e-12
assert abs(np.trace(gain) - a['same_fold_global_gain']) < 1e-12
assert abs(gain.sum() - np.trace(gain) - a['cross_fold_global_gain']) < 1e-12
print('PASS: 25 pair cells reconstruct pooled AUC and saved attribution; predictions unchanged')
