import json,glob,collections
A={}; OTH=[]
for f in glob.glob("roff_af/*.json")+glob.glob("roff/*.json")+glob.glob("rlive3/*.json"):
    try: r=json.load(open(f))
    except: continue
    for p,n in enumerate(r["names"]):
        k=json.dumps([a[p] for a in r["acts"][1:60]],sort_keys=True)
        if n=="Arjun Vinod": A[k]=1
        else: OTH.append((k,n,r["eid"]))
c=collections.Counter(n for k,n,e in OTH if k in A)
print("与 Arjun 某局前59步完全相同的其他玩家:",sum(c.values()),c.most_common(20))
