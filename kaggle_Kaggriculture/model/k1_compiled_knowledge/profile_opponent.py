"""对手卡片流水线：任意队伍 → 结构化对手卡片 JSON（自动化框架的「新对手入口」）。

一条命令完成 v71 逆向五件套的核心取证：
  1. 从 replay 索引收集该队全部对局
  2. 录带 vs 反应式判别（跨局逐步动作重合、分叉步分布）
  3. 行为参数：雇工曲线、买地时点、卖出相位、卖肥门槛、开局签名
  4. 可收编性判定 + 最强局带导出（带类对手 → 可直接入 race 对手池）

用法:
  python profile_opponent.py <TeamName> [--out cards/] [--export-tape]
产出:
  cards/<team>.json         对手卡片
  cards/<team>_tape.json    最强一局的 719 步动作带（--export-tape，仅带类可靠）
"""
import argparse
import collections
import json
import statistics
from pathlib import Path

IDX = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture/model_data/kaggriculture_episodes_index")
PRODUCTS = ["WHEAT", "CARROT", "TOMATO", "STRAWBERRY", "MELON", "EGG", "MILK", "WOOL", "FERTILIZER"]


def collect(team, max_games=80):
    games = []
    for ddir in sorted(IDX.glob("date=*/data"), reverse=True):
        for fp in ddir.glob("*.json"):
            raw = fp.read_text()
            if team not in raw:
                continue
            try:
                rep = json.loads(raw)
            except Exception:
                continue
            names = (rep.get("info") or {}).get("TeamNames") or []
            if team not in names:
                continue
            seat = names.index(team)
            steps = rep.get("steps") or []
            if len(steps) < 700:
                continue
            acts = [steps[t][seat].get("action") or {} for t in range(1, len(steps))]
            ob0 = steps[0][seat].get("observation") or {}
            reward = steps[-1][seat].get("reward")
            over0 = (steps[1][seat].get("observation") or {}).get("remainingOverageTime")
            over1 = (steps[2][seat].get("observation") or {}).get("remainingOverageTime") if len(steps) > 2 else None
            games.append({"ep": fp.stem, "seat": seat, "acts": acts, "reward": reward,
                          "opp": names[1 - seat], "t0_overage": over0, "t1_overage": over1,
                          "date": ddir.parent.name})
            if len(games) >= max_games:
                return games
    return games


def unit_key(a):
    return json.dumps([a.get("farmer") or []] + list(a.get("hands") or []))


def profile(team, games):
    n = len(games)
    card = {"team": team, "n_games": n, "dates": sorted({g["date"] for g in games}),
            "rewards": {}, "verdict": {}, "behavior": {}}
    if not n:
        return card
    rw = [g["reward"] for g in games if isinstance(g["reward"], (int, float))]
    if rw:
        card["rewards"] = {"mean": round(statistics.mean(rw)), "median": round(statistics.median(rw)),
                           "max": round(max(rw)), "min": round(min(rw))}

    # ---- 录带判别：每步众数动作占比 + 首次分叉步 ----
    mode_share = {}
    for t in (0, 2, 5, 10, 24, 72, 144, 288, 500, 700):
        c = collections.Counter(unit_key(g["acts"][t]) for g in games if t < len(g["acts"]))
        mode_share[t] = round(c.most_common(1)[0][1] / n, 3) if c else None
    fork_steps = []
    for i in range(n):
        for j in range(i + 1, min(i + 4, n)):
            a, b = games[i]["acts"], games[j]["acts"]
            for t in range(min(len(a), len(b))):
                if unit_key(a[t]) != unit_key(b[t]):
                    fork_steps.append(t)
                    break
    card["verdict"] = {
        "mode_share_by_step": mode_share,
        "median_fork_step": statistics.median(fork_steps) if fork_steps else None,
        # 分叉晚+众数占比高 → 录带/半录带（可收编）；早分叉 → 自适应（免疫抄带，t144 同质步的高重合不算）
        "is_tape_like": bool(fork_steps and statistics.median(fork_steps) >= 144
                             and mode_share.get(288, 0) and mode_share[288] >= 0.8),
        "is_adaptive": bool(fork_steps and statistics.median(fork_steps) < 24),
    }
    # 开局重计算指纹（Majkel 式 t0 长思考）
    o0 = [g["t0_overage"] for g in games if g.get("t0_overage") is not None]
    o1 = [g["t1_overage"] for g in games if g.get("t1_overage") is not None]
    if o0 and o1:
        card["verdict"]["t0_think_seconds"] = round(statistics.median(o0) - statistics.median(o1), 1)

    # ---- 行为参数 ----
    hire_by_day = collections.defaultdict(list)
    land_turns = collections.defaultdict(list)
    sell_phase = {p: collections.Counter() for p in PRODUCTS}
    sell_qty = collections.Counter()
    for g in games:
        nland = 0
        hires_today = 0
        for t, a in enumerate(g["acts"]):
            day, hour = t // 24, t % 24
            if hour == 0:
                hires_today = 0
            for o in a.get("market") or []:
                if not o:
                    continue
                if o[0] == "HIRE":
                    hires_today += 1
                elif o[0] == "BUY_LAND":
                    nland += 1
                    land_turns[nland].append(t)
                elif o[0] == "SELL" and len(o) >= 3 and o[1] in sell_phase:
                    sell_phase[o[1]][t % 4] += 1
                    sell_qty[o[1]] += o[2] if isinstance(o[2], (int, float)) else 0
            if hour == 23:
                hire_by_day[day].append(hires_today)
    card["behavior"]["hires_by_day"] = {d: round(statistics.mean(v), 1)
                                        for d, v in sorted(hire_by_day.items()) if v}
    card["behavior"]["land_buy_turn_median"] = {k: statistics.median(v)
                                                for k, v in sorted(land_turns.items())}
    card["behavior"]["sell_phase_pref"] = {
        p: {"dominant_phase": c.most_common(1)[0][0], "share": round(c.most_common(1)[0][1] / sum(c.values()), 2)}
        for p, c in sell_phase.items() if sum(c.values()) >= 8}
    card["behavior"]["sell_qty_total_mean"] = {p: round(q / n, 1) for p, q in sell_qty.most_common()}

    # ---- 收编建议 ----
    v = card["verdict"]
    if v.get("is_adaptive"):
        card["recommendation"] = "ADAPTIVE_IMMUNE: 抄带无效；切片只作考官；把 behavior 参数写入反制配置"
    elif v.get("is_tape_like"):
        card["recommendation"] = "TAPE_LIKE: 常态带可收编；front_run 预测表可装填"
    else:
        card["recommendation"] = "HYBRID: 段级马赛克候选；先跨 seed 复验切片稳定性"
    return card


def export_tape(games, out_fp):
    best = max((g for g in games if isinstance(g["reward"], (int, float))),
               key=lambda g: g["reward"], default=None)
    if best:
        out_fp.write_text(json.dumps(best["acts"]))
        return best["ep"], best["reward"]
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("team")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "cards"))
    ap.add_argument("--export-tape", action="store_true")
    ap.add_argument("--max-games", type=int, default=80)
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(exist_ok=True)
    games = collect(args.team, args.max_games)
    card = profile(args.team, games)
    if args.export_tape and games:
        ep, rw = export_tape(games, out / f"{args.team}_tape.json")
        card["exported_tape"] = {"ep": ep, "reward": rw}
    fp = out / f"{args.team}.json"
    fp.write_text(json.dumps(card, indent=2, ensure_ascii=False))
    print(json.dumps(card, indent=2, ensure_ascii=False))
    print(f"\ncard -> {fp}")


if __name__ == "__main__":
    main()
