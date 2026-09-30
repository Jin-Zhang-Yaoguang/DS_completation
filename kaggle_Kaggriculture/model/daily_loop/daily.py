"""每日快循环：拉在役提交的线上局 → 增量下载 replay → 家族聚类 → 战绩分解报告。

用法：python daily.py <label:submission_id> [<label:sid> ...]
输出：model_data/<label>/ 下增量 replay + 本目录 report_<date>.md
"""
import json, sys, subprocess, hashlib, collections, csv, glob, time
from datetime import date
from pathlib import Path

KAGGLE = "/Users/a1-6/.local/bin/kaggle"
ROOT = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture")
HERE = Path(__file__).resolve().parent
ME = "datatuu"
KNOWN = {"c333c13954": "扰动B", "fba802dce0": "扰动C", "9bdce54945": "高产A", "30e869f37d": "高产D",
         "dea7027bc9": "高产E", "d64342e748": "跟随W", "73e88e3c7a": "跟随X", "4a983c01db": "家族4a98",
         "ff71bda897": "新强F", "b55af2d9c3": "新强G", "ceb73997da": "扰动H"}

def sh(args):
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True)

def fetch(label, sid):
    r = sh([KAGGLE, "competitions", "episodes", str(sid), "--format", "json"])
    t = r.stdout; rows = json.loads(t[:t.rfind("]") + 1])
    ids = [int(x["id"]) for x in rows if "COMPLETED" in x.get("state", "") and "PUBLIC" in x.get("type", "")]
    tgt = ROOT / "model_data" / label / "replays"; tgt.mkdir(parents=True, exist_ok=True)
    todo = [e for e in ids if not (tgt / f"episode-{e}-replay.json").exists()]
    print(f"{label}: {len(ids)} public, {len(todo)} new", flush=True)
    backoff = 5
    while todo:
        e = todo[0]
        r = sh([KAGGLE, "competitions", "replay", str(e), "--path", str(tgt), "--quiet"])
        if r.returncode == 0 and (tgt / f"episode-{e}-replay.json").exists():
            todo.pop(0); backoff = 5; time.sleep(0.7)
        else:
            time.sleep(backoff); backoff = min(backoff * 2, 120)
    return tgt

def lb_ranks():
    d = HERE / "lb"; d.mkdir(exist_ok=True)
    sh([KAGGLE, "competitions", "leaderboard", "kaggriculture", "--download", "-p", str(d)])
    for z in d.glob("*.zip"):
        subprocess.run(["unzip", "-o", "-q", str(z), "-d", str(d / "x")])
    out = {}
    for p in sorted((d / "x").glob("*.csv")):
        for r0 in csv.DictReader(open(p, encoding="utf-8-sig")):
            out[r0["TeamName"].strip()] = (int(r0["Rank"]), float(r0["Score"]))
    return out

def analyze(label, tgt, lb, lines):
    rows = []
    for f in tgt.glob("episode-*-replay.json"):
        try: d = json.load(open(f))
        except Exception: continue
        st = d["steps"]; names = d["info"]["TeamNames"]
        try: me = names.index(ME)
        except ValueError: continue
        opp = 1 - me
        h = hashlib.md5(json.dumps([st[t + 1][opp].get("action") for t in range(300)], sort_keys=True).encode()).hexdigest()[:10]
        mk0 = (st[1][opp].get("action") or {}).get("market") or []
        pert = any(o and o[0] == "BUY_PRODUCT" and len(o) > 2 and isinstance(o[2], (int, float)) and o[2] >= 20 for o in mk0)
        r_me = st[-1][me]["reward"]; r_opp = st[-1][opp]["reward"]
        rows.append({"h": h, "pert": pert, "opp": names[opp].strip(),
                     "res": "W" if r_me > r_opp else ("L" if r_me < r_opp else "D"), "m": r_me - r_opp})
    n = len(rows); W = sum(r["res"] == "W" for r in rows)
    lines.append(f"\n## {label}: n={n} wr={W/max(1,n):.1%}")
    for name, sel in (("对手扰动型", [r for r in rows if r["pert"]]), ("对手无扰动", [r for r in rows if not r["pert"]])):
        if sel:
            lines.append(f"- {name}: n={len(sel)} wr={sum(r['res']=='W' for r in sel)/len(sel):.1%} margin={sum(r['m'] for r in sel)/len(sel):+.0f}")
    cl = collections.defaultdict(list)
    for r in rows: cl[r["h"]].append(r)
    lines.append("- 已知家族: " + "; ".join(
        f"{KNOWN[h]}={sum(r['res']=='W' for r in rs)}W{sum(r['res']=='L' for r in rs)}L"
        for h, rs in sorted(cl.items()) if h in KNOWN and rs) or "-")
    alerts = [(h, rs) for h, rs in cl.items() if h not in KNOWN and len(rs) >= 3 and sum(r["res"] == "L" for r in rs) / len(rs) >= 0.5]
    for h, rs in alerts:
        r0 = rs[0]; rk = lb.get(r0["opp"], (None,))[0]
        lines.append(f"- ⚠️ 新威胁家族 {h}: n={len(rs)} W/L={sum(r['res']=='W' for r in rs)}/{sum(r['res']=='L' for r in rs)} "
                     f"margin={sum(r['m'] for r in rs)/len(rs):+.0f} 例={r0['opp']}(rank {rk}) pert={sum(r['pert'] for r in rs)}")
    return rows

if __name__ == "__main__":
    lb = lb_ranks()
    my = lb.get(ME); lines = [f"# 每日线上复盘 {date.today()}", f"\n当前排名: {my[0]} 分数: {my[1]}" if my else ""]
    for job in sys.argv[1:]:
        label, sid = job.split(":")
        tgt = fetch(label, sid)
        analyze(label, tgt, lb, lines)
    lines.append("\n> 换血预案：对新威胁家族先跑 `sweep_seeds` 测其带单人产出；若 >195k 且我方在役底盘 <其-5k，"
                 "按 v26_f_base/build.py 流程当天换母带（发现→门控→上线 ~2h）。")
    out = HERE / f"report_{date.today()}.md"
    out.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nwritten: {out}")
