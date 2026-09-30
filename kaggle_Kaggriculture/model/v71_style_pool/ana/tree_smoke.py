import json,sys,os
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent; os.chdir(HERE); sys.path.insert(0,str(HERE))
from pub_splice import OPP,M
sys.path.insert(0,str(M/"v16_online_fidelity")); sys.path.insert(0,str(M/"v4_demand_race"/"harness"))
import fidelity,engine
from concurrent.futures import ProcessPoolExecutor
def one(seed):
    ns={}; exec(Path("agents/v55f_main.py").read_text(),ns); me=ns["v55f_agent"]
    op=fidelity.make_agent(f"sub:{OPP['me2965_28']}")
    k=engine.load_kagsim(); g=k.Game(seed=seed); log=[]
    while not engine._val(g.done):
        o0=g.observe(0); st=ns["_ST"].get(0); e0=st and st.get("eid")
        a=me(o0); st=ns["_ST"][0]
        if st.get("eid")!=e0: log.append((o0["step"],st["eid"]))
        g.step(a,op(g.observe(1)))
    return seed,g.observe(0)["town"]["unlocked_shops"][:4],log,float(g.reward(0)-g.reward(1))
if __name__=="__main__":
    IDX=json.load(open("combo_big.json"))["v54"]; seeds=[IDX[c][18] for c in sorted(IDX)][:32]
    with ProcessPoolExecutor(8) as ex:
        R=list(ex.map(one,seeds))
    n=0
    for s,sh,log,d in R:
        n+=bool(log); print(s,sh,"切换:",log,f"{d:+.0f}")
    print("有切换",n,"/",len(R))
