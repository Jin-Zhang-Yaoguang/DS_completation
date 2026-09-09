"""打包 V1 baseline：归档根目录只放 main.py，并输出校验信息。"""
import hashlib, tarfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = HERE / "main.py"
ARCHIVE = HERE / "submission.tar.gz"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    src_sha = sha256(MAIN)
    with tarfile.open(ARCHIVE, "w:gz") as tf:
        info = tf.gettarinfo(str(MAIN), arcname="main.py")
        info.mtime = 0
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        with MAIN.open("rb") as fh:
            tf.addfile(info, fh)
    print(f"main.py      {MAIN.stat().st_size} bytes  sha256={src_sha}")
    print(f"submission   {ARCHIVE.stat().st_size} bytes  sha256={sha256(ARCHIVE)}")
    with tarfile.open(ARCHIVE) as tf:
        names = tf.getnames()
    print("archive members:", names)
    assert names == ["main.py"], "归档根目录必须且只能有 main.py"
    print("built at", time.strftime("%Y-%m-%d %H:%M:%S"))


if __name__ == "__main__":
    main()
