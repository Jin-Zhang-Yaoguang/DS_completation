"""本地公开集验证与 submission.json 生成。"""

import argparse
import hashlib
import json
from pathlib import Path

from solver import predict, valid


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(challenges, submission):
    if set(challenges) != set(submission):
        raise ValueError("task ID 集合不一致")
    for task_id, task in challenges.items():
        outputs = submission[task_id]
        if len(outputs) != len(task["test"]):
            raise ValueError(f"{task_id}: test 数量不一致")
        for row in outputs:
            if set(row) != {"attempt_1", "attempt_2"} or not all(valid(value) for value in row.values()):
                raise ValueError(f"{task_id}: attempt 格式或网格非法")


def score(submission, solutions):
    total = correct = 0
    for task_id, targets in solutions.items():
        for pred, target in zip(submission[task_id], targets):
            total += 1
            correct += int(target == pred["attempt_1"] or target == pred["attempt_2"])
    return {"correct": correct, "total": total, "accuracy": correct / total if total else None}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--challenges", required=True)
    parser.add_argument("--solutions")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    challenges = load(args.challenges)
    submission = predict(challenges)
    validate(challenges, submission)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(submission, separators=(",", ":")), encoding="utf-8")
    summary = {"tasks": len(challenges), "test_outputs": sum(len(t["test"]) for t in challenges.values()),
               "submission_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
               "challenges_sha256": hashlib.sha256(Path(args.challenges).read_bytes()).hexdigest()}
    if args.solutions:
        summary.update(score(submission, load(args.solutions)))
        summary["solutions_sha256"] = hashlib.sha256(Path(args.solutions).read_bytes()).hexdigest()
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
