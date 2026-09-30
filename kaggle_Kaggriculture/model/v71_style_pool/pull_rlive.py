"""拉取 r1-r4 全部线上对局 replay 到 rlive/。"""
import json, urllib.request, time
from pathlib import Path
HERE=Path(__file__).resolve().parent; DST=HERE/"rlive"
def api(path, body):
    req=urllib.request.Request("https://www.kaggle.com/api/i/competitions.EpisodeService/"+path,
        data=json.dumps(body).encode(), headers={"Content-Type":"application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))
n_new=0
for sub in (56447333,56449925,56452959,56455208):
    eps=api("ListEpisodes",{"submissionId":sub}).get("episodes",[])
    for e in eps:
        eid=e["id"]; p=DST/f"episode-{eid}-replay.json"
        if p.exists(): continue
        try:
            import urllib.request as _u; rp=json.load(_u.urlopen(f"https://www.kaggleusercontent.com/episodes/{eid}.json",timeout=60)); r={"replay":rp}
            rp=r.get("replay")
            if isinstance(rp,str): rp=json.loads(rp)
            p.write_text(json.dumps(rp)); n_new+=1
        except Exception as ex:
            print("skip",eid,ex)
        time.sleep(0.4)
print("新增", n_new, "总数", len(list(DST.glob("*.json"))))
