"""动物优先开局目标队伍:每队最近 120 局完整回放 → roff_af/<eid>.json(双方动作/现金/商店全序列/种子/队名/奖励)。"""
import json, subprocess, glob, csv
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
HERE=Path(__file__).resolve().parent; DST=HERE/"roff_af"
TEAMS=["Luca","Aaweg","Planned Economy","Arjun Vinod","high frequency farming","Alan C52","daulettoibazar","pangzi233","DeeperNet","Vlas Veles","tine.sh agent"]
T=json.load(open(HERE/"team_subs.json"))
eids=[]
for s,v in T.items():
    if v["team"] in TEAMS: eids+= [str(e) for e in sorted(v["eps"],reverse=True)[:120]]
eids=sorted(set(eids)); print("待拉",len(eids),flush=True)
def one(eid):
    p=DST/f"{eid}.json"
    if p.exists(): return "have"
    for k in range(3):
        try:
            raw=subprocess.run(["curl","-sL","--compressed","-m","400",f"https://www.kaggleusercontent.com/episodes/{eid}.json"],capture_output=True).stdout
            r=json.loads(raw); s=r["steps"]
            acts=[[(s[t][q].get("action") or {}) for q in (0,1)] for t in range(len(s))]
            money=[]; shops_seq=[]; herd=[]
            for t in range(len(s)):
                ob=s[t][0].get("observation") or {}; f=ob.get("farms")
                money.append([f[0]["money"],f[1]["money"]] if f else None)
                shops_seq.append(len((ob.get("town") or {}).get("unlocked_shops") or []))
            last=(s[-1][0].get("observation") or {})
            p.write_text(json.dumps({"eid":eid,"seed":r["info"]["seed"],"names":r["info"]["TeamNames"],"rewards":r["rewards"],"acts":acts,"money":money,
                                      "shops":(last.get("town") or {}).get("unlocked_shops"),"key2":[[(s[2][q]["observation"]["farms"][1-q]["money"]),s[2][q]["observation"]["market"]["inventory"]["WHEAT"]] for q in (0,1)]}))
            return "ok"
        except Exception as ex: err=str(ex)[:60]
    return "err "+err
from collections import Counter
with ThreadPoolExecutor(3) as ex: c=Counter(x[:3] for x in ex.map(one,eids))
print("完成",dict(c))
