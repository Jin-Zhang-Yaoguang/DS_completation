"""抽查我方对局回放:每步我方状态(ERROR/TIMEOUT)、剩余超时额度(remainingOverageTime)最小值、异常步。"""
import json, subprocess, sys, collections
from concurrent.futures import ThreadPoolExecutor
def one(eid):
    raw=subprocess.run(["curl","-sL","--compressed","-m","300",f"https://www.kaggleusercontent.com/episodes/{eid}.json"],capture_output=True).stdout
    try:
        r=json.loads(raw); nm=r["info"]["TeamNames"]; p=nm.index("datatuu"); s=r["steps"]
        st=collections.Counter(x[p].get("status") for x in s); over=[x[p].get("observation",{}).get("remainingOverageTime") for x in s]
        over=[o for o in over if o is not None]
        first_bad=next((t for t,x in enumerate(s) if x[p].get("status") not in ("ACTIVE","DONE","INACTIVE")),None)
        return eid,dict(status=dict(st),min_over=min(over) if over else None,first_bad=first_bad,steps=len(s),rew=r["rewards"],opp_status=dict(collections.Counter(x[1-p].get("status") for x in s)))
    except Exception as ex: return eid,{"err":str(ex)[:80]}
ids=sys.argv[1:]
with ThreadPoolExecutor(4) as ex:
    for e,v in ex.map(one,ids): print(e,v)
