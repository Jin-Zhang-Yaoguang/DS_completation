import sys, json
from pathlib import Path
MODEL = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODEL / "v16_online_fidelity")); sys.path.insert(0, str(MODEL / "v4_demand_race" / "harness"))
import fidelity
opp = "tape:" + str(MODEL / "opponent_pool_v1/tapes/ymg_slice0.json")
for label, pack in [("parent", "y68f_parent.py"), ("beat0", "cands/mj_e161725f7a.py"), ("beat1", "cands/mj_d7c68d9250.py")]:
    r = fidelity.play("sub:" + str(Path(pack).resolve()), opp, 1009, [])
    print(f"== {label} bank {r['bank'][0]:.0f} vs {r['bank'][1]:.0f} zero_sell_steps(me) {r['zero_sell_steps'][0]}")
    print("   prod:", {k: v for k, v in sorted(r['prod'][0].items())})
    print("   money every 3 days:", r["money_by_day"][0][::3])
