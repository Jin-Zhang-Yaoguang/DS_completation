"""yhay 家族侦察:扫 episodes_index 09-05/09-06 全量 replay,
对 pub_yhay_0..3 各自计算 144 步工人重合度,≥0.90 存出同族带。
用法: python yhay_scout.py
"""
import json, sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor

HERE = Path(__file__).resolve().parent
TAPES = HERE.parent / "v16_online_fidelity" / "tapes"
IDX = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model_data/kaggriculture_episodes_index")
OUT = HERE / "t955_family"
OUT.mkdir(exist_ok=True)

def sig(acts, n=144):
    return [json.dumps({"f": x.get("farmer"), "h": x.get("hands")}, sort_keys=True) for x in acts[:n]]

BASES = {}
for i in range(5):
    p = TAPES / f"pub_t955_{i}.json"
    if p.exists():
        BASES[i] = sig(json.load(open(p))["actions"])

def one(fp):
    try:
        rep = json.load(open(fp))
    except Exception:
        return []
    info = rep.get("info") or {}
    names = info.get("TeamNames") or ["?", "?"]
    steps = rep.get("steps") or []
    if len(steps) < 700:
        return []
    res = []
    for seat in (0, 1):
        acts = []
        for t in range(1, len(steps)):
            a = steps[t][seat].get("action") or {}
            acts.append({"farmer": a.get("farmer") or ["PASS"],
                         "hands": a.get("hands") or [],
                         "market": a.get("market") or []})
        s = sig(acts)
        best_i, best_o = -1, 0.0
        for i, b in BASES.items():
            o = sum(x == y for x, y in zip(s, b)) / 144
            if o > best_o:
                best_i, best_o = i, o
        if best_o >= 0.80:
            rw = (rep.get("rewards") or [0, 0])[seat] or 0
            res.append((Path(fp).stem, seat, names[seat], best_i, round(best_o, 3), rw, acts))
    return res

if __name__ == "__main__":
    files = []
    for d in ("date=2026-09-07", "date=2026-09-08"):
        files += sorted((IDX / d / "data").glob("*.json"))
    print(f"扫描 {len(files)} 局", flush=True)
    hits = []
    with ProcessPoolExecutor(8) as ex:
        for res in ex.map(one, files, chunksize=8):
            hits.extend(res)
    hits.sort(key=lambda h: -h[4])
    n_saved = 0
    seen = set()
    for ep, seat, name, bi, ov, rw, acts in hits:
        key = (name, bi)
        print(f"{ep} seat{seat} {name[:24]:24s} ~yhay{bi} ov={ov:.3f} bank={rw:.0f}", flush=True)
        if ov >= 0.90 and rw >= 100000:
            out = OUT / f"t9{bi}_{ep}_{seat}.json"
            json.dump({"actions": acts, "bank": rw, "team": name}, out.open("w"))
            n_saved += 1
    print(f"done: {len(hits)} 命中(ov>=0.80), 存出 {n_saved} 条同族强带(ov>=0.90 & bank>=100k)", flush=True)
