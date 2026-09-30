"""拉取 r14/r17/r20/r22 全部线上对局 replay 到 rlive2/。"""
import json, urllib.request, time
from pathlib import Path
HERE=Path(__file__).resolve().parent; DST=HERE/"rlive2"
def api(body):
    req=urllib.request.Request("https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes",
        data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))
meta={}
for sub,name in ((56498028,"r14"),(56508668,"r17"),(56511631,"r20"),(56540435,"r22")):
    for e in api({"submissionId":sub}).get("episodes",[]):
        eid=e["id"]; me=opp=None
        for a in e.get("agents",[]):
            if a.get("submissionId")==sub: me=a
            else: opp=a
        meta[eid]={"ver":name,"my_score_after":(me or {}).get("updatedScore"),
                   "opp_init":(opp or {}).get("initialScore"),"my_reward":(me or {}).get("reward"),
                   "opp_reward":(opp or {}).get("reward")}
        p=DST/f"episode-{eid}-replay.json"
        if p.exists(): continue
        try:
            rp=json.load(urllib.request.urlopen(f"https://www.kaggleusercontent.com/episodes/{eid}.json",timeout=60))
            p.write_text(json.dumps(rp))
        except Exception as ex: print("skip",eid,ex)
        time.sleep(0.3)
json.dump(meta,open(DST/"meta.json","w"))
print("总局数", len(meta), "本地文件", len(list(DST.glob("episode-*.json"))))
