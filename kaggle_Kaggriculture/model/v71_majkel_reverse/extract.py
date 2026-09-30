"""抽取目标队伍全部对局:逐步动作(压缩)、商店时间线、剩余超时预算、关键时刻农场状态、终局分。
用法: python extract.py <team> <out.jsonl> <date_dir...>
"""
import sys, json, glob
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
TEAM = sys.argv[1]

def one(fp):
    raw = open(fp).read()
    if TEAM not in raw: return None
    try: rep = json.loads(raw)
    except Exception: return None
    info = rep.get("info") or {}; names = info.get("TeamNames") or []
    if TEAM not in names: return None
    seat = names.index(TEAM); steps = rep.get("steps") or []
    if len(steps) < 700: return None
    acts, opp_acts, overage, shops, snaps = [], [], [], [], {}
    last_shops = None
    for t in range(1, len(steps)):
        acts.append(steps[t][seat].get("action") or {})
        opp_acts.append(steps[t][1 - seat].get("action") or {})
    for t in range(len(steps)):
        ob = steps[t][seat].get("observation") or {}
        overage.append(ob.get("remainingOverageTime"))
        ob0 = steps[t][0].get("observation") or {}
        cur = ((ob0.get("town") or {}).get("unlocked_shops")) or []
        cur = [s if isinstance(s, str) else s.get("name") for s in cur]
        if cur != last_shops: shops.append((t, cur)); last_shops = cur
        if t in (0, 1, 24, 72, 144, 216, 288, 360, 432, 504, 576, 648, 700, 718):
            farms = ob0.get("farms") or []
            if len(farms) == 2:
                snaps[t] = {"farm": farms[seat], "opp_farm": farms[1 - seat], "market": ob0.get("market"),
                            "private": ob.get("private")}
    rewards = [steps[-1][s].get("reward") for s in (0, 1)]
    return {"ep": Path(fp).stem, "date": Path(fp).parent.parent.name, "seed": info.get("seed"), "seat": seat,
            "opp": names[1 - seat], "reward": rewards[seat], "opp_reward": rewards[1 - seat],
            "statuses": [steps[-1][s].get("status") for s in (0, 1)],
            "acts": acts, "opp_acts": opp_acts, "overage": overage, "shops": shops, "snaps": snaps,
            "config": rep.get("configuration")}

if __name__ == "__main__":
    files = [f for d in sys.argv[3:] for f in glob.glob(str(Path(d) / "data" / "*.json"))]
    n = 0
    with ProcessPoolExecutor(14) as ex, open(sys.argv[2], "w") as out:
        for r in ex.map(one, files, chunksize=8):
            if r: out.write(json.dumps(r) + "\n"); n += 1
    print("games", n)
