# 综合解包:writefile / 最长b64|b85字符串 / SOURCE_BLOB 拼接 / tar
import json, ast, base64, zlib, gzip, io, tarfile, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
NAMES = ["kaggriculture-2887-score-fieldcraft-agent","the-2950-peak-farm","farmer-john-and-the-wheat-seller",
         "kaggriculture-more-wheat-smarter-sales","a-song-of-ice-and-fire-fixed-flexible","kaggriculture-auto-top1",
         "kaggriculture-master-engine-v3","kaggriculture-pipe19-sale-advance-overflow",
         "demand-preserving-turn-sale-timing","kaggriculture-autonomous-ai-farming-agent"]
def decode_any(s):
    s=s.strip()
    for dec in (base64.b64decode, base64.b85decode):
        try: raw=dec(s)
        except Exception: continue
        for f in (zlib.decompress, gzip.decompress, lambda b:b):
            try: out=f(raw)
            except Exception: continue
            if out[:11]==b"LICENSE.txt" or out[:2]==b"ma" or b"\x00" in out[:600]:
                try:
                    tf=tarfile.open(fileobj=io.BytesIO(out))
                    for n in tf.getnames():
                        if n.endswith(".py"): return tf.extractfile(n).read()
                except Exception: pass
            if b"def " in out and b"\x00" not in out[:2000]: return out
    return None
for name in NAMES:
    p=HERE/f"{name}.ipynb"
    if not p.exists(): print(name,"缺文件"); continue
    cells=json.load(open(p))["cells"]
    result=None
    # 1) writefile
    for c in cells:
        if c["cell_type"]!="code": continue
        src="".join(c["source"])
        if src.split("\n")[0].startswith("%%writefile") and "def " in src and len(src)>3000:
            body="\n".join(src.split("\n")[1:]).encode()
            if result is None or len(body)>len(result): result=body
    # 2) 字符串常量(取每个 code cell 里全部长串,含拼接)
    if result is None:
        for c in cells:
            if c["cell_type"]!="code": continue
            src="".join(c["source"])
            try: tree=ast.parse(src)
            except Exception: continue
            # SOURCE_BLOB 式拼接
            for n in ast.walk(tree):
                if isinstance(n,(ast.Tuple,ast.List)) and len(getattr(n,'elts',[]))>3:
                    parts=[e.value for e in n.elts if isinstance(e,ast.Constant) and isinstance(e.value,str)]
                    if parts and sum(map(len,parts))>50000:
                        out=decode_any("".join(parts))
                        if out and (result is None or len(out)>len(result)): result=out
                if isinstance(n,ast.Constant) and isinstance(n.value,str) and len(n.value)>50000:
                    out=decode_any(n.value)
                    if out and (result is None or len(out)>len(result)): result=out
    # 3) 裸大 code cell
    if result is None:
        for c in cells:
            if c["cell_type"]!="code": continue
            src="".join(c["source"])
            if re.search(r"def \w+\(obs", src) and len(src)>5000:
                if result is None or len(src.encode())>len(result): result=src.encode()
    if result:
        (HERE/f"{name}_main.py").write_bytes(result); print(f"{name}: {len(result)}")
    else: print(f"{name}: 失败")
