"""从真实线上 episode 抽取 64 个评测场景（seed + 商店解锁时刻表）。

选取规则：最近日期优先、module_version==1.32.7、720 步完整局；
每局提取 info.seed 与逐步 town.unlocked_shops 的增量（商店名 + 首次可见 step）。
"""
from __future__ import annotations

import json
import random
from pathlib import Path

INDEX = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/"
              "model_data/kaggriculture_episodes_index")
OUT = Path(__file__).resolve().parent / "scenarios_64.json"
N = 64


def extract(fp: Path):
    d = json.loads(fp.read_text())
    if d.get("module_version") != "1.32.7":
        return None
    steps = d.get("steps") or []
    if len(steps) < 719:
        return None
    seed = (d.get("info") or {}).get("seed")
    if seed is None:
        return None
    shops, seen = [], []
    for i, st in enumerate(steps):
        town = st[0]["observation"].get("town") or {}
        cur = town.get("unlocked_shops") or []
        while len(cur) > len(seen):
            shop = cur[len(seen)]
            seen.append(shop)
            shops.append([shop, i])
    return {"episode": d.get("id"), "seed": int(seed), "shops": shops}


def main():
    rng = random.Random(20260901)
    dates = sorted(p for p in INDEX.glob("date=*") if (p / "data").is_dir())[::-1]
    picked, per_date = [], max(8, N // 6)
    for dp in dates:
        files = sorted((dp / "data").glob("*.json"))
        rng.shuffle(files)
        got = 0
        for fp in files:
            if got >= per_date or len(picked) >= N:
                break
            try:
                sc = extract(fp)
            except Exception:
                continue
            if sc:
                sc["date"] = dp.name.split("=")[1]
                picked.append(sc)
                got += 1
        print(f"{dp.name}: +{got} (total {len(picked)})")
        if len(picked) >= N:
            break
    OUT.write_text(json.dumps(picked[:N], indent=1))
    print(f"wrote {min(len(picked), N)} scenarios -> {OUT}")


if __name__ == "__main__":
    main()
