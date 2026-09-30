"""从 hits.json 抽取每队的 tape 库：720 步动作 + 商店时间线 + 结果。gzip 落盘。"""
import json, sys, gzip, pathlib
from concurrent.futures import ProcessPoolExecutor
M = pathlib.Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model_data/kaggriculture_episodes_index")
HERE = pathlib.Path(__file__).resolve().parent

def one(h):
    f = M / f"date={h['day']}" / "data" / f"{h['ep']}.json"
    try:
        d = json.load(f.open())
    except Exception:
        return None
    seat = h["seat"]
    steps = d["steps"]
    # steps[i].action 是"产生 steps[i] 的动作"，即第 i-1 回合的动作；turn t 的动作在 steps[t+1]
    acts = []
    for t in range(720):
        a = (steps[t + 1][seat].get("action") if t + 1 < len(steps) else None) or {"farmer": ["PASS"], "hands": [], "market": []}
        acts.append({"farmer": a.get("farmer") or ["PASS"], "hands": a.get("hands") or [], "market": a.get("market") or []})
    shops, seen = [], []
    for i, st in enumerate(steps):
        cur = list(((st[0].get("observation") or {}).get("town") or {}).get("unlocked_shops") or [])
        if len(cur) > len(seen):
            for s in cur[len(seen):]:
                shops.append([s, i])
            seen = cur
    return {"ep": h["ep"], "day": h["day"], "seat": seat, "seed": d["info"].get("seed"),
            "r_me": h["r_me"], "r_opp": h["r_opp"], "opp": h["opp"], "shops": shops, "actions": acts}

def main():
    hits = json.load(open(HERE / "lib" / "hits.json"))
    teams = sys.argv[1:] or list(hits)
    for team in teams:
        games = hits.get(team, [])
        with ProcessPoolExecutor(max_workers=6) as ex:
            out = [g for g in ex.map(one, games) if g]
        fn = HERE / "lib" / f"{team.replace(' ', '_')}.json.gz"
        with gzip.open(fn, "wt") as fh:
            json.dump({"team": team, "games": out}, fh)
        print(f"{team}: {len(out)} games -> {fn.name} ({fn.stat().st_size//1024} KB)", flush=True)

if __name__ == "__main__":
    main()
