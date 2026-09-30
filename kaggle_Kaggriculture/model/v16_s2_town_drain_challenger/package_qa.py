"""Raw-loader and two-seat smoke QA for the V16 archive."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
import sys
import tarfile
from tempfile import TemporaryDirectory


HERE = Path(__file__).resolve().parent
SEEDS = (93451031, 93451032)


def qa() -> dict:
    from kaggle_environments import make
    from kaggle_environments.agent import get_last_callable

    games = []
    with TemporaryDirectory(prefix="v16_s2_qa_") as directory:
        root = Path(directory)
        with tarfile.open(HERE / "submission.tar.gz", "r:gz") as tar:
            tar.extractall(root, filter="data")
        source = (root / "main.py").read_text(encoding="utf-8")
        for seed in SEEDS:
            for seat in (0, 1):
                for name in [key for key in list(sys.modules) if key.startswith("kaggle_agent_")]:
                    sys.modules.pop(name, None)
                handle = get_last_callable(source, path=str(root / "main.py"))
                calls = 0

                def traced(obs, configuration=None):
                    nonlocal calls
                    calls += 1
                    return handle(obs, configuration)

                agents = [traced, "random"] if seat == 0 else ["random", traced]
                stdout, stderr = StringIO(), StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    steps = make("kaggriculture", configuration={"seed": seed}, debug=False).run(agents)
                final = steps[-1]
                games.append({
                    "seed": seed,
                    "seat": seat,
                    "steps": len(steps),
                    "calls": calls,
                    "statuses": [str(state.status) for state in final],
                    "rewards": [float(state.reward or 0) for state in final],
                    "stdout": stdout.getvalue(),
                    "stderr": stderr.getvalue(),
                })
    checks = {
        "four_games": len(games) == 4,
        "all_done": all(row["steps"] == 720 and row["calls"] == 719 and row["statuses"] == ["DONE", "DONE"] for row in games),
        "zero_output": all(not row["stdout"] and not row["stderr"] for row in games),
    }
    result = {"candidate": "v16_s2_town_drain_challenger", "games": games, "checks": checks,
              "verdict": "PASS" if all(checks.values()) else "FAIL"}
    (HERE / "package_qa_report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    result = qa()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(result["verdict"] != "PASS")
