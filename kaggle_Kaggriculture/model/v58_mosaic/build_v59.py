"""v59 组装:v58_main.py(已含 T0 马赛克)+ 注入 T1..T4 马赛克 schedule。
产出 scratchpad/v59_main.py。
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRATCH = Path("/private/tmp/claude-501/-Users-a1-6-Desktop-PycharmProjects-DS-completation--claude-worktrees-trusting-carson-f2e0f9/59979e26-3970-412a-b349-4361ccd0c249/scratchpad")

src = (SCRATCH / "v58_main.py").read_text()
anchor = "SCHEDULES[0] = _j.loads(_MOSAIC_T0)"
assert anchor in src
inject = [anchor]
for i in range(1, 5):
    p = HERE / f"mosaic_t{i}.json"
    acts = json.load(open(p))["actions"]
    s = json.dumps(json.dumps(acts, separators=(",", ":")))
    inject.append(f"_MOSAIC_T{i} = {s}")
    inject.append(f"SCHEDULES[{i}] = _j.loads(_MOSAIC_T{i})")
out = src.replace(anchor, "\n".join(inject))
(SCRATCH / "v59_main.py").write_text(out)
print("v59_main.py written,", len(out), "bytes")
