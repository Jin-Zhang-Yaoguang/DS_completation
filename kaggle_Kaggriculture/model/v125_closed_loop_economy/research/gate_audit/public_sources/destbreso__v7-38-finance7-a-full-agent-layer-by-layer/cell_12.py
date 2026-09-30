import tarfile

# main.py must sit at the ROOT of the archive, and the archive must be a plain
# gzip tar. Kaggle rejects an archive with extended headers, and the CLI reports
# only "400 Bad Request" while the API body says why, so build it with tarfile
# and normalised headers rather than with the system tar.
out = WORK / "submission.tar.gz"
with tarfile.open(out, "w:gz", format=tarfile.GNU_FORMAT) as t:
    for name in ("main.py", LIB):
        p = WORK / name
        ti = tarfile.TarInfo(name)
        ti.size, ti.mtime, ti.mode = p.stat().st_size, 0, 0o644
        ti.uid = ti.gid = 0
        ti.uname = ti.gname = ""
        with p.open("rb") as fh:
            t.addfile(ti, fh)

print(f"{out}  {out.stat().st_size:,} bytes")
with tarfile.open(out) as t:
    for m in t.getmembers():
        print(f"  {m.name:<10} {m.size:>9,} bytes")
