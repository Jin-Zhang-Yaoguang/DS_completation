"""全部对局:与 Majkel 开局前 N 步(单位+市场)完全相同的队伍;以及 Majkel 旧版本(09-10 以前 5 局)是否同开局。"""
import sys, json, glob, collections
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
G = [json.loads(l) for l in open("majkel_0910_12.jsonl")]
REF = [json.dumps(G[-1]["acts"][t], sort_keys=True) for t in range(3)]
REF_U = [json.dumps([G[-1]["acts"][t].get("farmer"), G[-1]["acts"][t].get("hands")]) for t in range(3)]

def one(fp):
    try: rep = json.load(open(fp))
    except Exception: return []
    names = (rep.get("info") or {}).get("TeamNames") or []; steps = rep.get("steps") or []
    if len(steps) < 5: return []
    out = []
    for s in (0, 1):
        a = [steps[t][s].get("action") or {} for t in (1, 2, 3)]
        full = [json.dumps(x, sort_keys=True) for x in a] == REF
        units = [json.dumps([x.get("farmer"), x.get("hands")]) for x in a] == REF_U
        t0 = json.dumps(a[0], sort_keys=True)
        out.append((names[s] if s < len(names) else "?", full, units, t0))
    return out

if __name__ == "__main__":
    files = [f for d in sys.argv[1:] for f in glob.glob(str(Path(d) / "data" / "*.json"))]
    full = collections.Counter(); units = collections.Counter(); games = collections.Counter(); t0sig = collections.Counter()
    with ProcessPoolExecutor(14) as ex:
        for rows in ex.map(one, files, chunksize=8):
            for name, f, u, t0 in rows:
                games[name] += 1; full[name] += f; units[name] += u
                if "BUY_ANIMAL" in t0: t0sig[name] += 1
    print("teams with Majkel's exact 3-step opening (full / units-only / games):")
    for name in sorted(games, key=lambda k: -(full[k] + units[k])):
        if full[name] or units[name]: print(f"  {name[:28]:28s} full={full[name]:3d} units={units[name]:3d} games={games[name]}")
    print("teams opening with BUY_ANIMAL at t0:", [(k, v, games[k]) for k, v in t0sig.most_common(15)])
