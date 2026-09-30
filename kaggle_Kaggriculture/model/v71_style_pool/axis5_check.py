import sys, json
import board_eval2 as be
if __name__=="__main__":
    B=[x for x in json.load(open("boards_all.json")) if x.get("seed") is not None and (x["key"],x["lin"])==("1042.0","cha")]
    base=json.load(open("be2_cha_base.json"))["r30"]
    variants=[("基线(应=r30)",[]),("开回 DAWNPX",["KAG_EXEC_REON=DP"]),("开回 BUYDIP",["KAG_EXEC_REON=BD"]),
              ("关 ADVF",["KAG_EXEC_OPTOFF=ADVF"]),("关 ADV",["KAG_EXEC_OPTOFF=ADV"]),("关 FRO",["KAG_EXEC_OPTOFF=FRO"]),
              ("ADV 提前3步",["KAG_ADV_LOOK=3"]),("ADV 提前6步",["KAG_ADV_LOOK=6"]),("ADV 从t216",["KAG_ADV_FROM=216"]),
              ("FRO 从t144",["KAG_FRO_FROM=144"]),("FRO 从t360",["KAG_FRO_FROM=360"])]
    out={}
    for name,env in variants:
        res=be.run(B,"r30probe","engineV3",env)
        w=sum(1 for d in res.values() if d is not None and d>0)
        up=sum(1 for e,d in res.items() if d is not None and base.get(e) is not None and base[e]<=0<d)
        dn=sum(1 for e,d in res.items() if d is not None and base.get(e) is not None and d<=0<base[e])
        print(f"  {name:12s} {w}/{len(B)}  翻盘 {up} 被翻 {dn}",flush=True); out[name]=res
    json.dump(out,open("axis5_check.json","w"))
