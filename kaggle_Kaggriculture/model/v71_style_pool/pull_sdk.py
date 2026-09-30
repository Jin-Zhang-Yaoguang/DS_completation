"""用认证 SDK 列我方提交的对局 → 压缩回放 rlive3/<eid>.json(含 rkey/lin/opp_team/双方奖励),并写 online_games.json 索引。"""
import json, subprocess, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from kaggle.api.kaggle_api_extended import KaggleApi
HERE=Path(__file__).resolve().parent
VERS={"r34":56638210,"r36":56660113,"r38":56663930,"r38b":56665280,"r38c":56670130,"r38f":56692542,"r38g":56692636,"v55b":56701997,"v55d":56706261,"v55g":56711393}
api=KaggleApi(); api.authenticate()
IDXF=HERE/"online_games.json"; IDX=json.load(open(IDXF)) if IDXF.exists() else {}
def fetch(item):
    eid,ver,sub,opp_team,rew=item
    p=HERE/f"rlive3/{eid}.json"
    try:
        if not p.exists():
            raw=subprocess.run(["curl","-sL","--compressed","-m","400",f"https://www.kaggleusercontent.com/episodes/{eid}.json"],capture_output=True).stdout
            r=json.loads(raw); nm=r["info"]["TeamNames"]; seat=nm.index("datatuu"); s=r["steps"]
            acts=[[(s[t][q].get("action") or {}) for q in (0,1)] for t in range(len(s))]
            money=[]; shops=None
            for t in range(len(s)):
                ob=s[t][seat].get("observation") or {}
                if "farms" not in ob: ob=s[t][0].get("observation") or {}
                f=ob.get("farms"); money.append([f[0]["money"],f[1]["money"]] if f else None)
                if ob.get("town"): shops=ob["town"].get("unlocked_shops")
            ob=s[2][seat]["observation"]; key=[float(ob["farms"][1-seat]["money"]),int(ob["market"]["inventory"]["WHEAT"])]
            p.write_text(json.dumps({"eid":eid,"seed":r["info"]["seed"],"names":nm,"seat":seat,"rewards":r["rewards"],"acts":acts,"money":money,"shops":shops,"meta":ver,"key":key}))
        r=json.load(open(p))
        o=1-r["seat"]; M=r["money"]; lin="cha" if (M[92] and M[91] and M[92][o]-M[91][o]>50) else "main"
        key=r.get("key")
        return eid,dict(ver=ver,opp_team=opp_team,d=rew[0]-rew[1],seat=r["seat"],seed=r["seed"],key=key,lin=lin,shops=(r.get("shops") or [])[:2])
    except Exception as ex: return eid,{"err":str(ex)[:80]}
items=[]
for ver,sub in VERS.items():
    for e in api.competition_list_episodes(sub):
        if "PUBLIC" not in str(e.type) or not str(e.state).endswith("COMPLETED"): continue
        me=[a for a in e.agents if a.submission_id==sub]; op=[a for a in e.agents if a.submission_id!=sub]
        if not me or not op or me[0].reward is None or op[0].reward is None: continue
        items.append((str(e.id),ver,sub,op[0].team_name,(me[0].reward,op[0].reward),str(e.end_time)))
print("对局",len(items),flush=True)
ends={i[0]:i[5] for i in items}
with ThreadPoolExecutor(4) as ex:
    for eid,v in ex.map(fetch,[i[:5] for i in items]):
        if "err" not in v: v["end"]=ends[eid]; IDX[eid]=v
json.dump(IDX,open(IDXF,"w"),ensure_ascii=False)
import collections
print("已索引",len(IDX),dict(collections.Counter(v["ver"] for v in IDX.values())))
