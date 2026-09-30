"""V26：V120 执行核 + fam_F 顶配母带（198k）+ V17 护栏/扰动 + V24 fill + V25 做市。"""
import json, zlib, base64, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
M = HERE.parent
V120 = (M / "v120_hierarchical_top5_distillation" / "main.py").read_text()
FTAPE = json.load(open(M / "v16_online_fidelity" / "tapes" / "fam_F_new.json"))["actions"]
V19B = (M / "v19_v10_guard" / "build_submission.py").read_text()
V24B = (M / "v24_hybrid" / "build.py").read_text()
V25B = (M / "v25_market_maker" / "build.py").read_text()

# 1) tape 替换段
blob = base64.b85encode(zlib.compress(json.dumps(FTAPE).encode())).decode()
tape_swap = f'''

# ==================== V26: swap skeleton tape to fam_F (198k) ====================
_F_ACTIONS = json.loads(zlib.decompress(base64.b85decode("{blob}")).decode())
_LOW_ROUTE_ACTIONS = _F_ACTIONS
_HIGH_ROUTE_ACTIONS = _F_ACTIONS
_ACTIONS = _F_ACTIONS
'''

# 2) V17 GUARD 段（护栏+扰动）：从 v19 build 里抠 GUARD 文本
g0 = V19B.index("GUARD = '''"); g1 = V19B.index("'''", g0 + 12)
guard = V19B[g0 + len("GUARD = '''"):g1]
guard = guard.replace("__ATTACK__", "True").replace("__LEAD__", "False")

# 3) V24 fill 段
e0 = V24B.index("EXTRA = '''"); e1 = V24B.index("'''", e0 + 12)
fill = V24B[e0 + len("EXTRA = '''"):e1].replace("__W13__", "False")

# 4) V25 MM 段
m0 = V25B.index("EXTRA = '''"); m1 = V25B.index("'''\n", m0 + 12)
mm = V25B[m0 + len("EXTRA = '''"):m1]

out = V120 + tape_swap + guard + fill + mm
(HERE / "main.py").write_text(out)
print("main.py:", len(out), "bytes")
