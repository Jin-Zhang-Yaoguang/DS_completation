"""K1 B1 达标线自检：solo(vs PASS) 金币、空闲率、覆盖率、日程曲线、现金曲线。

达标线（v71 README B1）：solo >= 100k；空闲率 <= 0.50；浇水/喂养覆盖 >= 0.95；
人手与地块曲线对 Majkel 逆向表偏差 <= 10%。
用法: /opt/anaconda3/bin/python3 selfcheck.py [seed ...]
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
import engine  # noqa: E402


def run_probe(seed):
    import importlib.util
    spec = importlib.util.spec_from_file_location(f"k1_{seed}", HERE / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    k = engine.load_kagsim()
    g = k.Game(seed=seed)

    def pa(o):
        return {"farmer": ["PASS"], "hands": [], "market": []}

    stats = {
        "hands_by_day": {}, "money_by_day": {}, "min_money": 10**9,
        "acts": {"PASS": 0, "MOVE": 0, "WORK": 0}, "n_unit_turns": 0,
        "water_miss": 0, "water_due": 0, "feed_miss": 0, "feed_due": 0,
        "planted_by_day": {}, "animals_by_day": {}, "sell_gold": 0.0,
        "errors": 0, "shops": None, "starve_lost": 0,
    }
    prev_animals = 0
    while not (g.done() if callable(g.done) else g.done):
        o0 = g.observe(0)
        o1 = g.observe(1)
        day, hour = int(o0["day"]), int(o0["hour"])
        turn = day * 24 + hour
        farm = o0["farms"][0]
        tiles = farm["tiles"]

        # 日界快照(money h0;hands h2——引擎日初清工,h0/h1 重雇)
        if hour == 2:
            stats["hands_by_day"][day] = len(farm.get("hands") or [])
        if hour == 0:
            stats["money_by_day"][day] = farm["money"]
            planted = {}
            n_animals = 0
            for row in tiles:
                for t in row:
                    if isinstance(t, dict):
                        if t.get("kind") == "PLANT":
                            planted[t["crop"]] = planted.get(t["crop"], 0) + 1
                        if "animal" in t:
                            n_animals += 1
            stats["planted_by_day"][day] = planted
            stats["animals_by_day"][day] = n_animals
            if n_animals < prev_animals and day < 29:
                stats["starve_lost"] += prev_animals - n_animals
            prev_animals = n_animals
            stats["shops"] = list((o0.get("town") or {}).get("unlocked_shops") or [])

        # 覆盖率：hour 23 时未浇/未喂计 miss
        if hour == 23:
            for row in tiles:
                for t in row:
                    if isinstance(t, dict):
                        if t.get("kind") == "PLANT":
                            stats["water_due"] += 1
                            if not t.get("watered_today"):
                                stats["water_miss"] += 1
                        if "animal" in t and day < 28:
                            stats["feed_due"] += 1
                            if not t.get("fed_today"):
                                stats["feed_miss"] += 1

        stats["min_money"] = min(stats["min_money"], farm["money"])
        try:
            a0 = mod.agent(o0)
        except Exception:
            stats["errors"] += 1
            a0 = {"farmer": ["PASS"], "hands": [], "market": []}
        units = [a0.get("farmer") or ["PASS"]] + list(a0.get("hands") or [])
        for u in units:
            stats["n_unit_turns"] += 1
            op = (u or ["PASS"])[0]
            if op == "PASS":
                stats["acts"]["PASS"] += 1
            elif op in ("NORTH", "SOUTH", "EAST", "WEST"):
                stats["acts"]["MOVE"] += 1
            else:
                stats["acts"]["WORK"] += 1
        g.step(a0, pa(o1))
    bank = float(g.reward(0))
    return bank, stats


def main():
    seeds = [int(s) for s in sys.argv[1:]] or [1009, 1046, 2083, 3120]
    kn = json.loads((HERE / "knowledge.json").read_text())
    banks = []
    for seed in seeds:
        bank, s = run_probe(seed)
        banks.append(bank)
        idle = (s["acts"]["PASS"] + s["acts"]["MOVE"]) / max(1, s["n_unit_turns"])
        wcov = 1 - s["water_miss"] / max(1, s["water_due"])
        fcov = 1 - s["feed_miss"] / max(1, s["feed_due"])
        # 日程曲线偏差(人手)
        dev = []
        for d, h in s["hands_by_day"].items():
            tgt = kn["hands_by_day"][min(d, 29)]
            if tgt:
                dev.append(abs(h - tgt) / tgt)
        hands_dev = sum(dev) / max(1, len(dev))
        print(f"seed {seed}: bank {bank:.0f} | idle {idle:.3f} | water_cov {wcov:.3f} "
              f"| feed_cov {fcov:.3f} | hands_dev {hands_dev:.2f} | min_money {s['min_money']} "
              f"| starve_lost {s['starve_lost']} | errors {s['errors']} | shops {s['shops']}")
        # 关键日地块快照
        for d in (0, 2, 6, 9, 12, 16, 20, 24, 27):
            if d in s["planted_by_day"]:
                print(f"    d{d}: hands {s['hands_by_day'].get(d)} money {s['money_by_day'].get(d)} "
                      f"animals {s['animals_by_day'].get(d)} planted {s['planted_by_day'][d]}")
    print(f"\nmean bank: {sum(banks)/len(banks):.0f}  (B1 达标线 100k)")


if __name__ == "__main__":
    main()
