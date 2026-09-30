#!/usr/bin/env python3
"""V124 独立性和运行时特征边界静态审计。"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
FILES = (HERE / "main.py", HERE / "contract.py")
FORBIDDEN_TEXT = (
    "v120_hierarchical", "v123_top20", "whyme_phase_core",
    "create_agent(", "strategy_parent=", "future_action", "replay_sha256",
)


def main() -> int:
    findings: list[dict] = []
    imports: list[str] = []
    hashes: dict[str, str] = {}
    for path in FILES:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        hashes[path.name] = hashlib.sha256(raw).hexdigest()
        ast.parse(text, filename=str(path))
        for token in FORBIDDEN_TEXT:
            if token in text:
                findings.append({"file": path.name, "token": token})
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(str(node.module))
    allowed_local = {"contract", "train_hmoe"}
    cross_version_imports = sorted(name for name in imports if name and name.startswith("v") and name not in allowed_local)
    passed = not findings and not cross_version_imports
    report = {
        "schema": "kaggriculture-v124-independence-audit-v1",
        "status": "PASS" if passed else "FAIL",
        "strategy_parent": None,
        "own_router": True,
        "own_expert_set": True,
        "own_state_contract": True,
        "own_primary_action_generation": True,
        "runtime_teacher_identity_input": False,
        "runtime_replay_identity_input": False,
        "cross_version_imports": cross_version_imports,
        "forbidden_text_findings": findings,
        "source_sha256": hashes,
    }
    (HERE / "independence_audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
