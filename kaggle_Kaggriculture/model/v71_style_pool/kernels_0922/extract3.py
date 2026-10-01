import json, ast, base64, zlib, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
for name in ["kaggriculture-v55-one-turn-market-race-edge","kaggriculture-v56-smarter-seeds-and-fertilizer"]:
    cells=json.load(open(HERE/f"{name}.ipynb"))["cells"]
    src="".join(cells[2]["source"])
    tree=ast.parse(src)
    blob=None; sha=None
    for n in ast.walk(tree):
        if isinstance(n, ast.Assign) and getattr(n.targets[0],'id','')=="SOURCE_BLOB":
            parts=[c.value for c in ast.walk(n.value) if isinstance(c,ast.Constant) and isinstance(c.value,str)]
            blob="".join(p for p in parts if len(p)>10)
        if isinstance(n, ast.Assign) and getattr(n.targets[0],'id','')=="EXPECTED_MAIN_SHA256":
            sha=n.value.value
    out=zlib.decompress(base64.b85decode(blob))
    got=hashlib.sha256(out).hexdigest()
    p=HERE/f"{name}_main.py"; p.write_bytes(out)
    print(name, len(out), "sha_ok" if got==sha else f"SHA不符 {got[:12]} vs {sha[:12]}")
