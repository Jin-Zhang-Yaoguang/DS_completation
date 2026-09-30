"""Build and verify the deterministic multi-file v3 submission archive."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
MEMBERS = ("main.py", "base_agent.py", "policy_weights.npz")
OUTPUT = HERE / "submission.tar.gz"


def build(output=OUTPUT, weights=None):
    output = Path(output)
    sources = {
        "main.py": HERE / "main.py",
        "base_agent.py": HERE / "base_agent.py",
        "policy_weights.npz": Path(weights) if weights is not None else HERE / "policy_weights.npz",
    }
    missing = [name for name, path in sources.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"missing submission members: {missing}")

    payloads = {name: path.read_bytes() for name, path in sources.items()}
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.GNU_FORMAT) as archive:
        for name in MEMBERS:
            info = tarfile.TarInfo(name)
            info.size = len(payloads[name])
            info.mode = 0o644
            info.mtime = info.uid = info.gid = 0
            info.uname = info.gname = ""
            archive.addfile(info, io.BytesIO(payloads[name]))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", compresslevel=9, fileobj=raw, mtime=0) as compressed:
            compressed.write(tar_buffer.getvalue())

    with tarfile.open(output, "r:gz") as archive:
        assert tuple(archive.getnames()) == MEMBERS
        for member in archive.getmembers():
            assert member.isfile() and not member.issym() and not member.islnk()
            extracted = archive.extractfile(member)
            assert extracted is not None and extracted.read() == payloads[member.name]
    return {
        "archive": str(output),
        "members": list(MEMBERS),
        "bytes": output.stat().st_size,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "member_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()},
    }


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
