"""逐步紧凑状态:价格、市场库存、自家仓库/资金/工人数、对手资金、作物地块计数、双方卖单。
用法: python extract_state.py <team> <in_games.jsonl> <out.jsonl> <date_dir...>
"""
import sys, json, glob
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
TEAM = sys.argv[1]
WANT = {json.loads(l)["ep"] for l in open(sys.argv[2])}

def one(fp):
    if Path(fp).stem not in WANT: return None
    rep = json.load(open(fp)); names = rep["info"]["TeamNames"]; seat = names.index(TEAM); steps = rep["steps"]
    rows = []
    for t in range(min(720, len(steps))):
        ob = steps[t][seat].get("observation") or {}; ob0 = steps[t][0].get("observation") or {}
        farms = ob0.get("farms") or []
        if len(farms) < 2: continue
        f, of = farms[seat], farms[1 - seat]; mk = ob0.get("market") or {}
        crops = {}
        for row in f["tiles"]:
            for x in row:
                if isinstance(x, dict):
                    k = x.get("crop") or (x.get("kind") + ("+" if x.get("animal") else ""))
                    crops[k] = crops.get(k, 0) + 1
                elif x == "LOCKED": crops["LOCKED"] = crops.get("LOCKED", 0) + 1
        priv = ob.get("private") or {}
        rows.append({"t": t, "p": mk.get("prices"), "inv": mk.get("inventory"), "shed": priv.get("shed"), "seeds": priv.get("seeds"),
                     "money": f.get("money"), "opp_money": of.get("money"), "hands": len(f.get("hands") or []), "crops": crops,
                     "shops": [s if isinstance(s, str) else s.get("name") for s in ((ob0.get("town") or {}).get("unlocked_shops") or [])]})
    return {"ep": Path(fp).stem, "seat": seat, "rows": rows}

if __name__ == "__main__":
    files = [f for d in sys.argv[4:] for f in glob.glob(str(Path(d) / "data" / "*.json"))]
    n = 0
    with ProcessPoolExecutor(14) as ex, open(sys.argv[3], "w") as out:
        for r in ex.map(one, files, chunksize=8):
            if r: out.write(json.dumps(r) + "\n"); n += 1
    print("states", n)
