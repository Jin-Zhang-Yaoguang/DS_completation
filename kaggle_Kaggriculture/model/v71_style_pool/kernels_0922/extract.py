# 从 notebook 提取写出的 main.py 代理源码(找 %%writefile 或含 agent 函数的大 code cell)
import json, glob, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
for nb in glob.glob(str(HERE/"*.ipynb")):
    name = Path(nb).stem
    cells = json.load(open(nb))["cells"]
    best = None
    for c in cells:
        if c["cell_type"] != "code": continue
        src = "".join(c["source"])
        if "%%writefile" in src.split("\n")[0] and ("def " in src):
            body = "\n".join(src.split("\n")[1:])
            if best is None or len(body) > len(best): best = body
    if best is None:
        for c in cells:
            if c["cell_type"] != "code": continue
            src = "".join(c["source"])
            if re.search(r"def \w+\(obs", src) and len(src) > 3000:
                if best is None or len(src) > len(best): best = src
    if best:
        out = HERE/f"{name}_main.py"; out.write_text(best)
        print(f"{name}: {len(best)} chars -> {out.name}")
    else:
        print(f"{name}: 未找到代理源码")
