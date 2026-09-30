"""打包 V10：main.py + v120_core.py（V120 执行链原件）。"""
import hashlib, tarfile
from pathlib import Path
HERE = Path(__file__).resolve().parent
OUT = HERE / "submission.tar.gz"
members = [("main.py", HERE / "main.py"), ("v120_core.py", HERE / "v120_core.py")]
with tarfile.open(OUT, "w:gz") as tf:
    for arc, path in members:
        info = tf.gettarinfo(str(path), arcname=arc); info.mtime = 0; info.uid = info.gid = 0; info.uname = info.gname = ""
        with path.open("rb") as fh: tf.addfile(info, fh)
for arc, path in members:
    print(f"{arc:<16} {path.stat().st_size:>8} bytes sha256={hashlib.sha256(path.read_bytes()).hexdigest()[:16]}")
print(f"{'submission.tar.gz':<16} {OUT.stat().st_size:>8} bytes sha256={hashlib.sha256(OUT.read_bytes()).hexdigest()[:16]}")
with tarfile.open(OUT) as tf: print("members:", tf.getnames())
