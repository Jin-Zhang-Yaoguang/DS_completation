"""V4 冒烟测试：完整局、动作合法性、打包一致性。"""
import argparse, importlib.util, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "harness"))


def load(path, name="m"):
    spec = importlib.util.spec_from_file_location(f"{name}_{id(object())}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", default=str(HERE / "main.py"))
    ap.add_argument("--seeds", default="601,602,603")
    ap.add_argument("--official", action="store_true", help="用官方引擎跑（parity 抽检）")
    args = ap.parse_args()
    seeds = [int(s) for s in args.seeds.split(",")]

    if args.official:
        from kaggle_environments import make
        for seed in seeds:
            mod = load(args.main)
            env = make("kaggriculture", configuration={"episodeSteps": 720, "seed": seed})
            env.run([mod.agent, "starter"])
            last = env.steps[-1]
            print(json.dumps({"engine": "official", "seed": seed,
                              "banks": [float(s.reward or 0) for s in last],
                              "status": [str(s.status) for s in last]}))
        return

    from engine import load_kagsim, _val
    k = load_kagsim()
    import importlib.util as iu
    spec = iu.spec_from_file_location("kg", Path(sys.prefix) /
        "lib/python3.12/site-packages/kaggle_environments/envs/kaggriculture/kaggriculture.py")
    kg = iu.module_from_spec(spec); spec.loader.exec_module(kg)
    for seed in seeds:
        for opp_name, opp in (("starter", kg.starter_agent), ("random", kg.random_agent)):
            mod = load(args.main)
            g = k.Game(seed=seed)
            t0 = time.time()
            while not _val(g.done):
                g.step(mod.agent(g.observe(0)), opp(g.observe(1)))
            print(json.dumps({"seed": seed, "opp": opp_name,
                              "mine": g.reward(0), "theirs": g.reward(1),
                              "secs": round(time.time() - t0, 2)}))


if __name__ == "__main__":
    main()
