"""从 pub0925/*.json notebook 中抽取 %%writefile 目标文件 → pub0925/<name>/..."""
import json, re, sys
from pathlib import Path
D=Path(__file__).resolve().parent/"agents"/"pub0929"
for f in sorted(D.glob("*.json")):
    nb=json.loads(json.load(open(f))["blob"]["source"]); out=D/f.stem; out.mkdir(exist_ok=True)
    tg=[]
    for c in nb["cells"]:
        if c["cell_type"]!="code": continue
        src="".join(c["source"]) if isinstance(c["source"],list) else c["source"]
        m=re.match(r"\s*%%writefile\s+(-a\s+)?(\S+)",src)
        if m:
            name=Path(m.group(2)).name; body=src.split("\n",1)[1] if "\n" in src else ""
            mode="a" if m.group(1) else "w"
            with open(out/name,mode) as w: w.write(body)
            tg.append(name)
    print(f.stem[:55], "→", sorted(set(tg)) or "无writefile", len(nb["cells"]))
