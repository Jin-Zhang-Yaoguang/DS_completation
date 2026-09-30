import json,collections
IDX=json.load(open("online_games.json"))
G=sorted([(v["end"],e,v) for e,v in IDX.items() if v["ver"]=="v55b"])
def summ(acts,o,T):
    c=collections.Counter()
    for t in range(min(T,len(acts))):
        a=acts[t][o]
        if isinstance(a,dict):
            for x in (a.get("actions") or a.get("commands") or [a] if a else []):
                if isinstance(x,dict): c[(x.get("type") or x.get("action") or "?")+":"+str(x.get("item") or x.get("product") or x.get("animal") or "")]+=1
    return c
w=l=d=0
for end,e,v in G:
    r=json.load(open(f"rlive3/{e}.json")); o=1-r["seat"]; M=r["money"]
    res="W" if v["d"]>0 else ("L" if v["d"]<0 else "D")
    w+=res=="W"; l+=res=="L"; d+=res=="D"
    fin=M[-1] if M[-1] else M[-2]
    print(end[5:16],e,res,f"{v['d']:+8.0f}",v["opp_team"][:22].ljust(22),"seat",r["seat"],"key",[round(k) for k in v["key"]],v["lin"],v["shops"],"fin",[round(x) for x in fin] if fin else None)
print("W/L/D",w,l,d)
