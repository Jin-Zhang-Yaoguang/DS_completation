# 拼装 busyaprime 两个 V54 fork
import hashlib, json
from pathlib import Path
HERE=Path(__file__).resolve().parent
v54=(HERE.parent/"agents"/"v54_main.py").read_bytes()
assert hashlib.sha256(v54).hexdigest()=="5fbb75c9c40e6d9e26d95272ace47329b1ca319b3b2118232404de30806e7e9c"
# fork1: race window
L1=b"""

# busyaprime fork of V54, 2026-09-21. Apache-2.0 like everything above.
# The RACE layer (from Thomas Tschinkel's v9) pre-sells a planned lot when the tape plans it within V9_RACE_DEFAULT
# turns (40), and stretches that to V9_RACE_MAX (48) when it sees the rival sell ahead of it. The fork starts at 72.
# The cap of 96 never binds: the stretch is the rival's lead plus 12, and the layer searches 30 turns for a lead.
V9_RACE_DEFAULT = 72
V9_RACE_MAX = 96
"""
(HERE/"busya_race_main.py").write_bytes(v54+L1)
# fork2: seed float(from notebook cell 源码字面量)
import ast
cells=json.load(open(HERE/"92-vs-the-best-public-farm-a-seed-leak-in-v54.ipynb"))["cells"]
src=next("".join(c["source"]) for c in cells if "LAYER_SEED_FLOAT" in "".join(c["source"]))
tree=ast.parse(src); g={}
for n in tree.body:
    if isinstance(n,ast.Assign) and getattr(n.targets[0],'id','') in ("LAYER_SEED_FLOAT","LAYER_FERT_DAY29"):
        g[n.targets[0].id]=n.value.value
main=v54+b"\n\n"+g["LAYER_SEED_FLOAT"].encode()+b"\n\n"+g["LAYER_FERT_DAY29"].encode()
print("seedfloat sha:", hashlib.sha256(main).hexdigest()[:16], "expect 562f34ad0ba7824b")
(HERE/"busya_seedfloat_main.py").write_bytes(main)
print("forks ok")
