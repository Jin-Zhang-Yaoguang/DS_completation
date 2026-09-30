# 高频未知族内部一致性:对手前150步动作流哈希 + 首日市场单摘要
import json, glob, collections, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
rows = json.load(open(HERE/"rival_freq.json"))
TOP = [(988.0,9989),(1041.0,9989),(167.0,9959),(1052.0,9989),(1059.0,9989),(1044.0,9989),(1006.0,9989)]
idx = {}
for d in ("v54live","wk5live","wk2live"):
    for p in glob.glob(str(HERE/d/"episode-*-replay.json")):
        idx[int(p.split("episode-")[1].split("-")[0])] = p
def sig(ep, opp_seat):
    r = json.load(open(idx[ep]))
    acts=[]; mkt=[]
    for t in range(min(150,len(r["steps"]))):
        a = r["steps"][t][opp_seat].get("action") or {}
        acts.append(json.dumps(a, sort_keys=True))
        for m in (a.get("market") or []):
            if t < 48: mkt.append((t, *m[:3]))
    return hashlib.md5("|".join(acts).encode()).hexdigest()[:8], tuple(mkt)
for rk in TOP:
    games = [x for x in rows if tuple(x["rkey"])==list(rk) or tuple(x["rkey"])==rk]
    hs=collections.Counter(); mk=collections.Counter()
    for x in games[:30]:
        r = json.load(open(idx[x["ep"]]))
        opp = 1 - r["info"]["TeamNames"].index("datatuu")
        h,m = sig(x["ep"], opp); hs[h]+=1; mk[m]+=1
    m0,mc = mk.most_common(1)[0]
    print(f"{rk}  n={len(games)}  前150步哈希分布={dict(hs.most_common(5))}")
    print(f"   主流首2日市场单({mc}/{sum(mk.values())}): {list(m0)[:8]}")
