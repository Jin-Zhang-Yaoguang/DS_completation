"""每日母带再生成管线（V41 时代版）：
拉在役提交的新 replay → 提取强对手带 → 单人产出验证 → 与带库家族比对 → 候选报告。

用法：python3 rebirth.py <label:submission_id> [<label:sid> ...]
不自动提交、不自动换血——只产出候选清单与推荐动作，决策留给主会话/人。

判定标准（2026-09-06 校准）：
- 候选门槛：对手 bank>95k（对战口径）且带单人产出（tape: 口径,3 seed）min>=197k；
- 家族新颖性：与带库(tapes/)所有带的前 300 步动作重合率 <60% 才算新家族；
- 推荐换血：单人产出 >198.5k（超 fam_F 代差）或新家族且矩阵试打不弱于 V41。
"""
import collections
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
M = HERE.parent
TAPES = M / "v16_online_fidelity" / "tapes"
FID = M / "v16_online_fidelity"
ROOT = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture")
ME = "datatuu"
sys.path.insert(0, str(HERE))
from daily import fetch  # 复用增量下载

BANK_FLOOR = 95000.0
SOLO_FLOOR = 197000.0
NOVEL_MAX_OVERLAP = 0.60


def norm_actions(steps, seat, n=720):
    out = []
    for t in range(n):
        a = (steps[t + 1][seat].get("action") if t + 1 < len(steps) else None) or {}
        out.append({"farmer": a.get("farmer") or ["PASS"], "hands": a.get("hands") or [],
                    "market": a.get("market") or []})
    return out


def overlap(a, b, n=300):
    sa = [json.dumps(x, sort_keys=True) for x in a[:n]]
    sb = [json.dumps(x, sort_keys=True) for x in b[:n]]
    return sum(x == y for x, y in zip(sa, sb)) / n


def solo_bank(tape_path):
    r = subprocess.run([sys.executable, "sweep_seeds.py", f"tape:{tape_path}", "101,202,303"],
                       cwd=FID, capture_output=True, text=True, timeout=1800)
    banks = [json.loads(l)["bank"] for l in r.stdout.strip().splitlines() if l.strip()]
    return min(banks) if banks else 0.0


def main():
    lib = {}
    for f in TAPES.glob("*.json"):
        try:
            lib[f.stem] = json.load(open(f))["actions"]
        except Exception:
            pass
    print(f"带库 {len(lib)} 条")

    cands = {}
    for arg in sys.argv[1:]:
        label, sid = arg.split(":")
        tgt = fetch(label, sid)
        for f in tgt.glob("episode-*-replay.json"):
            try:
                d = json.load(open(f))
            except Exception:
                continue
            names = [n.strip() for n in d["info"]["TeamNames"]]
            if ME not in names:
                continue
            st = d["steps"]
            opp = 1 - names.index(ME)
            bank = st[-1][opp]["reward"]
            if bank is None or bank < BANK_FLOOR:
                continue
            acts = norm_actions(st, opp)
            h = hashlib.md5(json.dumps(acts[:300], sort_keys=True).encode()).hexdigest()[:10]
            if h not in cands or bank > cands[h]["bank"]:
                cands[h] = {"bank": bank, "team": names[opp], "acts": acts, "seed": d["info"]["seed"]}

    print(f"强对手带候选 {len(cands)} 条（bank>{BANK_FLOOR:.0f}）")
    report = []
    for h, c in sorted(cands.items(), key=lambda kv: -kv[1]["bank"]):
        best_name, best_ov = max(((k, overlap(c["acts"], v)) for k, v in lib.items()),
                                 key=lambda kv: kv[1], default=("-", 0.0))
        novel = best_ov < NOVEL_MAX_OVERLAP
        fn = TAPES / f"rb_{h}.json"
        json.dump({"team": c["team"], "hash": h, "seed": c["seed"], "actions": c["acts"]}, open(fn, "w"))
        solo = solo_bank(fn)
        keep = solo >= SOLO_FLOOR
        if not keep:
            fn.unlink()
        verdict = ("推荐换血评估" if keep and (solo > 198500 or novel)
                   else "入库备用" if keep else "淘汰")
        row = (f"{h} {c['team'][:18]:18s} 对战bank={c['bank']:>8.0f} 单人={solo:>8.0f} "
               f"最近家族={best_name[:22]}({best_ov:.0%}) {'新家族' if novel else '已知系'} -> {verdict}")
        print(row)
        report.append(row)

    out = HERE / "rebirth_report.md"
    from datetime import date
    with open(out, "a") as fh:
        fh.write(f"\n## {date.today()}\n" + "\n".join(report or ["(无候选)"]) + "\n")
    print(f"报告追加至 {out}")


if __name__ == "__main__":
    main()
