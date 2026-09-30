import sys, json
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
if __name__=="__main__":
    B=[x for x in json.load(open(sys.argv[1])) if x.get("seed") is not None]
    for opp in sys.argv[3].split(","):
        d=be.run(B,sys.argv[2],opp)
        w=sum(1 for v in d.values() if v and v>0); print(f"  {sys.argv[2]} vs {opp:12s} {w}/{len(B)} ({w/len(B):.0%})",flush=True)
