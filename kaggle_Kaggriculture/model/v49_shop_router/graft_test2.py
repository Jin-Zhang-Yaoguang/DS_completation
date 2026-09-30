"""嫁接验证第二批:cand_0 与变体们能否接 fam_F 前 72 步。"""
import sys, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
TAPES = HERE.parent / "v16_online_fidelity" / "tapes"
import fidelity

F = json.load(open(TAPES / "fam_F_new.json"))["actions"]
CUT = 72
for name in ["cand_0_ec979a", "famF_var_621efa65ad", "rb_var_8830803d1a"]:
    T = json.load(open(TAPES / f"{name}.json"))["actions"]
    g = F[:CUT] + T[CUT:]
    p = HERE / f"graft_F72_{name}.json"
    json.dump({"actions": g}, p.open("w"))
    orig, graft = [], []
    for sd in (11, 22, 33):
        orig.append(int(fidelity.play(f"tape:{TAPES}/{name}.json", "pass:", sd, [])["bank"][0]))
        graft.append(int(fidelity.play(f"tape:{p}", "pass:", sd, [])["bank"][0]))
    print(f"{name:24s} orig={orig} graft={graft}")
