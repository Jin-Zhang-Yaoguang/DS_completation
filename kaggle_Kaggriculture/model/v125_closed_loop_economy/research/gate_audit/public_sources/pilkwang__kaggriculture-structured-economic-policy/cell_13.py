import gzip
import hashlib
import io
import tarfile

payload = MAIN_PATH.read_bytes()
raw = io.BytesIO()
with gzip.GzipFile(
    fileobj=raw,
    mode="wb",
    filename="",
    mtime=0,
) as zipped:
    with tarfile.open(fileobj=zipped, mode="w") as archive:
        info = tarfile.TarInfo("main.py")
        info.size = len(payload)
        info.mode = 0o644
        info.mtime = 0
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        archive.addfile(info, io.BytesIO(payload))

archive_path = WORK_DIR / "submission.tar.gz"
archive_path.write_bytes(raw.getvalue())
with tarfile.open(archive_path, "r:gz") as archive:
    assert archive.getnames() == ["main.py"]
    assert archive.extractfile("main.py").read() == payload

print(
    {
        "archive": archive_path.name,
        "main_sha256": hashlib.sha256(payload).hexdigest(),
        "archive_sha256": hashlib.sha256(
            archive_path.read_bytes()
        ).hexdigest(),
    }
)
