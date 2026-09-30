"""对轰局收入归因：无 yarn 钉商店，逐品统计双方 SELL 实收（单品步）。"""
import sys, json, collections
from fidelity import make_agent, engine
NOYARN=[("BAKERY",72),("PIZZA_SHOP",144),("BRUNCH_SPOT",216),("SMOOTHIE_SHOP",288),("FARMERS_MARKET",360),("ICE_CREAM_SHOP",432),("PET_CAFE",504),("FARMERS_MARKET",576)]
def run(s0, s1, seed):
    a=[make_agent(s0),make_agent(s1)]
    k=engine.load_scenario(); g=k.Game(seed=seed); g.force_shops([])
    rev=[collections.Counter(),collections.Counter()]; qty=[collections.Counter(),collections.Counter()]
    cost=[collections.Counter(),collections.Counter()]
    step=0
    while not engine._val(g.done):
        obs=[g.observe(0),g.observe(1)]
        acts=[]
        for p in (0,1):
            try: acts.append(a[p](obs[p]))
            except Exception: acts.append({"farmer":["PASS"],"hands":[],"market":[]})
        m0=[obs[p]["farms"][p]["money"] for p in (0,1)]
        g.step(acts[0],acts[1]); step+=1
        g.force_shops([n for n,st in NOYARN if st<=step])
        if engine._val(g.done): break
        ob2=[g.observe(0),g.observe(1)]
        for p in (0,1):
            mk=[o for o in (acts[p].get("market") or []) if o]
            d=ob2[p]["farms"][p]["money"]-m0[p]
            sl=[o for o in mk if o[0]=="SELL"]; buys=[o for o in mk if o[0]!="SELL"]
            if sl and not buys and len({o[1] for o in sl})==1 and d>0:
                it=sl[0][1]; rev[p][it]+=d; qty[p][it]+=sum(int(o[2]) for o in sl)
            elif buys and not sl and len({(o[0],o[1] if len(o)>1 else "") for o in buys})==1 and d<0:
                b=buys[0]; cost[p][str(b[0])+":"+(str(b[1]) if len(b)>1 else "")]+=-d
    return engine._val(g.reward(0)), engine._val(g.reward(1)), rev, qty, cost
if __name__=="__main__":
    s0,s1,seed=sys.argv[1],sys.argv[2],int(sys.argv[3])
    r0,r1,rev,qty,cost=run(s0,s1,seed)
    print(f"final {r0:.0f} vs {r1:.0f} (diff {r0-r1:+.0f})")
    items=sorted(set(rev[0])|set(rev[1]))
    print(f"{'item':11s} {'my_rev':>7s} {'op_rev':>7s} {'diff':>6s} | {'my_q':>4s} {'op_q':>4s} | my_avg op_avg")
    for it in items:
        a0,a1=rev[0][it],rev[1][it]; q0,q1=qty[0][it],qty[1][it]
        print(f"{it:11s} {a0:7.0f} {a1:7.0f} {a0-a1:+6.0f} | {q0:4d} {q1:4d} | {a0/max(1,q0):6.1f} {a1/max(1,q1):6.1f}")
    allc=sorted(set(cost[0])|set(cost[1]))
    for c in allc:
        if abs(cost[0][c]-cost[1][c])>50: print(f"cost {c:16s} my={cost[0][c]:.0f} opp={cost[1][c]:.0f} diff={cost[0][c]-cost[1][c]:+.0f}")
