"""看板推送助手:把各刀 history.jsonl 未推送的代转成 write_db batch(<=50 条)JSON 打印到 stdout。
全局序号 seq 从 SEQ0(structv3 gen799 = 969)续编;游标存 monitor/pushed.json。
用法: python monitor/push_pending.py            # 打印待推 batch
      python monitor/push_pending.py --commit   # 推送成功后调用,推进游标
"""
import json, sys
from pathlib import Path
V = Path(__file__).resolve().parents[1]
SEQ0 = 1170  # 2026-09-13 第二轮:接续第一轮最后 seq(g1169),避免覆盖旧记录
CUR = V / "monitor" / "pushed.json"
st = json.loads((V / "runs/_funsearch/state.json").read_text())
runs = [k["run"] for k in st["knives"]] + ([st["current"]["run"]] if st.get("current") else [])
rows = []
for r in runs:
    p = V / "runs" / r / "history.jsonl"
    if p.exists():
        rows += [json.loads(l) for l in p.open()]
cur = json.loads(CUR.read_text()) if CUR.exists() else {"pushed": 0}
pend = rows[cur["pushed"]:cur["pushed"] + 50]
writes = []
for i, r in enumerate(pend):
    seq = SEQ0 + cur["pushed"] + i
    d = {"seq": seq, "gen": r["gen"], "run": r["run"], "best_avg": round(r["best_avg"]), "best_min": round(r["best_min"]),
         "pop_mean": round(r["pop_mean"]), "seed_epoch": r["seed_epoch"], "champ_train": round(r["champ_train"]),
         "crown": r["crown"]}
    if "valid_avg" in r:
        d["valid_avg"] = round(r["valid_avg"])
    if "valid_t" in r:
        d["valid_t"] = round(r["valid_t"], 2)
    writes.append({"op": "set", "collection": "history", "doc_id": f"g{seq:04d}", "data": d})
PEND = V / "monitor" / "pending_count.json"
if "--commit" in sys.argv:
    n = json.loads(PEND.read_text())["n"] if PEND.exists() else 0
    cur["pushed"] += n; CUR.write_text(json.dumps(cur)); PEND.write_text(json.dumps({"n": 0}))
    print("cursor ->", cur["pushed"]); sys.exit()
PEND.write_text(json.dumps({"n": len(pend)}))
print(json.dumps(writes, ensure_ascii=False))
print(f"# pending {len(pend)} of {len(rows) - cur['pushed']} (seq {SEQ0 + cur['pushed']}..)", file=sys.stderr)
