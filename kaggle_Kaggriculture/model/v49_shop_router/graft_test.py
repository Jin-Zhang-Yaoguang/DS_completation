"""嫁接实验:验证 fam_F / rb7925 能否在 t=72(首店解锁)边界互接而不掉单人产出。
同时打印两带前 72 步的差异明细(判断分歧性质)。"""
import sys, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
TAPES = HERE.parent / "v16_online_fidelity" / "tapes"
import fidelity

F = json.load(open(TAPES / "fam_F_new.json"))["actions"]
R = json.load(open(TAPES / "rb_7925cb146f.json"))["actions"]

print("=== fam_F vs rb7925 前 72 步差异明细 ===")
for i in range(72):
    a, b = json.dumps(F[i], sort_keys=True), json.dumps(R[i], sort_keys=True)
    if a != b:
        print(f"t={i}\n  F: {a[:200]}\n  R: {b[:200]}")

# 生成嫁接带
CUT = 72
grafts = {
    "graft_F72_Rtail": F[:CUT] + R[CUT:],
    "graft_R72_Ftail": R[:CUT] + F[CUT:],
}
for name, acts in grafts.items():
    p = HERE / f"{name}.json"
    json.dump({"actions": acts}, p.open("w"))

print("\n=== 单人产出(vs PASS,3 seeds)===")
for name in ["fam_F_new", "rb_7925cb146f"]:
    banks = []
    for sd in (11, 22, 33):
        r = fidelity.play(f"tape:{TAPES}/{name}.json", "pass:", sd, [])
        banks.append(r["bank"][0])
    print(f"{name:22s} {[int(b) for b in banks]}")
for name in grafts:
    banks = []
    for sd in (11, 22, 33):
        r = fidelity.play(f"tape:{HERE}/{name}.json", "pass:", sd, [])
        banks.append(r["bank"][0])
    print(f"{name:22s} {[int(b) for b in banks]}")
