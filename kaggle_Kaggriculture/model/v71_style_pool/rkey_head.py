"""流式只读回放开头 → 对手 rkey(我方 t2 观测的对手现金, 市场小麦库存) + 对手 t1-3 市场动作签名。"""
import json, subprocess, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
HERE=Path(__file__).resolve().parent
meta=json.load(open(HERE/"meta_live.json"))
OUT=HERE/"rkey_head.json"
done=json.load(open(OUT)) if OUT.exists() else {}
def one(eid):
    raw=subprocess.run(f"curl -sL https://www.kaggleusercontent.com/episodes/{eid}.json | head -c 1200000",
                       shell=True,capture_output=True).stdout.decode("utf8","ignore")
    try:
        names=json.JSONDecoder().raw_decode(raw[raw.index('"TeamNames"')+len('"TeamNames"'):].lstrip(": "))[0]
        i=raw.index('"steps"'); j=raw.index("[",i)+1; dec=json.JSONDecoder(); steps=[]
        while len(steps)<4:
            while raw[j] in " ,\n": j+=1
            st,j=dec.raw_decode(raw,j); steps.append(st)
        p=names.index("datatuu"); o=1-p
        ob=steps[2][p]["observation"]
        rk=(float(ob["farms"][o]["money"]),int(ob["market"]["inventory"]["WHEAT"]))
        acts=[(steps[t][o].get("action") or {}).get("market") for t in (1,2,3)]
        return eid,{"rkey":rk,"opp_acts":acts,"pos":p}
    except Exception as e: return eid,{"err":str(e)[:80]}
todo=[e for e,v in meta.items() if v["ver"] in sys.argv[1:] and e not in done]
print("待取",len(todo),flush=True)
with ThreadPoolExecutor(8) as ex:
    for k,(e,r) in enumerate(ex.map(one,todo)):
        done[e]=r
        if k%40==0: json.dump(done,open(OUT,"w")); print(k,flush=True)
json.dump(done,open(OUT,"w")); print("完成",len(done))
