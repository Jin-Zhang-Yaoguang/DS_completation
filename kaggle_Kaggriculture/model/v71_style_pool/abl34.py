"""r34 执行层去重消融:新版人群 A 半(vs me2965_28) + cha 半数(vs engineV3)。"""
import sys, json, glob, hashlib, collections
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
def half(e,salt): return "A" if int(hashlib.md5((salt+str(e)).encode()).hexdigest(),16)%2==0 else "B"
def boards(grp,salt,which):
    comp=set(f.split("/")[-1][:-5] for f in glob.glob("rlive3/*.json")); seen=set(); B=[]
    for fn in ("boards_recent.json","boards_all.json"):
        for x in json.load(open(fn)):
            if x.get("seed") is None or (x["key"],x["lin"])!=grp or x["eid"] in seen or x["eid"] not in comp: continue
            seen.add(x["eid"])
            if half(x["eid"],salt)==which: B.append(x)
    return B
if __name__=="__main__":
    which=sys.argv[1] if len(sys.argv)>1 else "A"
    NG=boards(("1042.0","main"),"cs",which); CH=boards(("1042.0","cha"),"ls",which)
    V=[("基线",[])]+[(f"关{l}",[f"KAG_EXEC_OFF={l}"]) for l in ("MPX","MP","FX","DP","SM","MG","IG","CXD","MA","WB3")]+[(f"关{l}",[f"KAG_EXEC_OPTOFF={l}"]) for l in ("ADV","FRO","VQ","R148","T62A","ADVF")]+[("开HERD",["KAG_EXEC_ON=HERD"]),("开BD",["KAG_EXEC_REON=BD"])]
    V+=[(f"{n}={v}",[f"KAGP_{n}={v}"]) for n,vals in (("_S738_LOOK",(5,6)),("_S809_LOOK",(4,5)),("_HP_WINDOW",(3,5)),("_S731_FROM",(600,696)),("_S793_BUDGET",(1600,))) for v in vals]
    if len(sys.argv)>2: V=[v for v in V if v[0] in sys.argv[2].split(",") or (sys.argv[2]=="PARAM" and "=" in v[0]) or (sys.argv[2]=="PARAM" and v[0]=="基线")]
    base=None; out={}
    for name,env in V:
        a=be.run(NG,"r34probe","me2965_28",env); b=be.run(CH,"r34probe","engineV3",env)
        wa=sum(1 for d in a.values() if d and d>0); wb=sum(1 for d in b.values() if d and d>0)
        if base is None: base=(wa,wb)
        print(f"  {name:8s} 新版 {wa}/{len(NG)}  cha {wb}/{len(CH)}  合计变化 {wa+wb-base[0]-base[1]:+d}",flush=True)
        out[name]={**a,**b}
    json.dump(out,open(f"abl34_{which}.json","w"))
