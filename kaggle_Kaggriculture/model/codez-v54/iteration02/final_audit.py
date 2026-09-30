"""Read back qualified artifacts and freeze a separate second-round manifest."""
import hashlib
import json
import tarfile
from pathlib import Path

P = Path(__file__).resolve().parent
ROOT = P.parent


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024), b""): h.update(chunk)
    return h.hexdigest()


def main(version="v021"):
    q = json.loads((P/f"qualification_{version}.json").read_text())
    decision = json.loads((ROOT/f"versions/{version}/decision.json").read_text())
    registry = json.loads((ROOT/"registry.json").read_text())
    assert q["qualification"] and registry["latest_candidate"] == version
    assert q["online_submission"] is None and registry["online_submission"] is None
    source = ROOT/f"versions/{version}/main.py"
    package = ROOT/f"versions/{version}/submission.tar.gz"
    assert sha(source) == q["source_sha256"] == decision["source_sha256"]
    assert sha(package) == decision["package_sha256"]
    assert sha(P/f"qualification_{version}.json") == decision["qualification_sha256"]
    with tarfile.open(package) as tar:
        assert tar.getnames() == ["main.py", "NOTICE.txt"]
        assert hashlib.sha256(tar.extractfile("main.py").read()).hexdigest() == sha(source)
    assert sha(ROOT/"versions/v000/main.py") == "5fbb75c9c40e6d9e26d95272ace47329b1ca319b3b2118232404de30806e7e9c"
    assert sha(ROOT/"versions/v002/main.py") == "b06870d3f16cd2c1780ad8737dd2682bc859bb92183eb49ee8a1d2be024852d6"
    assert sha(ROOT/"versions/v002/submission.tar.gz") == "2776d8eec2eb4cd496dd7b37aeb62a76923a92aaa7031ad490e53739671bf7ea"
    checked = 0
    for manifest in sorted((ROOT/"runs").glob("*.json")) + sorted(P.glob("*.json")):
        data = json.loads(manifest.read_text())
        if not isinstance(data, dict) or "hashes" not in data: continue
        for relative, digest in data["hashes"].items():
            assert sha(ROOT/relative) == digest, (manifest.name, relative)
            checked += 1
    report = {"status": "ok", "candidate": version, "frozen_input_hash_checks": checked,
        "source_sha256": sha(source), "package_sha256": sha(package),
        "original_v000_and_v002_preserved": True, "online_submission": None}
    (P/"final_artifact_audit.json").write_text(json.dumps(report, indent=2))
    dest = P/"artifact_manifest_final.json"
    assert not dest.exists()
    files = [f for f in ROOT.rglob("*") if f.is_file() and f != dest and "__pycache__" not in f.parts and f.suffix != ".pyc"]
    data = {"scope": "Second-round snapshot; original root artifact_manifest.json remains the historical first-round snapshot.", "files": {str(f.relative_to(ROOT)): {"sha256": sha(f), "bytes": f.stat().st_size} for f in sorted(files)}}
    dest.write_text(json.dumps(data, indent=2))
    assert json.loads(dest.read_text()) == data
    print(json.dumps(dict(report, artifact_count=len(files), artifact_manifest_sha256=sha(dest)), indent=2))


if __name__ == "__main__": main()
