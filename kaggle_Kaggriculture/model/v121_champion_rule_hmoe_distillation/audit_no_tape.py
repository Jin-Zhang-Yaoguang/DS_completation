#!/usr/bin/env python3
"""静态与结构化审计：serving 产物不得退化为 Replay/tape。"""

from __future__ import annotations

import ast
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODEL = HERE / "rule_hmoe_model.json"
RUNTIME = HERE / "runtime_policy.py"
SERVING = (RUNTIME, HERE / "behavior_agent.py", HERE / "rule_hmoe_agent.py")


def main() -> int:
    model = json.loads(MODEL.read_text(encoding="utf-8"))
    text = MODEL.read_text(encoding="utf-8") + "\n".join(path.read_text(encoding="utf-8") for path in SERVING)
    forbidden_tokens = ("_ACTIONS[step]", "replay_data/raw", "steps[turn + 1]", "selected_route_id")
    token_hits = [token for token in forbidden_tokens if token in text]
    for path in SERVING:
        ast.parse(path.read_text(encoding="utf-8"))
    contract = model.get("runtime_contract", {})
    violations = []
    if token_hits:
        violations.append(f"FORBIDDEN_TOKEN:{token_hits}")
    if contract.get("tape") is not False:
        violations.append("TAPE_FLAG")
    if contract.get("step_action_lookup") is not False:
        violations.append("STEP_ACTION_LOOKUP")
    if any(key in model for key in ("actions", "route_actions", "episode_actions")):
        violations.append("ACTION_ARRAY")

    def scan(value, path="root"):
        if isinstance(value, list):
            if len(value) >= 100:
                violations.append(f"LONG_SEQUENCE:{path}:{len(value)}")
            for index, item in enumerate(value):
                scan(item, f"{path}[{index}]")
        elif isinstance(value, dict):
            numeric = [str(key).isdigit() for key in value]
            if len(value) >= 100 and numeric and all(numeric):
                violations.append(f"STEP_KEYED_MAPPING:{path}:{len(value)}")
            for key, item in value.items():
                scan(item, f"{path}.{key}")

    scan(model)
    report = {
        "schema": "kaggriculture-v121-no-tape-audit-v1",
        "files": [MODEL.name, *[path.name for path in SERVING]],
        "violations": violations,
        "pass": not violations,
        "verdict": "NO_TAPE_PASS" if not violations else "NO_TAPE_FAIL",
    }
    (HERE / "no_tape_audit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
