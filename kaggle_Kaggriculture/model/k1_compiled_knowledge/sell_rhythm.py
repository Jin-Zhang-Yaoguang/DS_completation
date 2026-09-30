"""卖出节奏对照：Majkel 回放（活跃版本 60 局）vs K1（kagsim vs y68g，8 局）。
每个产品：每局卖出次数、件数、每次件数分布、相邻两次卖出间隔（步）、卖出时 价格/基准价、卖出时市场库存/I0、
按天卖出件数分布（前中后）、卖出所在小时分布、卖出时是否有消耗该产品的商店已解锁。
实际成交按「仓库减少量」核实（Majkel 用下一步观测的 shed 差），价格取下单那一步的挂牌价。"""
import json, os, sys, statistics, importlib.util
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
LS = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/leader_style_20260915'
M = '/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model'
BASE = {"WHEAT": 25, "CARROT": 35, "TOMATO": 60, "STRAWBERRY": 120, "MELON": 250, "EGG": 50, "MILK": 160, "WOOL": 200, "FERTILIZER": 100}
SHOPS = {"BAKERY": ["EGG", "WHEAT"], "PIZZA_SHOP": ["MILK", "TOMATO", "WHEAT"], "BRUNCH_SPOT": ["EGG", "WHEAT", "STRAWBERRY"],
         "YARN_STORE": ["WOOL"], "ICE_CREAM_SHOP": ["STRAWBERRY", "MILK", "WHEAT"], "PET_CAFE": ["CARROT"],
         "SMOOTHIE_SHOP": ["STRAWBERRY", "MILK"], "FARMERS_MARKET": ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY"]}


def rows_from(obs_seq, act_seq, seat):
    """obs_seq[t] = 第 t 步决策前观测；act_seq[t] = 第 t 步动作。返回卖出事件列表。"""
    ev = []
    for t in range(len(act_seq) - 1):
        o, a, o2 = obs_seq[t], act_seq[t], obs_seq[t + 1]
        if not o or not a or not o2:
            continue
        req = Counter()
        for od in a.get('market') or []:
            if od and od[0] == 'SELL' and len(od) >= 3:
                req[od[1]] += int(od[2] or 0)
        if not req:
            continue
        sh0 = (o.get('private') or {}).get('shed') or {}
        prices = (o.get('market') or {}).get('prices') or {}
        inv = (o.get('market') or {}).get('inventory') or {}
        shops = (o.get('town') or {}).get('unlocked_shops') or []
        for p, q in req.items():
            q_real = min(q, sh0.get(p, 0))
            if q_real <= 0:
                continue
            ev.append({"t": t, "day": int(o['day']), "hour": int(o['hour']), "p": p, "q": q_real, "req": q,
                       "px": prices.get(p, 0) / BASE[p], "inv": inv.get(p, 10000) / 10000.0,
                       "demand_shops": sum(1 for s in shops if p in SHOPS.get(s, [])), "stock": sh0.get(p, 0)})
    return ev


def majkel_one(ep):
    p = ep['path'] if os.path.exists(ep['path']) else f"{LS}/replays/episode-{ep['episode_id']}-replay.json"
    rep = json.load(open(p))
    seat = ep['seat']; steps = rep['steps']
    obs = [steps[t][seat].get('observation') for t in range(len(steps) - 1)]
    act = [steps[t + 1][seat].get('action') for t in range(len(steps) - 1)]
    return rows_from(obs, act, seat)


def k1_one(seed):
    sys.path.insert(0, '/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness')
    sys.path.insert(0, f'{M}/v16_online_fidelity')
    import engine, fidelity
    spec = importlib.util.spec_from_file_location(f'sr_{seed}', f'{HERE}/main.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    opp = fidelity.make_agent(f'sub:{M}/v58_mosaic/dist_backup/y68g_main.py')
    g = engine.load_kagsim().Game(seed=seed)
    obs, act = [], []
    while not engine._val(g.done):
        o0, o1 = g.observe(0), g.observe(1)
        a0 = mod.agent(o0); a1 = opp(o1)
        obs.append(o0); act.append(a0)
        g.step(a0, a1)
    obs.append(g.observe(0)); act.append({})
    return rows_from(obs, act, 0)


def summarize(games, label):
    out = {}
    n = len(games)
    for p in BASE:
        evs = [e for g in games for e in g if e['p'] == p]
        if not evs:
            continue
        per_game_qty = [sum(e['q'] for e in g if e['p'] == p) for g in games]
        per_game_cnt = [sum(1 for e in g if e['p'] == p) for g in games]
        gaps = []
        for g in games:
            ts = sorted(e['t'] for e in g if e['p'] == p)
            gaps += [b - a for a, b in zip(ts, ts[1:])]
        out[p] = {
            "件/局": statistics.mean(per_game_qty), "次/局": statistics.mean(per_game_cnt),
            "件/次 中位": statistics.median(e['q'] for e in evs), "件/次 p90": sorted(e['q'] for e in evs)[int(len(evs) * 0.9)],
            "间隔 中位": statistics.median(gaps) if gaps else 0,
            "价/基准 均": statistics.mean(e['px'] for e in evs), "价/基准 按件加权": sum(e['px'] * e['q'] for e in evs) / sum(e['q'] for e in evs),
            "库存/I0 均": statistics.mean(e['inv'] for e in evs),
            "有需求店 占比": statistics.mean(1 if e['demand_shops'] > 0 else 0 for e in evs),
            "卖出时仓库存 中位": statistics.median(e['stock'] for e in evs),
            "卖量占比 d0-9/10-19/20-29": "/".join(f"{sum(e['q'] for e in evs if lo <= e['day'] < lo + 10) / sum(e['q'] for e in evs):.2f}" for lo in (0, 10, 20)),
            "卖出小时 top3": [h for h, _ in Counter(e['hour'] for e in evs).most_common(3)],
        }
    return out


def main():
    eps = [e for e in json.load(open(f'{LS}/episode_table.json')) if str(e.get('submission_id')) == '56156662'][:60]
    with ProcessPoolExecutor(max_workers=8) as pool:
        mj = list(pool.map(majkel_one, eps))
        k1 = list(pool.map(k1_one, [950077 + 271 * i for i in range(8)]))
    S = {"Majkel": summarize(mj, "M"), "K1": summarize(k1, "K")}
    json.dump(S, open(f'{HERE}/sell_rhythm_result.json', 'w'), ensure_ascii=False, indent=1)
    keys = ["件/局", "次/局", "件/次 中位", "件/次 p90", "间隔 中位", "价/基准 均", "价/基准 按件加权", "库存/I0 均", "有需求店 占比",
            "卖出时仓库存 中位", "卖量占比 d0-9/10-19/20-29", "卖出小时 top3"]
    for p in BASE:
        if p not in S["Majkel"] and p not in S["K1"]:
            continue
        print(f"\n== {p}")
        for k in keys:
            a = S["Majkel"].get(p, {}).get(k, "-"); b = S["K1"].get(p, {}).get(k, "-")
            fa = f"{a:.2f}" if isinstance(a, float) else str(a); fb = f"{b:.2f}" if isinstance(b, float) else str(b)
            print(f"   {k:22s} Majkel {fa:>18s} | K1 {fb:>18s}")


if __name__ == '__main__':
    main()
