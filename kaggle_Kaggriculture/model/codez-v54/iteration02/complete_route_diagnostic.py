"""Complete all 41 existing routes for the four unresolved fixed-tape cases."""
import concurrent.futures
import json
from pathlib import Path
import route_diagnostic as lab

P = Path(__file__).resolve().parent


def main():
    manifest = P / "complete_route_diagnostic_manifest.json"
    prior_path = P / "route_diagnostic.jsonl"
    prior = [json.loads(s) for s in prior_path.read_text().splitlines()]
    groups = {}
    for row in prior:
        assert row["status"] == "ok"
        groups.setdefault(row["job"]["episode_id"], []).append(row)
    ids = sorted(eid for eid, rows in groups.items() if max(r["margin"] for r in rows) <= 0)
    _, ns = lab.research.load(lab.research.ROOT / "versions/v003/main.py")
    routes = sorted(ns["_IMPL"].chassis.routes)
    assert len(routes) == 41 and len(ids) == 4
    known = {(r["job"]["episode_id"], r["job"]["route"]) for r in prior}
    jobs = [dict(episode_id=eid, route=rid) for eid in ids for rid in routes if (eid, rid) not in known]
    if not manifest.exists():
        files = ["iteration02/complete_route_diagnostic.py", "iteration02/route_diagnostic.py", "iteration02/route_diagnostic.jsonl", "research.py", "research_official.py", "versions/v003/main.py"]
        files += [f"iteration02/tapes/{eid}.json" for eid in ids]
        manifest.write_text(json.dumps(dict(jobs=jobs, routes=routes, hashes={f:lab.research.digest(lab.research.ROOT/f) for f in files}, scope="Hindsight existing-route screen against fixed requests; neither online wins nor a deployable router."), indent=2))
    spec = json.loads(manifest.read_text())
    assert spec["jobs"] == jobs
    for f, digest in spec["hashes"].items():
        assert lab.research.digest(lab.research.ROOT/f) == digest
    output = P / "complete_route_diagnostic.jsonl"
    done = {}
    if output.exists():
        for line in output.read_text().splitlines():
            row = json.loads(line); key = json.dumps(row["job"], sort_keys=True)
            assert key not in done; done[key] = row
    pending = [j for j in jobs if json.dumps(j, sort_keys=True) not in done]
    with output.open("a") as f, concurrent.futures.ProcessPoolExecutor(2) as ex:
        for row in ex.map(lab.one, pending):
            f.write(json.dumps(row)+"\n"); f.flush()
            done[json.dumps(row["job"], sort_keys=True)] = row
            if len(done)%10 == 0: print("remaining-route checks", len(done), "/", len(jobs), flush=True)
    assert len(done) == len(jobs) and all(r["status"] == "ok" for r in done.values())
    summary = {"complete": True, "errors": 0, "scope": spec["scope"], "episodes": []}
    for eid in ids:
        rows = groups[eid] + [r for r in done.values() if r["job"]["episode_id"] == eid]
        assert sorted(r["job"]["route"] for r in rows) == routes
        best = max(rows, key=lambda r:r["margin"])
        summary["episodes"].append(dict(episode_id=eid, routes_tested=len(rows), best_route=best["job"]["route"], best_margin=best["margin"], winning_routes=[r["job"]["route"] for r in rows if r["margin"]>0]))
    (P/"complete_route_diagnostic.summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__": main()
