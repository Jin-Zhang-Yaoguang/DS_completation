"""改带实验:奶类世界羊/鹅→牛。真实棋盘奶类子集:新版人群(vs me2965_28/guru28)+ cha(vs engineV3)。"""
import sys, json, glob, collections
import board_eval2 as be
MILK={"PIZZA_SHOP","ICE_CREAM_SHOP","SMOOTHIE_SHOP"}
if __name__=="__main__":
    comp={}
    for f in glob.glob("rlive3/*.json"):
        r=json.load(open(f)); comp[str(r["eid"])]=r
    def milk_boards(grp):
        seen=set(); B=[]
        for fn in ("boards_recent.json","boards_all.json"):
            for x in json.load(open(fn)):
                if x.get("seed") is None or (x["key"],x["lin"])!=grp or x["eid"] in seen or x["eid"] not in comp: continue
                seen.add(x["eid"])
                if MILK & set((comp[x["eid"]].get("shops") or [])[:2]): B.append(x)
        return B
    NG=milk_boards(("1042.0","main")); CH=milk_boards(("1042.0","cha"))
    print("奶类棋盘 新版",len(NG),"cha",len(CH),flush=True)
    for name,env in (("r34",[]),("羊→牛",["KAG_MILKCOW=S"]),("羊鹅→牛",["KAG_MILKCOW=SG"])):
        r=[]
        for B,opp in ((NG,"me2965_28"),(NG,"guru28"),(CH,"engineV3")):
            d=be.run(B,"r34probe",opp,env); r.append(sum(1 for v in d.values() if v and v>0))
        print(f"  {name:6s} 新版 vs me2965 {r[0]}/{len(NG)}  vs guru28 {r[1]}/{len(NG)}  cha {r[2]}/{len(CH)}",flush=True)
