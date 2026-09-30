"""Arjun 全部本地对局(roff_af+roff,去重)→ agents/arjun100.json:{eid:{shops(完整),tape,won,margin,okey}}。tape[t]=acts[t+1][p]。"""
import json,glob
PASS={"farmer":["PASS"],"hands":[],"market":[]}
out={}
for f in glob.glob("roff_af/*.json")+glob.glob("roff/*.json"):
    try: r=json.load(open(f))
    except: continue
    for p,n in enumerate(r["names"]):
        if n!="Arjun Vinod" or str(r["eid"]) in out: continue
        o=1-p; rw=r["rewards"]
        tape=[(r["acts"][t+1][p] or PASS) for t in range(len(r["acts"])-1)]
        out[str(r["eid"])]=dict(shops=r["shops"] or [],tape=tape,won=(rw[p] or 0)>(rw[o] or 0),margin=(rw[p] or 0)-(rw[o] or 0),okey=(r.get("key2") or [[0,0],[0,0]])[p])
json.dump(out,open("agents/arjun100.json","w"))
import collections
print(len(out),"局; 胜",sum(v["won"] for v in out.values()),"; 商店序列长度",collections.Counter(len(v["shops"]) for v in out.values()))
