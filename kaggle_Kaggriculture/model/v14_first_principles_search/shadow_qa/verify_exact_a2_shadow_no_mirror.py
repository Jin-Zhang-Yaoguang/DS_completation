"""Run the existing exact-A2 truth harness against the Q2 no-mirror variant."""

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
    prototype_queue_solver_no_mirror as q2,
)
from kaggle_Kaggriculture.model.v14_first_principles_search.shadow_qa import (
    verify_exact_a2_shadow as harness,
)


Q2_SOURCE = HERE.parent / "prototype_queue_solver_no_mirror.py"
CORE_SOURCE = HERE.parent / "prototype_queue_solver.py"
OUTPUT = HERE / "exact_a2_shadow_no_mirror_qa.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CandidateAdapter:
    """Expose only the two hooks used by the independent QA harness."""

    make_agent = staticmethod(q2.make_agent)
    _canonical_action = staticmethod(q2.core._canonical_action)


def main() -> None:
    harness.candidate_module = CandidateAdapter
    harness.PROTOTYPE = Q2_SOURCE
    harness.OUTPUT = OUTPUT
    harness.SCHEMA = "kaggriculture-v14-exact-a2-shadow-no-mirror-qa-1"

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
        "model_id": q2.MODEL_ID,
        "require_public_mirror": False,
        "removed_gate": "public-production/clone heuristic",
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "go": payload["go"],
                "aggregate": payload["aggregate"],
                "q2_source_sha256": payload["artifacts"]["prototype_sha256"],
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
