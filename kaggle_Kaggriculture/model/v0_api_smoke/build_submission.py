"""Build and verify a deterministic Kaggriculture submission archive."""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path


SCHEME_DIR = Path(__file__).resolve().parent
SOURCE = SCHEME_DIR / "main.py"
OUTPUT = SCHEME_DIR / "submission.tar.gz"


def build():
    source_bytes = SOURCE.read_bytes()
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w", format=tarfile.GNU_FORMAT) as archive:
        info = tarfile.TarInfo("main.py")
        info.size = len(source_bytes)
        info.mode = 0o644
        info.mtime = 0
        info.uid = 0
        info.gid = 0
        info.uname = ""
        info.gname = ""
        archive.addfile(info, io.BytesIO(source_bytes))

    with OUTPUT.open("wb") as raw_file:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            compresslevel=9,
            fileobj=raw_file,
            mtime=0,
        ) as compressed:
            compressed.write(tar_buffer.getvalue())

    with tarfile.open(OUTPUT, "r:gz") as archive:
        members = archive.getmembers()
        assert [member.name for member in members] == ["main.py"]
        assert members[0].isfile() and not members[0].issym() and not members[0].islnk()
        packaged = archive.extractfile(members[0])
        assert packaged is not None and packaged.read() == source_bytes

    return {
        "archive": str(OUTPUT),
        "members": ["main.py"],
        "bytes": OUTPUT.stat().st_size,
        "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
