"""链路审计:一局内各生产链的达成率(理论 vs 实际),定位最大缺口。"""
import sys, json, collections, importlib.util
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
import engine, fidelity

def audit(opp_spec="pass:", seed=22, agent_spec=None):
    spec = importlib.util.spec_from_file_location("sched", HERE / "scheduler.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    cfg = json.load(open(HERE / "best_cfg.json"))["cfg"]
    k = engine.load_kagsim(); g = k.Game(seed=seed)
    s = m.Sched(m.Cfg(**cfg))
    opp = fidelity.make_agent(opp_spec)
    # 统计
    crop_days = collections.Counter()      # 作物 × 在田步数
    crop_unwatered = collections.Counter() # 作物 × 当日未浇快照
    animal_days = collections.Counter()    # 动物 × 在栏步数
    animal_unfed = collections.Counter()
    animal_yield_wait = collections.Counter()  # 动物有产未收的步数
    crop_yield_wait = collections.Counter()
    fert_active = 0; fert_possible = 0
    idle = 0; total_units = 0
    for step in range(719):
        obs = g.observe(0); obs["player"] = 0
        a = s.act(obs)
        farm = obs["farms"][0]
        day = int(obs.get("day", 0))
        if step % 8 == 3:  # 抽样降耗
            for y in range(10):
                for x in range(10):
                    t = farm["tiles"][y][x]
                    if not isinstance(t, dict): continue
                    if t.get("kind") == "PLANT":
                        c = t.get("crop")
                        crop_days[c] += 1
                        if not t.get("watered_today"): crop_unwatered[c] += 1
                        if int(t.get("yield_units", 0) or 0) > 0: crop_yield_wait[c] += 1
                        if c in ("STRAWBERRY", "TOMATO"):
                            fert_possible += 1
                            if int(t.get("fertilized_until_day", -1)) >= day: fert_active += 1
                    elif t.get("animal"):
                        an = t["animal"]
                        animal_days[an] += 1
                        if not t.get("fed_today"): animal_unfed[an] += 1
                        if int(t.get("yield_units", 0) or 0) > 0: animal_yield_wait[an] += 1
        units = [a["farmer"]] + a["hands"]
        total_units += len(units)
        idle += sum(1 for u in units if u and u[0] == "PASS")
        try: b = opp(g.observe(1))
        except Exception: b = {"farmer": ["PASS"], "hands": [], "market": []}
        g.step(a, b)
    bank = g.reward(0)
    print(f"=== audit opp={opp_spec} seed={seed} bank={bank:.0f} ===")
    print(f"劳力闲置率: {idle}/{total_units} = {idle/max(total_units,1):.1%}")
    print(f"施肥覆盖率(草莓+番茄·抽样步): {fert_active}/{fert_possible} = {fert_active/max(fert_possible,1):.1%}")
    print("作物 在田量(步) 未浇率 带产待收率:")
    for c in crop_days:
        print(f"  {c:12s} {crop_days[c]:5d}  {crop_unwatered[c]/crop_days[c]:.1%}  {crop_yield_wait[c]/crop_days[c]:.1%}")
    print("动物 在栏量 未喂率 有产待收率:")
    for an in animal_days:
        print(f"  {an:8s} {animal_days[an]:5d}  {animal_unfed[an]/animal_days[an]:.1%}  {animal_yield_wait[an]/animal_days[an]:.1%}")

if __name__ == "__main__":
    audit(sys.argv[1] if len(sys.argv) > 1 else "pass:")
