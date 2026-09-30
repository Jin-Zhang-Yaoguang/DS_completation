"""近期金牌区 replay:每队施肥量、按作物(执行者脚下地块)、按日分布、胜率。
用法: python gold_fert_crops.py <date_dir> [<date_dir> ...]
"""
import sys, json, glob, collections, statistics as S
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

def one(fp):
    try: rep = json.load(open(fp))
    except Exception: return None
    steps = rep.get("steps") or []; names = (rep.get("info") or {}).get("TeamNames") or ["?", "?"]
    if len(steps) < 700: return None
    out = []
    rewards = [steps[-1][s].get("reward") or 0 for s in (0, 1)]
    for seat in (0, 1):
        crops = collections.Counter(); days = collections.Counter(); n = 0
        for t in range(1, min(720, len(steps))):
            a = steps[t][seat].get("action") or {}
            units = [a.get("farmer") or []] + list(a.get("hands") or [])
            if not any(u and u[0] == "FERTILIZE" for u in units): continue
            obs = steps[t - 1][0].get("observation") or {}
            farms = obs.get("farms") or []
            if len(farms) < 2: continue
            farm = farms[seat]; pos = [farm.get("farmer")] + list(farm.get("hands") or [])
            for i, u in enumerate(units):
                if u and u[0] == "FERTILIZE":
                    n += 1; days[(t - 1) // 24] += 1
                    crop = "?"
                    if i < len(pos) and pos[i]:
                        x, y = pos[i]; tile = farm["tiles"][y][x]
                        crop = tile.get("crop", tile.get("kind")) if isinstance(tile, dict) else str(tile)
                    crops[crop] += 1
        out.append({"team": names[seat], "win": rewards[seat] > rewards[1 - seat], "reward": rewards[seat],
                    "fert": n, "crops": dict(crops), "days": dict(days)})
    return out

if __name__ == "__main__":
    files = [f for d in sys.argv[1:] for f in glob.glob(str(Path(d) / "data" / "*.json"))]
    by = collections.defaultdict(list)
    with ProcessPoolExecutor(14) as ex:
        for r in ex.map(one, files, chunksize=4):
            for s in (r or []): by[s["team"]].append(s)
    rows = [(k, v) for k, v in by.items() if len(v) >= 30]
    rows.sort(key=lambda kv: -S.mean(x["win"] for x in kv[1]))
    for k, v in rows[:25]:
        crops = collections.Counter(); days = collections.Counter()
        for x in v:
            for c, n in x["crops"].items(): crops[c] += n / len(v)
            for d, n in x["days"].items(): days[int(d)] += n / len(v)
        dtxt = " ".join(f"{d}:{days[d]:.0f}" for d in range(6, 30) if days[d] >= 0.5)
        print(f"{k[:20]:20s} n={len(v):3d} win={S.mean(x['win'] for x in v):.2f} rew={S.mean(x['reward'] for x in v):6.0f} fert={S.mean(x['fert'] for x in v):5.1f} "
              f"crops={ {c: round(n, 1) for c, n in crops.most_common(5)} } | days {dtxt}")
