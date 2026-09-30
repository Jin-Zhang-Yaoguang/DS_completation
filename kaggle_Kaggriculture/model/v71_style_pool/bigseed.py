"""大种子检验:随机 20 亿量级种子 → 实际组合 → 奶类受影响组合上 r34 vs r35(对 me2965_28)。"""
import sys, json, random
from concurrent.futures import ProcessPoolExecutor
import board_eval2 as be
from combo_check import one as combo_one
if __name__=="__main__":
    pick=json.load(open("milk34_pick.json")); rnd=random.Random(20260929)
    seeds=[rnd.randint(1_000_000_000,2_147_000_000) for _ in range(int(sys.argv[1]))]
    with ProcessPoolExecutor(7) as ex: lab=list(ex.map(combo_one,[(s,"","v54r34","me2965_28") for s in seeds]))
    B=[dict(seed=s,seat=i%2,eid=f"big{s}") for i,(s,l,r) in enumerate(lab) if r in pick]
    print("大种子",len(seeds),"落在受影响组合",len(B),flush=True)
    a=be.run(B,"v54r34","me2965_28"); b=be.run(B,"v54r35","me2965_28")
    print(f"大种子 vs me2965_28: r34 {sum(1 for v in a.values() if v and v>0)}/{len(B)} → r35 {sum(1 for v in b.values() if v and v>0)}/{len(B)}")
    json.dump([lab,B],open("bigseed.json","w"))
