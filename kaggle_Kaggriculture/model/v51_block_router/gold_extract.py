"""金牌区 replay 摘要提取:每局 → 双席位生产/市场行为指纹 + 胜负。
用法: python gold_extract.py <date_dir> <out.jsonl>
"""
import sys, json, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

PRODS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]


def one(fp):
    try:
        rep = json.load(open(fp))
    except Exception:
        return None
    info = rep.get("info") or {}
    names = info.get("TeamNames") or ["?", "?"]
    steps = rep.get("steps") or []
    if len(steps) < 700:
        return None
    out = {"ep": Path(fp).stem, "teams": names, "seed": info.get("seed")}
    # 首店序列
    shops = []
    for t in (73, 145, 217, 361, 505, 577):
        if t < len(steps):
            try:
                cur = ((steps[t][0].get("observation") or {}).get("town") or {}).get("unlocked_shops") or []
                for s in cur:
                    nm = s if isinstance(s, str) else s.get("name")
                    if nm not in shops:
                        shops.append(nm)
            except Exception:
                pass
    out["shops"] = shops[:3]
    seats = []
    for seat in (0, 1):
        acts_cnt = collections.Counter()
        sell_qty = collections.Counter()
        buy_qty = collections.Counter()
        fert_turns = []
        sell_turns = []
        animals = collections.Counter()
        hires = 0
        for t in range(1, min(720, len(steps))):
            a = steps[t][seat].get("action") or {}
            units = [a.get("farmer") or []] + list(a.get("hands") or [])
            for u in units:
                if not u:
                    continue
                op = str(u[0])
                acts_cnt[op] += 1
                if op == "FERTILIZE":
                    fert_turns.append(t - 1)
            for o in (a.get("market") or []):
                if not o:
                    continue
                op = str(o[0])
                if op == "SELL" and len(o) >= 3:
                    sell_qty[str(o[1])] += int(o[2])
                    sell_turns.append(t - 1)
                elif op in ("BUY_PRODUCT",) and len(o) >= 3:
                    buy_qty[str(o[1])] += int(o[2])
                elif op == "BUY_ANIMAL" and len(o) >= 3:
                    animals[str(o[1])] += int(o[2])
                elif op == "HIRE":
                    hires += 1
        try:
            reward = steps[-1][seat].get("reward")
        except Exception:
            reward = None
        # 卖出空窗:相邻卖出 turn 的最大间隔(t50 之后)
        st = [t for t in sell_turns if t >= 50]
        gap = max((st[i + 1] - st[i] for i in range(len(st) - 1)), default=720) if len(st) > 1 else 720
        seats.append({
            "team": names[seat], "reward": reward,
            "fert_n": acts_cnt.get("FERTILIZE", 0), "fert_first": fert_turns[0] if fert_turns else -1,
            "harvest_n": acts_cnt.get("HARVEST", 0), "plant_n": acts_cnt.get("PLANT", 0),
            "feed_n": acts_cnt.get("FEED", 0), "care_n": acts_cnt.get("CARE", 0),
            "collect_n": acts_cnt.get("COLLECT_FERTILIZER", 0),
            "move_n": sum(acts_cnt.get(d, 0) for d in ("NORTH", "SOUTH", "EAST", "WEST")),
            "sell": {k: v for k, v in sell_qty.items()}, "buy": {k: v for k, v in buy_qty.items()},
            "animals": dict(animals), "hires": hires, "max_sell_gap": gap,
        })
    out["seats"] = seats
    return out


if __name__ == "__main__":
    d = Path(sys.argv[1])
    outp = Path(sys.argv[2])
    files = sorted(d.rglob("*.json"))
    files = [f for f in files if f.name != "dataset_metadata.json"]
    print(f"{len(files)} replays", flush=True)
    n = 0
    with outp.open("w") as fh, ProcessPoolExecutor(8) as ex:
        for r in ex.map(one, files, chunksize=4):
            if r:
                fh.write(json.dumps(r) + "\n")
            n += 1
            if n % 100 == 0:
                print(f"  {n}/{len(files)}", flush=True)
    print("done ->", outp)
