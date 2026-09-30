"""动作审计:我方 cfg vs 带类对手,每局的动作构成、人次密度、空闲率、按天资金曲线。
用法: python diag/action_audit.py --cfg runs/_funsearch/baseline.json --seeds 5 --out runs/_signal/audit.json
       可选 --state runs/k1_x/state.json  附带种群各维收敛度与冠军贴边界度
"""
import sys, json, argparse, collections, statistics
from pathlib import Path
V = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(V))
import arena, evolve, space

MOVES = {"NORTH", "SOUTH", "EAST", "WEST"}


def unit_acts(a):
    return [a.get("farmer") or ["PASS"]] + [h for h in (a.get("hands") or [])]


def tally(actions_by_step):
    """actions_by_step: list of action dict(farmer/hands/market) -> 统计。"""
    cnt = collections.Counter(); mk = collections.Counter()
    units = 0; useful = 0; steps = len(actions_by_step)
    by_day = collections.defaultdict(collections.Counter)
    for t, a in enumerate(actions_by_step):
        ua = unit_acts(a)
        units += len(ua)
        for u in ua:
            k = str(u[0]) if u else "PASS"
            cat = "MOVE" if k in MOVES else k
            cnt[cat] += 1
            if cat not in ("MOVE", "PASS"):
                useful += 1
                by_day[t // 24][cat] += 1
        for o in (a.get("market") or []):
            if o:
                mk[str(o[0])] += 1
    return {"steps": steps, "units_per_step": units / steps, "useful_per_step": useful / steps,
            "idle_rate": (cnt["MOVE"] + cnt["PASS"]) / max(1, units),
            "actions": dict(cnt), "market": dict(mk),
            "useful_by_day": {d: sum(c.values()) for d, c in sorted(by_day.items())},
            "fert_by_day": {d: c.get("FERTILIZE", 0) for d, c in sorted(by_day.items())}}


def play_audit(job):
    cfg, opp_spec, seed = job
    arena._paths()
    import engine, fidelity
    mod = arena.load_scheduler()
    sched = mod.Sched(mod.Cfg(**cfg))
    opp = fidelity.make_agent(opp_spec)
    k = engine.load_kagsim(); g = k.Game(seed=seed)
    fallback = {"farmer": ["PASS"], "hands": [], "market": []}
    ours, money = [], [[], []]
    for t in range(719):
        o0 = g.observe(0); o0["player"] = 0
        o1 = g.observe(1)
        if t % 24 == 0:
            money[0].append(o0["farms"][0]["money"]); money[1].append(o1["farms"][1]["money"])
        try: a = sched.act(o0)
        except Exception: a = fallback
        try: b = opp(o1)
        except Exception: b = fallback
        ours.append(a)
        g.step(a, b)
    return {"seed": seed, "opp": opp_spec, "margin": float(g.reward(0) - g.reward(1)),
            "bank": [float(g.reward(0)), float(g.reward(1))],
            "ours": tally(ours), "money": money}


def boundary_report(cfg):
    out = {}
    for k, (lo, hi) in space.SPACE.items():
        v = cfg.get(k)
        if v is None or hi - lo <= 1: continue
        if v <= lo: out[k] = f"{v} =下界{lo}"
        elif v >= hi: out[k] = f"{v} =上界{hi}"
    return out


def convergence(pop):
    out = {}
    for k, (lo, hi) in space.SPACE.items():
        vs = [p[k] for p in pop if k in p]
        if len(vs) < 2: continue
        sd = statistics.pstdev(vs)
        out[k] = {"mean": round(statistics.mean(vs), 1), "sd": round(sd, 2), "rel": round(sd / max(1, hi - lo), 3)}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cfg", default=str(V / "runs" / "_funsearch" / "baseline.json"))
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--out", default=str(V / "runs" / "_signal" / "audit.json"))
    ap.add_argument("--state", default="")
    a = ap.parse_args()
    d = json.loads(Path(a.cfg).read_text()); cfg = space.clamp(d.get("cfg", d))
    pool = evolve.load_seed_pool(); seeds = evolve.pick_valid_seeds(pool)[:a.seeds]
    opps = [o for o in arena.default_opponents() if o.startswith("tape:")]
    from concurrent.futures import ProcessPoolExecutor
    jobs = [(cfg, op, sd) for op in opps for sd in seeds]
    with ProcessPoolExecutor(14) as ex:
        res = list(ex.map(play_audit, jobs))
    # 我方汇总
    def agg(key_fn, rows):
        keys = set(); [keys.update(key_fn(r).keys()) for r in rows]
        return {k: round(statistics.mean(key_fn(r).get(k, 0) for r in rows), 1) for k in sorted(keys, key=str)}
    ours = {"units_per_step": round(statistics.mean(r["ours"]["units_per_step"] for r in res), 2),
            "useful_per_step": round(statistics.mean(r["ours"]["useful_per_step"] for r in res), 2),
            "idle_rate": round(statistics.mean(r["ours"]["idle_rate"] for r in res), 3),
            "actions": agg(lambda r: r["ours"]["actions"], res), "market": agg(lambda r: r["ours"]["market"], res),
            "useful_by_day": agg(lambda r: r["ours"]["useful_by_day"], res),
            "fert_by_day": agg(lambda r: r["ours"]["fert_by_day"], res),
            "final_bank": round(statistics.mean(r["bank"][0] for r in res)),
            "money_by_day": [round(statistics.mean(r["money"][0][i] for r in res)) for i in range(30)]}
    opp_stats = {}
    for op in opps:
        acts = json.loads(Path(op.split(":", 1)[1]).read_text())["actions"]
        rows = [r for r in res if r["opp"] == op]
        t = tally(acts)
        t["final_bank"] = round(statistics.mean(r["bank"][1] for r in rows))
        t["money_by_day"] = [round(statistics.mean(r["money"][1][i] for r in rows)) for i in range(30)]
        t["margin_vs_us"] = round(statistics.mean(r["margin"] for r in rows))
        opp_stats[Path(op).stem] = t
    out = {"cfg": cfg, "seeds": seeds, "ours": ours, "opponents": opp_stats,
           "boundary": boundary_report(cfg)}
    if a.state:
        st = json.loads(Path(a.state).read_text())
        out["convergence"] = convergence(st["pop"])
    Path(a.out).write_text(json.dumps(out, indent=1))
    # 文本摘要
    print(f"我方: 人次/步 {ours['units_per_step']}  有效动作/步 {ours['useful_per_step']}  空闲率 {ours['idle_rate']}  终局 {ours['final_bank']}")
    print("  动作:", ours["actions"]); print("  市场:", ours["market"])
    for n, t in opp_stats.items():
        print(f"{n}: 人次/步 {t['units_per_step']:.2f}  有效/步 {t['useful_per_step']:.2f}  空闲率 {t['idle_rate']:.3f}  终局 {t['final_bank']}  我方margin {t['margin_vs_us']}")
        print("  动作:", t["actions"]); print("  市场:", t["market"])
    if out["boundary"]: print("贴边界:", out["boundary"])
    print("->", a.out)


if __name__ == "__main__":
    main()
