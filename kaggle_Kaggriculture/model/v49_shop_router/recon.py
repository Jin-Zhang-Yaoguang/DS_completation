"""侦察:①obs 中商店字段结构与解锁时刻;②带库各带与 fam_F 的逐 turn 分歧点。"""
import sys, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "v4_demand_race" / "harness"))
sys.path.insert(0, str(HERE.parent / "v16_online_fidelity"))
import engine

TAPES = HERE.parent / "v16_online_fidelity" / "tapes"


def probe_shops(seed):
    """跑一局 PASS vs PASS,记录商店解锁时间线与 obs 结构。"""
    k = engine.load_kagsim()
    g = k.Game(seed=seed)
    seen = {}
    obs_keys_printed = False
    for step in range(720):
        obs = g.observe(0)
        if not obs_keys_printed:
            print("obs keys:", sorted(obs.keys()))
            for key in ("town", "market", "shops"):
                if key in obs:
                    v = obs[key]
                    print(f"  obs[{key!r}]:", json.dumps(v)[:400] if not isinstance(v, (int, float)) else v)
            obs_keys_printed = True
        # 寻找商店列表字段
        town = obs.get("town") or {}
        shops = town.get("unlocked_shops") if isinstance(town, dict) else None
        if shops is None:
            shops = obs.get("shops")
        if shops:
            names = [s if isinstance(s, str) else s.get("name", str(s)) for s in shops]
            for n in names:
                if n not in seen:
                    seen[n] = step
        g.step({"farmer": ["PASS"], "hands": [], "market": []},
               {"farmer": ["PASS"], "hands": [], "market": []})
    print(f"seed={seed} shop unlock timeline: {sorted(seen.items(), key=lambda x: x[1])}")


def tape_actions(name):
    d = json.load(open(TAPES / name))
    return d["actions"]


def divergence():
    base = tape_actions("fam_F_new.json")
    for name in ["rb_7925cb146f.json", "cand_0_ec979a.json", "cand_1_bf2b55.json",
                 "cand_2_c333c1.json", "famF_var_382c261c39.json", "famF_var_5af1d02af0.json",
                 "famF_var_621efa65ad.json", "rb_var_4581c03056.json", "rb_var_8830803d1a.json",
                 "top_keiz_82acad.json", "tape_Crop_Dusta_104547425.json", "tape_OceanMix_104547425.json"]:
        try:
            other = tape_actions(name)
        except Exception as e:
            print(f"{name}: ERR {e}")
            continue
        n = min(len(base), len(other))
        div = None
        ndiff = 0
        for i in range(n):
            if json.dumps(base[i], sort_keys=True) != json.dumps(other[i], sort_keys=True):
                if div is None:
                    div = i
                ndiff += 1
        print(f"{name:32s} first_div={div} ndiff={ndiff}/{n}")


if __name__ == "__main__":
    for sd in (42, 7, 123):
        probe_shops(sd)
    print("--- divergence vs fam_F_new ---")
    divergence()
