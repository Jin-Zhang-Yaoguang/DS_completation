"""配对噪声:冠军 vs 当前种群 top2,在同 4 组 seed 上的配对差 → 刀级验收所需 seed 数。"""
import sys, json, random, statistics
from concurrent.futures import ProcessPoolExecutor
V="/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v70_evolver"
sys.path.insert(0, V)
import arena, evolve
champ=json.load(open(f"{V}/runs/structv3/best_cfg.json"))["cfg"]
pop=json.load(open(f"{V}/runs/structv3/state.json"))["pop"]
cands={"champ":champ,"pop0":pop[0],"pop1":pop[1]}
pool=evolve.load_seed_pool(); valid=set(evolve.pick_valid_seeds(pool))
used=set(valid)
for ep in range(80): used|=set(evolve.train_seeds_for(pool, ep*10, valid))
fresh=[s for s in pool if s not in used]; r=random.Random(777); r.shuffle(fresh)
seeds=fresh[:32]; opps=arena.default_opponents()
if __name__=="__main__":
    per={}
    with ProcessPoolExecutor(8) as ex:
        for name,cfg in cands.items():
            jobs=[(cfg,op,sd) for sd in seeds for op in opps]
            ms=list(ex.map(arena.play_one, jobs, chunksize=4))
            per[name]=[sum(ms[i*6:(i+1)*6])/6 for i in range(32)]  # 每 seed 对 6 对手均值
            print(f"{name}: 32-seed avg={statistics.mean(per[name]):+.0f} per-seed sd={statistics.pstdev(per[name]):.0f}", flush=True)
    for a in ("pop0","pop1"):
        d=[x-y for x,y in zip(per[a],per["champ"])]
        sd=statistics.pstdev(d); m=statistics.mean(d)
        print(f"{a}-champ 配对差: mean={m:+.0f} per-seed sd={sd:.0f} -> 32seed 均值的 se={sd/32**.5:.0f}; 8seed se={sd/8**.5:.0f}; 胜局 {sum(1 for x in d if x>0)}/32")
    json.dump({"seeds":seeds,"per":per}, open("paired_noise.json","w"))
