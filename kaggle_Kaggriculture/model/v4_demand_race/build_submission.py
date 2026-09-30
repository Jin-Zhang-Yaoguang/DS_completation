"""打包 V4：归档根目录只有 main.py；输出哈希。"""
import hashlib, tarfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = HERE / "main.py"
ARCHIVE = HERE / "submission.tar.gz"


def sha256(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    with tarfile.open(ARCHIVE, "w:gz") as tf:
        info = tf.gettarinfo(str(MAIN), arcname="main.py")
        info.mtime = 0
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        with MAIN.open("rb") as fh:
            tf.addfile(info, fh)
    print(f"main.py    {MAIN.stat().st_size} bytes sha256={sha256(MAIN)}")
    print(f"archive    {ARCHIVE.stat().st_size} bytes sha256={sha256(ARCHIVE)}")
    with tarfile.open(ARCHIVE) as tf:
        assert tf.getnames() == ["main.py"]
    print("built", time.strftime("%F %T"))


if __name__ == "__main__":
    main()
