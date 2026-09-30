"""官方回放(最近 5 天):≥2000 对手提交(分数前 150)各取最近 6 局非我方对局 → roff/<eid>.json(双方动作/现金/商店/种子/队名/奖励)。"""
import json, subprocess, datetime, time, csv, io, os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
HERE=Path(__file__).resolve().parent; DST=HERE/"roff"
m=json.load(open(HERE/"meta_live.json"))
SINCE=(datetime.datetime.now(datetime.UTC)-datetime.timedelta(days=5)).strftime("%Y-%m-%d %H")
S2=SINCE.replace(" ","T")
subs={}
for e,v in m.items():
    if (v.get("end") or "")>=S2 and v.get("opp") and (v["opp"].get("initialScore") or 0)>=2000:
        s=v["opp"]["submissionId"]; subs[s]=max(subs.get(s,0),v["opp"]["initialScore"])
top=sorted(subs.items(),key=lambda kv:-kv[1])[:150]
ours=set(m)
L=HERE/"roff_list.json"; lst=json.load(open(L)) if L.exists() else {}
for s,sc in top:
    if str(s) in lst: continue
    out=subprocess.run(["kaggle","competitions","episodes",str(s),"-v"],capture_output=True,text=True).stdout
    rows=[r for r in csv.DictReader(io.StringIO(out)) if r.get("state")=="EpisodeState.COMPLETED" and r.get("type","").endswith("PUBLIC") and (r.get("endTime") or "")>=SINCE and r["id"] not in ours]
    rows.sort(key=lambda r:r["endTime"],reverse=True)
    lst[str(s)]={"score":sc,"eps":[r["id"] for r in rows[:6]]}
    json.dump(lst,open(L,"w")); time.sleep(1.5)
eids=sorted({e for v in lst.values() for e in v["eps"]})
print("提交",len(lst),"对局",len(eids),flush=True)
def one(eid):
    p=DST/f"{eid}.json"
    if p.exists(): return "have"
    try:
        raw=subprocess.run(["curl","-sL","--compressed","-m","400",f"https://www.kaggleusercontent.com/episodes/{eid}.json"],capture_output=True).stdout
        r=json.loads(raw); s=r["steps"]
        acts=[[(s[t][q].get("action") or {}) for q in (0,1)] for t in range(len(s))]
        money=[]; shops=None
        for t in range(len(s)):
            ob=s[t][0].get("observation") or {}; f=ob.get("farms")
            money.append([f[0]["money"],f[1]["money"]] if f else None)
            if ob.get("town"): shops=ob["town"].get("unlocked_shops")
        p.write_text(json.dumps({"eid":eid,"seed":r["info"]["seed"],"names":r["info"]["TeamNames"],"rewards":r["rewards"],"acts":acts,"money":money,"shops":shops,"end":None}))
        return "ok"
    except Exception as ex: return f"err {str(ex)[:60]}"
from collections import Counter
with ThreadPoolExecutor(3) as ex: c=Counter(x[:3] for x in ex.map(one,eids))
print("下载",dict(c))
