"""冠军 cfg 在 4 组互不重叠、且未被 train/valid 用过的 8-seed 组上的 valid 波动 → 刀级验收阈值依据。"""
import sys, json, random, statistics
from concurrent.futures import ProcessPoolExecutor
V="/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v70_evolver"
sys.path.insert(0, V)
import arena, evolve
champ=json.load(open(f"{V}/runs/structv3/best_cfg.json"))["cfg"]
pool=evolve.load_seed_pool(); valid=set(evolve.pick_valid_seeds(pool))
used=set(valid)
for ep in range(80): used|=set(evolve.train_seeds_for(pool, ep*10, valid))
fresh=[s for s in pool if s not in used]
r=random.Random(777); r.shuffle(fresh)
groups=[fresh[i*8:(i+1)*8] for i in range(4)]
opps=arena.default_opponents()
if __name__=="__main__":
    with ProcessPoolExecutor(8) as ex:
        res=[]
        for g in groups:
            jobs=[(champ,op,sd) for op in opps for sd in g]
            ms=list(ex.map(arena.play_one, jobs))
            res.append(sum(ms)/len(ms))
            print(f"group seeds={g}: valid={res[-1]:+.0f}", flush=True)
    print(f"mean={statistics.mean(res):+.0f} sd={statistics.pstdev(res):.0f} range={max(res)-min(res):.0f} unused_seeds={len(fresh)}")
