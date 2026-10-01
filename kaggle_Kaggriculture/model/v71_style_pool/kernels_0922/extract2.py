# 通用解包:找最长字符串字面量,尝试 base64/zlib/gzip 解码链
import json, ast, base64, zlib, gzip
from pathlib import Path
HERE = Path(__file__).resolve().parent
def longest_str(src):
    best=""
    try: tree=ast.parse(src)
    except Exception: return best
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value,str) and len(n.value)>len(best): best=n.value
    return best
def try_decode(s):
    try: raw=base64.b64decode(s)
    except Exception: return None
    for f in (zlib.decompress, gzip.decompress, lambda b:b):
        try:
            out=f(raw)
            if b"def " in out[:200000] or b"import" in out[:1000]: return out
        except Exception: pass
    return None
for name in ["kaggriculture-v55-one-turn-market-race-edge","kaggriculture-v56-smarter-seeds-and-fertilizer","kaggriculture-top-2-master-engine-v4","kaggriculture-multi-route-farming-agent","the-metav4-farm-submission-v13"]:
    cells=json.load(open(HERE/f"{name}.ipynb"))["cells"]
    big=max(("".join(c["source"]) for c in cells if c["cell_type"]=="code"), key=len)
    s=longest_str(big)
    out=try_decode(s.strip())
    if out:
        p=HERE/f"{name}_main.py"; p.write_bytes(out)
        print(f"{name}: 解包 {len(out)} bytes")
    else:
        print(f"{name}: 解包失败 (最长串 {len(s)})")
