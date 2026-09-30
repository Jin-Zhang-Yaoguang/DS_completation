"""从官方 top episodes 快照提取 top 队伍路线并做代差判定（预注册协议）。

判定协议（2026-08-20 预注册）：
1. 固定路线族：同一队伍 ≥3 场 replay，两两 field 动作一致率 ≥99% 且 market ≥95%；
2. 收敛新一代：top 10 固定路线族中 ≥60% 共享同一 field hash；
3. 代差：该收敛路线与 V8 Kawa 路线逐回合 field 差异 >50 回合 → 吸收进 v10。
否则维持 v8。
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "..", "model_data", "top_replays_0819"))

# 当前 top 10（2026-08-20 排行榜快照），用于优先匹配
TOP_TEAMS = ["tetsuya", "Ryo Hasegawa", "カワシギ", "Arman Tuganbaev", "ReCurSiON",
             "Xiaowenhao404", "Kobe BRYANT", "Galaxantic", "u", "Efe Can Celiksoy"]


def find_replays():
    return sorted(glob.glob(os.path.join(DATA, "**", "*.json"), recursive=True),
                  key=lambda p: os.path.getsize(p), reverse=True)


def load_replay(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def extract_trace(d, seat):
    """提取某 seat 的 719 步 (field, market) 动作指纹。"""
    field, market = [], []
    for st in (d.get("steps") or [])[:719]:
        if not isinstance(st, list) or seat >= len(st):
            field.append(None); market.append(None); continue
        a = (st[seat] or {}).get("action") or {}
        field.append(json.dumps([a.get("farmer"), a.get("hands")], sort_keys=True))
        market.append(json.dumps(a.get("market"), sort_keys=True))
    return field, market


def agree_rate(a, b):
    if not a or not b:
        return 0.0
    n = min(len(a), len(b))
    return sum(1 for i in range(n) if a[i] == b[i]) / n


def main():
    files = find_replays()
    print("replay files:", len(files))
    team_traces = defaultdict(list)
    scanned = 0
    for p in files:
        d = load_replay(p)
        if not d:
            continue
        names = (d.get("info") or {}).get("TeamNames") or []
        if len(names) < 2:
            continue
        scanned += 1
        for seat in (0, 1):
            team_traces[names[seat]].append((extract_trace(d, seat), p))
        if scanned % 50 == 0:
            print(f"scanned {scanned}, teams {len(team_traces)}", flush=True)
    print("total scanned:", scanned, "teams:", len(team_traces))

    # 1. 固定路线族判定
    stable = {}
    for team, lst in team_traces.items():
        if len(lst) < 3:
            continue
        fs = [t[0][0] for t in lst[:5]]
        ms = [t[0][1] for t in lst[:5]]
        rates_f, rates_m = [], []
        for i in range(len(fs)):
            for j in range(i + 1, len(fs)):
                rates_f.append(agree_rate(fs[i], fs[j]))
                rates_m.append(agree_rate(ms[i], ms[j]))
        if min(rates_f) >= 0.99 and min(rates_m) >= 0.95:
            stable[team] = (fs[0], ms[0], len(lst))
    print("stable route families:", len(stable))
    for t in TOP_TEAMS:
        print(f"  {'YES' if t in stable else 'no '} {t} ({len(team_traces.get(t, []))} replays)")

    # 2. 收敛判定
    hashes = Counter()
    for team in TOP_TEAMS:
        if team in stable:
            hashes[hashlib.sha256(stable[team][0][-1].encode()).hexdigest()[:16]] += 1
    converged = False
    top_hash = None
    if hashes:
        top_hash, cnt = hashes.most_common(1)[0]
        n_stable_top = sum(1 for t in TOP_TEAMS if t in stable)
        print(f"convergence: top stable hash {top_hash} shared by {cnt}/{n_stable_top}")
        converged = n_stable_top >= 3 and cnt / n_stable_top >= 0.6
    else:
        print("convergence: no stable top families")

    # 3. 与 V8 Kawa 差异
    target_team = None
    if converged:
        for t in TOP_TEAMS:
            if t in stable and hashlib.sha256(stable[t][0][-1].encode()).hexdigest()[:16] == top_hash:
                target_team = t
                break
    elif any(t in stable for t in TOP_TEAMS):
        target_team = next(t for t in TOP_TEAMS if t in stable)
    if target_team:
        field, market, n = stable[target_team]
        sys.path.insert(0, os.path.join(HERE, "..", "v8_kawa_lead2_slot"))
        for m in ("base_agent", "v1_fallback", "routes"):
            sys.modules.pop(m, None)
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "v8m", os.path.join(HERE, "main.py"))
        v8 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(v8)
        kawa = v8._ACTIONS_8C6S_3Q
        diff = sum(1 for i in range(min(719, len(kawa)))
                   if json.dumps([kawa[i].get("farmer"), kawa[i].get("hands")],
                                 sort_keys=True) != field[i])
        print(f"field diff vs Kawa(8c6s): {diff}/719 turns (team={target_team})")
        print("VERDICT:", "NEW_GENERATION" if diff > 50 else "SAME_GENERATION")
        out = os.path.join(HERE, "top_route_candidate.json")
        json.dump({"team": target_team, "field": field, "market": market,
                   "diff_vs_kawa": diff}, open(out, "w"))
        print("saved:", out)
    else:
        print("VERDICT: NO_STABLE_TOP_ROUTE")


if __name__ == "__main__":
    main()
