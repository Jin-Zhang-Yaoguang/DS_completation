"""收官报告:各刀代数/验证触发/登基/验收,最佳配对差候选,写 runs/_funsearch/final_report.json 并打印。"""
import json, statistics
from pathlib import Path
V = Path(__file__).resolve().parents[1]
st = json.loads((V / "runs/_funsearch/state.json").read_text())
rows_all = []
report = {"budget_gens": st["budget_gens"], "baseline": {k: st["baseline"][k] for k in ("source", "holdout_avg", "valid_avg")}, "knives": []}
for k in st["knives"]:
    run = k["run"]; rows = [json.loads(l) for l in (V / "runs" / run / "history.jsonl").open()]
    rows_all += rows
    vt = [r for r in rows if "valid_avg" in r]
    best_v = max(vt, key=lambda r: r.get("valid_t", -9)) if vt else None
    report["knives"].append({"run": run, "gens": len(rows), "valid_triggers": len(vt), "crowns": sum(r["crown"] for r in rows),
                             "best_valid_t": round(best_v["valid_t"], 2) if best_v and "valid_t" in best_v else None,
                             "best_valid_avg": round(best_v["valid_avg"]) if best_v else None,
                             "accepted": k["accepted"], "reason": k["reason"],
                             "holdout": {kk: (round(k[kk], 2) if isinstance(k[kk], float) else k[kk]) for kk in ("diff", "t", "wins") if kk in k}})
report["used_gens"] = len(rows_all)
report["valid_triggers_total"] = sum(1 for r in rows_all if "valid_avg" in r)
report["crowns_total"] = sum(r["crown"] for r in rows_all)
report["train_best_overall"] = round(min(r["best_avg"] for r in rows_all) * -1 * -1)
report["train_best_max"] = round(max(r["best_avg"] for r in rows_all))
(V / "runs/_funsearch/final_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False))
print(json.dumps(report, indent=1, ensure_ascii=False))
