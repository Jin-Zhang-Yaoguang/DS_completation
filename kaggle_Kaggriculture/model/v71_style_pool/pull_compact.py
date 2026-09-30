"""拉 r20/r22 对 ≥1900 对手的完整回放 → 压缩为 rlive3/<eid>.json(种子/双方动作/逐步现金/商店),不落原始大文件。"""
import json, urllib.request, sys, os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
HERE=Path(__file__).resolve().parent; DST=HERE/"rlive3"
meta=json.load(open(HERE/"meta_live.json"))
def one(eid):
    p=DST/f"{eid}.json"
    if p.exists(): return eid,"have"
    try:
        import subprocess
        raw=subprocess.run(["curl","-sL","--compressed","-m","400",f"https://www.kaggleusercontent.com/episodes/{eid}.json"],capture_output=True).stdout
        r=json.loads(raw)
        nm=r["info"]["TeamNames"]; seat=nm.index("datatuu"); s=r["steps"]
        acts=[[(s[t][q].get("action") or {}) for q in (0,1)] for t in range(len(s))]
        money=[]; shops=None
        for t in range(len(s)):
            ob=s[t][seat].get("observation") or {}
            if "farms" not in ob: ob=s[t][0].get("observation") or {}
            f=ob.get("farms")
            money.append([f[0]["money"],f[1]["money"]] if f else None)
            if ob.get("town"): shops=ob["town"].get("unlocked_shops")
        out={"eid":eid,"seed":r["info"]["seed"],"names":nm,"seat":seat,"rewards":r["rewards"],"acts":acts,"money":money,"shops":shops,
             "meta":meta[eid]["ver"]}
        p.write_text(json.dumps(out)); return eid,"ok"
    except Exception as e: return eid,f"err {e}"
H=json.load(open(HERE/"rkey_head.json"))
todo=[e for e,v in meta.items() if v["ver"] in sys.argv[1:] and v.get("opp") and (v["opp"].get("initialScore") or 0)>=float(os.environ.get("MINSCORE","1900"))
      and v["opp"].get("reward") is not None]
todo.sort(key=lambda e: meta[e]["me"]["reward"]-meta[e]["opp"]["reward"])  # 败局优先
print("待取",len(todo),flush=True)
with ThreadPoolExecutor(3) as ex:
    for k,(e,st) in enumerate(ex.map(one,todo)):
        if st.startswith("err") or k%20==0: print(k,e,st,flush=True)
print("完成")
