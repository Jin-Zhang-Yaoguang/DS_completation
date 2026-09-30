"""大种子组合索引:随机 10-21 亿种子,用 r34 vs me2965_28 跑到 t146 得实际组合。"""
import sys, json, random, collections
from concurrent.futures import ProcessPoolExecutor
from combo_check import one as combo_one
if __name__=="__main__":
    rnd=random.Random(int(sys.argv[2])); seeds=[rnd.randint(1_000_000_000,2_147_000_000) for _ in range(int(sys.argv[1]))]
    with ProcessPoolExecutor(7) as ex: lab=list(ex.map(combo_one,[(s,"","v54r34","me2965_28") for s in seeds],chunksize=8))
    idx=collections.defaultdict(list)
    for s,l,r in lab: idx[r].append(s)
    json.dump({"v54":dict(idx)},open(sys.argv[3],"w"))
    n=sorted(len(v) for v in idx.values()); print("组合数",len(idx),"每组合种子数 最少/中位",n[0],n[len(n)//2])
