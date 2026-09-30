import os, json
from concurrent.futures import ProcessPoolExecutor
W = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model"
from fidelity import play
CAND = f"sub:{W}/v25_market_maker/main.py"
def one(a):
    cfg, opp, sd = a
    os.environ["MM_PARAMS"] = json.dumps(cfg)
    r0 = play(CAND, opp, sd, []); r1 = play(opp, CAND, sd, [])
    return (r0["bank"][0] - r0["bank"][1], r1["bank"][1] - r1["bank"][0])
if __name__ == "__main__":
    for label, cfg in (("ON ", {}), ("OFF", {"buy": 0.01})):
        tot = 0; w = 0; n = 0
        for opp in ("tape:tapes/fam_C_0w5l.json", "tape:tapes/fam_W_17w5l.json"):
            jobs = [(cfg, opp, sd) for sd in (61, 62, 63, 64)]
            with ProcessPoolExecutor(8) as ex:
                for d0, d1 in ex.map(one, jobs):
                    tot += d0 + d1; w += (d0 > 0) + (d1 > 0); n += 2
        print(f"MM {label}: w={w}/{n} avg_margin={tot/n:+.0f}", flush=True)
