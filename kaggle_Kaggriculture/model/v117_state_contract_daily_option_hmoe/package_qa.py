#!/usr/bin/env python3
"""验证当前模块化 archive 的安全形状、文件哈希和包内外动作/收益一致。"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
MODEL = HERE.parent
CPPSIM = (MODEL / "community_research" / "2026-08-26" / "live_cli" /
          "external_repos" / "kaggriculture-cppsim")
ARCHIVE = HERE / "submission.tar.gz"
MANIFEST = HERE / "submission_manifest.json"
RESULTS = HERE / "package_qa_results.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def engine() -> Any:
    builds = sorted((CPPSIM / "build").glob("lib.*"))
    sys.path.insert(0, str(builds[-1]))
    import kagsim  # type: ignore
    return kagsim


def run_episode(kagsim: Any, module: Any, seed: int, seat: int) -> dict[str, Any]:
    game = kagsim.Game(seed)
    policy = module.V117Policy()
    actions: list[Any] = []
    calls = 0
    while not game.done:
        observation = game.observe(seat)
        action = policy.act(observation)
        actions.append(action)
        pair = [{}, {}]
        pair[seat] = action
        game.step(pair[0], pair[1])
        calls += 1
    return {"actions": actions, "calls": calls, "reward": float(game.reward(seat))}


def main() -> int:
    kagsim = engine()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected = list(manifest["archive_members"])
    with tarfile.open(ARCHIVE, "r:gz") as archive:
        members = archive.getnames()
        safe = members == expected and all(not name.startswith(("/", "../")) and "/../" not in name for name in members)
        with tempfile.TemporaryDirectory(prefix="v117-r1-package-qa-") as tmp:
            archive.extractall(tmp, filter="data")
            package_root = Path(tmp)
            source_hashes = dict(manifest["source_sha256"])
            hashes_equal = all(sha256(HERE / name) == sha256(package_root / name) == source_hashes[name]
                               for name in expected)
            source_module = load(HERE / "main.py", "v117_r1_qa_source")
            tasks = [(seed, seat) for seed in (117501, 117502) for seat in (0, 1)]
            source_runs = {(seed, seat): run_episode(kagsim, source_module, seed, seat)
                           for seed, seat in tasks}
            runtime_modules = ("schema", "contracts", "state_ledger", "experts", "router",
                               "executor", "market", "safety", "diagnostics")
            for module_name in list(sys.modules):
                if any(module_name == prefix or module_name.startswith(prefix + ".") for prefix in runtime_modules):
                    sys.modules.pop(module_name, None)
            package_module = load(package_root / "main.py", "v117_r1_qa_package")
            rows = []
            for seed, seat in tasks:
                source = source_runs[(seed, seat)]
                package = run_episode(kagsim, package_module, seed, seat)
                rows.append({
                    "seed": seed, "seat": seat, "calls": source["calls"],
                    "reward": source["reward"], "actions_equal": source["actions"] == package["actions"],
                    "reward_equal": source["reward"] == package["reward"], "package_calls": package["calls"],
                })
            checks = {
                "engine_1_32_7": str(kagsim.ENGINE_VERSION) == "1.32.7",
                "archive_members_exact": safe, "all_runtime_hashes_equal": hashes_equal,
                "all_719_calls": all(row["calls"] == row["package_calls"] == 719 for row in rows),
                "all_actions_equal": all(row["actions_equal"] for row in rows),
                "all_rewards_equal": all(row["reward_equal"] for row in rows),
            }
    payload = {
        "schema": "v117-r2.1-package-qa-v1",
        "archive_sha256": sha256(ARCHIVE), "members": members, "checks": checks,
        "rows": rows, "pass": all(checks.values()),
    }
    RESULTS.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
