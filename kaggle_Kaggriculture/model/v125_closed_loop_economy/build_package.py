"""构建单文件研究包，并用已保存动作轨迹验证原始加载器行为；不提交。"""
from __future__ import annotations

import argparse
import ast
import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tarfile
from datetime import datetime, timezone


HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def package_source(source):
    tree = ast.parse(source)
    entries = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "agent"]
    if len(entries) != 1:
        raise ValueError("必须恰有一个agent入口")
    # 官方raw loader按全局插入顺序选最后一个callable；只移动定义顺序，不改函数行为。
    entry = entries[0]
    tree.body.remove(entry)
    tree.body.append(entry)
    packed = ast.unparse(tree) + "\n"
    old = {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(source).body
           if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    new = {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(packed).body
           if isinstance(n, (ast.FunctionDef, ast.ClassDef))}
    if old != new:
        raise RuntimeError("函数/类AST发生变化，不能宣称只移动入口")
    return packed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--game-index", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source = args.candidate.resolve()
    output = args.output.resolve()
    if not output.is_relative_to(HERE / "packages"):
        raise ValueError("输出必须位于V125 packages目录")
    if output.exists():
        raise FileExistsError("拒绝覆盖已有包")
    manifest = json.loads((args.run_dir / "run_manifest.json").read_text())
    row = json.loads((args.run_dir / "games.jsonl").read_text().splitlines()[args.game_index])
    raw = source.read_bytes()
    assert sha(raw) == manifest["candidate"]["entry_sha256"]
    assert row["status"] == "DONE" and row["calls"] == 719
    trace_path = Path(row["trace"]["path"])
    assert sha(trace_path.read_bytes()) == row["trace"]["sha256"]
    trace = json.loads(gzip.decompress(trace_path.read_bytes()))
    harness = Path(manifest["harness"]["path"])
    assert sha(harness.read_bytes()) == manifest["harness"]["sha256"]
    h = load_module(harness, "v125_package_verifier")
    make, rules, fast, engine = h.import_engines()
    assert engine["composite_sha256"] == manifest["engine"]["composite_sha256"]
    for path, fingerprint in manifest["candidate"]["files"].items():
        assert sha(Path(path).read_bytes()) == fingerprint
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        from kaggle_environments.agent import get_last_callable
        original_raw_name = get_last_callable(raw.decode(), path=str(source)).__name__
        packed = package_source(raw.decode())
        callback = get_last_callable(packed, path="main.py")
    assert callback.__name__ == "agent", callback.__name__
    original = load_module(source, "v125_package_original")
    game = fast.Game(trace["seed"])
    seat = trace["candidate_seat"]
    matches = 0
    for step, recorded in enumerate(trace["actions"]):
        observation = game.observe(seat)
        assert observation["step"] == step
        expected = original.agent(observation, {})
        got = callback(observation, {})
        if expected != got or expected != recorded[seat]:
            raise RuntimeError(f"动作不一致：step={step}")
        matches += 1
        game.step(recorded[0], recorded[1])
    assert game.done and matches == 719
    assert [game.reward(0), game.reward(1)] == row["rewards"]
    output.mkdir(parents=True)
    data = packed.encode()
    (output / "main.py").write_bytes(data)
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as tar:
        info = tarfile.TarInfo("main.py")
        info.size, info.mode, info.mtime = len(data), 0o644, 0
        tar.addfile(info, io.BytesIO(data))
    archive = gzip.compress(stream.getvalue(), mtime=0)
    (output / "submission.tar.gz").write_bytes(archive)
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
        assert tar.getnames() == ["main.py"]
        assert tar.extractfile("main.py").read() == data
    receipt = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PACKAGE_ENGINEERING_QA_ONLY_NOT_RELEASE_ELIGIBLE",
        "candidate_id": getattr(original, "CANDIDATE_ID", None),
        "source_sha256": sha(raw), "package_main_sha256": sha(data),
        "archive_sha256": sha(archive), "builder_sha256": sha(Path(__file__).read_bytes()),
        "original_raw_loader_selected": original_raw_name,
        "package_raw_loader_selected": callback.__name__,
        "function_asts_unchanged": True, "action_parity_steps": matches,
        "parity_trace_sha256": row["trace"]["sha256"], "candidate_seat": seat,
        "same_saved_trace_no_new_strength_game": True,
        "kaggle_submitted": False, "gold_status": "NOT_GOLD",
        "limits": "仅验证本条已见完整轨迹的包行为；完整双席/多种子/G1-G5资格仍需分别通过。",
    }
    (output / "package_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
