"""局面路由特征分析：route_feat_rows.json → 通用特征与「回放相对 K1 分差变化」的相关、单阈值规则，按对手分组二折交叉验证（规则只在一半对手上选，另一半评估）。"""
import json, statistics, random
from collections import defaultdict

rows = json.load(open('route_feat_rows.json'))


def feats(r):
    f, rec = r['feat'], r['rec']
    out = {}
    for t in ('23', '47', '71'):
        me, op = f.get(f'me{t}', {}), f.get(f'op{t}', {})
        rme = (rec.get(t) or {}).get('me', {})
        rop = (rec.get(t) or {}).get('op', {})
        for k in ('money', 'crops', 'animals', 'hands'):
            out[f'me{t}_{k}'] = me.get(k, 0)
            out[f'op{t}_{k}'] = op.get(k, 0)
            out[f'me-rec{t}_{k}'] = me.get(k, 0) - rme.get(k, 0)
            out[f'op-rec{t}_{k}'] = op.get(k, 0) - rop.get(k, 0)
        out[f'me-op{t}_money'] = me.get('money', 0) - op.get('money', 0)
        out[f'me-op{t}_crops'] = me.get('crops', 0) - op.get('crops', 0)
        out[f'me-op{t}_animals'] = me.get('animals', 0) - op.get('animals', 0)
    out['valid72'] = f.get('valid72', 0)
    shops = f.get('shops72') or []
    for s in ('YARN_STORE', 'ICE_CREAM_SHOP', 'SMOOTHIE_SHOP', 'PET_CAFE', 'BAKERY', 'PIZZA_SHOP', 'BRUNCH_SPOT', 'FARMERS_MARKET'):
        out[f'shop1_{s}'] = int(bool(shops) and shops[0] == s)
    return out


X = [feats(r) for r in rows]
y = [r['delta'] for r in rows]
names = sorted(X[0])


def corr(a, b):
    if statistics.pstdev(a) == 0 or statistics.pstdev(b) == 0:
        return 0.0
    ma, mb = statistics.mean(a), statistics.mean(b)
    return sum((p - ma) * (q - mb) for p, q in zip(a, b)) / (len(a) * statistics.pstdev(a) * statistics.pstdev(b))


cs = sorted(((corr([x[n] for x in X], y), n) for n in names), key=lambda z: -abs(z[0]))
print(f"{len(rows)} 行；均值 delta {statistics.mean(y):+.0f}；相关性前 15：")
for c, n in cs[:15]:
    print(f"  {n:22s} r={c:+.2f}")


def best_rule(idx):
    """在 idx 行上选单特征阈值规则：继续回放 iff 特征 >= thr（或 <= thr），目标 = 选用回放的 delta 之和（其余用 K1 = 0）。"""
    best = (0.0, None)
    for n in names:
        vals = sorted({X[i][n] for i in idx})
        for thr in vals:
            for sign in (1, -1):
                gain = sum(y[i] for i in idx if (X[i][n] - thr) * sign >= 0)
                if gain > best[0]:
                    best = (gain, (n, thr, sign))
    return best


opps = sorted({r['opp'] for r in rows})
rng = random.Random(7)
print("\n按对手二折交叉验证（5 次随机划分）：训练半选规则 → 测试半每局平均增益（相对全 K1）/ 全回放增益")
tests = []
for rep in range(5):
    rng.shuffle(opps)
    half = set(opps[:len(opps) // 2])
    for train_set, test_set in ((half, set(opps) - half), (set(opps) - half, half)):
        tr = [i for i, r in enumerate(rows) if r['opp'] in train_set]
        te = [i for i, r in enumerate(rows) if r['opp'] in test_set]
        g, rule = best_rule(tr)
        if rule is None:
            tests.append(0.0); print("  无正规则"); continue
        n, thr, sign = rule
        gain_te = sum(y[i] for i in te if (X[i][n] - thr) * sign >= 0) / len(te)
        frac = sum(1 for i in te if (X[i][n] - thr) * sign >= 0) / len(te)
        all_eps = sum(y[i] for i in te) / len(te)
        tests.append(gain_te)
        print(f"  规则 {n} {'>=' if sign > 0 else '<='} {thr} | 训练每局 {g / len(tr):+7.0f} | 测试每局 {gain_te:+7.0f}（回放占比 {frac:.2f}）| 测试全回放 {all_eps:+7.0f}")
print(f"测试半平均增益 {statistics.mean(tests):+.0f}，为正次数 {sum(1 for t in tests if t > 0)}/{len(tests)}")
g, rule = best_rule(list(range(len(rows))))
print(f"\n全量最优规则（仅供参考，样本内）：{rule} 每局 {g / len(rows):+.0f}")
