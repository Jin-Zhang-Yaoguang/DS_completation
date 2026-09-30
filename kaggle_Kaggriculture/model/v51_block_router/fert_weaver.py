"""fert weaver v1:离线改写带——解锁 straw_shedfert 池。
pass1: kagsim 重放,记录每 unit 每 turn (位置, 动作, 随身肥) + 合法 shed 交互位置集 + 机会点。
pass2: 贪心插入 PICKUP FERTILIZER(在 shed 交互位置上的 PASS turn),机会点 PASS->FERTILIZE。
pass3: 输出改写带,3 seed 单人验证(vs 原带)。
用法: python fert_weaver.py <tape_name>
"""
import sys, json, collections
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
import engine, fidelity

TAPES = HERE.parent / "v16_online_fidelity" / "tapes"
PICK_QTY = 1


def replay_record(tape_name, seed):
    k = engine.load_kagsim()
    g = k.Game(seed=seed)
    ag = fidelity.make_agent(f"tape:{TAPES}/{tape_name}.json")
    rec = []          # rec[t] = list of (unit_idx, pos, op, carry_fert)
    shed_spots = set()  # 出现过 DROP/PICKUP 的位置(经验合法交互点)
    opps = []         # (t, unit_idx) straw_shedfert / straw_nofert 机会
    step = 0
    while not engine._val(g.done) and step < 719:
        obs = g.observe(0)
        act = ag(obs)
        farm = obs["farms"][0]
        tiles = farm["tiles"]
        pos = [farm.get("farmer")] + [h for h in (farm.get("hands") or [])]
        invs = (obs.get("private") or {}).get("inventories") or []
        day = int(obs.get("day", 0))
        units_act = [act.get("farmer") or []] + list(act.get("hands") or [])
        row = []
        for i, u in enumerate(units_act):
            op = str(u[0]) if u else "PASS"
            p = tuple(pos[i]) if i < len(pos) and pos[i] else None
            cf = int((invs[i] or {}).get("FERTILIZER", 0) or 0) if i < len(invs) else 0
            row.append((i, p, op, cf))
            if op in ("DROP", "PICKUP") and p:
                shed_spots.add(p)
            if op == "PASS" and p:
                try:
                    t = tiles[p[0]][p[1]]
                except Exception:
                    t = None
                if (isinstance(t, dict) and t.get("kind") == "PLANT" and t.get("crop") == "STRAWBERRY"
                        and int(t.get("fertilized_until_day", -1)) < day and day <= 27 and cf == 0):
                    opps.append((step, i))
        rec.append(row)
        g.step(act, {"farmer": ["PASS"], "hands": [], "market": []})
        step += 1
    return rec, shed_spots, opps


def weave(tape_name, seeds=(11, 22, 33)):
    acts = json.load(open(TAPES / f"{tape_name}.json"))["actions"]
    recs, spots_l, opps_l = [], [], []
    for sd in seeds:
        rec, shed_spots, opps = replay_record(tape_name, sd)
        recs.append(rec); spots_l.append(shed_spots); opps_l.append(set(opps))
    rec = recs[0]
    shed_spots = set.intersection(*[set(s0) for s0 in spots_l])
    opp_set = set.intersection(*opps_l)
    opps = sorted(opp_set)
    # 插入点也需三 seed 都 PASS(rec 的 op 在带固定下相同,但保险检查全部 rec)
    def all_pass_at(tb, ui):
        for rc in recs:
            if tb >= len(rc) or ui >= len(rc[tb]):
                return False
            _, p, op, _ = rc[tb][ui]
            if op != "PASS" or p not in shed_spots:
                return False
        return True
    print(f"{tape_name}: shed 交互点 {sorted(shed_spots)}, 交集机会 {len(opps)} 个 (各 seed: {[len(o) for o in opps_l]})")
    new_acts = [json.loads(json.dumps(a)) for a in acts]
    carry = collections.defaultdict(int)   # 虚拟额外携带(由插入的 PICKUP 提供)
    used_insert = set()
    n_pick = n_fert = 0
    for (t, ui) in opps:
        if carry[ui] <= 0:
            # 向前找插入点:该 unit 在 shed 交互位置上且动作 PASS
            ins = None
            for tb in range(t - 1, max(-1, t - 200), -1):
                if (tb, ui) in used_insert:
                    continue
                row = rec[tb] if tb < len(rec) else None
                if not row or ui >= len(row):
                    continue
                _, p, op, _ = row[ui]
                if all_pass_at(tb, ui):
                    ins = tb
                    break
            if ins is None:
                continue
            a = new_acts[ins]
            units = [a.get("farmer") or ["PASS"]] + [list(h) for h in (a.get("hands") or [])]
            units[ui] = ["PICKUP", "FERTILIZER", PICK_QTY]
            a["farmer"] = units[0]
            a["hands"] = units[1:]
            used_insert.add((ins, ui))
            carry[ui] += PICK_QTY
            n_pick += 1
        # 机会点改 FERTILIZE
        a = new_acts[t]
        units = [a.get("farmer") or ["PASS"]] + [list(h) for h in (a.get("hands") or [])]
        if units[ui] and str(units[ui][0]) == "PASS":
            units[ui] = ["FERTILIZE"]
            a["farmer"] = units[0]
            a["hands"] = units[1:]
            carry[ui] -= 1
            n_fert += 1
    out = TAPES / f"{tape_name}_fw.json"
    json.dump({"actions": new_acts, "weaver": {"picks": n_pick, "ferts": n_fert, "seeds": list(seeds)}}, out.open("w"))
    print(f"插入 PICKUP {n_pick} 次, FERTILIZE {n_fert} 次 -> {out.name}")
    # 3 seed 验证
    for sd in (11, 22, 33):
        b0 = int(fidelity.play(f"tape:{TAPES}/{tape_name}.json", "pass:", sd, [])["bank"][0])
        b1 = int(fidelity.play(f"tape:{out}", "pass:", sd, [])["bank"][0])
        print(f"  seed{sd}: {b0} -> {b1} ({b1-b0:+d})")


if __name__ == "__main__":
    weave(sys.argv[1] if len(sys.argv) > 1 else "fam_F_new")
