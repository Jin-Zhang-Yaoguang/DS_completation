"""每日巡视(触发器 1/3/4/5/7 的数据采集):
1 数据同步+侦察 | 3 自身战报 | 4 社区 kernel 动态 | 5 生态位移 | 7 反制迹象(嵌在 3)
产出 patrol_report_<date>.md,供会话分析并给触发建议。
"""
import json, re, subprocess, sys, statistics
from datetime import datetime, timezone
from pathlib import Path
from collections import Counter, defaultdict

HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
ROOT = Path("/Users/a1-6/Desktop/PycharmProjects/DS_completation/kaggle_Kaggriculture")
IDX = ROOT / "model_data" / "kaggriculture_episodes_index"
KAGGLE = "/Users/a1-6/.local/bin/kaggle"
T = MODEL / "v16_online_fidelity" / "tapes"
POOL = MODEL / "opponent_pool_v1"
STATE = HERE / "patrol_state.json"
today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
rep = [f"# 每日巡视报告 {today} (UTC)\n"]
state = json.loads(STATE.read_text()) if STATE.exists() else {}

def run(cmd, timeout=1800):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)

# ---------- 1. 数据同步 ----------
r = run(["/opt/anaconda3/bin/python3", str(ROOT / "model_data" / "sync_kaggriculture_index.py")])
rep.append("## 1 数据同步\n```\n" + (r.stdout or r.stderr)[-600:] + "\n```\n")

# ---------- 3. 自身战报 ----------
def sig(acts, a=0, b=144):
    return [json.dumps({"f": x.get("farmer"), "h": x.get("hands")}, sort_keys=True) for x in acts[a:b]]
r = run([KAGGLE, "competitions", "submissions", "-c", "kaggriculture", "-v"])
subs = []
for line in r.stdout.strip().split("\n")[1:3]:
    parts = line.split(",")
    if len(parts) >= 2:
        subs.append(parts[0])
rep.append(f"## 3 自身战报(最近 2 提交 slot: {subs})\n")
rep.append("```\n" + "\n".join(r.stdout.strip().split("\n")[:4]) + "\n```\n")
losses_detail = []
for sid in subs:
    try:
        er = run([KAGGLE, "competitions", "episodes", str(sid), "--format", "json"])
        raw = er.stdout
        eps = json.loads(raw[raw.index("["):raw.rindex("]") + 1])
        done = [e["id"] for e in eps if "COMPLETED" in str(e.get("state"))]
        seen = set(state.get("seen_eps", []))
        new = [e for e in done if e not in seen]
        rep.append(f"- 提交 {sid}: 总局 {len(eps)}, 新完成 {len(new)}\n")
        wins = loss = 0
        rdir = Path(__file__).resolve().parent / "replays"
        rdir.mkdir(parents=True, exist_ok=True)
        for eid in new[:60]:
            # 2026-09-14 修复(用户授权):官方索引不含己方对局(入选线 avgElo~2950),
            # 改为用 kaggle CLI 直接拉取自己的 replay(串行,避免限流)。
            p = rdir / f"episode-{eid}-replay.json"
            if not p.exists():
                run([KAGGLE, "competitions", "replay", str(eid), "--path", str(rdir), "--quiet"], timeout=120)
            if not p.exists():
                continue
            g = json.load(open(p))
            names = (g.get("info") or {}).get("TeamNames") or []
            if "datatuu" not in names:
                continue
            seat = names.index("datatuu")
            rw = g.get("rewards") or [0, 0]
            if (rw[seat] or 0) > (rw[1 - seat] or 0):
                wins += 1
            else:
                loss += 1
                losses_detail.append((sid, eid, names[1 - seat], (rw[seat] or 0) - (rw[1 - seat] or 0)))
            seen.add(eid)
        state["seen_eps"] = list(seen)[-3000:]
        if wins + loss:
            rep.append(f"  本地可析新局 {wins}W{loss}L(胜率 {wins/(wins+loss):.0%})\n")
    except Exception as e:
        rep.append(f"- 提交 {sid}: 战报拉取失败 {e}\n")
if losses_detail:
    rep.append("### 新输局清单(触发 3/7 分析对象)\n")
    for sid, eid, opp, d in sorted(losses_detail, key=lambda r: r[3])[:12]:
        rep.append(f"- sub{sid} ep{eid} vs {opp}: {d:+.0f}\n")
    big = [l for l in losses_detail if l[3] < -10000]
    if big:
        rep.append(f"**警报:大崩局 {len(big)} 场(>10k)——触发 3 优先归因**\n")

# ---------- 4. 社区动态 ----------
r = run([KAGGLE, "kernels", "list", "--competition", "kaggriculture", "--sort-by", "dateCreated", "-p", "1", "--page-size", "20"])
lines = r.stdout.strip().split("\n")[2:]
known = set(state.get("known_kernels", []))
new_k = []
for l in lines:
    ref = l.split()[0] if l.split() else ""
    if ref and ref not in known:
        new_k.append(l[:110])
        known.add(ref)
state["known_kernels"] = list(known)[-500:]
rep.append("## 4 社区新 kernel(自上次巡视)\n")
rep.append("```\n" + ("\n".join(new_k) if new_k else "无新增") + "\n```\n")
v_series = [l for l in new_k if "ahmedberatozer" in l or re.search(r"[Vv]3[89]|[Vv]4\d", l)]
if v_series:
    rep.append(f"**警报:疑似 V 系列/高版本更新 {len(v_series)} 条——触发 4 底盘换代评估**\n")

# ---------- 1+5. 侦察与生态位移 ----------
latest = sorted(IDX.glob("date=*/data"))[-1]
bases = {}
for nm, p in (("yhay", T / "pub_yhay_0.json"), ("t955", T / "pub_t955_0.json")):
    bases[nm] = sig(json.load(open(p))["actions"])
v38r0 = json.load(open(HERE.parent / "opponent_pool_v1" / "tapes" / "ult_normal.json"))
bases["ult"] = sig(v38r0["actions"])
fam_c = Counter(); hi = []
files = sorted(latest.glob("*.json"))
for fp in files:
    try:
        g = json.load(open(fp))
    except Exception:
        continue
    steps = g.get("steps") or []
    if len(steps) < 700:
        continue
    names = (g.get("info") or {}).get("TeamNames") or ["?", "?"]
    rw = g.get("rewards") or [0, 0]
    for seat in (0, 1):
        if (rw[seat] or 0) < 120000:
            continue
        acts = []
        for t in range(1, len(steps)):
            a = steps[t][seat].get("action") or {}
            acts.append({"farmer": a.get("farmer") or ["PASS"], "hands": a.get("hands") or []})
        s = sig(acts)
        fam, ov = max(((n, sum(x == y for x, y in zip(s, b)) / 144) for n, b in bases.items()), key=lambda kv: kv[1])
        lab = fam if ov >= 0.6 else "NEW/other"
        fam_c[lab] += 1
        hi.append((rw[seat], str(names[seat]), lab))
rep.append(f"## 1+5 侦察({latest.parent.name},高产席位 {sum(fam_c.values())})\n")
rep.append(f"- 家族分布: {dict(fam_c)}\n")
prev = state.get("fam_dist", {})
if prev:
    diffs = {k: fam_c.get(k, 0) - prev.get(k, 0) for k in set(fam_c) | set(prev)}
    rep.append(f"- 与上次巡视 diff: {diffs}\n")
state["fam_dist"] = dict(fam_c)
hi.sort(reverse=True)
rep.append("- top8 高产: " + ", ".join(f"{n}({int(b/1000)}k,{l})" for b, n, l in hi[:8]) + "\n")

STATE.write_text(json.dumps(state))
out = HERE / f"patrol_report_{today}.md"
out.write_text("".join(rep))
print(str(out))
print("".join(rep)[:3000])
