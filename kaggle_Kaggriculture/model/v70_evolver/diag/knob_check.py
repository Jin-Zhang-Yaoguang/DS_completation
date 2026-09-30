"""快速检查:基线 cfg 开启新旋钮后 4 seed × 6 对手的分数变化(仅供提议者判断 patch 是否有效,不做决策)。"""
import sys, json
from pathlib import Path
V = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(V))
import arena, evolve
from concurrent.futures import ProcessPoolExecutor
if __name__ == "__main__":
    base = json.load(open(V / 'runs/_funsearch/baseline.json'))['cfg']
    variants = {"base": {}}
    for arg in sys.argv[1:]:  # 形如 melon_age=10,melon_dump=1
        variants[arg] = {k: int(v) for k, v in (kv.split("=") for kv in arg.split(","))}
    opps = arena.default_opponents(); seeds = evolve.pick_valid_seeds(evolve.load_seed_pool())[:8]
    with ProcessPoolExecutor(14) as ex:
        for n, ov in variants.items():
            c = {**base, **ov}
            ms = list(ex.map(arena.play_one, [(c, o, s) for s in seeds for o in opps]))
            print(f"{n:28s} avg={sum(ms)/len(ms):+.0f}", flush=True)
