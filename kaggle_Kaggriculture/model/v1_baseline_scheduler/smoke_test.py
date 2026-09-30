"""V1 baseline 冒烟测试：跑完整局、审计动作合法性与终局状态。"""
import argparse, importlib.util, json, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_agent(path):
    spec = importlib.util.spec_from_file_location("v1_baseline_main", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(opponent, seed, seat, steps=720, main_path=None):
    from kaggle_environments import make
    mod = load_agent(main_path or (HERE / "main.py"))
    me = mod.agent
    env = make("kaggriculture", configuration={"episodeSteps": steps, "seed": seed})
    agents = [me, opponent] if seat == 0 else [opponent, me]
    t0 = time.time()
    env.run(agents)
    last = env.steps[-1]
    banks = [float(s.reward or 0) for s in last]
    status = [str(s.status) for s in last]
    mine, theirs = banks[seat], banks[1 - seat]
    return {"seed": seed, "seat": seat, "opp": getattr(opponent, "__name__", str(opponent)),
            "mine": mine, "theirs": theirs, "margin": mine - theirs,
            "win": mine > theirs, "status": status, "secs": round(time.time() - t0, 1)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--opponents", default="starter,random,pass")
    ap.add_argument("--seeds", default="101,102,103")
    ap.add_argument("--steps", type=int, default=720)
    ap.add_argument("--selfplay", action="store_true")
    ap.add_argument("--main", default=None)
    args = ap.parse_args()

    rows = []
    for opp in args.opponents.split(","):
        if not opp:
            continue
        for seed in [int(s) for s in args.seeds.split(",")]:
            for seat in (0, 1):
                rows.append(run(opp, seed, seat, args.steps, args.main))
                print(json.dumps(rows[-1], ensure_ascii=False), flush=True)
    if args.selfplay:
        mod = load_agent(args.main or (HERE / "main.py"))
        rows.append(run(mod.agent, 400, 0, args.steps, args.main))
        print(json.dumps(rows[-1], ensure_ascii=False), flush=True)

    ext = [r for r in rows if r["opp"] != "agent"]
    wins = sum(1 for r in ext if r["win"])
    print(f"\n外部对局 {wins}/{len(ext)} 胜；平均终局金币 "
          f"{sum(r['mine'] for r in ext)/max(1,len(ext)):.1f}；"
          f"平均 margin {sum(r['margin'] for r in ext)/max(1,len(ext)):.1f}")
    bad = [r for r in rows if any(s != "DONE" for s in r["status"])]
    print("非 DONE 结束的对局:", bad if bad else "无")


if __name__ == "__main__":
    sys.exit(main())
