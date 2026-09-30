"""官方对局清单:最近 5 天,我们遇到过的 ≥2000 对手提交 → 它们与其他队伍的对局(不含我们)。"""
import json, urllib.request, datetime, collections, time
from concurrent.futures import ThreadPoolExecutor
m=json.load(open("meta_live.json"))
OURS={56498028,56508668,56511631,56540435,56567648,56570881,56579294,56624940,56630296,56637585,56638210,56660113,56663930,56665280,56665104,56670130}
SINCE=(datetime.datetime.now(datetime.UTC)-datetime.timedelta(days=5)).strftime("%Y-%m-%dT%H")
subs={}
for e,v in m.items():
    if (v.get("end") or "")>=SINCE and v.get("opp") and (v["opp"].get("initialScore") or 0)>=2000:
        subs[v["opp"]["submissionId"]]=max(subs.get(v["opp"]["submissionId"],0),v["opp"]["initialScore"])
subs=dict(sorted(subs.items(),key=lambda kv:-kv[1])[:150])
print("取分数最高的对手提交",len(subs),"最低分",min(subs.values()),flush=True)
def lst(s):
    time.sleep(2.5)
    for k in range(4):
        try:
            req=urllib.request.Request("https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes",data=json.dumps({"submissionId":s}).encode(),headers={"Content-Type":"application/json"})
            return s,json.load(urllib.request.urlopen(req,timeout=120))
        except Exception: time.sleep(60)
    return s,{}
eps={}; teams={}
with ThreadPoolExecutor(1) as ex:
    for s,r in ex.map(lst,list(subs)):
        tm={t["id"]:t.get("teamName") for t in r.get("teams",[])}; sb={x["id"]:x.get("teamId") for x in r.get("submissions",[])}
        for e in r.get("episodes",[]):
            if (e.get("endTime") or "")<SINCE: continue
            ag=e.get("agents",[])
            if len(ag)!=2 or any(a.get("submissionId") in OURS for a in ag) or any(a.get("reward") is None for a in ag): continue
            eps[e["id"]]={"end":e["endTime"],"agents":[{"sub":a["submissionId"],"score":a.get("initialScore"),"reward":a["reward"],"team":tm.get(sb.get(a["submissionId"]))} for a in ag]}
json.dump(eps,open("official_eps.json","w"),ensure_ascii=False)
lo=[min(a["score"] or 0 for a in v["agents"]) for v in eps.values()]
print("对局",len(eps)," 双方≥2000:",sum(x>=2000 for x in lo)," ≥1800:",sum(x>=1800 for x in lo))
print("按天:",sorted(collections.Counter(v["end"][5:10] for v in eps.values()).items()))
