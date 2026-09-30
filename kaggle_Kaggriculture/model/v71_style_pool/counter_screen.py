import sys, json, collections
import board_eval2 as be
if __name__=="__main__":
    B=[x for x in json.load(open(sys.argv[1])) if x.get("seed") is not None and (x["key"],x["lin"]) in (("1042.0","main"),("1042.0","cha"))]
    opp=sys.argv[2]; tag=sys.argv[3]
    SHORT=[0,100,101,103,107,110,112,115,118,120,123,124,126]
    V=[("r31","v54r31",[]),("强制cha行","r31probe",["KAG_FORCE_CHA=1"])]+[(f"t144带{r}","r31probe",[f"KAG_CUT144={r}"]) for r in SHORT]
    if len(sys.argv)>4: V+=[(f"本体:{a}",a,[]) for a in sys.argv[4].split(",")]
    out={}
    for name,agent,env in V:
        if agent.startswith("本体") : continue
        if name.startswith("本体:"):
            import board_eval2
            jobs=[(None,)]  # placeholder
        res=be.run(B,agent if not name.startswith("本体:") else None,opp,env) if not name.startswith("本体:") else None
        if res is None:
            from pathlib import Path
            from pub_splice import OPP
            rel=str(Path(OPP[agent]).relative_to(Path("agents").resolve())) if False else None
        out[name]=res
        if res is not None:
            w=sum(1 for d in res.values() if d is not None and d>0); print(f"  {name:12s} {w}/{len(B)} ({w/len(B):.0%})",flush=True)
    json.dump(out,open(f"counter_{tag}.json","w"))
