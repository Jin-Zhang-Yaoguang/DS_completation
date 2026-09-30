"""规则挖掘（无 sklearn）：对每个决策变量，在训练集上找解释力最强的单观测分裂（decision stump），
报告分组中位数与方差削减比；只看自适应队伍（tetsuya / Crop_Dusta / MtN），跨队一致才采信。"""
import json, pathlib, statistics, itertools
HERE = pathlib.Path(__file__).resolve().parent
rows = [r for r in json.load(open(HERE / "lib" / "decisions.json")) if r["split"] == "train"]
OBS = ["first_YARN_STORE", "n_YARN_STORE", "nshop_WOOL_by8", "nshop_MILK_by8", "nshop_MILK_by14", "nshop_STRAWBERRY_by8",
       "nshop_STRAWBERRY_by14", "nshop_EGG_by8", "nshop_CARROT_by8", "first_PIZZA_SHOP", "first_SMOOTHIE_SHOP", "first_ICE_CREAM_SHOP"]
DEC = ["SHEEP_total", "SHEEP_late", "COW_total", "COW_late", "GOOSE_total", "seed_STRAWBERRY", "seed_MELON", "seed_CARROT",
       "hires", "land2", "n_land", "firstsell_WOOL", "firstsell_MILK", "firstsell_STRAWBERRY", "sell_WOOL", "sell_MILK", "sell_STRAWBERRY", "sell_MELON"]

def var(xs):
    return statistics.pvariance(xs) if len(xs) > 1 else 0.0

def best_stump(rs, dec, obs):
    xs = [(r[obs], r.get(dec, 0)) for r in rs]
    ys = [y for _, y in xs]; base = var(ys) * len(ys)
    if base == 0: return None
    best = None
    for thr in sorted(set(x for x, _ in xs)):
        lo = [y for x, y in xs if x <= thr]; hi = [y for x, y in xs if x > thr]
        if len(lo) < 8 or len(hi) < 8: continue
        sse = var(lo) * len(lo) + var(hi) * len(hi)
        red = 1 - sse / base
        if best is None or red > best[0]:
            best = (red, thr, statistics.median(lo), statistics.median(hi), len(lo), len(hi))
    return best

for team in ["tetsuya", "Crop_Dusta", "MtN"]:
    rs = [r for r in rows if r["team"] == team]
    print(f"\n===== {team}（train n={len(rs)}）=====")
    for dec in DEC:
        cands = []
        for obs in OBS:
            b = best_stump(rs, dec, obs)
            if b: cands.append((b[0], obs, b))
        cands.sort(reverse=True)
        if not cands: continue
        red, obs, (r2, thr, mlo, mhi, nlo, nhi) = cands[0]
        ys = [r.get(dec, 0) for r in rs]
        if red < 0.15:
            print(f"  {dec:<22} 无强规则（最佳 {obs} 方差削减 {red:.2f}）；中位 {statistics.median(ys)}")
        else:
            print(f"  {dec:<22} ← {obs} ≤ {thr}: 中位 {mlo} (n={nlo}) | > {thr}: 中位 {mhi} (n={nhi})   方差削减 {red:.2f}")
