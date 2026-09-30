"""只拉线上对局元数据(不拉 replay):对手、对手分、奖励。"""
import json, urllib.request, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
def api(path,body):
    time.sleep(3)
    for k in range(5):
        try:
            req=urllib.request.Request("https://www.kaggle.com/api/i/competitions.EpisodeService/"+path,
                data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
            return json.load(urllib.request.urlopen(req, timeout=120))
        except Exception as ex: print("retry",ex,flush=True); time.sleep(30*(k+1))
    req=urllib.request.Request("https://www.kaggle.com/api/i/competitions.EpisodeService/"+path,
        data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))
out={}
for sub,name in ((56498028,"r14"),(56508668,"r17"),(56511631,"r20"),(56540435,"r22"),(56567648,"r25"),(56570881,"r26"),(56579294,"r28"),(56624940,"r30"),(56630296,"r32"),(56637585,"r33"),(56638210,"r34"),(56660113,"r36"),(56663930,"r38"),(56665280,"r38b"),(56665104,"c1v18"),(56670130,"r38c")):
    r=api("ListEpisodes",{"submissionId":sub})
    for e in r.get("episodes",[]):
        me=opp=None
        for a in e.get("agents",[]):
            if a.get("submissionId")==sub: me=a
            else: opp=a
        out[e["id"]]={"ver":name,"end":e.get("endTime"),"me":me,"opp":opp}
    teams={t["id"]:t.get("teamName") for t in r.get("teams",[])}
    subs={s["id"]:s.get("teamId") for s in r.get("submissions",[])}
    for eid,v in out.items():
        if v["ver"]==name and v["opp"]:
            v["opp_team"]=teams.get(subs.get(v["opp"].get("submissionId")))
json.dump(out,open(HERE/"meta_live.json","w"),default=str)
print(len(out)); k=next(iter(out)); print(json.dumps(out[k],default=str)[:800])
