"""Final 4314-call exact-A2 truth QA for the Q2b conservative variant."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[3]
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from kaggle_Kaggriculture.model.v14_first_principles_search import (
    prototype_queue_solver_no_mirror as q2b,
)
from kaggle_Kaggriculture.model.v14_first_principles_search.shadow_qa import (
    verify_exact_a2_shadow as harness,
)


Q2B_SOURCE = HERE.parent / "prototype_queue_solver_no_mirror.py"
CORE_SOURCE = HERE.parent / "prototype_queue_solver.py"
OUTPUT = HERE / "exact_a2_shadow_q2b_qa.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CandidateAdapter:
    make_agent = staticmethod(q2b.make_agent)
    _canonical_action = staticmethod(q2b.core._canonical_action)


def main() -> None:
    harness.candidate_module = CandidateAdapter
    harness.PROTOTYPE = Q2B_SOURCE
    harness.OUTPUT = OUTPUT
    harness.SCHEMA = "kaggriculture-v14-exact-a2-shadow-q2b-qa-1"

    exit_code = 0
    try:
        harness.main()
    except SystemExit as exc:
        exit_code = int(exc.code or 0)

    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    payload["artifacts"].update(
        {
            "qa_driver_path": str(Path(__file__).resolve()),
            "qa_driver_sha256": _sha256(Path(__file__).resolve()),
            "stateful_core_path": str(CORE_SOURCE),
            "stateful_core_sha256": _sha256(CORE_SOURCE),
        }
    )
    payload["variant"] = {
        "label": "Q2b",
        "model_id": q2b.MODEL_ID,
        "require_public_mirror": False,
        "max_clone_distance": 4,
        "removed_gate": "full public-production equality",
        "retained_gate": "clone_distance<=4",
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "go": payload["go"],
                "aggregate": payload["aggregate"],
                "q2b_source_sha256": payload["artifacts"]["prototype_sha256"],
                "stateful_core_sha256": payload["artifacts"]["stateful_core_sha256"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if exit_code or not payload["go"]:
        raise SystemExit(exit_code or 1)


if __name__ == "__main__":
    main()
