import json,sys,collections
PH=[(0,216),(216,360),(360,504),(504,576),(576,720)]
for eid in sys.argv[1].split(","):
    r=json.load(open(f"rlive3/{eid}.json")); A=r["acts"]; s=r["seat"]; o=1-s
    print("="*60,eid,r["names"][o])
    for a,b in PH:
        for nm,q in (("我",s),("敌",o)):
            c=collections.Counter()
            for t in range(a,min(b,len(A))):
                for m in (A[t][q] or {}).get("market") or []:
                    if not m: continue
                    key=m[0] if m[0] in ("HIRE","BUY_LAND") else m[0]+":"+str(m[1])
                    c[key]+=(m[2] if len(m)>2 and isinstance(m[2],int) else 1)
            print(f" [{a}-{b}) {nm}",{k:v for k,v in c.most_common() if not k.startswith("SELL")})
