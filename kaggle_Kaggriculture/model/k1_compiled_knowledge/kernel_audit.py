"""K0 内核规格测量：从逐步「观测→单位动作」还原执行内核的行为规格。

同一套提取逻辑用于两个来源，逐项对比：
  majkel  —— 原始 replay（steps[t] 的动作基于 steps[t-1] 的观测）
  k1      —— kagsim 自跑 K1（对手 y68c）

指标：
  A 各小时 工作/移动/PASS 占比
  B 随身携带：非仓库格单位持麦/持肥比例与均量；PICKUP 次数与均量
  C 工作类型分布（按天段）
  D 移动目标推断：与「先纵后横+缩短距离」一致的候选任务中取最近者，
    统计它在全部候选里的距离排名（0=全局最近）
  E 连续两次工作之间的格距（任务链连贯度）
  F 同格多任务的执行先后（动物：FEED/CARE/COLLECT/HARVEST 首动作分布）
  G 空间布局模板（d12 h3 各格 kind 众数）

用法: /opt/anaconda3/bin/python3 kernel_audit.py [n_majkel_games] [n_k1_games]
"""
import importlib.util
import json
import statistics
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
V71 = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v71_majkel_reverse")
IDX = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model_data/kaggriculture_episodes_index")
POOL = "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/opponent_pool_v1"
MOVES = {"NORTH": (0, -1), "SOUTH": (0, 1), "WEST": (-1, 0), "EAST": (1, 0)}
WORK_OPS = {"WATER", "HARVEST", "FEED", "CARE", "COLLECT_FERTILIZER", "FERTILIZE", "PLANT",
            "BUILD_PASTURE", "BUILD_COOP", "DIG", "PLACE", "PICKUP", "DROP"}


def shed_tiles(bs):
    h = bs // 2
    return {(h - 1, h - 1), (h, h - 1), (h - 1, h), (h, h)}


def candidates(tiles, day):
    """当前状态下的待办任务格：(pos, type)。"""
    out = []
    for y, row in enumerate(tiles):
        for x, t in enumerate(row):
            if not isinstance(t, dict):
                continue
            if "animal" in t:
                if not t.get("fed_today"):
                    out.append(((x, y), "FEED"))
                if not t.get("cared_today"):
                    out.append(((x, y), "CARE"))
                if t.get("fertilizer_available"):
                    out.append(((x, y), "COLLECT"))
                if t.get("yield_units", 0) > 0:
                    out.append(((x, y), "A_HARVEST"))
            elif t.get("kind") == "PLANT":
                if not t.get("watered_today"):
                    out.append(((x, y), "WATER"))
                if t.get("yield_units", 0) > 0:
                    out.append(((x, y), "HARVEST"))
            elif t.get("kind") == "WEED":
                out.append(((x, y), "DIG"))
    return out


def audit_game(obs_seq, act_seq, seat):
    """obs_seq[i] 是做 act_seq[i] 时看到的观测。返回原始计数字典（可合并）。"""
    R = {
        "hour": defaultdict(Counter),      # hour -> WORK/MOVE/PASS
        "carry": Counter(),                # units_off_shed / with_wheat / with_fert / wheat_sum / fert_sum
        "pickup": Counter(),               # item -> 次数 ; item_qty -> 总量
        "worktype": defaultdict(Counter),  # seg -> op
        "move_rank": Counter(),            # 0/1/2/3+/none
        "move_target": Counter(),          # 目标任务类型
        "chain_dist": Counter(),           # 连续工作格距 0/1/2/3/4+
        "animal_first": Counter(),         # 进入动物格后的首个工作动作
        "layout": defaultdict(Counter),    # (x,y) -> kind
        "days": set(),
    }
    last_work = {}
    for obs, act in zip(obs_seq, act_seq):
        if not obs or not act:
            continue
        farms = obs.get("farms") or []
        if seat >= len(farms):
            continue
        farm = farms[seat]
        tiles = farm.get("tiles") or []
        bs = len(tiles)
        if not bs:
            continue
        day, hour = int(obs.get("day", 0)), int(obs.get("hour", 0))
        R["days"].add(day)
        sheds = shed_tiles(bs)
        positions = [tuple(farm["farmer"])] + [tuple(p) for p in (farm.get("hands") or [])]
        units = [act.get("farmer") or ["PASS"]] + list(act.get("hands") or [])
        invs = (obs.get("private") or {}).get("inventories") or []
        cands = candidates(tiles, day)
        seg = f"d{(day // 6) * 6:02d}"
        if day == 12 and hour == 3:
            for y, row in enumerate(tiles):
                for x, t in enumerate(row):
                    k = t if isinstance(t, str) else ("EMPTY" if t is None else
                                                      (t.get("crop") or t.get("kind")))
                    R["layout"][(x, y)][k] += 1
        for ui, (pos, u) in enumerate(zip(positions, units)):
            op = (u or ["PASS"])[0]
            inv = invs[ui] if ui < len(invs) and isinstance(invs[ui], dict) else {}
            if pos not in sheds:
                R["carry"]["off_shed"] += 1
                if inv.get("WHEAT", 0) > 0:
                    R["carry"]["with_wheat"] += 1
                    R["carry"]["wheat_sum"] += inv["WHEAT"]
                if inv.get("FERTILIZER", 0) > 0:
                    R["carry"]["with_fert"] += 1
                    R["carry"]["fert_sum"] += inv["FERTILIZER"]
            if op in MOVES:
                R["hour"][hour]["MOVE"] += 1
                dx, dy = MOVES[op]
                ok = []
                for cpos, ctype in cands:
                    ddx, ddy = cpos[0] - pos[0], cpos[1] - pos[1]
                    if ddx == 0 and ddy == 0:
                        continue
                    if dy != 0 and ddy * dy > 0:
                        ok.append((abs(ddx) + abs(ddy), cpos, ctype))
                    elif dx != 0 and ddy == 0 and ddx * dx > 0:
                        ok.append((abs(ddx) + abs(ddy), cpos, ctype))
                if not ok:
                    R["move_rank"]["none"] += 1
                else:
                    d0, cpos, ctype = min(ok)
                    rank = sum(1 for c2, _ in cands
                               if 0 < abs(c2[0] - pos[0]) + abs(c2[1] - pos[1]) < d0)
                    R["move_rank"][str(min(rank, 3)) if rank < 3 else "3+"] += 1
                    R["move_target"][ctype] += 1
            elif op == "PASS":
                R["hour"][hour]["PASS"] += 1
            else:
                R["hour"][hour]["WORK"] += 1
                R["worktype"][seg][op] += 1
                if op == "PICKUP" and len(u) >= 3:
                    R["pickup"][u[1]] += 1
                    R["pickup"][u[1] + "_qty"] += int(u[2] or 0)
                key = (day, ui)
                if key in last_work:
                    d = abs(last_work[key][0] - pos[0]) + abs(last_work[key][1] - pos[1])
                    R["chain_dist"][str(d) if d < 4 else "4+"] += 1
                last_work[key] = pos
                if 0 <= pos[1] < bs and 0 <= pos[0] < bs:
                    t = tiles[pos[1]][pos[0]]
                    if isinstance(t, dict) and "animal" in t and op in (
                            "FEED", "CARE", "COLLECT_FERTILIZER", "HARVEST"):
                        prev = last_work.get(("animal_prev", ui))
                        if prev != (day, pos):
                            R["animal_first"][op] += 1
                        last_work[("animal_prev", ui)] = (day, pos)
    return R


def merge(rs):
    M = {"hour": defaultdict(Counter), "carry": Counter(), "pickup": Counter(),
         "worktype": defaultdict(Counter), "move_rank": Counter(), "move_target": Counter(),
         "chain_dist": Counter(), "animal_first": Counter(), "layout": defaultdict(Counter), "n": 0}
    for r in rs:
        M["n"] += 1
        for h, c in r["hour"].items():
            M["hour"][h].update(c)
        for s, c in r["worktype"].items():
            M["worktype"][s].update(c)
        for p, c in r["layout"].items():
            M["layout"][p].update(c)
        for k in ("carry", "pickup", "move_rank", "move_target", "chain_dist", "animal_first"):
            M[k].update(r[k])
    return M


def majkel_one(line):
    g = json.loads(line)
    fp = IDX / g["date"] / "data" / f"{g['ep']}.json"
    if not fp.exists():
        return None
    rep = json.loads(fp.read_text())
    names = (rep.get("info") or {}).get("TeamNames") or []
    if "Majkel1337" not in names:
        return None
    seat = names.index("Majkel1337")
    steps = rep.get("steps") or []
    obs_seq = [steps[t - 1][seat].get("observation") for t in range(1, len(steps))]
    act_seq = [steps[t][seat].get("action") for t in range(1, len(steps))]
    return audit_game(obs_seq, act_seq, seat)


def k1_one(seed):
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model/v4_demand_race/harness")
    sys.path.insert(0, "/Users/a1-6/Desktop/PycharmProjects/DS_completation/.claude/worktrees/kaggriculture-setup-8e6892/kaggle_Kaggriculture/model/v16_online_fidelity")
    import engine
    import fidelity
    spec = importlib.util.spec_from_file_location(f"k1_audit_{seed}", HERE / "main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    opp = fidelity.make_agent(f"sub:{POOL}/packs/y68c_main.py")
    k = engine.load_kagsim()
    g = k.Game(seed=seed)
    obs_seq, act_seq = [], []
    fb = {"farmer": ["PASS"], "hands": [], "market": []}
    while not (g.done() if callable(g.done) else g.done):
        o0, o1 = g.observe(0), g.observe(1)
        a0 = mod.agent(o0)
        try:
            a1 = opp(o1)
        except Exception:
            a1 = dict(fb)
        obs_seq.append(o0)
        act_seq.append(a0)
        g.step(a0, a1)
    return audit_game(obs_seq, act_seq, 0)


def pct(c, keys=None):
    tot = sum(c.values()) or 1
    keys = keys or [k for k, _ in c.most_common()]
    return " ".join(f"{k}:{c.get(k, 0) / tot:.0%}" for k in keys)


def report(name, M):
    print(f"\n==================== {name}（{M['n']} 局）====================")
    print("A 各小时 工作/移动/PASS：")
    for h in (0, 2, 4, 6, 8, 12, 16, 20, 22, 23):
        c = M["hour"].get(h, Counter())
        tot = sum(c.values()) or 1
        print(f"   h{h:02d}: WORK {c['WORK'] / tot:.0%}  MOVE {c['MOVE'] / tot:.0%}  PASS {c['PASS'] / tot:.0%}")
    tot_all = Counter()
    for c in M["hour"].values():
        tot_all.update(c)
    t = sum(tot_all.values()) or 1
    print(f"   全天: WORK {tot_all['WORK'] / t:.1%} MOVE {tot_all['MOVE'] / t:.1%} PASS {tot_all['PASS'] / t:.1%} "
          f"| 移动/工作 {tot_all['MOVE'] / max(1, tot_all['WORK']):.2f}")
    c = M["carry"]
    off = c["off_shed"] or 1
    print(f"B 离仓单位持麦 {c['with_wheat'] / off:.0%}（均 {c['wheat_sum'] / max(1, c['with_wheat']):.1f}）"
          f" 持肥 {c['with_fert'] / off:.0%}（均 {c['fert_sum'] / max(1, c['with_fert']):.1f}）")
    p = M["pickup"]
    for item in ("WHEAT", "FERTILIZER"):
        n_ = p.get(item, 0)
        print(f"   PICKUP {item}: {n_ / M['n']:.0f} 次/局，每次均 {p.get(item + '_qty', 0) / max(1, n_):.1f}")
    print("C 工作类型（按天段）：")
    for seg in sorted(M["worktype"]):
        print(f"   {seg}: {pct(M['worktype'][seg])[:150]}")
    print(f"D 移动目标距离排名: {pct(M['move_rank'], ['0', '1', '2', '3+', 'none'])}")
    print(f"   目标类型: {pct(M['move_target'])}")
    print(f"E 连续工作格距: {pct(M['chain_dist'], ['0', '1', '2', '3', '4+'])}")
    print(f"F 动物格首动作: {pct(M['animal_first'])}")


def layout_report(M):
    print("\nG Majkel d12 布局模板（各格众数，前 3 字母）：")
    for y in range(10):
        row = []
        for x in range(10):
            c = M["layout"].get((x, y))
            row.append(c.most_common(1)[0][0][:3] if c else "   ")
        print("   " + " ".join(f"{v:>3s}" for v in row))


def main():
    n_mj = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    n_k1 = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    lines = []
    with open(V71 / "majkel_0910_12.jsonl") as f:
        for line in f:
            if '"date=2026-09-10"' in line[:200]:
                continue
            lines.append(line)
            if len(lines) >= n_mj:
                break
    with ProcessPoolExecutor(max_workers=8) as pool:
        mj = [r for r in pool.map(majkel_one, lines) if r]
        k1 = list(pool.map(k1_one, [1009 + 137 * i for i in range(n_k1)]))
    MJ, K1 = merge(mj), merge(k1)
    report("Majkel1337", MJ)
    report("K1", K1)
    layout_report(MJ)
    out = {"majkel_layout": {f"{p[0]},{p[1]}": dict(c) for p, c in MJ["layout"].items()}}
    (HERE / "kernel_audit_layout.json").write_text(json.dumps(out))


if __name__ == "__main__":
    main()
