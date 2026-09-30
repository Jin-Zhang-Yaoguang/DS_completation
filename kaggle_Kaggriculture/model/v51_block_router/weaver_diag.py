"""fert weaver 诊断:重放我们的带(单人),逐 turn 统计施肥机会结构:
- PASS 且脚下作物可肥:手里有肥 / 手里无肥(但棚有) / 全局无肥
- 低价值动作(WATER 已浇过等)不计
输出:可改写机会的时段分布 → 决定改写器设计。"""
import sys, json, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
import engine, fidelity

TAPES = HERE.parent / "v16_online_fidelity" / "tapes"
FERTABLE = ("STRAWBERRY", "TOMATO", "WHEAT", "CARROT")


def diag(tape_name, seed):
    k = engine.load_kagsim()
    g = k.Game(seed=seed)
    ag = fidelity.make_agent(f"tape:{TAPES}/{tape_name}.json")
    stats = collections.Counter()
    seg_opp = collections.Counter()
    step = 0
    while not engine._val(g.done) and step < 719:
        obs = g.observe(0)
        act = ag(obs)
        farm = obs["farms"][0]
        tiles = farm["tiles"]
        me_pos = [farm.get("farmer")] + [h for h in (farm.get("hands") or [])]
        invs = (obs.get("private") or {}).get("inventories") or []
        shed_fert = int(((obs.get("private") or {}).get("shed") or {}).get("FERTILIZER", 0) or 0)
        units_act = [act.get("farmer") or []] + list(act.get("hands") or [])
        day = int(obs.get("day", 0))
        for i, u in enumerate(units_act):
            if not u or str(u[0]) != "PASS":
                continue
            if i >= len(me_pos) or not me_pos[i]:
                continue
            r, c = me_pos[i]
            try:
                t = tiles[r][c]
            except Exception:
                continue
            if not isinstance(t, dict) or t.get("kind") != "PLANT":
                stats["pass_not_on_crop"] += 1
                continue
            crop = t.get("crop")
            if crop == "STRAWBERRY" and int(t.get("fertilized_until_day", -1)) < day and day <= 27:
                has = i < len(invs) and int((invs[i] or {}).get("FERTILIZER", 0) or 0) > 0
                key = "straw_hasfert" if has else ("straw_shedfert" if shed_fert > 0 else "straw_nofert")
                stats[key] += 1
                seg_opp[(day // 6, key)] += 1
            elif crop in FERTABLE and int(t.get("fertilized_until_day", -1)) < day and day <= 27:
                stats[f"other_{crop[:4]}"] += 1
            else:
                stats["pass_on_crop_nofertable"] += 1
        g.step(act, {"farmer": ["PASS"], "hands": [], "market": []})
        step += 1
    print(f"== {tape_name} seed={seed} ==")
    for k2, v in stats.most_common():
        print(f"  {k2:24s} {v}")
    print("  草莓机会按 6 天段:", {f"d{6*s}({k2.split('_')[1]})": v for (s, k2), v in sorted(seg_opp.items())})


if __name__ == "__main__":
    for tape in ("fam_F_new", "rb_7925cb146f"):
        diag(tape, 11)
