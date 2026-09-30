"""把合格变体带打进 v41 骨架，产出待提交包。用法：python3 pack_variant.py <变体.json>"""
import base64
import json
import re
import subprocess
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
var_fn = Path(sys.argv[1])
d = json.load(open(var_fn))
acts, h = d["actions"], d["hash"]
skel = (HERE / "main.py").read_text()
m = re.search(r'(_ACTIONS = json\.loads\(zlib\.decompress\(base64\.b85decode\(")([^"]+)("\)\)\.decode\(\)\))', skel)
blob = base64.b85encode(zlib.compress(json.dumps(acts).encode())).decode()
out_dir = HERE / f"variant_{h}"
out_dir.mkdir(exist_ok=True)
(out_dir / "main.py").write_text(skel[:m.start(2)] + blob + skel[m.end(2):])
subprocess.run(["tar", "-czf", str(out_dir / "submission.tar.gz"), "-C", str(out_dir), "main.py"], check=True)
# 终验：sub: 口径产出指纹
r = subprocess.run([sys.executable, "sweep_seeds.py", f"sub:{out_dir}/main.py", "101"],
                   cwd=HERE.parent / "v16_online_fidelity", capture_output=True, text=True, timeout=1800)
print(r.stdout.strip())
print(f"包就绪: {out_dir}/submission.tar.gz （sub: 口径 bank 应 >=197,000 方可提交）")
