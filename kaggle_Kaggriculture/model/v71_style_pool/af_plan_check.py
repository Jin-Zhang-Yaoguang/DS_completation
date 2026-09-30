"""动物优先顶队针对不同对手类型的打法,对我方 r38g 的效果:用 r38g 替换其对手(实录开环),按原对手类型分组。"""
import json, glob, collections
from concurrent.futures import ProcessPoolExecutor
from official_eval import sim
from review_fp import cls
TEAMS=["Luca","Aaweg","Planned Economy","Arjun Vinod","high frequency farming","Alan C52","daulettoibazar","pangzi233","DeeperNet","Vlas Veles","tine.sh agent"]
FIXED={"新版人群","cha谱系","rescue7系","metav4","K52"}
if __name__=="__main__":
    B=[]
    for f in glob.glob("roff_af/*.json"):
        r=json.load(open(f)); nm=r["names"]; M=r["money"]
        for p,n in enumerate(nm):
            if n not in TEAMS: continue
            o=1-p; sk=r["key2"][o]
            if not (sk[1] in (9990,9991,9992) and sk[0]<900): continue
            k=r["key2"][p]; lin="cha" if (M[92] and M[91] and M[92][o]-M[91][o]>50) else "main"
            oc=cls(float(round(k[0])),lin)
            kind="固定路线型" if oc in FIXED else ("动物优先" if (k[1] in (9990,9991,9992) and k[0]<900) else "其他")
            B.append((r["eid"],o,n,kind,(r["rewards"][o] or 0)>(r["rewards"][p] or 0)))
    jobs=[("v54r38g","roff_af",e,o,()) for e,o,*_ in B]
    with ProcessPoolExecutor(8) as ex: R={j[2]+"|"+str(j[3]):(x or {}).get("d") for j,x in ex.map(sim,jobs,chunksize=2)}
    G=collections.defaultdict(lambda:[0,0,0,[]])
    for e,o,n,kind,orig in B:
        x=R.get(f"{e}|{o}")
        if x is None: continue
        a=G[kind]; a[0]+=1; a[1]+=x>0; a[2]+=orig; a[3].append(x)
    print("动物优先顶队的对局,用 r38g 替换其对手(对手=顶队,按实录回放);按顶队当时面对的原对手类型分组:")
    for k in ("固定路线型","动物优先","其他"):
        a=G[k]
        if a[0]: print(f"   顶队针对[{k}]的打法: 局 {a[0]:3d}  r38g 胜 {a[1]:3d} ({a[1]/a[0]:.0%}) 均差 {sum(a[3])/a[0]:7.0f} | 原对手胜 {a[2]} ({a[2]/a[0]:.0%})")
