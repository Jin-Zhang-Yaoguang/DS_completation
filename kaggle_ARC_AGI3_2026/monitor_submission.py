"""用 Kaggle CLI 跟踪一次正式提交，并原子更新 status.json。"""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import time


ROOT = Path(__file__).resolve().parent
STATUS_PATH = ROOT / "status.json"
CLI = "/Users/a1-6/.local/bin/kaggle"
COMPETITION = "arc-prize-2026-arc-agi-3"
SUBMISSION_ID = 56576143
INTERVAL_SECONDS = 50


def main() -> None:
    previous = None
    polls = 0
    while True:
        result = subprocess.run(
            [CLI, "competitions", "submissions", "-c", COMPETITION, "--format", "json"],
            text=True,
            capture_output=True,
            timeout=45,
            check=False,
        )
        if result.returncode:
            print(f"CLI 查询失败 exit={result.returncode}; 稍后重试", flush=True)
            time.sleep(INTERVAL_SECONDS)
            continue
        try:
            submissions, _ = json.JSONDecoder().raw_decode(result.stdout.lstrip())
            item = next(s for s in submissions if int(s["ref"]) == SUBMISSION_ID)
        except (ValueError, KeyError, StopIteration, TypeError):
            print("CLI 未返回目标提交；稍后重试", flush=True)
            time.sleep(INTERVAL_SECONDS)
            continue

        now = dt.datetime.now(dt.timezone.utc).isoformat()
        state = item.get("status")
        raw_score = item.get("publicScore")
        score = float(raw_score) if raw_score not in (None, "") else None
        status = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
        status.update(
            submission_id=SUBMISSION_ID,
            submission_status=state,
            public_score=score,
            last_checked_at=now,
            updated_at=now,
        )
        if state == "SubmissionStatus.COMPLETE" and score is not None:
            status.update(phase="complete", blocker=None, blockers=[])
        elif state in {"SubmissionStatus.ERROR", "SubmissionStatus.FAILED", "SubmissionStatus.CANCELLED"}:
            status.update(phase="submission_failed", blocker=f"Kaggle 返回 {state}", blockers=[f"Kaggle 返回 {state}"])
        else:
            status["phase"] = "submission_pending"
        tmp = STATUS_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, STATUS_PATH)

        signature = (state, score)
        polls += 1
        if signature != previous or polls % 10 == 0:
            print(f"{now} id={SUBMISSION_ID} status={state} publicScore={score}", flush=True)
            previous = signature
        if status["phase"] in {"complete", "submission_failed"}:
            return
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
