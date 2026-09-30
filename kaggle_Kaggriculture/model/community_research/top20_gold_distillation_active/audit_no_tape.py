#!/usr/bin/env python3
"""审计 serving 路径不含 Replay 动作带或父模型包装。"""

from __future__ import annotations

import ast
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
SERVING = (HERE / "main.py", HERE / "contract_features.py")
FORBIDDEN_TEXT = ("_ACTIONS", "base64", "b85decode", "zlib.decompress", "episode_id]", "replay_sha256]")


def main() -> int:
    failures = []
    imports = []
    for path in SERVING:
        text = path.read_text(encoding="utf-8")
        ast.parse(text)
        for token in FORBIDDEN_TEXT:
            if token in text:
                failures.append(f"{path.name}: forbidden token {token}")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
    parent_imports = [name for name in imports if name.startswith("v") and name[1:2].isdigit()]
    if parent_imports:
        failures.append(f"parent model imports: {parent_imports}")
    model = json.loads((HERE / "contract_hmoe_model.json").read_text(encoding="utf-8"))
    runtime = model.get("runtime_contract", {})
    if runtime.get("tape") is not False or runtime.get("step_action_lookup") is not False:
        failures.append("model runtime contract does not reject tape")
    spatial = json.loads((HERE / "spatial_priors.json").read_text(encoding="utf-8"))
    if spatial.get("contains_action_sequence") is not False:
        failures.append("spatial prior may contain action sequence")
    result = {
        "schema": "kaggriculture-v122-no-tape-audit-v1", "pass": not failures,
        "serving_files": [path.name for path in SERVING], "parent_model_imports": parent_imports,
        "forbidden_token_hits": failures, "primary_action_source": runtime.get("primary_action_source"),
        "verdict": "PASS_INDEPENDENT_HMOE" if not failures else "FAIL",
    }
    (HERE / "no_tape_audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
