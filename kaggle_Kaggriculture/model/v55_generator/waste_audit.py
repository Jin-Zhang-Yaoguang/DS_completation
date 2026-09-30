"""B 线:浪费审计——重放调度器,判定每个农场动作是否生效(状态对比),输出浪费分布。"""
import sys, json, collections, importlib.util
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
import engine, fidelity

def audit(opp_spec="pass:", seed=22):
    spec = importlib.util.spec_from_file_location("sched", HERE / "scheduler.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    cfg = json.load(open(HERE / "best_cfg.json"))["cfg"]
    k = engine.load_kagsim(); g = k.Game(seed=seed)
    s = m.Sched(m.Cfg(**cfg))
    opp = fidelity.make_agent(opp_spec)
    waste = collections.Counter()
    ok = collections.Counter()
    for step in range(719):
        obs = g.observe(0); obs["player"] = 0
        farm = obs["farms"][0]
        tiles_before = json.loads(json.dumps(farm["tiles"]))
        pos = [tuple(farm.get("farmer") or (0, 0))] + [tuple(h) for h in (farm.get("hands") or [])]
        invs_before = [dict(x or {}) for x in ((obs.get("private") or {}).get("inventories") or [])]
        a = s.act(obs)
        units = [a.get("farmer") or ["PASS"]] + list(a.get("hands") or [])
        try:
            b = opp(g.observe(1))
        except Exception:
            b = {"farmer": ["PASS"], "hands": [], "market": []}
        g.step(a, b)
        obs2 = g.observe(0)
        farm2 = obs2["farms"][0]
        tiles_after = farm2["tiles"]
        pos_after = [tuple(farm2.get("farmer") or (0, 0))] + [tuple(h) for h in (farm2.get("hands") or [])]
        for i, u in enumerate(units):
            if not u or i >= len(pos):
                continue
            op = str(u[0])
            x, y = pos[i]
            tb = tiles_before[y][x] if isinstance(tiles_before[y][x], dict) else {}
            ta = tiles_after[y][x] if isinstance(tiles_after[y][x], dict) else {}
            eff = None
            if op == "PASS":
                eff = False
            elif op in ("NORTH", "SOUTH", "EAST", "WEST"):
                eff = i < len(pos_after) and pos_after[i] != (x, y)
            elif op == "WATER":
                eff = (not tb.get("watered_today")) and ta.get("watered_today")
            elif op == "HARVEST":
                eff = int(tb.get("yield_units", 0) or 0) > int(ta.get("yield_units", 0) or 0)
            elif op == "FEED":
                eff = (not tb.get("fed_today")) and ta.get("fed_today")
            elif op == "CARE":
                eff = (not tb.get("cared_today")) and ta.get("cared_today")
            elif op == "FERTILIZE":
                eff = int(ta.get("fertilized_until_day", -1) or -1) > int(tb.get("fertilized_until_day", -1) or -1)
            elif op == "PLANT":
                eff = ta.get("kind") == "PLANT" and tb.get("kind") != "PLANT"
            elif op == "COLLECT_FERTILIZER":
                eff = tb.get("fertilizer_available") and not ta.get("fertilizer_available")
            elif op == "PICKUP":
                item = str(u[1]) if len(u) > 1 else "?"
                ib = invs_before[i].get(item, 0) if i < len(invs_before) else 0
                ia = ((obs2.get("private") or {}).get("inventories") or [{}]*(i+1))[i].get(item, 0) if i < len(((obs2.get("private") or {}).get("inventories") or [])) else 0
                eff = ia > ib
            else:
                eff = True
            (ok if eff else waste)[op] += 1
    print(f"=== waste audit opp={opp_spec} seed={seed} bank={g.reward(0):.0f} ===")
    total = sum(ok.values()) + sum(waste.values())
    print(f"总动作 {total}, 有效 {sum(ok.values())} ({sum(ok.values())/total:.0%})")
    print("浪费分布(动作: 无效次数 / 总次数):")
    for op in sorted(set(ok) | set(waste), key=lambda o: -waste.get(o, 0)):
        w, o2 = waste.get(op, 0), ok.get(op, 0)
        print(f"  {op:20s} {w:4d} / {w+o2:4d}  ({w/max(w+o2,1):.0%} 无效)")

if __name__ == "__main__":
    audit(sys.argv[1] if len(sys.argv) > 1 else "pass:")
