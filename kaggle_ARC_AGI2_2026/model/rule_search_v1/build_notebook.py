"""把已审查的 solver.py 源码嵌入独立、离线 Kaggle Notebook。"""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).with_name("solver.py")
TARGET = ROOT / "discussion" / "rule_search_v1" / "rule_search_v1.ipynb"


def cell(source):
    digest = hashlib.sha256(source.encode()).hexdigest()[:12]
    return {"cell_type": "code", "id": digest, "execution_count": None, "metadata": {}, "outputs": [],
            "source": source.splitlines(keepends=True)}


inference = '''import json
from pathlib import Path

input_root = Path("/kaggle/input")
matches = sorted(input_root.rglob("arc-agi_test_challenges.json"))
if len(matches) != 1:
    available = [str(p) for p in input_root.rglob("*.json")][:30]
    raise FileNotFoundError(f"Expected one test challenge file, found {matches}; visible json={available}")
challenges_path = matches[0]
with challenges_path.open(encoding="utf-8") as stream:
    challenges = json.load(stream)
submission = predict(challenges)
assert set(submission) == set(challenges)
for task_id, task in challenges.items():
    assert len(submission[task_id]) == len(task["test"])
    for guesses in submission[task_id]:
        assert set(guesses) == {"attempt_1", "attempt_2"}
        assert valid(guesses["attempt_1"]) and valid(guesses["attempt_2"])
output_path = Path("/kaggle/working/submission.json")
output_path.write_text(json.dumps(submission, separators=(",", ":")), encoding="utf-8")
print(f"Generated {len(submission)} tasks at {output_path}")
'''


def main():
    source = SOURCE.read_text(encoding="utf-8")
    notebook = {"cells": [cell(source), cell(inference)],
                "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                             "language_info": {"name": "python"}},
                "nbformat": 4, "nbformat_minor": 5}
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"notebook": str(TARGET), "solver_sha256": hashlib.sha256(source.encode()).hexdigest(),
                      "notebook_sha256": hashlib.sha256(TARGET.read_bytes()).hexdigest()}, indent=2))


if __name__ == "__main__":
    main()
