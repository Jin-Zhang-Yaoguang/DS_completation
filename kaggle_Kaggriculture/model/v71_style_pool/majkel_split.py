import json, hashlib, collections
from concurrent.futures import ProcessPoolExecutor
from majkel_tape import one
if __name__=="__main__":
    G=json.load(open("boards_majkel.json")); H=json.load(open("rkey_head.json"))
    print("键<900 的比例:",sum(1 for x in G if float(x["key"])<900),"/",len(G), " 键≥900 的:",[x["key"] for x in G if float(x["key"])>=900][:10])
    res={}
    for name,env in (("现状",()),("带126",("KAG_CUT144=126",))):
        with ProcessPoolExecutor(3) as ex: res[name]=dict(ex.map(one,[(x["eid"],env) for x in G]))
    json.dump(res,open("majkel_split.json","w"))
    for half in ("A","B"):
        for lvl,flt in (("全部",lambda x:True),("≥2000",lambda x:x["opp"]>=2000)):
            B=[x for x in G if flt(x) and ("A" if int(hashlib.md5(x["eid"].encode()).hexdigest(),16)%2==0 else "B")==half]
            a=sum(1 for x in B if (res["现状"].get(x["eid"]) or 0)>0); b=sum(1 for x in B if (res["带126"].get(x["eid"]) or 0)>0)
            print(f"  {half} 半 {lvl}({len(B)}): 现状 {a} → 带126 {b}")
